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

from pymodm_motor import fields, MotorMongoModel
from pymodm_motor.errors import OperationError

from test import (
    TORNADO_TEST, ASYNCIO_TEST,
    TornadoMotorODMTestCase, AsyncIOMotorODMTestCase, unittest_run_loop)


class ReferencedModel(MotorMongoModel):
    pass


class ReferencingModel(MotorMongoModel):
    ref = fields.ReferenceField(ReferencedModel)


# Model classes that both reference each other.
class A(MotorMongoModel):
    ref = fields.ReferenceField('B')


class B(MotorMongoModel):
    ref = fields.ReferenceField(A)


class MotorDeleteRulesTestCase:

    @unittest_run_loop
    async def test_nullify(self):
        ReferencedModel.register_delete_rule(
            ReferencingModel, 'ref', fields.ReferenceField.NULLIFY)
        reffed = await ReferencedModel().save()
        reffing = await ReferencingModel(reffed).save()
        await reffed.delete()
        await reffing.refresh_from_db()
        self.assertIsNone(reffing.ref)

    # Test the on_delete attribute for one rule.
    @unittest_run_loop
    async def test_nullify_on_delete_attribute(self):
        class ReferencingModelWithAttribute(MotorMongoModel):
            ref = fields.ReferenceField(
                ReferencedModel,
                on_delete=fields.ReferenceField.NULLIFY)

        reffed = await ReferencedModel().save()
        reffing = await ReferencingModelWithAttribute(reffed).save()
        await reffed.delete()
        await reffing.refresh_from_db()
        self.assertIsNone(reffing.ref)

    def test_bidirectional_on_delete_attribute(self):
        msg = 'Cannot specify on_delete without providing a Model class'
        with self.assertRaisesRegex(ValueError, msg):
            class ReferencingModelWithAttribute(MotorMongoModel):
                ref = fields.ReferenceField(
                    # Cannot specify class a string.
                    'ReferencedModel',
                    on_delete=fields.ReferenceField.NULLIFY)

    @unittest_run_loop
    async def test_cascade(self):
        ReferencedModel.register_delete_rule(
            ReferencingModel, 'ref', fields.ReferenceField.CASCADE)
        reffed = await ReferencedModel().save()
        await ReferencingModel(reffed).save()
        await reffed.delete()
        self.assertEqual(0, await ReferencingModel.objects.count())

    @unittest_run_loop
    async def test_infinite_cascade(self):
        A.register_delete_rule(B, 'ref', fields.ReferenceField.CASCADE)
        B.register_delete_rule(A, 'ref', fields.ReferenceField.CASCADE)
        a = await A().save()
        b = await B().save()
        a.ref = b
        b.ref = a
        await a.save()
        await b.save()
        # No SystemError due to infinite recursion.
        await a.delete()
        self.assertFalse(await A.objects.count())
        self.assertFalse(await B.objects.count())

    @unittest_run_loop
    async def test_deny(self):
        ReferencedModel.register_delete_rule(
            ReferencingModel, 'ref', fields.ReferenceField.DENY)
        reffed = await ReferencedModel().save()
        await ReferencingModel(reffed).save()
        with self.assertRaises(OperationError):
            await ReferencedModel.objects.delete()
        with self.assertRaises(OperationError):
            await reffed.delete()

    @unittest_run_loop
    async def test_pull(self):
        class MultiReferencingModel(MotorMongoModel):
            refs = fields.ListField(fields.ReferenceField(ReferencedModel))

        ReferencedModel.register_delete_rule(
            MultiReferencingModel, 'refs', fields.ReferenceField.PULL)

        refs = []
        for i in range(3):
            refs.append(await ReferencedModel().save())

        multi_reffing = await MultiReferencingModel(refs).save()

        await refs[0].delete()
        await multi_reffing.refresh_from_db()
        self.assertEqual(2, len(multi_reffing.refs))

    @unittest_run_loop
    async def test_bidirectional(self):
        A.register_delete_rule(B, 'ref', fields.ReferenceField.DENY)
        B.register_delete_rule(A, 'ref', fields.ReferenceField.NULLIFY)

        a = await A().save()
        b = await B(a).save()
        a.ref = b
        await a.save()

        with self.assertRaises(OperationError):
            await a.delete()
        await b.delete()
        await a.refresh_from_db()
        self.assertIsNone(a.ref)

    @unittest_run_loop
    async def test_bidirectional_order(self):
        A.register_delete_rule(B, 'ref', fields.ReferenceField.DENY)
        B.register_delete_rule(A, 'ref', fields.ReferenceField.CASCADE)

        a = await A().save()
        b = await B(a).save()
        a.ref = b
        await a.save()

        # Cannot delete A while referenced by a B.
        with self.assertRaises(OperationError):
            await a.delete()
        # OK to delete a B, and doing so deletes all referencing A objects.
        await b.delete()
        self.assertFalse(await A.objects.count())
        self.assertFalse(await B.objects.count())


@unittest.skipUnless(ASYNCIO_TEST, 'Motor not installed')
class AsyncIOMotorDeleteRulesTestCase(MotorDeleteRulesTestCase,
                                      AsyncIOMotorODMTestCase):

    def tearDown(self):
        super().tearDown()
        # Remove all delete rules.
        for model_class in (ReferencedModel, ReferencingModel, A, B):
            model_class._mongometa.delete_rules.clear()


@unittest.skipUnless(TORNADO_TEST, 'Tornado or Motor not installed')
class TornadoMotorDeleteRulesTestCase(MotorDeleteRulesTestCase,
                                      TornadoMotorODMTestCase):
    def tearDown(self):
        super().tearDown()
        # Remove all delete rules.
        for model_class in (ReferencedModel, ReferencingModel, A, B):
            model_class._mongometa.delete_rules.clear()
