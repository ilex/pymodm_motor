import unittest

from . import (
    TORNADO_TEST, ASYNCIO_TEST,
    TornadoMotorODMTestCase, AsyncIOMotorODMTestCase, unittest_run_loop)
from .models import User


class PY36MotorQuerySetTestCase:

    def setUp(self):
        super().setUp()
        self.set_up_models()

    @unittest_run_loop
    async def set_up_models(self):
        await User(fname='Garden', lname='Tomato', phone=1111111).save()
        await User(fname='Rotten', lname='Tomato', phone=2222222).save()
        await User(fname='Amon', lname='Amarth', phone=3333333).save()
        await User(fname='Garth', lname='Amarth', phone=4444444).save()

    @unittest_run_loop
    async def test_all_async_comprehension(self):
        results = [item async for item in User.objects.all()]
        self.assertEqual(4, len(results))

    @unittest_run_loop
    async def test_to_list(self):
        results = await User.objects.all().to_list(dereference=False)
        self.assertEqual(4, len(results))


@unittest.skipUnless(ASYNCIO_TEST, 'Motor not installed')
class AsyncIOPY36MotorQuerySetTestCase(PY36MotorQuerySetTestCase,
                                       AsyncIOMotorODMTestCase):
    pass


@unittest.skipUnless(TORNADO_TEST, 'Tornado or Motor not installed')
class TornadoPY36MotorQuerySetTestCase(PY36MotorQuerySetTestCase,
                                       TornadoMotorODMTestCase):
    pass
