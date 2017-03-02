import unittest

from bson import ObjectId

from pymodm_motor import MotorMongoModel, MotorEmbeddedMongoModel, fields
from pymodm_motor.context_managers import no_auto_dereference
from pymodm_motor.dereference import dereference

from test import (
    TORNADO_TEST, ASYNCIO_TEST,
    TornadoMotorODMTestCase, AsyncIOMotorODMTestCase, unittest_run_loop)


class Post(MotorMongoModel):
    title = fields.CharField(primary_key=True)
    body = fields.CharField()


class Comment(MotorMongoModel):
    body = fields.CharField()
    post = fields.ReferenceField(Post)


# Contrived models to test highly-nested structures.
class CommentWrapper(MotorEmbeddedMongoModel):
    comments = fields.ListField(fields.ReferenceField(Comment))


class CommentWrapperList(MotorMongoModel):
    wrapper = fields.EmbeddedDocumentListField(CommentWrapper)


class MotorDereferenceTestCase:

    @unittest_run_loop
    async def test_leaf_field_dereference(self):
        # Test basic dereference of a ReferenceField directly in the Model.
        post = await Post(title='This is a post.').save()
        comment = await Comment(
            body='This is a comment on the post.', post=post).save()

        # Force ObjectIds on comment.
        await comment.refresh_from_db()
        with no_auto_dereference(Comment):
            self.assertEqual(comment.post, post.title)

            await dereference(comment)
            self.assertEqual(comment.post, post)

    @unittest_run_loop
    async def test_list_dereference(self):
        # Test dereferencing items stored in a ListField(ReferenceField(X))
        class OtherModel(MotorMongoModel):
            name = fields.CharField()

        class Container(MotorMongoModel):
            one_to_many = fields.ListField(fields.ReferenceField(OtherModel))

        m1 = await OtherModel('a').save()
        m2 = await OtherModel('b').save()
        container = await Container([m1, m2]).save()

        # Force ObjectIds.
        await container.refresh_from_db()
        with no_auto_dereference(container):
            for item in container.one_to_many:
                self.assertIsInstance(item, ObjectId)

        await dereference(container)
        self.assertEqual([m1, m2], container.one_to_many)

    @unittest_run_loop
    async def test_highly_nested_dereference(self):
        # Test {outer: [{inner:[references]}]}
        comments = [
            await Comment('comment 1').save(),
            await Comment('comment 2').save()
        ]
        wrapper = CommentWrapper(comments)
        wrapper_list = await CommentWrapperList([wrapper]).save()

        # Force ObjectIds.
        await wrapper_list.refresh_from_db()

        await dereference(wrapper_list)

        for comment in wrapper_list.wrapper[0].comments:
            self.assertIsInstance(comment, Comment)

    @unittest_run_loop
    async def test_dereference_fields(self):
        # Test dereferencing only specific fields.

        # Contrived Models that contains more than one ReferenceField at
        # different levels of nesting.
        class MultiReferenceModelEmbed(MotorMongoModel):
            comments = fields.ListField(fields.ReferenceField(Comment))
            posts = fields.ListField(fields.ReferenceField(Post))

        class MultiReferenceModel(MotorMongoModel):
            comments = fields.ListField(fields.ReferenceField(Comment))
            posts = fields.ListField(fields.ReferenceField(Post))
            embeds = fields.EmbeddedDocumentListField(MultiReferenceModelEmbed)

        post = await Post(title='This is a post.').save()
        comments = [
            await Comment('comment 1', post).save(),
            await Comment('comment 2').save()
        ]
        embed = MultiReferenceModelEmbed(
            comments=comments,
            posts=[post])
        multi_ref = await MultiReferenceModel(
            comments=comments,
            posts=[post],
            embeds=[embed]).save()

        # Force ObjectIds.
        await multi_ref.refresh_from_db()

        await dereference(multi_ref, fields=['embeds.comments', 'posts'])

        await post.refresh_from_db()
        for comment in comments:
            await comment.refresh_from_db()
        with no_auto_dereference(MultiReferenceModel):
            self.assertEqual([post], multi_ref.posts)
            self.assertEqual(comments, multi_ref.embeds[0].comments)
            # multi_ref.comments has not been dereferenced.
            self.assertIsInstance(multi_ref.comments[0], ObjectId)

    @unittest.expectedFailure
    @unittest_run_loop
    async def test_auto_dereference(self):
        # Test automatic dereferencing.

        post = await Post(title='This is a post.').save()
        comments = [
            await Comment('comment 1', post).save(),
            await Comment('comment 2', post).save()
        ]
        wrapper = CommentWrapper(comments)
        wrapper_list = await CommentWrapperList([wrapper]).save()

        await wrapper_list.refresh_from_db()

        self.assertEqual(
            'This is a post.',
            wrapper_list.wrapper[0].comments[0].post.title
        )

    '''
    @unittest_run_loop
    async def _test_unhashable_id(self):
        # Test that we can reference a model whose id type is unhashable
        # e.g. a dict, list, etc.
        class CardIdentity(MotorEmbeddedMongoModel):
            HEARTS, DIAMONDS, SPADES, CLUBS = 0, 1, 2, 3

            rank = fields.IntegerField(min_value=0, max_value=12)
            suit = fields.IntegerField(
                choices=(HEARTS, DIAMONDS, SPADES, CLUBS))

        class Card(MotorMongoModel):
            id = fields.EmbeddedDocumentField(CardIdentity, primary_key=True)
            flavor = fields.CharField()

        class Hand(MotorMongoModel):
            cards = fields.ListField(fields.ReferenceField(Card))

        cards = [
            await Card(CardIdentity(4, CardIdentity.CLUBS)).save(),
            await Card(CardIdentity(12, CardIdentity.SPADES)).save()
        ]
        hand = await Hand(cards).save()
        await hand.refresh_from_db()
        await dereference(hand)
        self.assertIsInstance(hand.cards[0], Card)
        self.assertIsInstance(hand.cards[1], Card)
    '''

    async def _test_unhashable_id(self, final_value=True):
        # Test that we can reference a model whose id type is unhashable
        # e.g. a dict, list, etc.
        class CardIdentity(MotorEmbeddedMongoModel):
            HEARTS, DIAMONDS, SPADES, CLUBS = 0, 1, 2, 3

            rank = fields.IntegerField(min_value=0, max_value=12)
            suit = fields.IntegerField(
                choices=(HEARTS, DIAMONDS, SPADES, CLUBS))

            class Meta:
                final = final_value

        class Card(MotorMongoModel):
            id = fields.EmbeddedDocumentField(CardIdentity, primary_key=True)
            flavor = fields.CharField()

        class Hand(MotorMongoModel):
            cards = fields.ListField(fields.ReferenceField(Card))

        cards = [
            await Card(CardIdentity(4, CardIdentity.CLUBS)).save(),
            await Card(CardIdentity(12, CardIdentity.SPADES)).save()
        ]
        hand = await Hand(cards).save()

        # test auto dereferencing
        # note that pymodm_motor hasn't auto dereferencing
        await hand.refresh_from_db()
        self.assertIsInstance(hand.cards[0], CardIdentity)
        self.assertEqual(hand.cards[0].rank, 4)
        self.assertIsInstance(hand.cards[1], CardIdentity)
        self.assertEqual(hand.cards[1].rank, 12)

        with no_auto_dereference(hand):
            await hand.refresh_from_db()
            await dereference(hand)
            self.assertIsInstance(hand.cards[0], Card)
            self.assertEqual(hand.cards[0].id.rank, 4)
            self.assertIsInstance(hand.cards[1], Card)
            self.assertEqual(hand.cards[1].id.rank, 12)

    @unittest_run_loop
    async def test_unhashable_id_final_true(self):
        await self._test_unhashable_id(final_value=True)

    @unittest_run_loop
    async def test_unhashable_id_final_false(self):
        await self._test_unhashable_id(final_value=False)

    @unittest_run_loop
    async def test_reference_not_found(self):
        post = await Post(title='title').save()
        comment = await Comment(body='this is a comment', post=post).save()
        await post.delete()
        self.assertEqual(await Post.objects.count(), 0)
        await comment.refresh_from_db()
        await dereference(comment)
        self.assertIsNone(comment.post)

    @unittest_run_loop
    async def test_list_embedded_reference_dereference(self):
        # Test dereferencing items stored in a
        # ListField(EmbeddedDocument(ReferenceField(X)))
        class OtherModel(MotorMongoModel):
            name = fields.CharField()

        class OtherRefModel(MotorEmbeddedMongoModel):
            ref = fields.ReferenceField(OtherModel)

        class Container(MotorMongoModel):
            lst = fields.EmbeddedDocumentListField(OtherRefModel)

        m1 = await OtherModel('Aaron').save()
        m2 = await OtherModel('Bob').save()

        container = Container(lst=[OtherRefModel(ref=m1),
                                   OtherRefModel(ref=m2)])
        await container.save()

        # Force ObjectIds.
        await container.refresh_from_db()
        await dereference(container)

        # access through raw dicts not through __get__ of the field
        # cause __get__ can perform a query to db for reference fields
        # to dereference them using dereference_id function
        self.assertEqual(
            container._data['lst'][0]._data['ref']['name'],
            'Aaron')

        self.assertEqual(container.lst[0].ref.name, 'Aaron')

    @unittest_run_loop
    async def test_embedded_reference_dereference(self):
        # Test dereferencing items stored in a
        # EmbeddedDocument(ReferenceField(X))
        class OtherModel(MotorMongoModel):
            name = fields.CharField()

        class OtherRefModel(MotorEmbeddedMongoModel):
            ref = fields.ReferenceField(OtherModel)

        class Container(MotorMongoModel):
            emb = fields.EmbeddedDocumentField(OtherRefModel)

        m1 = await OtherModel('Aaron').save()

        container = Container(emb=OtherRefModel(ref=m1))
        await container.save()

        # Force ObjectIds.
        with no_auto_dereference(container):
            await container.refresh_from_db()
            self.assertIsInstance(container.emb.ref, ObjectId)
            await dereference(container)
            self.assertIsInstance(container.emb.ref, OtherModel)
            self.assertEqual(container.emb.ref.name, 'Aaron')

    @unittest_run_loop
    async def test_dereference_reference_not_found(self):
        post = await Post(title='title').save()
        comment = await Comment(body='this is a comment', post=post).save()
        await post.delete()
        self.assertEqual(await Post.objects.count(), 0)
        await comment.refresh_from_db()
        with no_auto_dereference(comment):
            await dereference(comment)
            self.assertIsNone(comment.post)

    @unittest_run_loop
    async def test_dereference_models_with_same_id(self):
        class User(MotorMongoModel):
            name = fields.CharField(primary_key=True)

        class CommentWithUser(MotorMongoModel):
            body = fields.CharField()
            post = fields.ReferenceField(Post)
            user = fields.ReferenceField(User)

        post = await Post(title='Bob').save()
        user = await User(name='Bob').save()

        comment = await CommentWithUser(
            body='this is a comment',
            post=post,
            user=user).save()

        await comment.refresh_from_db()
        with no_auto_dereference(CommentWithUser):
            await dereference(comment)
            self.assertIsInstance(comment.post, Post)
            self.assertIsInstance(comment.user, User)

    @unittest_run_loop
    async def test_dereference_missed_reference_field(self):
        comment = await Comment(body='Body Comment').save()
        with no_auto_dereference(comment):
            await comment.refresh_from_db()
            await dereference(comment)
            self.assertIsNone(comment.post)

    @unittest_run_loop
    async def test_dereference_dereferenced_reference(self):
        class CommentContainer(MotorMongoModel):
            ref = fields.ReferenceField(Comment)

        post = await Post(title='title').save()
        comment = await Comment(body='Comment Body', post=post).save()

        container = await CommentContainer(ref=comment).save()

        with no_auto_dereference(comment), no_auto_dereference(container):
            await comment.refresh_from_db()
            await container.refresh_from_db()
            container.ref = comment
            self.assertEqual(container.ref.post, 'title')
            await dereference(container)
            self.assertIsInstance(container.ref.post, Post)
            self.assertEqual(container.ref.post.title, 'title')
            await dereference(container)
            self.assertIsInstance(container.ref.post, Post)
            self.assertEqual(container.ref.post.title, 'title')


@unittest.skipUnless(ASYNCIO_TEST, 'Motor not installed')
class AsyncIOMotorDereferenceTestCase(MotorDereferenceTestCase,
                                      AsyncIOMotorODMTestCase):
    pass


@unittest.skipUnless(TORNADO_TEST, 'Tornado or Motor not installed')
class TornadoMotorDereferenceTestCase(MotorDereferenceTestCase,
                                      TornadoMotorODMTestCase):
    pass
