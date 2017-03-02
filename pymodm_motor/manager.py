"""Asynchronous manager."""
from pymodm.manager import Manager
from .queryset import MotorQuerySet

MotorManager = Manager.from_queryset(MotorQuerySet, 'MotorManager')
