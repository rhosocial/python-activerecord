# src/rhosocial/activerecord/field/integer_pk.py
"""Module providing integer primary key functionality."""
from ..interface import IActiveRecord


class IntegerPKMixin(IActiveRecord):
    """Integer Primary Key Mixin

    Provides support for integer-based primary keys in models.
    """

    def __init__(self, **data):
        super().__init__(**data)
        # Use primary_key_field() to get the correct Python attribute name
        # for the primary key. This is crucial for models that map their
        # primary key field to a different database column name.
        pk_field_name = self.primary_key_field()
        if pk_field_name not in data:
            setattr(self, pk_field_name, None)
