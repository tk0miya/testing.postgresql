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


Requirements
============
* Python 2.6, 2.7, 3.2, 3.3, 3.4
* pg8000 1.10

License
=======
Apache License 2.0


History
=======

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
