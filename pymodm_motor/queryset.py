"""Async QuerySet using motor."""
import sys
import textwrap

from pymodm.queryset import QuerySet
from . import errors
from .dereference import dereference as dereference_model
from .common import (
    _import, validate_boolean, validate_list_or_tuple, IndexesWrapper)

PY_36 = sys.version_info >= (3, 6)


if PY_36:
    from .queryset_async_gen import motor_queryset_gen
else:
    from .queryset_async_iterator import MotorQuerySetAsyncIterator


class MotorQuerySet(QuerySet):
    """Motor QuerySet."""

    async def get(self, raw_query):
        results = self.raw(raw_query).__aiter__()
        try:
            first = await results.__anext__()
        except StopAsyncIteration:
            raise self._model.DoesNotExist()
        try:
            await results.__anext__()
        except StopAsyncIteration:
            pass
        else:
            raise self._model.MultipleObjectsReturned()
        return first

    async def first(self):
        try:
            return await self.limit(-1).__aiter__().__anext__()
        except StopAsyncIteration:
            raise self._model.DoesNotExist()

    async def bulk_create(self, object_or_objects, retrieve=False,
                          full_clean=False):
        """Save Model instances in bulk.

        :parameters:
          - `object_or_objects`: A list of MotorMongoModel instances or a
            single instance.
          - `retrieve`: Whether to return the saved MongoModel
            instances. If ``False`` (the default), only the ids will be
            returned.
          - `full_clean`: Whether to validate each object by calling
            the :meth:`~pymodm.MongoModel.full_clean` method before saving.
            This isn't done by default.

        :returns: A list of ids for the documents saved, or of the
                  :class:`~pymodm_motor.MotorMongoModel` instances themselves
                  if `retrieve` is ``True``.

        example::

            >>> vacation_ids = await Vacation.objects.bulk_create([
            ...     Vacation(destination='TOKYO', travel_method='PLANE'),
            ...     Vacation(destination='ALGIERS', travel_method='PLANE')])
            >>> print(vacation_ids)
            [ObjectId('578926716e32ab1d6a8dc718'),
             ObjectId('578926716e32ab1d6a8dc719')]

        """
        retrieve = validate_boolean('retrieve', retrieve)
        full_clean = validate_boolean('full_clean', full_clean)
        MongoModel = _import('pymodm.base.models.MongoModel')
        if isinstance(object_or_objects, MongoModel):
            object_or_objects = [object_or_objects]
        object_or_objects = validate_list_or_tuple(
            'object_or_objects', object_or_objects)
        if full_clean:
            for object in object_or_objects:
                object.full_clean()
        docs = (obj.to_son() for obj in object_or_objects)
        # here what we should actually change...
        ids = (await self._collection.insert_many(docs)).inserted_ids
        if retrieve:
            return await self.raw({'_id': {'$in': ids}}).to_list()

        return ids

    async def delete(self):
        """Delete objects matched by this QuerySet.

        :returns: The number of documents deleted.

        """
        ReferenceField = _import('pymodm.fields.ReferenceField')
        if self._model._mongometa.delete_rules:
            # Don't apply any delete rules if no documents match.
            if not (await self.count()):
                return 0

            # Use values() to avoid overhead converting to Model instances.
            refs = list()
            async for doc in self.only('_id').values():
                refs.append(doc['_id'])

            # Check for DENY rules before anything else.
            for rule_entry in self._model._mongometa.delete_rules:
                rule = self._model._mongometa.delete_rules[rule_entry]
                if ReferenceField.DENY == rule:
                    related_model, related_field = rule_entry
                    related_qs = related_model._default_manager.raw(
                        {related_field: {'$in': refs}}).values()
                    if await related_qs.count() > 0:
                        raise errors.OperationError(
                            'Cannot delete a %s object while a %s object '
                            'refers to it through its "%s" field.'
                            % (self._model._mongometa.object_name,
                               related_model._mongometa.object_name,
                               related_field))

            # If we've made it this far, it's ok to delete the objects in this
            # QuerySet.
            result = (await self._collection.delete_many(
                self._query, collation=self._collation)).deleted_count

            # Apply the rest of the delete rules.
            for rule_entry in self._model._mongometa.delete_rules:
                rule = self._model._mongometa.delete_rules[rule_entry]
                if ReferenceField.DO_NOTHING == rule:
                    continue

                related_model, related_field = rule_entry
                related_qs = (related_model._default_manager
                              .raw({related_field: {'$in': refs}})
                              .values())
                if ReferenceField.NULLIFY == rule:
                    await related_qs.update({'$unset': {related_field: None}})
                elif ReferenceField.CASCADE == rule:
                    await related_qs.delete()
                elif ReferenceField.PULL == rule:
                    await related_qs.update(
                        {'$pull': {related_field: {'$in': refs}}})

            return result

        return (await self._collection.delete_many(
            self._query, collation=self._collation)).deleted_count

    async def update(self, update, **kwargs):
        """Update the objects in this QuerySet and return the number updated.

        :parameters:
          - `update`: The modifications to apply.
          - `kwargs`: (optional) keyword arguments to pass down to
            :meth:`~motor.collection.Collection.update_many`.

        example::

            await Subscription.objects.raw({"year": 1995}).update(
                {"$set": {"expired": True}},
                upsert=True)

        """
        # If we're doing an upsert on a non-final class, we need to add '_cls'
        # manually, since it won't be saved with upsert alone.
        if kwargs.get('upsert') and not self._model._mongometa.final:
            dollar_set = update.setdefault('$set', {})
            dollar_set['_cls'] = self._model._mongometa.object_name
        kwargs.setdefault('collation', self._collation)
        return (await self._collection.update_many(
            self.raw_query, update, **kwargs)).modified_count

    def __aiter__(self):
        if self._return_raw:
            return self._get_raw_cursor()

        if PY_36:
            # python 3.6 has async generators
            return motor_queryset_gen(self)

        return MotorQuerySetAsyncIterator(self)

    def __getitem__(self, key):
        """Emulate indexing and slicing.

        :returns: Awaitable result. To get actual value use `await`.

        example::

            name = (await User.objects[3]).name
            users = await User.objects[2:3]  # users is a list of Users
        """
        clone = self._clone()

        if isinstance(key, slice):
            # PyMongo will later raise an Exception if the slice is invalid.
            if key.start is not None:
                clone._skip = key.start
                if key.stop is not None:
                    clone._limit = key.stop - key.start
            elif key.stop is not None:
                clone._limit = key.stop
            return clone.to_list()
        else:
            return clone.skip(key).first()

    if PY_36:
        exec(textwrap.dedent("""
        async def to_list(self, dereference=False):
            if dereference:
                return [await dereference_model(item) async for item in self]

            return [item async for item in self]
        """), globals(), locals())
    else:  # python 3.5
        exec(textwrap.dedent("""
        async def to_list(self, dereference=False):
            lst = []
            if dereference:
                async for item in self:
                    lst.append(await dereference_model(item))
            else:
                async for item in self:
                    lst.append(item)

            return lst
        """), globals(), locals())

    async def create_indexes(self):
        """Create model indexes if any.

        Note that we wrap indexes into IndexesWrapper class.
        """
        meta = self._model._mongometa
        indexes = meta.indexes
        if isinstance(indexes, IndexesWrapper) and  indexes.indexes:
            await meta.collection.create_indexes(indexes.indexes)
