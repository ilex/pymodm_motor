"""Python 3.5 async iterator for results in queryset."""
from pymodm.common import _import


async def _from_document(queryset, doc):
    return queryset._model.from_document(doc)


async def _dereference_document(queryset, doc):
    dereference = _import('pymodm_motor.dereference.dereference')
    return await dereference(
        queryset._model.from_document(doc),
        queryset._select_related_fields)


class MotorQuerySetAsyncIterator:
    """Iterator for results of queryset."""

    def __init__(self, queryset):
        self._qs = queryset
        self.to_instance = _from_document
        if queryset._select_related_fields is not None:
            self.to_instance = _dereference_document
        self._cursor = queryset._get_raw_cursor()

    async def fetch_next(self):
        if await self._cursor.fetch_next:
            return self._cursor.next_object()

        raise StopAsyncIteration()

    async def __anext__(self):
        return await self.to_instance(self._qs, await self.fetch_next())

    def __aiter__(self):
        return self
