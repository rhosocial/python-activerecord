# src/rhosocial/activerecord/model.py
# Define the main ActiveRecord class by combining mixins
# This approach keeps the class definition clean and modular
from .base import BaseActiveRecord, QueryMixin
from .base.field_adapter_mixin import FieldAdapterMixin
from .base.metaclass import MetaclassMixin
from .base.column_mapping_mixin import ColumnMappingMixin
from .relation import RelationManagementMixin


class ActiveRecord(
    RelationManagementMixin,
    # FieldMixin, # import when needed
    QueryMixin,
    FieldAdapterMixin,
    ColumnMappingMixin,
    MetaclassMixin,
    BaseActiveRecord,
):
    """Complete ActiveRecord implementation combining core features.

    Inherits functionality from:

    - BaseActiveRecord: Core CRUD operations
    - RelationManagementMixin: Relationship handling
    - QueryMixin: Query builder
    - FieldAdapterMixin: Field-specific type adapter support
    - ColumnMappingMixin: Field-to-column name mapping support
    - MetaclassMixin: Metaclass-based model building support
    """
    ...


__all__ = [
    'ActiveRecord',
]