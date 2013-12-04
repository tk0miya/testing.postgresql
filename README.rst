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
  postgresql = testing.postgresql.Postgresql()  # Lanuch new PostgreSQL server

  # connect to PostgreSQL
  from sqlalchemy import create_engine
  engine = create_engine(postgresql.url())

  # if you use postgresql or other drivers:
  #   import psycopg2
  #   db = psycopg2.connect(**postgresql.dsn())

  #
  # do any tests using PostgreSQL...
  #

  del postgresql                     # Terminate PostgreSQL server


``testing.postgresql.Postgresql`` executes ``initdb`` and ``postmaster`` on instantiation.
On deleting Postgresql object, it terminates PostgreSQL instance and removes temporary directory.

If you want a database including tables and any fixtures for your apps,
use ``copy_data_from`` keyword::

  # uses a copy of specified data directory of PostgreSQL.
  postgresql = testing.postgresql.Postgresql(copy_data_from='/path/to/your/database')


You can specify parameters for PostgreSQL with ``my_cnf`` keyword::

  # boot PostgreSQL server without socket listener (use unix-domain socket) 
  postgresql = testing.postgresql.Postgresql(my_cnf={'skip-networking': None})


For example, you can setup new PostgreSQL server for each testcases on setUp() method::

  import unittest
  import testing.postgresql

  class MyTestCase(unittest.TestCase):
      def setUp(self):
          self.postgresql = testing.postgresql.Postgresql(my_cnf={'skip-networking': None})


Requirements
============
* Python 2.7, 3.3
* psycopg2

License
=======
Apache License 2.0


History
=======

1.0.0 (2013-12-04)
-------------------
* Add @skipIfNotFound decorator

0.1.0 (2013-11-26)
-------------------
* First release
