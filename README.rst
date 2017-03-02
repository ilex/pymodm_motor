============
PyMODM_Motor
============


An asynchronous ODM on top of `PyMODM`_ ODM library using `Motor`_ asynchronous
Python MongoDB driver. ``PyMODM_Motor`` works on ``Python 3.5`` and up. Some features
such as asynchronous comprehensions require at least ``Python 3.6``. ``PyMODM_Motor``
can be used with `asyncio`_ as well as with `Tornado`_.

``PyMODM_Motor`` uses ``PyMODM``'s machinery whenever it posible and just modify some 
functions and methods that actually work with database. So the most of 
`official PyMODM documentation`_ is fully compatible (see 
`Differences between PyMODM_Motor and PyMODM`_ for details) with ``PyMODM_Motor`` 
and can be browsed to learn more. You can also take a look at the simple 
`blog example`_ built with `asyncio`_ and `AIOHTTP`_ asynchronous web framework.

.. _PyMODM: https://pypi.python.org/pypi/pymodm
.. _Motor: https://pypi.python.org/pypi/motor
.. _official PyMODM documentation: http://pymodm.readthedocs.io/en/stable
.. _blog example: https://github.com/ilex/pymodm_motor/tree/develop/example/blog/aiohttp
.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _Tornado: https://pypi.python.org/pypi/tornado
.. _AIOHTTP: https://pypi.python.org/pypi/aiohttp


Install
=======

At this moment you need to install ``pymodm`` as follow::

    pip install https://github.com/mongodb/pymodm/archive/master.zip

And then install ``PyMODM_Motor`` using ``pip``::
    
    pip install https://github.com/ilex/pymodm_motor/archive/develop.zip 


Differences between PyMODM_Motor and PyMODM
===========================================

Although most of the ``PyMODM_Motor`` is very similar to ``PyMODM`` 
there are some differences due to asynchronous nature of ``PyMODM_Motor``:

1) Use classes with ``Motor`` prefix for models, managers and querysets 
   (note that each ``Motor*`` class derived from appropriate ``PyMODM`` class 
   and inherits most of their behavior):
    
   - ``pymodm_motor.MotorMongoModel`` in place of ``pymodm.MongoModel``
   - ``pymodm_motor.MotorEmbeddedMongoModel`` in place of ``pymodm.EmbeddedMongoModel``
   - ``pymodm_motor.MotorMongoModelMetaclass`` in place of ``pymodm.TopLevelMongoModelMetaclass``
   - ``pymodm_motor.MotorManager`` in place of ``pymodm.Manager``
   - ``pymodm_motor.MotorQuerySet`` in place of ``pymodm.QuerySet``
    
2) Some methods and functions are coroutines (see `List of Coroutines`_) so 
   the should be called with ``await``.

   .. code-block:: python

        from pymodm_motor import fields, MotorMongoModel

        class User(MotorMongoModel):
            name = fields.CharField()

        async def handler():
            user = await User(name='Bob').save()
            await user.refresh_from_db()
            await user.delete()
            users_count = await User.objects.count()
            
3) There is no *auto dereferencing* in ``PyMODM_Motor`` use ``dereference`` 
   coroutine explicitly to dereference reference fields in model instance.

   .. code-block:: python
       
        from bson import ObjectId
        from pymodm_motor import fields, MotorMongoModel
        from pymodm_motor.dereference import dereference

        class User(MotorMongoModel):
            # note that library will add an _id field
            # as there is no field with primary_key=True
            name = fields.CharField()

        class Post(MotorMongoModel):
            # note that title is an _id field
            title = fields.CharField(primary_key=True)
            user = fields.ReferenceField(User)

        async def handler():
            user = await User(name='Bob').save()
            post = await Post(title='My post', user=user).save()

            post_from_db = await Post.objects.get({'_id': 'My post'})
            assert isinstance(post_from_db.user, ObjectId) 

            await dereference(post_from_db)
            assert isinstance(post_from_db.user, User)

4) As there is no *auto dereferencing* the ``no_auto_dereference`` context
   manager is useless.
5) There is no *auto indexes creation* in ``PyMODM_Motor`` use 
   ``MotorQuerySet.create_indexes()`` coroutine method explicitly. As a bonus
   you can use ``switch_connection`` and ``switch_collection`` context managers
   with this method.

   .. code-block:: python
        
        from pymodm_motor import fields, MotorMongoModel
        from pymodm_motor.context_managers import swith_collection
        from pymongo import IndexModel, ASCENDING

        class User(MotorMongoModel):
            name = fields.CharField()

            class Meta:
                indexes = [
                    IndexModel([('name', ASCENDING)], unique=True, name='name_index')
                ]

        async def create_indexes():
            for model in (User, ): # list here models classes with indexes
                await model.objects.create_indexes()

        async def app_init():
            await create_indexes()
            # create indexes in another collection
            with switch_collection(User, 'backup_user') as BackupUser:
                await BackupUser.objects.create_indexes()

6) There are some additional parameters in ``connect`` function:

   - ``mongo_driver``: a string constant that specify which of the drivers to use
     ``pymodm_motor.MOTOR_ASYNCIO_DRIVER`` or ``pymodm_motor.MOTOR_TORNADO_DRIVER``.
   - ``kwargs``: will be passed to appropriate MotorClient. For example ``io_loop``
     parameter can be specified to pass a specific loop.

7) As there is no *auto indexes creation* ``connect`` can be called in any place but
   before any db operations are called.
8) For retrieve bunch of objects ``MotorQuerySet`` returns an asynchronous iterator
   or asynchronous generator (for Python 3.6 and up) so to iterate over items use
   ``async for`` construction. As a consequence you can not use ``list(await Model.objects.all())``
   or list comprehension ``[model for model in await Model.objects.all()]``. 
   If you need a list use ``MotorQuerySet.to_list()`` coroutine which returns 
   a list of models instances. For Python 3.6 the recommended way is to use 
   `asynchronous comprehensions`_.

   .. code-block:: python

        from pymodm_motor import fields, MotorMongoModel
        from pymodm_motor.dereference import dereference

        class User(MotorMongoModel):
            name = fields.CharField()

        async def handler():
            # iterate over objects 
            async for user in User.objects.all():
                print(user.name)

            # get list of the objects
            users = await User.objects.all().to_list()

            # get a list of the objects and dereference them
            users = await User.objects.all().to_list(dereference=True)

            # WITH PYTHON 3.6 AND UP

            # Note this will work only with Python 3.6 and up
            # create a list of dereferenced objects 
            users = [await dereference(user) 
                     async for user in User.objects.all()]

            # Note this will work only with Python 3.6 and up
            # create a list of tuples
            users_id_name = [(user._id, user.name) 
                             async for user in User.objects.all()]
                             
            # Note this will work only with Python 3.6 and up
            # create a dict
            users = {user._id: user.name async for user in User.objects.all()}

9) A slice operator and getitem operator should be used with ``await``.
    
   .. code-block:: python

        from pymodm_motor import fields, MotorMongoModel

        class User(MotorMongoModel):
            name = fields.CharField()

        async def handler():
            name = (await User.objects[3]).name
            users = await User.objects[2:3]  # users is a list of Users


.. _asynchronous comprehensions: https://www.python.org/dev/peps/pep-0530/#asynchronous-comprehensions

List of coroutines
==================
These functions and methods are coroutines or return awaitable:

- ``pymodm_motor.dereference`` module:

  - ``pymodm_motor.dereference.dereference``
  - ``pymodm_motor.dereference.dereference_id``

- ``pymodm_motor.MotorMongoModel`` class:

  - ``pymodm_motor.MotorMongoModel.save``
  - ``pymodm_motor.MotorMongoModel.delete``
  - ``pymodm_motor.MotorMongoModel.refresh_from_db``

- ``pymodm_motor.MotorQuerySet`` class:

  - ``pymodm_motor.MotorQuerySet.count``
  - ``pymodm_motor.MotorQuerySet.aggregate``
  - ``pymodm_motor.MotorQuerySet.get``
  - ``pymodm_motor.MotorQuerySet.first``
  - ``pymodm_motor.MotorQuerySet.bulk_create``
  - ``pymodm_motor.MotorQuerySet.delete``
  - ``pymodm_motor.MotorQuerySet.update``
  - ``pymodm_motor.MotorQuerySet.to_list``
  - ``pymodm_motor.MotorQuerySet.create_indexes``
  - ``pymodm_motor.MotorQuerySet.__getitem__``


Example
=======

Here's a basic example of how to define some models and connect them to MongoDB:

.. code-block:: python

    import asyncio
    from pymongo import IndexModel, TEXT, ASCENDING
    from pymodm_motor import (
        connect, fields, MOTOR_ASYNCIO_DRIVER, 
        MotorMongoModel, MotorEmbeddedMongoModel)


    # Now let's define some Models.
    class User(MotorMongoModel):
        # Use 'email' as the '_id' field in MongoDB.
        email = fields.EmailField(primary_key=True)
        fname = fields.CharField()
        lname = fields.CharField()

        class Meta:
            indexes = [IndexModel([('fname', ASCENDING)])]


    class BlogPost(MotorMongoModel):
        # This field references the User model above.
        # it just stores an user's _id in MongoDB
        author = fields.ReferenceField(User)
        title = fields.CharField(max_length=100)
        content = fields.CharField()
        tags = fields.ListField(fields.StringField(max_length=20))
        # These Comment objects will be stored inside each Post document in the
        # database.
        comments = fields.EmbeddedDocumentListField('Comment')

        class Meta:
            # Text index on content can be used for text search.
            indexes = [IndexModel([('content', TEXT)])]

    # This is an "embedded" model and will be stored as a sub-document.
    class Comment(MotorEmbeddedMongoModel):
        author = fields.ReferenceField(User)
        body = fields.CharField()
        vote_score = fields.IntegerField(min_value=0)


    async def create_indexes():
        # create all indexes
        for model in (User, BlogPost):
            await model.objects.create_indexes()


    async def go(loop):
        
        # Connect to MongoDB first. PyMODM_Motor supports all URI options supported by
        # Motor. Make sure also to specify a database in the connection string and 
        # one of the drivers MOTOR_ASYNCIO_DRIVER or MOTOR_TORNADO_DRIVER.
        # You can also specify other parameters to pass them to MotorClient.
        # For example you can specify a loop.
        connect('mongodb://localhost:27017/myApp', 
                mongo_driver=MOTOR_ASYNCIO_DRIVER, io_loop=loop)
        
        # Explicitly create indexes as PyMODM_Motor does not do that automaticaly
        await create_indexes()

        # We need to save these objects before referencing them later.
        han_solo = await User(
            'mongoblogger@reallycoolmongostuff.com', 'Han', 'Solo').save()
        chewbacca = await User(
            'someoneelse@reallycoolmongostuff.com', 'Chewbacca', 'Thomas').save()

        post = await BlogPost(
            # Since this is a ReferenceField, we had to save han_solo first.
            author=han_solo,
            title="Five Crazy Health Foods Jabba Eats.",
            content="...",
            tags=['alien health', 'slideshow', 'jabba', 'huts'],
            comments=[
                Comment(author=chewbacca, body='Rrrrrrrrrrrrrrrr!', vote_score=42)
            ]
        ).save()

        # Find objects using familiar MongoDB-style syntax.
        slideshows = BlogPost.objects.raw({'tags': 'slideshow'})

        # Only retrieve the 'title' field.
        slideshow_titles = slideshows.only('title')

        # 'Five Crazy Health Foods Jabba Eats.'
        print((await slideshow_titles.first()).title)

    # create an asyncio loop
    loop = asyncio.get_event_loop()
    # run our coroutine
    loop.run_until_complete(go(loop))


License
=======

The library is licensed under Apache License, Version 2.0.
