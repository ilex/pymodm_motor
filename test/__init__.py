# Copyright 2016 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Base classes for motor test cases."""

import asyncio
import functools
import gc
import os
import unittest

import pymongo

try:
    import motor.motor_tornado
    import tornado.ioloop
    TORNADO_TEST = True
except ImportError:
    TORNADO_TEST = False

try:
    import motor.motor_asyncio
    assert motor.motor_asyncio  # silence pyflakes
    ASYNCIO_TEST = True
except ImportError:
    ASYNCIO_TEST = False

from pymodm_motor.connection import (
    connect, DEFAULT_CONNECTION_ALIAS,
    MOTOR_ASYNCIO_DRIVER, MOTOR_TORNADO_DRIVER)


def get_test_suite():
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('test', pattern='test_*.py')
    return test_suite


MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017')

CLIENT = pymongo.MongoClient(MONGO_URI)
DB = CLIENT.odm_test


# Get the version of MongoDB.
server_info = pymongo.MongoClient(MONGO_URI).server_info()
MONGO_VERSION = tuple(server_info.get('versionArray', []))


class MotorODMTestCase(unittest.TestCase):
    """Base class for motor test cases."""

    def setUp(self):
        self.loop = self.setup_test_loop()
        self.connect_to_db(MONGO_URI, DB.name)

    def tearDown(self):
        CLIENT.drop_database(DB.name)
        self.teardown_test_loop()

    def assertEqualsModel(self, expected, model_instance):
        """Assert that a Model instance equals the expected document."""
        actual = model_instance.to_son()
        actual.pop('_cls', None)
        self.assertEqual(expected, actual)

    def setup_test_loop(self):
        pass

    def teardown_test_loop(self):
        pass

    def connect_to_db(self, uri, db_name, alias=DEFAULT_CONNECTION_ALIAS):
        pass


class AsyncIOMotorODMTestCase(MotorODMTestCase):
    """Base motor test case class with AsynIO driver."""

    def setup_test_loop(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(None)
        return loop

    def teardown_test_loop(self):
        """Teardown and cleanup an event loop created by setup_test_loop."""
        closed = self.loop.is_closed()
        if not closed:
            self.loop.call_soon(self.loop.stop)
            self.loop.run_forever()
            self.loop.close()
        gc.collect()
        asyncio.set_event_loop(None)

    def connect_to_db(self, uri, db_name, alias=DEFAULT_CONNECTION_ALIAS):
        self.mongo_driver = MOTOR_ASYNCIO_DRIVER
        connect('%s/%s' % (uri, db_name),
                alias=alias,
                mongo_driver=self.mongo_driver,
                io_loop=self.loop)


class TornadoMotorODMTestCase(MotorODMTestCase):
    """Base motor test case class with AsynIO driver."""

    def setup_test_loop(self):
        return tornado.ioloop.IOLoop.current()

    def teardown_test_loop(self):
        """Teardown and cleanup an event loop created by setup_test_loop."""
        pass

    def connect_to_db(self, uri, db_name, alias=DEFAULT_CONNECTION_ALIAS):
        self.mongo_driver = MOTOR_TORNADO_DRIVER
        connect('%s/%s' % (uri, db_name),
                alias=alias,
                mongo_driver=self.mongo_driver,
                io_loop=self.loop)


def unittest_run_loop(func):
    """A decorator to use with asynchronous methods of an MotorODMTestCase.

    Handles executing an asynchronous function, using
    the self.loop of the MotorODMTestCase.
    """
    @functools.wraps(func)
    def new_func(self):
        if isinstance(self.loop, asyncio.BaseEventLoop):
            return self.loop.run_until_complete(func(self))
        else:
            return self.loop.run_sync(functools.partial(func, self))

    return new_func
