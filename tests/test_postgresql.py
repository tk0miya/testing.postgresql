# -*- coding: utf-8 -*-

import os
import signal
import unittest
import testing.postgresql
from time import sleep
import psycopg2


class TestPostgresql(unittest.TestCase):
    def test_basic(self):
        # start postgresql server
        pgsql = testing.postgresql.Postgresql()
        self.assertIsNotNone(pgsql)
        params = pgsql.dsn()
        self.assertEqual('test', params['dbname'])
        self.assertEqual('127.0.0.1', params['host'])
        self.assertEqual(pgsql.port, params['port'])
        self.assertEqual('postgres', params['user'])

        # connect to postgresql
        conn = psycopg2.connect(**pgsql.dsn())
        self.assertIsNotNone(conn)
        self.assertRegexpMatches(pgsql.read_log(), 'is ready to accept connections')
        conn.close()

        # shutting down
        pid = pgsql.pid
        self.assertTrue(pid)
        os.kill(pid, 0)  # process is alive

        pgsql.stop()
        sleep(1)

        self.assertIsNone(pgsql.pid)
        with self.assertRaises(OSError):
            os.kill(pid, 0)  # process is down

    def test_dsn_and_url(self):
        pgsql = testing.postgresql.Postgresql(port=12345, auto_start=0)
        self.assertEqual({'dbname': 'test', 'host': '127.0.0.1', 'port': 12345, 'user': 'postgres'},
                         pgsql.dsn())
        self.assertEqual("postgresql://postgres@127.0.0.1:12345/test", pgsql.url())

    def test_with_statement(self):
        with testing.postgresql.Postgresql() as pgsql:
            self.assertIsNotNone(pgsql)

            # connect to postgresql
            conn = psycopg2.connect(**pgsql.dsn())
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

            with self.assertRaises(RuntimeError):
                testing.postgresql.Postgresql()
        finally:
            testing.postgresql.SEARCH_PATHS = search_paths

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
        data_dir = os.path.join(os.path.dirname(__file__), 'copy-data-from')
        pgsql = testing.postgresql.Postgresql(copy_data_from=data_dir)

        # connect to postgresql
        conn = psycopg2.connect(**pgsql.dsn())
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM hello ORDER BY id')
            self.assertEqual(cursor.fetchall(), [(1, 'hello'), (2, 'ciao')])
        conn.close()

    def test_skipIfNotFound_found(self):
        try:
            search_paths = testing.postgresql.SEARCH_PATHS
            testing.postgresql.SEARCH_PATHS = []

            @testing.postgresql.skipIfNotFound
            def testcase():
                pass

            self.assertEqual(True, hasattr(testcase, '__unittest_skip__'))
            self.assertEqual(True, hasattr(testcase, '__unittest_skip_why__'))
            self.assertEqual(True, testcase.__unittest_skip__)
            self.assertEqual("PostgreSQL does not found", testcase.__unittest_skip_why__)
        finally:
            testing.postgresql.SEARCH_PATHS = search_paths

    def test_skipIfNotFound_notfound(self):
        @testing.postgresql.skipIfNotFound
        def testcase():
            pass

        self.assertEqual(False, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(False, hasattr(testcase, '__unittest_skip_why__'))

    def test_skipIfNotFound_with_args_found(self):
        path = testing.postgresql.find_program('postmaster', ['bin'])

        @testing.postgresql.skipIfNotFound(path)
        def testcase():
            pass

        self.assertEqual(False, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(False, hasattr(testcase, '__unittest_skip_why__'))

    def test_skipIfNotFound_with_args_notfound(self):
        @testing.postgresql.skipIfNotFound("/path/to/anywhere")
        def testcase():
            pass

        self.assertEqual(True, hasattr(testcase, '__unittest_skip__'))
        self.assertEqual(True, hasattr(testcase, '__unittest_skip_why__'))
        self.assertEqual(True, testcase.__unittest_skip__)
        self.assertEqual("PostgreSQL does not found", testcase.__unittest_skip_why__)
