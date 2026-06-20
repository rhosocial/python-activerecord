# src/rhosocial/activerecord/backend/schema/snapshot.py
"""Immutable schema snapshot and builders (sync / async)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, TYPE_CHECKING

from ..introspection.base import SyncAbstractIntrospector, AsyncAbstractIntrospector

if TYPE_CHECKING:
    from ..dialect.base import SQLDialectBase
    from ..introspection.types import DatabaseInfo, TableInfo


@dataclass(frozen=True)
class SchemaSnapshot:
    """Immutable point-in-time capture of a database schema.

    Fields
    ------
    dialect_class : str
        Fully-qualified class name of the dialect that produced this snapshot
        (e.g. ``"rhosocial.activerecord.backend.impl.postgres.dialect.PostgreSQLDialect"``).
        Used by ``SchemaDiffer`` for dialect compatibility check. Stored as a
        string so the snapshot is a pure data object that can be hashed,
        serialised, and compared without holding a runtime reference.
    captured_at : datetime
        UTC timestamp when the snapshot was taken.
    database_info : DatabaseInfo
        Vendor / version metadata from ``introspector.get_database_info()``.
    tables : Dict[str, TableInfo]
        Mapping of table name → ``TableInfo`` (columns, indexes, FKs).
    schema_name : Optional[str]
        The schema / database name scoped during capture.
    """

    dialect_class: str
    captured_at: datetime
    database_info: "DatabaseInfo"
    tables: Dict[str, "TableInfo"]
    schema_name: Optional[str] = None
    extra: Dict = field(default_factory=dict)


class SyncSchemaSnapshotBuilder:
    """Build a ``SchemaSnapshot`` synchronously.

    Usage::

        builder = SyncSchemaSnapshotBuilder(introspector, dialect)
        snapshot = builder.build(schema="public")
    """

    def __init__(self, introspector: SyncAbstractIntrospector, dialect: "SQLDialectBase"):
        self._introspector = introspector
        self._dialect = dialect

    def build(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> SchemaSnapshot:
        db_info = self._introspector.get_database_info()
        table_list = self._introspector.list_tables(schema=schema, include_system=include_system)
        tables: Dict[str, "TableInfo"] = {}
        for tbl in table_list:
            full = self._introspector.get_table_info(tbl.name, schema=schema)
            if full is not None:
                tables[tbl.name] = full
        return SchemaSnapshot(
            dialect_class=f"{type(self._dialect).__module__}.{type(self._dialect).__qualname__}",
            captured_at=datetime.now(tz=timezone.utc),
            database_info=db_info,
            tables=tables,
            schema_name=schema,
        )


class AsyncSchemaSnapshotBuilder:
    """Build a ``SchemaSnapshot`` asynchronously.

    Usage::

        builder = AsyncSchemaSnapshotBuilder(introspector, dialect)
        snapshot = await builder.build(schema="public")
    """

    def __init__(self, introspector: AsyncAbstractIntrospector, dialect: "SQLDialectBase"):
        self._introspector = introspector
        self._dialect = dialect

    async def build(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> SchemaSnapshot:
        db_info = await self._introspector.get_database_info()
        table_list = await self._introspector.list_tables(schema=schema, include_system=include_system)
        tables: Dict[str, "TableInfo"] = {}
        for tbl in table_list:
            full = await self._introspector.get_table_info(tbl.name, schema=schema)
            if full is not None:
                tables[tbl.name] = full
        return SchemaSnapshot(
            dialect_class=f"{type(self._dialect).__module__}.{type(self._dialect).__qualname__}",
            captured_at=datetime.now(tz=timezone.utc),
            database_info=db_info,
            tables=tables,
            schema_name=schema,
        )
