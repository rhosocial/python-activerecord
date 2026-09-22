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
    DDLMixin,
    MetaclassMixin,
)
from .relation import RelationManagementMixin


class ActiveRecord(
    RelationManagementMixin,
    QueryMixin,
    ColumnNameMixin,
    FieldAdapterMixin,
    DerivedFieldMixin,
    DDLMixin,
    MetaclassMixin,
    BaseActiveRecord,
):
    """Complete ActiveRecord implementation combining core features."""

    @classmethod
    def truncate(cls, *, restart_identity: bool = False, cascade: bool = False):
        """Delete every row in the table (``TRUNCATE TABLE``).

        Args:
            restart_identity: reset identity/auto-increment columns
                (backends that support ``RESTART IDENTITY``).
            cascade: also truncate dependent tables (backends that support
                ``CASCADE``).

        Returns:
            The backend's ``QueryResult``.
        """
        expression = cls._deriver().truncate(
            restart_identity=restart_identity, cascade=cascade
        )
        sql, params = expression.to_sql()
        return cls.backend().execute(sql, params)


class AsyncActiveRecord(
    RelationManagementMixin,
    AsyncQueryMixin,
    ColumnNameMixin,
    FieldAdapterMixin,
    DerivedFieldMixin,
    DDLMixin,
    MetaclassMixin,
    AsyncBaseActiveRecord,
):
    """Complete Async ActiveRecord implementation combining core features."""

    @classmethod
    async def truncate(cls, *, restart_identity: bool = False, cascade: bool = False):
        """Delete every row in the table (``TRUNCATE TABLE``).

        Args:
            restart_identity: reset identity/auto-increment columns
                (backends that support ``RESTART IDENTITY``).
            cascade: also truncate dependent tables (backends that support
                ``CASCADE``).

        Returns:
            The backend's ``QueryResult``.
        """
        expression = cls._deriver().truncate(
            restart_identity=restart_identity, cascade=cascade
        )
        sql, params = expression.to_sql()
        return await cls.backend().execute(sql, params)


__all__ = [
    "ActiveRecord",
    "AsyncActiveRecord",
]
