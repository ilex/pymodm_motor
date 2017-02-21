from pymodm.common import *
from pymodm.common import _import


class IndexesWrapper(object):
    """Wrapper for model's indexes.

    Object of this class is always return False in truth value testing.
    This helps us to prevent from auto indexes creation by pymodm
    during model class evaluation.
    """

    def __init__(self, indexes):
        self.indexes = indexes

    def __bool__(self):
        return False
