# -*- encoding: utf-8 -*-

import unittest

from pymongo.collation import Collation, CollationStrength
from pymodm_motor import fields, MotorMongoModel

from test import (
    TORNADO_TEST, ASYNCIO_TEST, MONGO_VERSION,
    TornadoMotorODMTestCase, AsyncIOMotorODMTestCase, unittest_run_loop)


class ModelForCollations(MotorMongoModel):
    name = fields.CharField()

    class Meta:
        # Default collation: American English, differentiate base characters.
        collation = Collation('en_US', strength=CollationStrength.PRIMARY)


class MotorCollationTestCase:

    @classmethod
    @unittest.skipIf(MONGO_VERSION < (3, 4), 'Requires MongoDB >= 3.4')
    def setUpClass(cls):
        super().setUpClass()

    def setUp(self):
        # Initial data.
        super().setUp()
        self.setup_db()

    @unittest_run_loop
    async def setup_db(self):
        await ModelForCollations._mongometa.collection.drop()
        await ModelForCollations.objects.bulk_create([
            ModelForCollations(u'Aargren'),
            ModelForCollations(u'Åårgren'),
        ])

    @unittest_run_loop
    async def test_collation(self):
        # Use a different collation (not default) for this QuerySet.
        qs = ModelForCollations.objects.collation(
            Collation('en_US', strength=CollationStrength.TERTIARY))
        self.assertEqual(1, await qs.raw({'name': 'Aargren'}).count())

    @unittest_run_loop
    async def test_count(self):
        self.assertEqual(
            2,
            await ModelForCollations.objects.raw({'name': 'Aargren'}).count())

    @unittest_run_loop
    async def test_aggregate(self):
        lst = []
        cursor = await ModelForCollations.objects.aggregate(
            {'$match': {'name': 'Aargren'}},
            {'$project': {'name': 1, '_id': 0}}
        )
        async for item in cursor:
            lst.append(item)

        self.assertEqual([{'name': u'Aargren'}, {'name': u'Åårgren'}], lst)

        # Override with keyword argument.
        alternate_collation = Collation(
            'en_US', strength=CollationStrength.TERTIARY)

        cursor = await ModelForCollations.objects.aggregate(
            {'$match': {'name': 'Aargren'}},
            {'$project': {'name': 1, '_id': 0}},
            collation=alternate_collation)
        lst = []
        async for item in cursor:
            lst.append(item)

        self.assertEqual([{'name': u'Aargren'}], lst)

    @unittest_run_loop
    async def test_delete(self):
        self.assertEqual(2, await ModelForCollations.objects.delete())

    @unittest_run_loop
    async def test_update(self):
        self.assertEqual(2, await ModelForCollations.objects.raw(
            {'name': 'Aargren'}).update({'$set': {'touched': 1}}))
        # Override with keyword argument.
        alternate_collation = Collation(
            'en_US', strength=CollationStrength.TERTIARY)
        self.assertEqual(
            1,
            await ModelForCollations.objects.raw({'name': 'Aargren'}).update(
                {'$set': {'touched': 2}},
                collation=alternate_collation))

    @unittest_run_loop
    async def test_query(self):
        qs = ModelForCollations.objects.raw({'name': 'Aargren'})
        # Iterate the QuerySet.
        self.assertEqual(2, sum(1 for _ in await qs.to_list()))


@unittest.skipUnless(ASYNCIO_TEST, 'Motor not installed')
class AsyncIOMotorCollationTestCase(MotorCollationTestCase,
                                    AsyncIOMotorODMTestCase):
    pass


@unittest.skipUnless(TORNADO_TEST, 'Tornado or Motor not installed')
class TornadoMotorCollationTestCase(MotorCollationTestCase,
                                    TornadoMotorODMTestCase):
    pass
