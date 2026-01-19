# src/rhosocial/activerecord/model.py
# Define the main ActiveRecord class by combining mixins
# This approach keeps the class definition clean and modular
from .base import (
    BaseActiveRecord,
    AsyncBaseActiveRecord,
    QueryMixin,
    AsyncQueryMixin,
    ColumnNameMixin,
    FieldAdapterMixin,
    MetaclassMixin
)
from .relation import IRelationManagementMixin


class ActiveRecord(
    IRelationManagementMixin,
    # FieldMixin, # import when needed
    QueryMixin,
    ColumnNameMixin,  # Added ColumnNameMixin here
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


class AsyncActiveRecord(
    IRelationManagementMixin,
    AsyncQueryMixin,
    ColumnNameMixin,
    FieldAdapterMixin,
    MetaclassMixin,
    AsyncBaseActiveRecord,
):
    """Complete Async ActiveRecord implementation combining core features.

    Inherits functionality from:

    - AsyncBaseActiveRecord: Async core CRUD operations
    - RelationManagementMixin: Relationship handling
    - AsyncQueryMixin: Async query builder
    - FieldAdapterMixin: Field-specific type adapter support
    - MetaclassMixin: Metaclass-based model building support
    """

    ...


__all__ = [
    "ActiveRecord",
    "AsyncActiveRecord",
]
