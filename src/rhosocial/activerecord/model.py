# src/rhosocial/activerecord/model.py
"""
Final ActiveRecord classes assembled from modular mixins.

Each mixin contributes a distinct capability:
- RelationManagementMixin: has_many / belongs_to relation declarations and lazy loading
- QueryMixin / AsyncQueryMixin: find_one, find_all, query() builder entry point
- ColumnNameMixin: UseColumn annotation → physical column name mapping
- FieldAdapterMixin: UseAdapter annotation → per-field type conversion
- DerivedFieldMixin: DerivedField annotation → database-computed virtual columns
- MetaclassMixin: ActiveRecordMetaclass integration and feature handler dispatch
- BaseActiveRecord / AsyncBaseActiveRecord: CRUD, lifecycle hooks, backend binding
"""

from .base import (
    BaseActiveRecord,
    AsyncBaseActiveRecord,
    QueryMixin,
    AsyncQueryMixin,
    ColumnNameMixin,
    FieldAdapterMixin,
    DerivedFieldMixin,
    MetaclassMixin,
)
from .relation import RelationManagementMixin


class ActiveRecord(
    RelationManagementMixin,
    QueryMixin,
    ColumnNameMixin,
    FieldAdapterMixin,
    DerivedFieldMixin,
    MetaclassMixin,
    BaseActiveRecord,
):
    """Complete ActiveRecord implementation combining core features."""

    ...


class AsyncActiveRecord(
    RelationManagementMixin,
    AsyncQueryMixin,
    ColumnNameMixin,
    FieldAdapterMixin,
    DerivedFieldMixin,
    MetaclassMixin,
    AsyncBaseActiveRecord,
):
    """Complete Async ActiveRecord implementation combining core features."""

    ...


__all__ = [
    "ActiveRecord",
    "AsyncActiveRecord",
]
