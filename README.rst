``testing.postgresql`` automatically setups a postgresql instance in a temporary directory, and destroys it after testing

Install
=======
Use easy_install (or pip)::

   $ easy_install testing.postgresql

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


``testing.postgresql.Postgresql`` executes ``initdb`` and ``postmaster`` on instantiation.
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


Requirements
============
* Python 2.6, 2.7, 3.2, 3.3
* psycopg2

License
=======
Apache License 2.0


History
=======

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
