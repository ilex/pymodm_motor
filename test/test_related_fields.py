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

"""Test Embedded and Referenced documents."""
import unittest
from bson.objectid import ObjectId

from pymodm_motor import MotorMongoModel, MotorEmbeddedMongoModel, fields
from pymodm_motor.context_managers import no_auto_dereference
from pymodm_motor.dereference import dereference
from pymodm_motor.errors import ValidationError

from test import (
    TORNADO_TEST, ASYNCIO_TEST, DB,
    TornadoMotorODMTestCase, AsyncIOMotorODMTestCase, unittest_run_loop)


class Contributor(MotorMongoModel):
    name = fields.CharField()
    thumbnail = fields.EmbeddedDocumentField('Image')


class Image(MotorEmbeddedMongoModel):
    image_url = fields.CharField(required=True)
    alt_text = fields.CharField()
    photographer = fields.ReferenceField(Contributor)


class Post(MotorMongoModel):
    body = fields.CharField()
    images = fields.EmbeddedDocumentListField(Image)


class Comment(MotorMongoModel):
    body = fields.CharField()
    post = fields.ReferenceField(Post)


class MotorRelatedFieldsTestCase:

    @unittest_run_loop
    async def test_basic_reference(self):
        post = Post(body='This is a post.')
        comment = Comment(body='Love your post!', post=post)
        await post.save()
        self.assertTrue(post._id)

        await comment.save()
        loaded_comment = await dereference(await Comment.objects.first())
        self.assertEqual(post, loaded_comment.post)

    def test_assign_id_to_reference_field(self):
        # No ValidationError raised.
        Comment(post=1234).full_clean()

    @unittest_run_loop
    async def test_validate_embedded_document(self):
        with self.assertRaisesRegex(ValidationError, 'field is required'):
            # Image has all fields left blank, which isn't allowed.
            await Contributor(
                name='Mr. Contributor', thumbnail=Image()
            ).save()
        # Test with a dict.
        with self.assertRaisesRegex(ValidationError, 'field is required'):
            await Contributor(name='Mr. Contributor', thumbnail={
                'alt_text': ('a picture of nothing, '
                             'since there is no image_url.')
            }).save()

    @unittest_run_loop
    async def test_validate_embedded_document_list(self):
        with self.assertRaisesRegex(ValidationError, 'field is required'):
            await Post(images=[Image(alt_text='Vast, empty space.')]).save()
        with self.assertRaisesRegex(ValidationError, 'field is required'):
            await Post(images=[{'alt_text': 'Vast, empty space.'}]).save()

    @unittest_run_loop
    async def test_reference_errors(self):
        post = Post(body='This is a post.')
        comment = Comment(body='Love your post!', post=post)

        # post has not yet been saved to the database.
        with self.assertRaises(ValidationError) as cm:
            comment.full_clean()
        message = cm.exception.message
        self.assertIn('post', message)
        self.assertEqual(
            ['Referenced documents must be saved to the database first.'],
            message['post'])

        # Cannot save document when reference is unresolved.
        with self.assertRaises(ValidationError) as cm:
            await comment.save()
        self.assertIn('post', message)
        self.assertEqual(
            ['Referenced documents must be saved to the database first.'],
            message['post'])

    @unittest_run_loop
    async def test_embedded_document(self):
        contr = Contributor(name='Shep')
        # embedded field is not required.
        contr.full_clean()
        await contr.save()

        # Attach an image.
        thumb = Image(image_url='/images/shep.png', alt_text="It's Shep.")
        contr.thumbnail = thumb
        await contr.save()

        self.assertEqual(thumb, (await Contributor.objects.first()).thumbnail)

    @unittest_run_loop
    async def test_embedded_document_list(self):
        images = [
            Image(image_url='/images/kittens.png',
                  alt_text='some kittens'),
            Image(image_url='/images/blobfish.png',
                  alt_text='some kittens fighting a blobfish.')
        ]
        post = Post(body='Look at my fantastic photography.',
                    images=images)

        # Images get saved when the parent object is saved.
        await post.save()

        # Embedded documents are converted to their Model type when retrieved.
        retrieved_post = await Post.objects.first()
        self.assertEqual(images, retrieved_post.images)

    @unittest_run_loop
    async def test_refresh_from_db(self):
        post = Post(body='This is a post.')
        comment = Comment(body='This is a comment on the post.',
                          post=post)
        await post.save()
        await comment.save()

        await comment.refresh_from_db()

        with no_auto_dereference(Comment):
            self.assertIsInstance(comment.post, ObjectId)

        # Use PyMongo to update the comment, then update the Comment instance's
        # view of itself.

        DB.comment.update_one(
            {'_id': comment.pk}, {'$set': {'body': 'Edited comment.'}})
        # Set the comment's "post" to something else.
        other_post = Post(body='This is a different post.')
        comment.post = other_post
        await comment.refresh_from_db(fields=['body'])
        self.assertEqual('Edited comment.', comment.body)
        # "post" field is gone, since it wasn't part of the projection.
        self.assertIsNone(comment.post)

    @unittest_run_loop
    async def test_circular_reference(self):
        class ReferenceA(MotorMongoModel):
            ref = fields.ReferenceField('ReferenceB')

        class ReferenceB(MotorMongoModel):
            ref = fields.ReferenceField(ReferenceA)

        a = await ReferenceA().save()
        b = await ReferenceB().save()
        a.ref = b
        b.ref = a
        await a.save()
        await b.save()

        self.assertEqual(a, await ReferenceA.objects.first())
        with no_auto_dereference(ReferenceA):
            self.assertEqual(b.pk, (await ReferenceA.objects.first()).ref)
        self.assertEqual(
            b, (await ReferenceA.objects.select_related().first()).ref)

    @unittest_run_loop
    async def test_cascade_save(self):
        photographer = await Contributor('Curly').save()
        image = Image('kitten.png', 'kitten', photographer)
        post = Post('This is a post.', [image])
        # Photographer has already been saved to the database. Let's change it.
        photographer_thumbnail = Image('curly.png', "It's Curly.")
        photographer.thumbnail = photographer_thumbnail
        post.body += "edit: I'm a real author because I have a thumbnail now."
        # {'body': 'This is a post', 'images': [{
        #     'image_url': 'stew.png', 'photographer': {
        #         'name': 'Curly', 'thumbnail': {
        #             'image_url': 'curly.png', 'alt_text': "It's Curly."}
        #     }]
        # }
        await post.save(cascade=True)
        await post.refresh_from_db()
        await dereference(post)
        self.assertEqual(
            post.images[0].photographer.thumbnail, photographer_thumbnail)

    @unittest_run_loop
    async def test_coerce_reference_type(self):
        post = await Post('this is a post').save()
        post_id = str(post.pk)
        comment = await Comment(body='this is a comment', post=post_id).save()
        await comment.refresh_from_db()
        await dereference(comment)
        self.assertEqual('this is a post', comment.post.body)


@unittest.skipUnless(ASYNCIO_TEST, 'Motor not installed')
class AsyncIOMotorRelatedFieldsTestCase(MotorRelatedFieldsTestCase,
                                        AsyncIOMotorODMTestCase):
    pass


@unittest.skipUnless(TORNADO_TEST, 'Tornado or Motor not installed')
class TornadoMotorRelatedFieldsTestCase(MotorRelatedFieldsTestCase,
                                        TornadoMotorODMTestCase):
    pass
