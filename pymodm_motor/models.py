"""Motor mongo models."""
from pymodm import MongoModel, EmbeddedMongoModel
from pymodm.base.models import TopLevelMongoModelMetaclass

from .common import (
    validate_list_tuple_or_none, validate_boolean_or_none,
    validate_boolean, IndexesWrapper)
from .errors import OperationError
from .manager import MotorManager


class MotorMongoModelMetaclass(TopLevelMongoModelMetaclass):
    """Metaclass for motor mongo models.

    Set MotorManager as default manager.
    Set auto_dereference to False as it is impossible to automatically
    dereference reference fields with motor driver.
    """

    def __new__(mcls, name, bases, attrs):
        model_parents = [
            base for base in bases if isinstance(base,
                                                 MotorMongoModelMetaclass)]
        # Only perform Model initialization steps if the class has inherited
        # from a Model base class (i.e. MongoModel/EmbeddedMongoModel).
        if not model_parents:
            return type.__new__(mcls, name, bases, attrs)

        # wrap indexes in Meta if any with IndexesWrapper
        # to avoid auto indexes creation by pymodm
        meta = attrs.get('Meta', None)
        indexes = getattr(meta, 'indexes', None)
        if indexes:
            setattr(meta, 'indexes', IndexesWrapper(indexes))

        # create new model class
        new_class = super().__new__(mcls, name, bases, attrs)

        if hasattr(new_class, 'objects'):
            objects = getattr(new_class, 'objects')
            if not isinstance(objects, MotorManager):
                manager = MotorManager()
                new_class.add_to_class('objects', manager)
                new_class._default_manager = manager

        if hasattr(new_class, '_mongometa'):
            # do not use auto_dereference setter as it
            # try to traverse related fields while their models
            # could be not ready yet
            new_class._mongometa._auto_dereference = False

        return new_class


class MotorMongoModel(MongoModel, metaclass=MotorMongoModelMetaclass):
    """Base class for all top-level models.

    A MongoModel definition typically includes a number of field instances
    and possibly a ``Meta`` class attribute that provides metadata or settings
    specific to the model.

    MongoModels can be instantiated either with positional or keyword
    arguments. Positional arguments are bound to the fields in the order the
    fields are defined on the model. Keyword argument names are the same as
    the names of the fields::

        from pymongo.read_preferences import ReadPreference

        class User(MongoModel):
            email = fields.EmailField(primary_key=True)
            name = fields.CharField()

            class Meta:
                # Read from secondaries.
                read_preference = ReadPreference.SECONDARY

        # Instantiate User using positional arguments:
        jane = User('jane@janesemailaddress.net', 'Jane')
        # Keyword arguments:
        roy = User(name='Roy', email='roy@roysemailaddress.net')

    .. _metadata-attributes:

    The following metadata attributes are available:

      - `connection_alias`: The alias of the connection to use for the moel.
      - `collection_name`: The name of the collection to use. By default, this
        is the same name as the model, converted to snake case.
      - `codec_options`: An instance of
        :class:`~bson.codec_options.CodecOptions` to use for reading and
        writing documents of this model type.
      - `final`: Whether to restrict inheritance on this model. If ``True``,
        the ``_cls`` field will not be stored in the document. ``False`` by
        default.
      - `cascade`: If ``True``, save all :class:`~pymodm.MongoModel` instances
        this object references when :meth:`~pymodm.MongoModel.save` is called
        on this object.
      - `read_preference`: The
        :class:`~pymongo.read_preferences.ReadPreference` to use when reading
        documents.
      - `read_concern`: The :class:`~pymongo.read_concern.ReadConcern` to use
        when reading documents.
      - `write_concern`: The :class:`~pymongo.write_concern.WriteConcern` to
        use for write operations.
      - `indexes`: This is a list of :class:`~pymongo.operations.IndexModel`
        instances that describe the indexes that should be created for this
        model. Note that indexes are NOT created when the class definition
        is evaluated and should be created explicitly using
        :meth:``~pymodm_motor.queryset.MotorQuerySet.create_indexes``
        coroutine method.

    .. note:: Creating an instance of MongoModel does not create a document in
              the database.

    """

    async def save(self, cascade=None, full_clean=True, force_insert=False):
        """Coroutine to save this document into MongoDB.

        If there is no value for the primary key on this Model instance, the
        instance will be inserted into MongoDB. Otherwise, the entire document
        will be replaced with this version (upserting if necessary).

        :parameters:
          - `cascade`: If ``True``, all dereferenced MongoModels contained in
            this Model instance will also be saved.
          - `full_clean`: If ``True``, the
            :meth:`~pymodm.MongoModel.full_clean` method
            will be called before persisting this object.
          - `force_insert`: If ``True``, always do an insert instead of a
            replace. In this case, `save` will raise
            :class:`~pymongo.errors.DuplicateKeyError` if a document already
            exists with the same primary key.

        :returns: This object, with the `pk` property filled in if it wasn't
                  already.

        """
        cascade = validate_boolean_or_none('cascade', cascade)
        full_clean = validate_boolean('full_clean', full_clean)
        force_insert = validate_boolean('force_insert', force_insert)
        if full_clean:
            self.full_clean()
        if cascade or (self._mongometa.cascade and cascade is not False):
            for field_name in self:
                for referenced_object in self._find_referenced_objects(
                        getattr(self, field_name)):
                    await referenced_object.save()
        if force_insert or self._mongometa.pk.is_undefined(self):
            result = await self._mongometa.collection.insert_one(
                self.to_son())
            self.pk = result.inserted_id
        else:
            result = await self._mongometa.collection.replace_one(
                {'_id': self._mongometa.pk.to_mongo(self.pk)},
                self.to_son(), upsert=True)
        return self

    async def delete(self):
        await self._qs.delete()

    async def refresh_from_db(self, fields=None):
        """Reload this object from the database, overwriting local fields.

        :parameters:
          - `fields`: An iterable of fields to reload. Defaults to all fields.

        .. warning:: This method will reload the object from the database,
           possibly with only a subset of fields. Calling
           :meth:`~pymodm_motor.MotorMongoModel.save` after this may revert
           or unset fields in the database.

        """
        fields = validate_list_tuple_or_none('fields', fields)
        if self._qs is None:
            raise OperationError('Cannot refresh from db before saving.')
        qs = self._qs.values()
        if fields:
            qs = qs.only(*fields)
        db_inst = await qs.first()

        self._set_attributes(db_inst)
        return self


class MotorEmbeddedMongoModel(EmbeddedMongoModel,
                              metaclass=MotorMongoModelMetaclass):
    """Base class for all motor embedded models."""
