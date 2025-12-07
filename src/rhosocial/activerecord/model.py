# src/rhosocial/activerecord/model.py
# Define the main ActiveRecord class by combining mixins
# This approach keeps the class definition clean and modular
from .base import BaseActiveRecord, QueryMixin
from .base.column_name_mixin import ColumnNameMixin
from .base.field_adapter_mixin import FieldAdapterMixin
from .base.metaclass import MetaclassMixin
from .relation import RelationManagementMixin


class ActiveRecord(
    RelationManagementMixin,
    # FieldMixin, # import when needed
    QueryMixin,
    ColumnNameMixin, # Added ColumnNameMixin here
    FieldAdapterMixin,
    MetaclassMixin,
    BaseActiveRecord,
):
    """Complete ActiveRecord implementation combining core features.

    Inherits functionality from:

    - BaseActiveRecord: Core CRUD operations
    - RelationManagementMixin: Relationship handling
    - QueryMixin: Query builder
    - FieldAdapterMixin: Field-specific type adapter support
    - MetaclassMixin: Metaclass-based model building support
    """
    ...


__all__ = [
    'ActiveRecord',
]