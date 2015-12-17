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
import pg8000
import signal
import subprocess
from glob import glob
from contextlib import closing

from testing.common.database import (
    Database, DatabaseFactory, get_path_of, SkipIfNotInstalledDecorator
)


__all__ = ['Postgresql', 'skipIfNotFound']

SEARCH_PATHS = (['/usr/local/pgsql', '/usr/local'] +
                glob('/usr/lib/postgresql/*') +  # for Debian/Ubuntu
                glob('/opt/local/lib/postgresql*'))  # for MacPorts


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

    def poststart(self):
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

    def terminate(self, *args):
        # send SIGINT instead of SIGTERM
        super(Postgresql, self).terminate(signal.SIGINT)


class PostgresqlFactory(DatabaseFactory):
    target_class = Postgresql


class PostgresqlSkipIfNotInstalledDecorator(SkipIfNotInstalledDecorator):
    name = 'PostgreSQL'

    def search_server(self):
        find_program('postgres', ['bin'])


skipIfNotFound = skipIfNotInstalled = PostgresqlSkipIfNotInstalledDecorator()


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
