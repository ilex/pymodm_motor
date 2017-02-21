"""Async dereferencing."""
from collections import defaultdict, deque

from .connection import _get_db
from pymodm.dereference import (
    _ObjectMap, _find_references, _attach_objects)

"""
async def _resolve_references(database, reference_map):
    document_map = _ObjectMap()
    for collection_name in reference_map:
        collection = database[collection_name]
        query = {'_id': {'$in': reference_map[collection_name]}}
        documents = collection.find(query)
        async for document in documents:
            document_map[document['_id']] = document
    return document_map
"""


async def _resolve_references(database, reference_map):
    document_map = {}
    for collection_name in reference_map:
        document_map[collection_name] = _ObjectMap()

        collection = database[collection_name]
        query = {'_id': {'$in': reference_map[collection_name]}}
        documents = collection.find(query)
        async for document in documents:
            document_map[collection_name][document['_id']] = document

    return document_map


async def dereference(model_instance, fields=None):
    """Dereference ReferenceFields on a MotorMongoModel instance.

    This function is handy for dereferencing many fields at once and is more
    efficient than dereferencing one field at a time.

    :parameters:
      - `model_instance`: The MotorMongoModel instance.
      - `fields`: An iterable of field names in "dot" notation that should be
        dereferenced. If left blank, all fields will be dereferenced.
    """
    # Map of collection name --> list of ids to retrieve from the collection.
    reference_map = defaultdict(list)

    # Fields may be nested (dot-notation). Split each field into its parts.
    if fields:
        fields = [deque(field.split('.')) for field in fields]

    # Tell ReferenceFields not to look up their value while we scan the object
    # with no_auto_dereference(model_instance):
    _find_references(model_instance, reference_map, fields)

    db = _get_db(model_instance._mongometa.connection_alias)
    # Resolve all references, one collection at a time.
    # This will give us a mapping of id --> resolved object.
    document_map = await _resolve_references(db, reference_map)

    # Traverse the object and attach resolved references where needed.
    _attach_objects(model_instance, document_map, fields)

    return model_instance


async def dereference_id(model_class, model_id):
    """Dereference a single object by id.

    :parameters:
      - `model_class`: The class of a model to be dereferenced.
      - `model_id`: The id of the model to be dereferenced.
    """
    collection = model_class._mongometa.collection
    document = await collection.find_one(model_id)
    if document:
        return model_class.from_document(document)
