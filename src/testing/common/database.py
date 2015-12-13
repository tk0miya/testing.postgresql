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
import signal
import socket
import tempfile
from time import sleep
from shutil import rmtree
from datetime import datetime


class Database(object):
    DEFAULT_SETTINGS = {}

    def __init__(self, **kwargs):
        self.name = self.__class__.__name__
        self.settings = dict(self.DEFAULT_SETTINGS)
        self.settings.update(kwargs)
        self.pid = None
        self._owner_pid = os.getpid()
        self._use_tmpdir = False

        self.base_dir = self.settings.pop('base_dir')
        if self.base_dir:
            if self.base_dir[0] != '/':
                self.base_dir = os.path.join(os.getcwd(), self.base_dir)
        else:
            self.base_dir = tempfile.mkdtemp()
            self._use_tmpdir = True

        self.initialize()

        if self.settings['auto_start']:
            if self.settings['auto_start'] >= 2:
                self.setup()

            self.start()

    def setup(self):
        pass

    def start(self):
        if self.pid:
            return  # already started

        self.prestart()

        logger = open(os.path.join(self.base_dir, '%s.log' % self.name), 'wt')
        self.pid = os.fork()
        if self.pid == 0:
            os.dup2(logger.fileno(), sys.__stdout__.fileno())
            os.dup2(logger.fileno(), sys.__stderr__.fileno())

            try:
                command = self.get_server_commandline()
                os.execl(command[0], *command)
                self.invoke_server()
            except Exception as exc:
                raise RuntimeError('failed to launch %s: %r' % (self.name, exc))
        else:
            logger.close()

            try:
                self.wait_booting()
                self.create_default_database()
            except:
                self.stop()
                raise

    def get_server_commandline(self):
        raise NotImplemented

    def wait_booting(self):
        exec_at = datetime.now()
        while True:
            if os.waitpid(self.pid, os.WNOHANG)[0] != 0:
                raise RuntimeError("*** failed to launch %s ***\n" % self.name +
                                   self.read_bootlog())

            if self.is_server_available():
                break

            if (datetime.now() - exec_at).seconds > 10.0:
                raise RuntimeError("*** failed to launch %s (timeout) ***\n" % self.name +
                                   self.read_bootlog())

            sleep(0.1)

    def prestart(self):
        if self.settings['port'] is None:
            self.settings['port'] = get_unused_port()

    def create_default_database(self):
        pass

    def is_server_available(self):
        return False

    def stop(self, _signal=signal.SIGINT):
        try:
            self.terminate(_signal)
        finally:
            self.cleanup()

    def terminate(self, _signal=signal.SIGINT):
        if self.pid is None:
            return  # not started

        if self._owner_pid != os.getpid():
            return  # could not stop in child process

        try:
            os.kill(self.pid, _signal)
            killed_at = datetime.now()
            while (os.waitpid(self.pid, os.WNOHANG)):
                if (datetime.now() - killed_at).seconds > 10.0:
                    os.kill(self.pid, signal.SIGKILL)
                    raise RuntimeError("*** failed to shutdown postgres (timeout) ***\n" + self.read_bootlog())

                sleep(0.1)
        except OSError:
            pass

        self.pid = None

    def cleanup(self):
        if self.pid is not None:
            return

        if self._use_tmpdir and os.path.exists(self.base_dir):
            rmtree(self.base_dir, ignore_errors=True)
            self._use_tmpdir = False

    def read_bootlog(self):
        try:
            with open(os.path.join(self.base_dir, '%s.log' % self.name)) as log:
                return log.read()
        except Exception as exc:
            raise RuntimeError("failed to open file:%s.log: %r" % (self.name, exc))

    def __del__(self):
        self.stop()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()


def get_unused_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    _, port = sock.getsockname()
    sock.close()

    return port
