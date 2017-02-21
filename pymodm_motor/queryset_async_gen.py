"""Python 3.6 async generator for queryset results."""
from .queryset_async_iterator import _from_document, _dereference_document


async def motor_queryset_gen(queryset):
    to_instance = _from_document
    if queryset._select_related_fields is not None:
        to_instance = _dereference_document
    cursor = queryset._get_raw_cursor()
    async for doc in cursor:
        yield await to_instance(queryset, doc)
