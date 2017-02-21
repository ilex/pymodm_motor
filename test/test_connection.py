import unittest

from pymodm_motor.connection import connect, _get_connection

from test import (
    TORNADO_TEST, ASYNCIO_TEST,
    TornadoMotorODMTestCase, AsyncIOMotorODMTestCase)


class MotorConnectionTestCase:
    def test_connect_with_kwargs(self):
        connect('mongodb://localhost:27017/foo?maxPoolSize=42',
                'foo-connection',
                mongo_driver=self.mongo_driver,
                io_loop=self.loop,
                minpoolsize=10)
        client = _get_connection('foo-connection').database.client
        self.assertEqual(42, client.max_pool_size)
        self.assertEqual(10, client.min_pool_size)


@unittest.skipUnless(ASYNCIO_TEST, 'Motor not installed')
class AsyncIOMotorBasicModelTestCase(MotorConnectionTestCase,
                                     AsyncIOMotorODMTestCase):
    pass


@unittest.skipUnless(TORNADO_TEST, 'Tornado or Motor not installed')
class TornadoMotorBasicModelTestCase(MotorConnectionTestCase,
                                     TornadoMotorODMTestCase):
    pass
