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
import unittest

from pymodm_motor.errors import InvalidModel, ValidationError
from pymodm_motor import MotorMongoModel, CharField, MotorManager

from test import (
    TORNADO_TEST, ASYNCIO_TEST, DB,
    TornadoMotorODMTestCase, AsyncIOMotorODMTestCase, unittest_run_loop)
from test.models import User


class MotorBasicModelTestCase:

    def test_instantiation(self):
        msg = 'Got 5 arguments for only 4 fields'
        with self.assertRaisesRegex(ValueError, msg):
            User('Gary', 1234567, '12 Apple Street', 42, 'cucumber')
        msg = 'Unrecognized field name'
        with self.assertRaisesRegex(ValueError, msg):
            User(last_name='Gygax')
        msg = 'name specified more than once in constructor for User'
        with self.assertRaisesRegex(ValueError, msg):
            User('Gary', fname='Gygax')

    def test_default_manager(self):
        self.assertTrue(isinstance(User.objects, MotorManager))

    @unittest_run_loop
    async def test_save(self):
        await User('Gary').save()
        self.assertEqual('Gary', DB.some_collection.find_one()['_id'])

    @unittest_run_loop
    async def test_delete(self):
        gary = await User('Gary').save()
        self.assertTrue(DB.some_collection.find_one())
        await gary.delete()
        self.assertIsNone(DB.some_collection.find_one())

    @unittest_run_loop
    async def test_refresh_from_db(self):
        gary = await User('Gary').save()
        DB.some_collection.update_one(
            {'_id': 'Gary'},
            {'$set': {'phone': 1234567}})
        await gary.refresh_from_db()
        self.assertEqual(1234567, gary.phone)

    def test_blank_field(self):
        class ModelWithBlankField(MotorMongoModel):
            field = CharField(blank=True)

        instance = ModelWithBlankField(None)
        # No exception.
        instance.full_clean()
        self.assertIsNone(instance.field)

    def test_same_mongo_name(self):
        msg = '.* cannot have the same mongo_name of existing field .*'
        with self.assertRaisesRegex(InvalidModel, msg):
            class SameMongoName(MotorMongoModel):
                field = CharField()
                new_field = CharField(mongo_name='field')

        class Parent(MotorMongoModel):
            field = CharField(mongo_name='child_field')

        with self.assertRaisesRegex(InvalidModel, msg):
            class SameMongoNameAsParent(Parent):
                child_field = CharField()

    @unittest_run_loop
    async def test_save_pk_field_required(self):
        self.assertTrue(User.fname.required)

        # This should raise ValidationError, since we explicitly defined
        # `fname` as the primary_key, but it hasn't been given a value.
        # `fname` should be required:
        # ValidationError: {'fname': ['field is required.']}
        with self.assertRaises(ValidationError) as cm:
            await User().save()

        message = cm.exception.message
        self.assertIsInstance(message, dict)
        self.assertIn('fname', message)
        self.assertIsInstance(message['fname'], list)
        self.assertIn('field is required.', message['fname'])


@unittest.skipUnless(ASYNCIO_TEST, 'Motor not installed')
class AsyncIOMotorBasicModelTestCase(MotorBasicModelTestCase,
                                     AsyncIOMotorODMTestCase):
    pass


@unittest.skipUnless(TORNADO_TEST, 'Tornado or Motor not installed')
class TornadoMotorBasicModelTestCase(MotorBasicModelTestCase,
                                     TornadoMotorODMTestCase):
    pass
