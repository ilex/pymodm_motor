import unittest

from bson.objectid import ObjectId

from pymongo.errors import DuplicateKeyError
from pymongo.write_concern import WriteConcern

from pymodm_motor.context_managers import (
    switch_connection, switch_collection, no_auto_dereference,
    collection_options)
from pymodm_motor import (
    MotorMongoModel, MotorEmbeddedMongoModel, fields)
from pymodm_motor.dereference import dereference

from test import (
    TORNADO_TEST, ASYNCIO_TEST, DB, MONGO_URI, CLIENT,
    TornadoMotorODMTestCase, AsyncIOMotorODMTestCase, unittest_run_loop)


class Game(MotorMongoModel):
    title = fields.CharField()


class Badge(MotorEmbeddedMongoModel):
    name = fields.CharField()
    game = fields.ReferenceField(Game)


class User(MotorMongoModel):
    fname = fields.CharField()
    friend = fields.ReferenceField('test_context_managers.User')
    badges = fields.EmbeddedDocumentListField(Badge)


class MotorContextManagersTestCase:

    @unittest_run_loop
    async def test_switch_connection(self):
        with switch_connection(User, 'backups') as BackupUser:
            await BackupUser('Bert').save()
        await User('Ernie').save()

        self.assertEqual('Ernie', DB.user.find_one()['fname'])
        self.assertEqual('Bert', self.db.user.find_one()['fname'])

    @unittest_run_loop
    async def test_switch_collection(self):
        with switch_collection(User, 'copies') as CopiedUser:
            await CopiedUser('Bert').save()
        await User('Ernie').save()

        self.assertEqual('Ernie', DB.user.find_one()['fname'])
        self.assertEqual('Bert', DB.copies.find_one()['fname'])

    @unittest_run_loop
    async def test_no_auto_dereference(self):
        game = await Game('Civilization').save()
        badge = Badge(name='World Domination', game=game)
        ernie = await User(fname='Ernie').save()
        bert = await User(fname='Bert', badges=[badge], friend=ernie).save()

        await bert.refresh_from_db()

        # MotorMongoModel does not do auto dereferencing
        self.assertIsInstance(bert.friend, ObjectId)
        self.assertIsInstance(bert.badges[0].game, ObjectId)

        with no_auto_dereference(User):
            self.assertIsInstance(bert.friend, ObjectId)
            self.assertIsInstance(bert.badges[0].game, ObjectId)

        await dereference(bert)
        self.assertIsInstance(bert.friend, User)
        self.assertIsInstance(bert.badges[0].game, Game)

    @unittest_run_loop
    async def test_collection_options(self):
        user_id = ObjectId()
        await User(_id=user_id).save()
        wc = WriteConcern(w=0)
        with collection_options(User, write_concern=wc):
            await User(_id=user_id).save(force_insert=True)
        with self.assertRaises(DuplicateKeyError):
            await User(_id=user_id).save(force_insert=True)


@unittest.skipUnless(ASYNCIO_TEST, 'Motor not installed')
class AsyncIOMotorContextManagersTestCase(MotorContextManagersTestCase,
                                          AsyncIOMotorODMTestCase):
    def setUp(self):
        super().setUp()
        self.db_name = 'alternate-db'
        self.connect_to_db(MONGO_URI, self.db_name, alias='backups')
        self.db = CLIENT[self.db_name]

    def tearDown(self):
        super().tearDown()
        CLIENT.drop_database(self.db_name)


@unittest.skipUnless(TORNADO_TEST, 'Tornado or Motor not installed')
class TornadoMotorContextManagersTestCase(MotorContextManagersTestCase,
                                          TornadoMotorODMTestCase):
    def setUp(self):
        super().setUp()
        self.db_name = 'alternate-db'
        self.connect_to_db(MONGO_URI, self.db_name, alias='backups')
        self.db = CLIENT[self.db_name]

    def tearDown(self):
        super().tearDown()
        CLIENT.drop_database(self.db_name)
