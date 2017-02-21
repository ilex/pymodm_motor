import unittest

from pymodm_motor import fields, MotorMongoModel
from pymodm_motor.context_managers import switch_collection, switch_connection
from pymongo import IndexModel, ASCENDING

from test import (
    TORNADO_TEST, ASYNCIO_TEST, DB, MONGO_URI, CLIENT,
    TornadoMotorODMTestCase, AsyncIOMotorODMTestCase, unittest_run_loop)


class MotorModelIndexesTestCase:

    def setUp(self):
        super().setUp()
        self.db_name = 'alternate-db'
        self.connect_to_db(MONGO_URI, self.db_name, alias='backups')
        self.db = CLIENT[self.db_name]

    def tearDown(self):
        super().tearDown()
        CLIENT.drop_database(self.db_name)

    @unittest_run_loop
    async def test_model_with_indexes_auto_creation(self):
        class ModelWithIndexes(MotorMongoModel):
            product_id = fields.IntegerField()
            name = fields.CharField()

            class Meta:
                indexes = [
                    IndexModel(
                        [('product_id', ASCENDING), ('name', ASCENDING)],
                        unique=True, name='product_name')
                ]

        # ensure collection is created
        await ModelWithIndexes(product_id=1, name='item').save()

        index_info = DB.model_with_indexes.index_information()
        # index 'product_name' should not be created
        self.assertNotIn('product_name', index_info)

    @unittest_run_loop
    async def test_model_without_indexes_auto_creation(self):
        class ModelWithoutIndexes(MotorMongoModel):
            product_id = fields.IntegerField()
            name = fields.CharField()

        # ensure collection is created
        await ModelWithoutIndexes(product_id=1, name='item').save()

        index_info = DB.model_without_indexes.index_information()
        # there should be only _id index
        self.assertEqual(len(index_info), 1)

    @unittest_run_loop
    async def test_model_with_empty_indexes_auto_creation(self):
        class ModelWithEmptyIndexes(MotorMongoModel):
            product_id = fields.IntegerField()
            name = fields.CharField()

            class Meta:
                indexes = []

        # ensure collection is created
        await ModelWithEmptyIndexes(product_id=1, name='item').save()

        index_info = DB.model_with_empty_indexes.index_information()
        # there should be only _id index
        self.assertEqual(len(index_info), 1)

    @unittest_run_loop
    async def test_model_with_indexes_create_indexes_explicitly(self):
        class ModelWithIndexes(MotorMongoModel):
            product_id = fields.IntegerField()
            name = fields.CharField()

            class Meta:
                indexes = [
                    IndexModel(
                        [('product_id', ASCENDING), ('name', ASCENDING)],
                        unique=True, name='product_name')
                ]

        # ensure collection is created
        await ModelWithIndexes(product_id=1, name='item').save()
        # create indexes explicitly
        await ModelWithIndexes.objects.create_indexes()
        index_info = DB.model_with_indexes.index_information()

        self.assertTrue(index_info['product_name']['unique'])

    @unittest_run_loop
    async def test_model_without_indexes_create_indexes_explicitly(self):
        class ModelWithoutIndexes(MotorMongoModel):
            product_id = fields.IntegerField()
            name = fields.CharField()

        # ensure collection is created
        await ModelWithoutIndexes(product_id=1, name='item').save()
        # create indexes explicitly
        await ModelWithoutIndexes.objects.create_indexes()
        index_info = DB.model_without_indexes.index_information()

        # there should be only _id index
        self.assertEqual(len(index_info), 1)

    @unittest_run_loop
    async def test_model_with_empty_indexes_create_indexes_explicitly(self):
        class ModelWithEmptyIndexes(MotorMongoModel):
            product_id = fields.IntegerField()
            name = fields.CharField()

            class Meta:
                indexes = []

        # ensure collection is created
        await ModelWithEmptyIndexes(product_id=1, name='item').save()
        # create indexes explicitly
        await ModelWithEmptyIndexes.objects.create_indexes()
        index_info = DB.model_with_empty_indexes.index_information()

        # there should be only _id index
        self.assertEqual(len(index_info), 1)

    @unittest_run_loop
    async def test_create_indexes_switch_collection_context_manager(self):
        class ModelWithIndexes(MotorMongoModel):
            product_id = fields.IntegerField()
            name = fields.CharField()

            class Meta:
                indexes = [
                    IndexModel(
                        [('product_id', ASCENDING), ('name', ASCENDING)],
                        unique=True, name='product_name')
                ]

        context_manager = switch_collection(ModelWithIndexes,
                                            'copied_model_with_indexes')
        with context_manager as CopiedModelWithIndexes:
            await CopiedModelWithIndexes.objects.create_indexes()

        index_info = DB.copied_model_with_indexes.index_information()
        self.assertIn('product_name', index_info)

        await ModelWithIndexes(product_id=1, name='item').save()
        index_info = DB.model_with_indexes.index_information()
        self.assertNotIn('product_name', index_info)

    @unittest_run_loop
    async def test_create_indexes_switch_connection_context_manager(self):
        class ModelWithIndexes(MotorMongoModel):
            product_id = fields.IntegerField()
            name = fields.CharField()

            class Meta:
                indexes = [
                    IndexModel(
                        [('product_id', ASCENDING), ('name', ASCENDING)],
                        unique=True, name='product_name')
                ]

        context_manager = switch_connection(ModelWithIndexes, 'backups')
        with context_manager as BackupModelWithIndexes:
            await BackupModelWithIndexes.objects.create_indexes()

        index_info = self.db.model_with_indexes.index_information()
        self.assertIn('product_name', index_info)

        await ModelWithIndexes(product_id=1, name='item').save()
        index_info = DB.model_with_indexes.index_information()
        self.assertNotIn('product_name', index_info)


@unittest.skipUnless(ASYNCIO_TEST, 'Motor not installed')
class AsyncIOMotorModelIndexesTestCase(MotorModelIndexesTestCase,
                                       AsyncIOMotorODMTestCase):
    pass


@unittest.skipUnless(TORNADO_TEST, 'Tornado or Motor not installed')
class TornadoMotorModelIndexesTestCase(MotorModelIndexesTestCase,
                                       TornadoMotorODMTestCase):
    pass
