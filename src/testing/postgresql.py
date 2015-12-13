# -*- coding: utf-8 -*-
#  Copyright 2013 Takeshi KOMIYA
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import sys
import socket
import pg8000
import subprocess
from glob import glob
from time import sleep
from shutil import copytree
from datetime import datetime
from contextlib import closing

from testing.common.database import Database


__all__ = ['Postgresql', 'skipIfNotFound']

SEARCH_PATHS = (['/usr/local/pgsql', '/usr/local'] +
                glob('/usr/lib/postgresql/*') +  # for Debian/Ubuntu
                glob('/opt/local/lib/postgresql*'))  # for MacPorts


class PostgresqlFactory(object):
    def __init__(self, **kwargs):
        self.cache = None
        self.settings = kwargs

        init_handler = self.settings.pop('on_initialized', None)
        if self.settings.pop('cache_initialized_db', None):
            if init_handler:
                try:
                    self.cache = Postgresql()
                    init_handler(self.cache)
                except:
                    self.cache.stop()
                    raise
                finally:
                    self.cache.terminate()
            else:
                self.cache = Postgresql(auto_start=0)
                self.cache.setup()
            self.settings['copy_data_from'] = self.cache.base_dir + '/data'

    def __call__(self):
        return Postgresql(**self.settings)

    def clear_cache(self):
        if self.cache:
            self.settings['copy_data_from'] = None
            self.cache.cleanup()


class Postgresql(Database):
    DEFAULT_SETTINGS = dict(auto_start=2,
                            base_dir=None,
                            initdb=None,
                            initdb_args='-U postgres -A trust',
                            postgres=None,
                            postgres_args='-h 127.0.0.1 -F -c logging_collector=off',
                            pid=None,
                            port=None,
                            copy_data_from=None)

    def initialize(self):
        self.initdb = self.settings.pop('initdb')
        if self.initdb is None:
            self.settings['initdb'] = find_program('initdb', ['bin'])

        if self.postgres is None:
            self.settings['postgres'] = find_program('postgres', ['bin'])

    def __getattr__(self, name):
        if name in self.settings:
            return self.settings[name]
        else:
            raise AttributeError("'Postgresql' object has no attribute '%s'" % name)

    def dsn(self, **kwargs):
        # "database=test host=localhost user=postgres"
        params = dict(kwargs)
        params.setdefault('port', self.port)
        params.setdefault('host', '127.0.0.1')
        params.setdefault('user', 'postgres')
        params.setdefault('database', 'test')

        return params

    def url(self, **kwargs):
        params = self.dsn(**kwargs)

        url = ('postgresql://%s@%s:%d/%s' %
               (params['user'], params['host'], params['port'], params['database']))

        return url

    def setup(self):
        # copy data files
        if self.copy_data_from:
            try:
                copytree(self.copy_data_from, os.path.join(self.base_dir, 'data'))
                os.chmod(os.path.join(self.base_dir, 'data'), 0o700)
            except Exception as exc:
                raise RuntimeError("could not copytree %s to %s: %r" %
                                   (self.copy_data_from, os.path.join(self.base_dir, 'data'), exc))

        # (re)create directory structure
        for subdir in ['data', 'tmp']:
            path = os.path.join(self.base_dir, subdir)
            if not os.path.exists(path):
                os.makedirs(path)
                os.chmod(path, 0o700)

        # initdb
        if not os.path.exists(os.path.join(self.base_dir, 'data', 'PG_VERSION')):
            args = ([self.initdb, '-D', os.path.join(self.base_dir, 'data'), '--lc-messages=C'] +
                    self.initdb_args.split())

            try:
                p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, err = p.communicate()
                if p.returncode != 0:
                    self.cleanup()
                    raise RuntimeError("initdb failed: %r" % err)
            except OSError as exc:
                self.cleanup()
                raise RuntimeError("failed to spawn initdb: %s" % exc)

    def start(self):
        if self.pid:
            return  # already started

        if self.port is None:
            self.port = get_unused_port()

        logger = open(os.path.join(self.base_dir, 'tmp', 'postgresql.log'), 'wt')
        pid = os.fork()
        if pid == 0:
            os.dup2(logger.fileno(), sys.__stdout__.fileno())
            os.dup2(logger.fileno(), sys.__stderr__.fileno())

            try:
                os.execl(self.postgres, self.postgres,
                         '-p', str(self.port),
                         '-D', os.path.join(self.base_dir, 'data'),
                         '-k', os.path.join(self.base_dir, 'tmp'),
                         *self.postgres_args.split())
            except Exception as exc:
                raise RuntimeError('failed to launch postgres: %r' % exc)
        else:
            logger.close()

            exec_at = datetime.now()
            while True:
                if os.waitpid(pid, os.WNOHANG)[0] != 0:
                    error = RuntimeError("*** failed to launch postgres ***\n" + self.read_log())
                    self.stop()
                    raise error

                if self.is_connection_available():
                    break

                if (datetime.now() - exec_at).seconds > 10.0:
                    error = RuntimeError("*** failed to launch postgres (timeout) ***\n" + self.read_log())
                    self.stop()
                    raise error

                sleep(0.1)

            self.pid = pid

            # create test database
            with closing(pg8000.connect(**self.dsn(database='postgres'))) as conn:
                conn.autocommit = True
                with closing(conn.cursor()) as cursor:
                    cursor.execute("SELECT COUNT(*) FROM pg_database WHERE datname='test'")
                    if cursor.fetchone()[0] <= 0:
                        cursor.execute('CREATE DATABASE test')

    def read_log(self):
        try:
            with open(os.path.join(self.base_dir, 'tmp', 'postgresql.log')) as log:
                return log.read()
        except Exception as exc:
            raise RuntimeError("failed to open file:tmp/postgresql.log: %r" % exc)

    def is_connection_available(self):
        try:
            with closing(pg8000.connect(**self.dsn(database='template1'))):
                pass
        except pg8000.Error:
            return False
        else:
            return True


def skipIfNotInstalled(arg=None):
    if sys.version_info < (2, 7):
        from unittest2 import skipIf
    else:
        from unittest import skipIf

    def decorator(fn, path=arg):
        if path:
            cond = not os.path.exists(path)
        else:
            try:
                find_program('postgres', ['bin'])  # raise exception if not found
                cond = False
            except:
                cond = True  # not found

        return skipIf(cond, "PostgreSQL not found")(fn)

    if callable(arg):  # execute as simple decorator
        return decorator(arg, None)
    else:  # execute with path argument
        return decorator


skipIfNotFound = skipIfNotInstalled


def find_program(name, subdirs):
    path = get_path_of(name)
    if path:
        return path

    for base_dir in SEARCH_PATHS:
        for subdir in subdirs:
            path = os.path.join(base_dir, subdir, name)
            if os.path.exists(path):
                return path

    raise RuntimeError("command not found: %s" % name)


def get_path_of(name):
    path = subprocess.Popen(['/usr/bin/which', name],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE).communicate()[0]
    if path:
        return path.rstrip().decode('utf-8')
    else:
        return None


def get_unused_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    _, port = sock.getsockname()
    sock.close()

    return port
