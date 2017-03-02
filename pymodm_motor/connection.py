from pymongo import uri_parser
from pymodm.connection import (
    _get_connection, _get_db, _CONNECTIONS, DEFAULT_CONNECTION_ALIAS,
    ConnectionInfo)


__all__ = ['connect', 'MOTOR_ASYNCIO_DRIVER', 'MOTOR_TORNADO_DRIVER']

MOTOR_ASYNCIO_DRIVER = 'motor_asyncio'
MOTOR_TORNADO_DRIVER = 'motor_tornado'


def connect(mongodb_uri, alias=DEFAULT_CONNECTION_ALIAS,
            mongo_driver=MOTOR_ASYNCIO_DRIVER, **kwargs):
    """Register a connection to MongoDB, optionally providing a name for it.

    :parameters:
      - `mongodb_uri`: A MongoDB connection string. Any options may be passed
        within the string that are supported by Motor. `mongodb_uri` must
        specify a database, which will be used by any
        :class:`~pymodm_motor.models.MotorMongoModel` that uses this
        connection.
      - `alias`: An optional name for this connection, backed by a
        `MotorClient` instance that is cached under this name.
        You can specify what connection a MotorMongoModel uses by
        specifying the connection's alias via the `connection_alias` attribute
        inside their `Meta` class.  Switching connections is also possible
        using the :class:`~pymodm_motor.context_managers.switch_connection`
        context manager.  Note that calling `connect()` multiple times with
        the same alias will replace any previous connections.
      - `mongo_driver`: Specify mongodb driver to use. Possible values are
        ``pymodm_motor.connection.MOTOR_ASYNCIO_DRIVER`` and
        ``pymodm_motor.connection.MOTOR_TORNADO_DRIVER``.
      - `kwargs`: Additional keyword arguments to pass to the underlying
        :class:`~motor.motor_asyncio.AsyncIOMotorClient` or
        :class:`~motor.motor_tornado.MotorClient`.

    """
    # Make sure the database is provided.
    parsed_uri = uri_parser.parse_uri(mongodb_uri)
    if not parsed_uri.get('database'):
        raise ValueError('Connection must specify a database.')

    if mongo_driver == MOTOR_ASYNCIO_DRIVER:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(mongodb_uri, **kwargs)
    elif mongo_driver == MOTOR_TORNADO_DRIVER:
        from motor.motor_tornado import MotorClient
        client = MotorClient(mongodb_uri, **kwargs)
    else:
        raise ValueError('Connection must specify a valid mongo_driver.')

    _CONNECTIONS[alias] = ConnectionInfo(
        parsed_uri=parsed_uri,
        conn_string=mongodb_uri,
        database=client[parsed_uri['database']])
