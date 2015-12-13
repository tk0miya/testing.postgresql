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
import pg8000
import subprocess
from glob import glob
from contextlib import closing

from testing.common.database import Database, get_path_of


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
    subdirectories = ['data', 'tmp']

    def initialize(self):
        self.initdb = self.settings.pop('initdb')
        if self.initdb is None:
            self.initdb = find_program('initdb', ['bin'])

        self.postgres = self.settings.pop('postgres')
        if self.postgres is None:
            self.postgres = find_program('postgres', ['bin'])

    def dsn(self, **kwargs):
        # "database=test host=localhost user=postgres"
        params = dict(kwargs)
        params.setdefault('port', self.settings['port'])
        params.setdefault('host', '127.0.0.1')
        params.setdefault('user', 'postgres')
        params.setdefault('database', 'test')

        return params

    def url(self, **kwargs):
        params = self.dsn(**kwargs)

        url = ('postgresql://%s@%s:%d/%s' %
               (params['user'], params['host'], params['port'], params['database']))

        return url

    def get_data_directory(self):
        return os.path.join(self.base_dir, 'data')

    def initialize_database(self):
        if not os.path.exists(os.path.join(self.base_dir, 'data', 'PG_VERSION')):
            args = ([self.initdb, '-D', os.path.join(self.base_dir, 'data'), '--lc-messages=C'] +
                    self.settings['initdb_args'].split())

            try:
                p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                output, err = p.communicate()
                if p.returncode != 0:
                    raise RuntimeError("initdb failed: %r" % err)
            except OSError as exc:
                raise RuntimeError("failed to spawn initdb: %s" % exc)

    def get_server_commandline(self):
        return ([self.postgres,
                 '-p', str(self.settings['port']),
                 '-D', os.path.join(self.base_dir, 'data'),
                 '-k', os.path.join(self.base_dir, 'tmp')] +
                self.settings['postgres_args'].split())

    def create_default_database(self):
        with closing(pg8000.connect(**self.dsn(database='postgres'))) as conn:
            conn.autocommit = True
            with closing(conn.cursor()) as cursor:
                cursor.execute("SELECT COUNT(*) FROM pg_database WHERE datname='test'")
                if cursor.fetchone()[0] <= 0:
                    cursor.execute('CREATE DATABASE test')

    def is_server_available(self):
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
