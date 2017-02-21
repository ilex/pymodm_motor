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
import sys
import unittest

from bson.objectid import ObjectId

from pymodm.compat import text_type
from pymodm_motor import fields, MotorMongoModel
from pymodm_motor.context_managers import no_auto_dereference

from test import (
    TORNADO_TEST, ASYNCIO_TEST,
    TornadoMotorODMTestCase, AsyncIOMotorODMTestCase, unittest_run_loop)
from test.models import ParentModel, User

if sys.version_info >= (3, 6):
    from test.py36_test_queryset import (
        TornadoPY36MotorQuerySetTestCase, AsyncIOPY36MotorQuerySetTestCase)


class Vacation(MotorMongoModel):
    destination = fields.CharField()
    travel_method = fields.CharField()
    price = fields.FloatField()


class MotorQuerySetTestCase:

    @unittest_run_loop
    async def set_up_models(self):
        await User(fname='Garden', lname='Tomato', phone=1111111).save()
        await User(fname='Rotten', lname='Tomato', phone=2222222).save()
        await User(fname='Amon', lname='Amarth', phone=3333333).save()
        await User(fname='Garth', lname='Amarth', phone=4444444).save()

    @unittest_run_loop
    async def test_aggregate(self):
        await Vacation.objects.bulk_create([
            Vacation(destination='HAWAII', travel_method='PLANE', price=999),
            Vacation(destination='BIGGEST BALL OF TWINE', travel_method='CAR',
                     price=0.02),
            Vacation(destination='GRAND CANYON', travel_method='CAR',
                     price=123.12),
            Vacation(destination='GRAND CANYON', travel_method='CAR',
                     price=25.31)
        ])
        results = Vacation.objects.raw({'travel_method': 'CAR'}).aggregate(
            {'$group': {'_id': 'destination', 'price': {'$min': '$price'}}},
            {'$sort': {'price': -1}}
        )
        last_price = float('inf')
        async for result in results:
            self.assertGreaterEqual(last_price, result['price'])
            self.assertNotEqual('HAWAII', result['_id'])
            last_price = result['price']

    @unittest_run_loop
    async def test_does_not_exist(self):
        with self.assertRaises(User.DoesNotExist) as ctx:
            await User.objects.get({'fname': 'Tulip'})
        self.assertIsInstance(ctx.exception, ParentModel.DoesNotExist)
        self.assertFalse(
            issubclass(ParentModel.DoesNotExist, User.DoesNotExist))

    @unittest_run_loop
    async def test_multiple_objects_returned(self):
        with self.assertRaises(User.MultipleObjectsReturned):
            await User.objects.get({'lname': 'Tomato'})

    @unittest_run_loop
    async def test_all_to_list(self):
        results = await User.objects.all().to_list()
        self.assertEqual(4, len(results))

    @unittest_run_loop
    async def test_all_async_for(self):
        results = []
        async for item in User.objects.all():
            results.append(item)
        self.assertEqual(4, len(results))

    @unittest_run_loop
    async def test_get(self):
        user = await User.objects.get({'_id': 'Amon'})
        self.assertEqual('Amarth', user.lname)

    @unittest_run_loop
    async def test_count(self):
        self.assertEqual(2,
                         await User.objects.raw({'lname': 'Tomato'}).count())
        self.assertEqual(3, await User.objects.skip(1).count())
        self.assertEqual(1, await User.objects.skip(1).limit(1).count())

    @unittest_run_loop
    async def test_raw(self):
        results = User.objects.raw({'lname': 'Tomato'}).raw({'_id': 'Rotten'})
        self.assertEqual(1, await results.count())

    @unittest_run_loop
    async def test_order_by(self):
        results = []
        async for item in User.objects.order_by([('_id', 1)]):
            results.append(item)
        self.assertEqual('Amarth', results[0].lname)
        self.assertEqual('Tomato', results[1].lname)
        self.assertEqual('Amarth', results[2].lname)
        self.assertEqual('Tomato', results[3].lname)

    @unittest_run_loop
    async def test_project(self):
        results = User.objects.project({'lname': 1})
        async for result in results:
            self.assertIsNotNone(result.lname)
            self.assertIsNotNone(result.pk)
            self.assertIsNone(result.phone)

    @unittest_run_loop
    async def test_only(self):
        results = User.objects.only('phone')
        async for result in results:
            self.assertIsNone(result.lname)
            self.assertIsInstance(result.phone, int)
            # Primary key cannot be projected out.
            self.assertIsNotNone(result.pk)

    @unittest_run_loop
    async def test_exclude(self):
        results = User.objects.exclude('_id').exclude('phone')
        async for result in results:
            self.assertIsNone(result.phone)
            self.assertIsInstance(result.lname, text_type)
            # Primary key cannot be projected out.
            self.assertIsNotNone(result.pk)

    @unittest_run_loop
    async def test_skip(self):
        results = list()
        async for item in User.objects.skip(1):
            results.append(item)
        self.assertEqual(3, len(results))

    @unittest_run_loop
    async def test_limit(self):
        results = list()
        async for item in User.objects.limit(2):
            results.append(item)
        self.assertEqual(2, len(results))

    @unittest_run_loop
    async def test_values(self):
        async for result in User.objects.values():
            self.assertIsInstance(result, dict)

    @unittest_run_loop
    async def test_first(self):
        qs = User.objects.order_by([('phone', 1)])
        result = await qs.first()
        self.assertEqual('Tomato', result.lname)
        # Returns the same result the second time called.
        self.assertEqual(result, await qs.first())

    @unittest_run_loop
    async def test_create(self):
        result = await User.objects.create(
            fname='George',
            lname='Washington')
        retrieved = await User.objects.get({'lname': 'Washington'})
        self.assertEqual(result, retrieved)

    @unittest_run_loop
    async def test_bulk_create(self):
        results = await User.objects.bulk_create(
            User(fname='Louis', lname='Armstrong'))
        self.assertEqual(['Louis'], results)

        results = await User.objects.bulk_create([
            User(fname='Woodrow', lname='Wilson'),
            User(fname='Andrew', lname='Jackson')])
        self.assertEqual(['Woodrow', 'Andrew'], results)
        franklins = [
            User(fname='Benjamin', lname='Franklin'),
            User(fname='Aretha', lname='Franklin')
        ]
        results = await User.objects.bulk_create(franklins, retrieve=True)
        for result in results:
            self.assertIn(result, franklins)

    @unittest_run_loop
    async def test_delete(self):
        self.assertEqual(
            2, await User.objects.raw({'lname': 'Tomato'}).delete())
        results = list()
        async for item in User.objects.all():
            results.append(item)
        self.assertEqual(2, len(results))
        for obj in results:
            self.assertNotEqual(obj.lname, 'Tomato')

    @unittest_run_loop
    async def test_update(self):
        self.assertEqual(
            2, await User.objects.raw({'lname': 'Tomato'}).update(
                {'$set': {'phone': 1234567}}
            ))
        results = list()
        async for item in User.objects.raw({'phone': 1234567}):
            results.append(item)
        self.assertEqual(2, len(results))
        for result in results:
            self.assertEqual('Tomato', result.lname)

        await User.objects.raw({'phone': 7654321}).update(
            {'$set': {'lname': 'Ennis'}},
            upsert=True)
        await User.objects.get({'phone': 7654321})

    @unittest_run_loop
    async def test_getitem(self):
        users = User.objects.order_by([('phone', 1)])
        self.assertEqual(1111111, (await users[0]).phone)
        self.assertEqual(4444444, (await users[3]).phone)

    @unittest_run_loop
    async def test_slice(self):
        users = await User.objects.order_by([('phone', 1)])[2:3]
        for user in users:
            self.assertEqual('Amon', user.fname)
            self.assertEqual('Amarth', user.lname)

    @unittest_run_loop
    async def test_select_related(self):
        class Comment(MotorMongoModel):
            body = fields.CharField()

        class Post(MotorMongoModel):
            body = fields.CharField()
            comments = fields.ListField(fields.ReferenceField(Comment))

        # Create a few objects...
        await Post(body='Nobody read this post').save()
        comments = [
            await Comment(body='This is a great post').save(),
            await Comment(body='Horrible read').save()
        ]
        await Post(body='More popular post', comments=comments).save()

        with no_auto_dereference(Post):
            posts = list()
            async for item in Post.objects.all():
                posts.append(item)
            self.assertIsNone(posts[0].comments)
            self.assertIsInstance(posts[1].comments[0], ObjectId)
            self.assertIsInstance(posts[1].comments[1], ObjectId)

            posts = list()
            async for item in Post.objects.select_related():
                posts.append(item)
            self.assertIsNone(posts[0].comments)
            self.assertEqual(posts[1].comments, comments)


@unittest.skipUnless(ASYNCIO_TEST, 'Motor not installed')
class AsyncIOMotorQuerySetTestCase(MotorQuerySetTestCase,
                                   AsyncIOMotorODMTestCase):

    def setUp(self):
        super().setUp()
        self.set_up_models()


@unittest.skipUnless(TORNADO_TEST, 'Tornado or Motor not installed')
class TornadoMotorQuerySetTestCase(MotorQuerySetTestCase,
                                   TornadoMotorODMTestCase):

    def setUp(self):
        super().setUp()
        self.set_up_models()
