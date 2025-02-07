"""Module providing integer primary key functionality."""
from ..interface import IActiveRecord


class IntegerPKMixin(IActiveRecord):
    """Integer Primary Key Mixin

    Provides support for integer-based primary keys in models.
    """

    def __init__(self, **data):
        super().__init__(**data)
        if self.primary_key() not in data:
            setattr(self, self.primary_key(), None)