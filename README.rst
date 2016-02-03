About
=====
``testing.postgresql`` automatically setups a postgresql instance in a temporary directory, and destroys it after testing.

.. image:: https://travis-ci.org/tk0miya/testing.postgresql.svg?branch=master
   :target: https://travis-ci.org/tk0miya/testing.postgresql

.. image:: https://coveralls.io/repos/tk0miya/testing.postgresql/badge.png?branch=master
   :target: https://coveralls.io/r/tk0miya/testing.postgresql?branch=master

.. image:: https://codeclimate.com/github/tk0miya/testing.postgresql/badges/gpa.svg
   :target: https://codeclimate.com/github/tk0miya/testing.postgresql


Documentation
  https://github.com/tk0miya/testing.postgresql
Issues
  https://github.com/tk0miya/testing.postgresql/issues
Download
  https://pypi.python.org/pypi/testing.postgresql

Install
=======
Use pip::

   $ pip install testing.postgresql

And ``testing.postgresql`` requires PostgreSQL server in your PATH.


Usage
=====
Create PostgreSQL instance using ``testing.postgresql.Postgresql``::

  import testing.postgresql
  from sqlalchemy import create_engine

  # Lanuch new PostgreSQL server
  with testing.postgresql.Postgresql() as postgresql:
      # connect to PostgreSQL
      engine = create_engine(postgresql.url())

      # if you use postgresql or other drivers:
      #   import psycopg2
      #   db = psycopg2.connect(**postgresql.dsn())

      #
      # do any tests using PostgreSQL...
      #

  # PostgreSQL server is terminated here


``testing.postgresql.Postgresql`` executes ``initdb`` and ``postgres`` on instantiation.
On deleting Postgresql object, it terminates PostgreSQL instance and removes temporary directory.

If you want a database including tables and any fixtures for your apps,
use ``copy_data_from`` keyword::

  # uses a copy of specified data directory of PostgreSQL.
  postgresql = testing.postgresql.Postgresql(copy_data_from='/path/to/your/database')


For example, you can setup new PostgreSQL server for each testcases on setUp() method::

  import unittest
  import testing.postgresql

  class MyTestCase(unittest.TestCase):
      def setUp(self):
          self.postgresql = testing.postgresql.Postgresql()

      def tearDown(self):
          self.postgresql.stop()


To make your tests faster
-------------------------

``testing.postgresql.Postgresql`` invokes ``initdb`` command on every instantiation.
That is very simple. But, in many cases, it is very waste that generating brandnew database for each testcase.

To optimize the behavior, use ``testing.postgresql.PostgresqlFactory``.
The factory class is able to cache the generated database beyond the testcases,
and it reduces the number of invocation of ``initdb`` command::

  import unittest
  import testing.postgresql

  # Generate Postgresql class which shares the generated database
  Postgresql = testing.postgresql.PostgresqlFactory(cache_initialized_db=True)


  def tearDownModule(self):
      # clear cached database at end of tests
      Postgresql.clear_cache()


  class MyTestCase(unittest.TestCase):
      def setUp(self):
          # Use the generated Postgresql class instead of testing.postgresql.Postgresql
          self.postgresql = Postgresql()

      def tearDown(self):
          self.postgresql.stop()

If you want to insert fixtures to the cached database, use ``initdb_handler`` option::

  # create initial data on create as fixtures into the database
  def handler(postgresql):
      conn = psycopg2.connect(**postgresql.dsn())
      cursor = conn.cursor()
      cursor.execute("CREATE TABLE hello(id int, value varchar(256))")
      cursor.execute("INSERT INTO hello values(1, 'hello'), (2, 'ciao')")
      cursor.close()
      conn.commit()
      conn.close()

  # Use `handler()` on initialize database
  Postgresql = testing.postgresql.PostgresqlFactory(cache_initialized_db=True,
                                                    on_initialized=handler)


Requirements
============
* Python 2.6, 2.7, 3.2, 3.3, 3.4, 3.5
* pg8000 1.10

License
=======
Apache License 2.0


History
=======

1.3.0 (2016-02-03)
-------------------
* Add testing.postgresql.PostgresqlFactory
* Depend on ``testing.common.database`` package

1.2.1 (2015-08-22)
-------------------
* Fix bug:

  - Close #3 Fix AttributeError on end of tests

1.2.0 (2015-05-17)
-------------------
* Use `pg8000` for connector to create test database
* Connect to `postgres` to create test database (instead of `template1`)

1.1.2 (2015-04-06)
-------------------
* Fix bugs:

  - Do not call os.getpid() on destructor (if not needed)
  - Raise detailed RuntimeError if initdb exits non-zero

1.1.1 (2015-01-18)
-------------------
* Disable logging_collector feature (For Fedora)
* Fix bugs:

  - MacPorts default path is /opt/local/lib/postgresql*, no dash

1.1.0 (2014-12-20)
-------------------
* Invoke 'postgres' command instead of 'postmaster'

1.0.6 (2014-07-19)
-------------------
* Fix #1 Dirty postmaster shut down

1.0.5 (2014-07-19)
-------------------
* Fix path for PostgreSQL
* Use absolute path for which command

1.0.4 (2014-06-19)
-------------------
* Fix timeout on terminating postgresql
* Support PostgreSQL on /usr/local/bin (cf. FreeBSD ports)
* Fix bugs

1.0.3 (2014-06-11)
-------------------
* Fix ImportError if caught SIGINT on py3

1.0.2 (2013-12-06)
-------------------
* Change behavior: Postgresql#stop() cleans workdir
* Fix caught AttributeError on object deletion

1.0.1 (2013-12-05)
-------------------
* Add @skipIfNotInstalled decorator (alias of skipIfNotFound)
* Suport python 2.6 and 3.2

1.0.0 (2013-12-04)
-------------------
* Add @skipIfNotFound decorator

0.1.0 (2013-11-26)
-------------------
* First release
