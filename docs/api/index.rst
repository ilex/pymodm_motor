API Documentation
=================

Connecting
----------

.. automodule:: pymodm_motor.connection

    .. autofunction:: connect

Defining Models
---------------

.. autoclass:: pymodm_motor.MotorMongoModel
    :members:
    :undoc-members:
    :inherited-members:


.. autoclass:: pymodm_motor.MotorEmbeddedMongoModel
    :members:
    :undoc-members:
    :inherited-members:

Model Fields
------------

.. autoclass:: pymodm_motor.base.fields.MongoBaseField

.. automodule:: pymodm_motor.fields
   :members:
   :exclude-members: GeoJSONField, ReferenceField, GenericIPAddressField

   .. autoclass:: GenericIPAddressField
      :members:
      :member-order: bysource

   .. autoclass:: ReferenceField
      :members:
      :member-order: bysource

QuerySet
--------

.. automodule:: pymodm_motor.queryset
   :members: 
   :undoc-members:
   :exclude-members: MotorQuerySet

    .. autoclass:: pymodm_motor.queryset.MotorQuerySet
        :members:
        :undoc-members:
        :exclude-members: count, aggregate

        .. automethod:: pymodm_motor.queryset.MotorQuerySet.count

            .. note:: This method returns `awaitable`.

        .. automethod:: pymodm_motor.queryset.MotorQuerySet.aggregate

            .. note:: The result of this method should be used with `async for`.
            

Dereferencing
-------------

.. automodule:: pymodm_motor.dereference
    :members:

Context Managers
----------------

.. automodule:: pymodm_motor.context_managers
    :members:

    .. autoclass:: switch_connection
        :members:

    .. autoclass:: switch_collection
        :members:

    .. autoclass:: collection_options
        :members:
