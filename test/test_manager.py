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

from pymodm_motor import (
    fields, MotorMongoModel, MotorManager, MotorQuerySet)

from test import (
    TORNADO_TEST, ASYNCIO_TEST,
    TornadoMotorODMTestCase, AsyncIOMotorODMTestCase, unittest_run_loop)


class CustomQuerySet(MotorQuerySet):
    def authors(self):
        """Return a QuerySet over documents representing authors."""
        return self.raw({'role': 'A'})

    def editors(self):
        """Return a QuerySet over documents representing editors."""
        return self.raw({'role': 'E'})


CustomManager = MotorManager.from_queryset(CustomQuerySet)


class BookCredit(MotorMongoModel):
    first_name = fields.CharField()
    last_name = fields.CharField()
    role = fields.CharField(choices=[('A', 'author'), ('E', 'editor')])

    contributors = CustomManager()
    more_contributors = CustomManager()


class MotorManagerTestCase:

    def test_motor_default_manager(self):
        class Model(MotorMongoModel):
            pass

        self.assertIsInstance(Model.objects, MotorManager)
        self.assertIs(Model._default_manager, Model.objects)

    def test_default_manager(self):
        # No auto-created Manager, since we defined our own.
        self.assertFalse(hasattr(BookCredit, 'objects'))
        # Check that our custom Manager was installed.
        self.assertIsInstance(BookCredit.contributors, CustomManager)
        # Contributors should be the default manager, not more_contributors.
        self.assertIs(BookCredit.contributors, BookCredit._default_manager)

    def test_get_queryset(self):
        self.assertIsInstance(
            BookCredit.contributors.get_queryset(), CustomQuerySet)

    def test_access(self):
        credit = BookCredit(first_name='Frank', last_name='Herbert', role='A')
        msg = "Manager isn't accessible via BookCredit instances"
        with self.assertRaisesRegex(AttributeError, msg):
            credit.contributors

    def test_wrappers(self):
        manager = BookCredit.contributors
        self.assertTrue(hasattr(manager, 'editors'))
        self.assertTrue(hasattr(manager, 'authors'))
        self.assertEqual(
            CustomQuerySet.editors.__doc__, manager.editors.__doc__)
        self.assertEqual(
            CustomQuerySet.authors.__doc__, manager.authors.__doc__)

    @unittest_run_loop
    async def test_manager_methods(self):
        await BookCredit(
            first_name='Frank', last_name='Herbert', role='A').save()
        await BookCredit(
            first_name='Bob', last_name='Edison', role='E').save()

        author = await BookCredit.contributors.authors().first()
        self.assertEqual(author.first_name, 'Frank')

        editor = await BookCredit.contributors.editors().first()
        self.assertEqual(editor.first_name, 'Bob')


@unittest.skipUnless(ASYNCIO_TEST, 'Motor not installed')
class AsyncIOMotorManagerTestCase(MotorManagerTestCase,
                                  AsyncIOMotorODMTestCase):
    pass


@unittest.skipUnless(TORNADO_TEST, 'Tornado or Motor not installed')
class TornadoMotorManagerTestCase(MotorManagerTestCase,
                                  TornadoMotorODMTestCase):
    pass
