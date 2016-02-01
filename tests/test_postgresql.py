# -*- coding: utf-8 -*-

import os
import sys
import signal
import tempfile
import testing.postgresql
from time import sleep
from shutil import rmtree
import pg8000
import psycopg2
import sqlalchemy
from contextlib import closing

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestPostgresql(unittest.TestCase):
    def test_basic(self):
        try:
            # start postgresql server
            pgsql = testing.postgresql.Postgresql()
            self.assertIsNotNone(pgsql)
            params = pgsql.dsn()
            self.assertEqual('test', params['database'])
            self.assertEqual('127.0.0.1', params['host'])
            self.assertEqual(pgsql.settings['port'], params['port'])
            self.assertEqual('postgres', params['user'])

            # connect to postgresql (w/ psycopg2)
            conn = psycopg2.connect(**pgsql.dsn())
            self.assertIsNotNone(conn)
            self.assertRegexpMatches(pgsql.read_bootlog(), 'is ready to accept connections')
            conn.close()

            # connect to postgresql (w/ sqlalchemy)
            engine = sqlalchemy.create_engine(pgsql.url())
            self.assertIsNotNone(engine)

            # connect to postgresql (w/ pg8000)
            conn = pg8000.connect(**pgsql.dsn())
            self.assertIsNotNone(conn)
            self.assertRegexpMatches(pgsql.read_bootlog(), 'is ready to accept connections')
            conn.close()
        finally:
            # shutting down
            pid = pgsql.pid
            self.assertTrue(pid)
            os.kill(pid, 0)  # process is alive

            pgsql.stop()
            sleep(1)

            self.assertIsNone(pgsql.pid)
            with self.assertRaises(OSError):
                os.kill(pid, 0)  # process is down

    def test_stop(self):
        # start postgresql server
        pgsql = testing.postgresql.Postgresql()
        self.assertIsNotNone(pgsql.pid)
        self.assertTrue(os.path.exists(pgsql.base_dir))
        pid = pgsql.pid
        os.kill(pid, 0)  # process is alive

        # call stop()
        pgsql.stop()
        self.assertIsNone(pgsql.pid)
        self.assertFalse(os.path.exists(pgsql.base_dir))
        with self.assertRaises(OSError):
            os.kill(pid, 0)  # process is down

        # call stop() again
        pgsql.stop()
        self.assertIsNone(pgsql.pid)
        self.assertFalse(os.path.exists(pgsql.base_dir))
        with self.assertRaises(OSError):
            os.kill(pid, 0)  # process is down

        # delete postgresql object after stop()
        del pgsql

    def test_dsn_and_url(self):
        pgsql = testing.postgresql.Postgresql(port=12345, auto_start=0)
        self.assertEqual({'database': 'test', 'host': '127.0.0.1', 'port': 12345, 'user': 'postgres'},
                         pgsql.dsn())
        self.assertEqual("postgresql://postgres@127.0.0.1:12345/test", pgsql.url())

    def test_with_statement(self):
        with testing.postgresql.Postgresql() as pgsql:
            self.assertIsNotNone(pgsql)

            # connect to postgresql
            conn = pg8000.connect(**pgsql.dsn())
            self.assertIsNotNone(conn)
            conn.close()

            pid = pgsql.pid
            os.kill(pid, 0)  # process is alive

        self.assertIsNone(pgsql.pid)
        with self.assertRaises(OSError):
            os.kill(pid, 0)  # process is down

    def test_multiple_postgresql(self):
        pgsql1 = testing.postgresql.Postgresql()
        pgsql2 = testing.postgresql.Postgresql()
        self.assertNotEqual(pgsql1.pid, pgsql2.pid)

        os.kill(pgsql1.pid, 0)  # process is alive
        os.kill(pgsql2.pid, 0)  # process is alive

    def test_postgresql_is_not_found(self):
        try:
            search_paths = testing.postgresql.SEARCH_PATHS
            testing.postgresql.SEARCH_PATHS = []
            path_env = os.environ['PATH']
            os.environ['PATH'] = ''

            with self.assertRaises(RuntimeError):
                testing.postgresql.Postgresql()
        finally:
            testing.postgresql.SEARCH_PATHS = search_paths
            os.environ['PATH'] = path_env

    def test_fork(self):
        pgsql = testing.postgresql.Postgresql()
        if os.fork() == 0:
            del pgsql
            pgsql = None
            os.kill(os.getpid(), signal.SIGTERM)  # exit tests FORCELY
        else:
            os.wait()
            sleep(1)
            self.assertTrue(pgsql.pid)
            os.kill(pgsql.pid, 0)  # process is alive (delete pgsql obj in child does not effect)

    def test_stop_on_child_process(self):
        pgsql = testing.postgresql.Postgresql()
        if os.fork() == 0:
            pgsql.stop()
            self.assertTrue(pgsql.pid)
            os.kill(pgsql.pid, 0)  # process is alive (calling stop() is ignored)
            os.kill(os.getpid(), signal.SIGTERM)  # exit tests FORCELY
        else:
            os.wait()
            sleep(1)
            self.assertTrue(pgsql.pid)
            os.kill(pgsql.pid, 0)  # process is alive (calling stop() in child is ignored)

    def test_copy_data_from(self):
        try:
            tmpdir = tempfile.mkdtemp()

            # create new database
            with testing.postgresql.Postgresql(base_dir=tmpdir) as pgsql:
                conn = pg8000.connect(**pgsql.dsn())
                with closing(conn.cursor()) as cursor:
                    cursor.execute("CREATE TABLE hello(id int, value varchar(256))")
                    cursor.execute("INSERT INTO hello values(1, 'hello'), (2, 'ciao')")
                conn.commit()
                conn.close()

            # create another database from first one
            data_dir = os.path.join(tmpdir, 'data')
            with testing.postgresql.Postgresql(copy_data_from=data_dir) as pgsql:
                conn = pg8000.connect(**pgsql.dsn())
                with closing(conn.cursor()) as cursor:
                    cursor.execute('SELECT * FROM hello ORDER BY id')
                    self.assertEqual(cursor.fetchall(), ([1, 'hello'], [2, 'ciao']))
                conn.close()
        finally:
            rmtree(tmpdir)

    def test_skipIfNotInstalled_found(self):
        try:
            search_paths = testing.postgresql.SEARCH_PATHS
            testing.postgresql.SEARCH_PATHS = []
            path_env = os.environ['PATH']
            os.environ['PATH'] = ''

            @testing.postgresql.skipIfNotInstalled
            def testcase():
                pass

            self.assertEqual(True, hasattr(testcase, '__unittest_skip__'))
            self.assertEqual(True, hasattr(testcase, '__unittest_skip_why__'))
            self.assertEqual(True, testcase.__unittest_skip__)
            self.assertEqual("PostgreSQL not found", testcase.__unittest_skip_why__)
        finally:
            testing.postgresql.SEARCH_PATHS = search_paths
            os.environ['PATH'] = path_env

    def test_skipIfNotInstalled_notfound(self):
        @testing.postgresql.skipIfNotInstalled
        def testcase():
            pass

        self.assertEqual(False, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(False, hasattr(testcase, '__unittest_skip_why__'))

    def test_skipIfNotInstalled_with_args_found(self):
        path = testing.postgresql.find_program('postgres', ['bin'])

        @testing.postgresql.skipIfNotInstalled(path)
        def testcase():
            pass

        self.assertEqual(False, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(False, hasattr(testcase, '__unittest_skip_why__'))

    def test_skipIfNotInstalled_with_args_notfound(self):
        @testing.postgresql.skipIfNotInstalled("/path/to/anywhere")
        def testcase():
            pass

        self.assertEqual(True, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(True, hasattr(testcase, '__unittest_skip_why__'))
        self.assertEqual(True, testcase.__unittest_skip__)
        self.assertEqual("PostgreSQL not found", testcase.__unittest_skip_why__)

    def test_skipIfNotFound_found(self):
        try:
            search_paths = testing.postgresql.SEARCH_PATHS
            testing.postgresql.SEARCH_PATHS = []
            path_env = os.environ['PATH']
            os.environ['PATH'] = ''

            @testing.postgresql.skipIfNotFound
            def testcase():
                pass

            self.assertEqual(True, hasattr(testcase, '__unittest_skip__'))
            self.assertEqual(True, hasattr(testcase, '__unittest_skip_why__'))
            self.assertEqual(True, testcase.__unittest_skip__)
            self.assertEqual("PostgreSQL not found", testcase.__unittest_skip_why__)
        finally:
            testing.postgresql.SEARCH_PATHS = search_paths
            os.environ['PATH'] = path_env

    def test_skipIfNotFound_notfound(self):
        @testing.postgresql.skipIfNotFound
        def testcase():
            pass

        self.assertEqual(False, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(False, hasattr(testcase, '__unittest_skip_why__'))

    def test_PostgresqlFactory(self):
        Postgresql = testing.postgresql.PostgresqlFactory(cache_initialized_db=True)
        with Postgresql() as pgsql1:
            self.assertTrue(pgsql1.settings['copy_data_from'])
            copy_data_from1 = pgsql1.settings['copy_data_from']
            self.assertTrue(os.path.exists(copy_data_from1))
        with Postgresql() as pgsql2:
            self.assertEqual(copy_data_from1, pgsql2.settings['copy_data_from'])
        Postgresql.clear_cache()
        self.assertFalse(os.path.exists(copy_data_from1))

    def test_PostgresqlFactory_with_initialized_handler(self):
        def handler(pgsql):
            conn = pg8000.connect(**pgsql.dsn())
            with closing(conn.cursor()) as cursor:
                cursor.execute("CREATE TABLE hello(id int, value varchar(256))")
                cursor.execute("INSERT INTO hello values(1, 'hello'), (2, 'ciao')")
            conn.commit()
            conn.close()

        Postgresql = testing.postgresql.PostgresqlFactory(cache_initialized_db=True,
                                                          on_initialized=handler)
        try:
            with Postgresql() as pgsql:
                conn = pg8000.connect(**pgsql.dsn())
                with closing(conn.cursor()) as cursor:
                    cursor.execute('SELECT * FROM hello ORDER BY id')
                    self.assertEqual(cursor.fetchall(), ([1, 'hello'], [2, 'ciao']))
                conn.close()
        finally:
            Postgresql.clear_cache()
