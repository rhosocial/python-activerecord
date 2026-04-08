# src/rhosocial/activerecord/backend/impl/sqlite/introspection/introspector.py
"""
SQLite concrete introspectors.

Implements SyncAbstractIntrospector and AsyncAbstractIntrospector for SQLite
databases using PRAGMA commands and the sqlite_master / sqlite_schema system
table for metadata queries.

The introspectors are exposed via ``backend.introspector`` and also provide
SQLite-specific access through ``backend.introspector.pragma``.

Key behaviours:
  - Version-aware: uses ``PRAGMA table_list`` (3.37+) or ``sqlite_master``
  - Extended column info: uses ``PRAGMA table_xinfo`` (3.26+)
  - ``_parse_*`` methods are pure Python — shared by sync and async introspectors

Design principle: Sync and Async are separate and cannot coexist.
- SyncSQLiteIntrospector: for synchronous backends
- AsyncSQLiteIntrospector: for asynchronous backends
"""

import copy
import sqlite3
from typing import Any, Dict, List, Optional

from rhosocial.activerecord.backend.introspection.base import (
    IntrospectorMixin,
    SyncAbstractIntrospector,
    AsyncAbstractIntrospector,
)
from rhosocial.activerecord.backend.introspection.executor import (
    SyncIntrospectorExecutor,
    AsyncIntrospectorExecutor,
)
from rhosocial.activerecord.backend.introspection.types import (
    DatabaseInfo,
    TableInfo,
    TableType,
    ColumnInfo,
    ColumnNullable,
    IndexInfo,
    IndexColumnInfo,
    IndexType,
    ForeignKeyInfo,
    ReferentialAction,
    ViewInfo,
    TriggerInfo,
    IntrospectionScope,
)
from .pragma_introspector import (
    SyncPragmaIntrospector,
    AsyncPragmaIntrospector,
)
from .status_introspector import (
    SyncSQLiteStatusIntrospector,
    AsyncSQLiteStatusIntrospector,
)


class SQLiteIntrospectorMixin(IntrospectorMixin):
    """Mixin providing shared SQLite-specific introspection logic.

    Both SyncSQLiteIntrospector and AsyncSQLiteIntrospector inherit
    from this mixin to share:
    - Default schema handling
    - SQLite version detection
    - SQL generation overrides
    - _parse_* implementations
    """

    def _get_default_schema(self) -> str:
        """Return the SQLite schema name for the primary database."""
        return "main"

    def _get_sqlite_version(self) -> tuple:
        """Return SQLite library version as an integer tuple."""
        parts = sqlite3.sqlite_version.split(".")
        return tuple(
            int(p) if p.isdigit() else 0
            for p in (parts + ["0", "0"])[:3]
        )

    # ------------------------------------------------------------------ #
    # SQL generation — uses base class implementation via Expression/Dialect
    # SQLite's format_*_query() methods in the Dialect layer handle PRAGMA
    # commands and sqlite_master queries.
    # ------------------------------------------------------------------ #

    # Note: SQLite does NOT override _build_*_sql() methods because:
    # 1. Base class IntrospectorMixin._build_*_sql() delegates to Expression.to_sql()
    # 2. Expression.to_sql() calls Dialect.format_*_query()
    # 3. SQLiteDialect.format_*_query() generates correct PRAGMA/sqlite_master SQL
    #
    # This follows the same pattern as MySQL and PostgreSQL backends.

    # ------------------------------------------------------------------ #
    # Parse methods — pure Python, no I/O
    # ------------------------------------------------------------------ #

    def _parse_database_info(self, rows: List[Dict[str, Any]]) -> DatabaseInfo:
        row = rows[0] if rows else {}
        version_str = row.get("version") or sqlite3.sqlite_version
        parts = version_str.split(".")
        version_tuple = tuple(
            int(p) if p.isdigit() else 0
            for p in (parts + ["0", "0"])[:3]
        )
        # SQLite's database name is the schema name (e.g., "main")
        # For file-based databases, we can also show the filename
        db_path = self._backend.config.database or ":memory:"
        return DatabaseInfo(
            name="main",  # SQLite's default schema name
            version=version_str,
            version_tuple=version_tuple,
            vendor="SQLite",
            extra={"path": db_path},
        )

    def _parse_tables(
        self, rows: List[Dict[str, Any]], schema: Optional[str]
    ) -> List[TableInfo]:
        tables = []
        for row in rows:
            type_str = row.get("type", "table").lower()
            if type_str == "table":
                table_type = TableType.BASE_TABLE
            elif type_str == "view":
                table_type = TableType.VIEW
            else:
                table_type = TableType.EXTERNAL

            tables.append(
                TableInfo(
                    name=row["name"],
                    schema=schema or self._get_default_schema(),
                    table_type=table_type,
                    row_count=None,
                    create_time=None,
                )
            )
        return tables

    def _parse_columns(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[ColumnInfo]:
        columns = []
        for row in rows:
            if row.get("hidden", 0) > 0:
                continue
            nullable = (
                ColumnNullable.NULLABLE
                if row["notnull"] == 0
                else ColumnNullable.NOT_NULL
            )
            raw_type = row.get("type") or "TEXT"
            # Extract base type (e.g., "VARCHAR" from "VARCHAR(255)")
            import re
            base_type_match = re.match(r'^([A-Za-z_]+)', raw_type)
            base_type = base_type_match.group(1) if base_type_match else raw_type
            # SQLite pk field: 0 = not primary key, >0 = primary key (or part of composite PK)
            is_pk = row.get("pk", 0) > 0
            columns.append(
                ColumnInfo(
                    name=row["name"],
                    table_name=table_name,
                    schema=schema,
                    ordinal_position=row["cid"] + 1,
                    data_type=base_type.lower(),
                    data_type_full=raw_type,
                    nullable=nullable,
                    default_value=row.get("dflt_value"),
                    is_primary_key=is_pk,
                    extra={},
                )
            )
        return columns

    def _parse_indexes(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[IndexInfo]:
        if not rows:
            return []
        idx_map: Dict[str, IndexInfo] = {}
        for row in rows:
            idx_name = row.get("name")
            if idx_name not in idx_map:
                idx_type = IndexType.BTREE
                is_unique = bool(row.get("unique", 0))
                is_primary = idx_name.startswith("sqlite_autoindex_")
                idx_map[idx_name] = IndexInfo(
                    name=idx_name,
                    table_name=table_name,
                    schema=schema,
                    is_unique=is_unique,
                    is_primary=is_primary,
                    index_type=idx_type,
                    columns=[],
                    extra={},
                )
            col_name = row.get("column_name")
            if col_name:
                idx_map[idx_name].columns.append(
                    IndexColumnInfo(
                        name=col_name,
                        ordinal_position=row.get("seq", 0) + 1,
                    )
                )
        return list(idx_map.values())

    def _parse_foreign_keys(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[ForeignKeyInfo]:
        if not rows:
            return []
        fk_map: Dict[int, ForeignKeyInfo] = {}
        action_map = {
            "NO ACTION": ReferentialAction.NO_ACTION,
            "RESTRICT": ReferentialAction.RESTRICT,
            "CASCADE": ReferentialAction.CASCADE,
            "SET NULL": ReferentialAction.SET_NULL,
            "SET DEFAULT": ReferentialAction.SET_DEFAULT,
        }
        for row in rows:
            fk_id = row["id"]
            if fk_id not in fk_map:
                on_update = action_map.get(
                    row.get("on_update", "NO ACTION").upper(),
                    ReferentialAction.NO_ACTION,
                )
                on_delete = action_map.get(
                    row.get("on_delete", "NO ACTION").upper(),
                    ReferentialAction.NO_ACTION,
                )
                fk_map[fk_id] = ForeignKeyInfo(
                    name=f"fk_{table_name}_{fk_id}",
                    table_name=table_name,
                    schema=schema,
                    referenced_table=row["table"],
                    on_update=on_update,
                    on_delete=on_delete,
                    columns=[],
                    referenced_columns=[],
                )
            fk_map[fk_id].columns.append(row["from"])
            fk_map[fk_id].referenced_columns.append(row["to"])
        return list(fk_map.values())

    def _parse_views(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[ViewInfo]:
        return [
            ViewInfo(name=row["name"], schema=schema, definition=row.get("sql"))
            for row in rows
        ]

    def _parse_view_info(
        self, rows: List[Dict[str, Any]], view_name: str, schema: str
    ) -> Optional[ViewInfo]:
        if not rows:
            return None
        row = rows[0]
        return ViewInfo(
            name=row["name"], schema=schema, definition=row.get("sql")
        )

    def _parse_triggers(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[TriggerInfo]:
        return [
            TriggerInfo(
                name=row["name"],
                table_name=row["tbl_name"],
                schema=schema,
                definition=row.get("sql"),
            )
            for row in rows
        ]


class SyncSQLiteIntrospector(SQLiteIntrospectorMixin, SyncAbstractIntrospector):
    """Synchronous introspector for SQLite backends.

    In addition to the standard SyncAbstractIntrospector interface, exposes the
    `.pragma` sub-introspector for direct PRAGMA access::

        # Standard API
        tables = backend.introspector.list_tables()

        # SQLite-specific
        mode = backend.introspector.pragma.get("journal_mode")
        backend.introspector.pragma.set("journal_mode", "WAL")
        errors = backend.introspector.pragma.integrity_check()
    """

    def __init__(self, backend: Any, executor: SyncIntrospectorExecutor) -> None:
        super().__init__(backend, executor)
        self._pragma_instance: Optional[SyncPragmaIntrospector] = None
        self._status_instance: Optional[SyncSQLiteStatusIntrospector] = None

    @property
    def pragma(self) -> SyncPragmaIntrospector:
        """SQLite-specific PRAGMA sub-introspector (lazily created)."""
        if self._pragma_instance is None:
            self._pragma_instance = SyncPragmaIntrospector(self._backend, self._executor)
        return self._pragma_instance

    @property
    def status(self) -> SyncSQLiteStatusIntrospector:
        """SQLite status introspector (lazily created)."""
        if self._status_instance is None:
            self._status_instance = SyncSQLiteStatusIntrospector(self._backend)
        return self._status_instance

    # ------------------------------------------------------------------ #
    # Override list_indexes for SQLite's two-step index query
    # ------------------------------------------------------------------ #

    def list_indexes(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[IndexInfo]:
        """List all indexes of the given table.

        SQLite requires two queries:
        1. PRAGMA index_list(table) - get index list
        2. PRAGMA index_xinfo(index) - get column info for each index
        """
        target_db = schema or self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.INDEX, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        # Step 1: Get index list
        index_rows = self.pragma.index_list(table_name, target_db)
        if not index_rows:
            return []

        indexes: List[IndexInfo] = []
        for idx_row in index_rows:
            idx_name = idx_row.get("name", "")
            is_unique = bool(idx_row.get("unique", 0))
            is_primary = False  # Will be set based on origin below
            origin = idx_row.get("origin", "c")

            # Map origin to index type
            if origin == "pk":
                is_primary = True
                idx_type = IndexType.BTREE
            elif origin == "u":
                is_unique = True
                idx_type = IndexType.BTREE
            else:
                idx_type = IndexType.BTREE

            # Step 2: Get column info for this index
            col_rows = self.pragma.index_xinfo(idx_name, target_db)
            columns: List[IndexColumnInfo] = []
            for col_row in col_rows:
                col_name = col_row.get("name")
                if col_name:  # Skip rows with no column name (e.g., partial index condition)
                    columns.append(
                        IndexColumnInfo(
                            name=col_name,
                            ordinal_position=col_row.get("seqno", 0) + 1,
                            is_descending=bool(col_row.get("desc", 0)),
                        )
                    )

            indexes.append(
                IndexInfo(
                    name=idx_name,
                    table_name=table_name,
                    schema=target_db,
                    is_unique=is_unique,
                    is_primary=is_primary,
                    index_type=idx_type,
                    columns=columns,
                    extra={"origin": origin},
                )
            )

        self._set_cached(key, indexes)
        return indexes

    # ------------------------------------------------------------------ #
    # get_table_info override — uses direct _parse, avoids redundant
    # list_tables() call and populates columns/indexes/FKs in one sweep.
    # ------------------------------------------------------------------ #

    def get_table_info(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[TableInfo]:
        schema or self._get_default_schema()
        key = self._make_cache_key(
            IntrospectionScope.TABLE, table_name, schema=schema
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        tables = self.list_tables(schema)
        table = next((t for t in tables if t.name == table_name), None)
        if table is None:
            return None

        # Copy to avoid mutating the object stored in the list_tables() cache
        table = copy.copy(table)
        table.columns = self.list_columns(table_name, schema)
        table.indexes = self.list_indexes(table_name, schema)
        table.foreign_keys = self.list_foreign_keys(table_name, schema)
        self._set_cached(key, table)
        return table


class AsyncSQLiteIntrospector(SQLiteIntrospectorMixin, AsyncAbstractIntrospector):
    """Asynchronous introspector for SQLite backends.

    In addition to the standard AsyncAbstractIntrospector interface, exposes the
    `.pragma` sub-introspector for direct PRAGMA access::

        # Standard API
        tables = await backend.introspector.list_tables()

        # SQLite-specific
        mode = await backend.introspector.pragma.get("journal_mode")
        await backend.introspector.pragma.set("journal_mode", "WAL")
        errors = await backend.introspector.pragma.integrity_check()
    """

    def __init__(self, backend: Any, executor: AsyncIntrospectorExecutor) -> None:
        super().__init__(backend, executor)
        self._pragma_instance: Optional[AsyncPragmaIntrospector] = None
        self._status_instance: Optional[AsyncSQLiteStatusIntrospector] = None

    @property
    def pragma(self) -> AsyncPragmaIntrospector:
        """SQLite-specific PRAGMA sub-introspector (lazily created)."""
        if self._pragma_instance is None:
            self._pragma_instance = AsyncPragmaIntrospector(self._backend, self._executor)
        return self._pragma_instance

    @property
    def status(self) -> AsyncSQLiteStatusIntrospector:
        """SQLite status introspector (lazily created)."""
        if self._status_instance is None:
            self._status_instance = AsyncSQLiteStatusIntrospector(self._backend)
        return self._status_instance

    # ------------------------------------------------------------------ #
    # Override list_indexes for SQLite's two-step index query
    # ------------------------------------------------------------------ #

    async def list_indexes(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[IndexInfo]:
        """List all indexes of the given table.

        SQLite requires two queries:
        1. PRAGMA index_list(table) - get index list
        2. PRAGMA index_xinfo(index) - get column info for each index
        """
        target_db = schema or self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.INDEX, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        # Step 1: Get index list
        index_rows = await self.pragma.index_list(table_name, target_db)
        if not index_rows:
            return []

        indexes: List[IndexInfo] = []
        for idx_row in index_rows:
            idx_name = idx_row.get("name", "")
            is_unique = bool(idx_row.get("unique", 0))
            is_primary = False  # Will be set based on origin below
            origin = idx_row.get("origin", "c")

            # Map origin to index type
            if origin == "pk":
                is_primary = True
                idx_type = IndexType.BTREE
            elif origin == "u":
                is_unique = True
                idx_type = IndexType.BTREE
            else:
                idx_type = IndexType.BTREE

            # Step 2: Get column info for this index
            col_rows = await self.pragma.index_xinfo(idx_name, target_db)
            columns: List[IndexColumnInfo] = []
            for col_row in col_rows:
                col_name = col_row.get("name")
                if col_name:  # Skip rows with no column name (e.g., partial index condition)
                    columns.append(
                        IndexColumnInfo(
                            name=col_name,
                            ordinal_position=col_row.get("seqno", 0) + 1,
                            is_descending=bool(col_row.get("desc", 0)),
                        )
                    )

            indexes.append(
                IndexInfo(
                    name=idx_name,
                    table_name=table_name,
                    schema=target_db,
                    is_unique=is_unique,
                    is_primary=is_primary,
                    index_type=idx_type,
                    columns=columns,
                    extra={"origin": origin},
                )
            )

        self._set_cached(key, indexes)
        return indexes

    # ------------------------------------------------------------------ #
    # get_table_info override — uses direct _parse, avoids redundant
    # list_tables() call and populates columns/indexes/FKs in one sweep.
    # ------------------------------------------------------------------ #

    async def get_table_info(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[TableInfo]:
        schema or self._get_default_schema()
        key = self._make_cache_key(
            IntrospectionScope.TABLE, table_name, schema=schema
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        tables = await self.list_tables(schema)
        table = next((t for t in tables if t.name == table_name), None)
        if table is None:
            return None

        # Copy to avoid mutating the object stored in the list_tables() cache
        table = copy.copy(table)
        table.columns = await self.list_columns(table_name, schema)
        table.indexes = await self.list_indexes(table_name, schema)
        table.foreign_keys = await self.list_foreign_keys(table_name, schema)
        self._set_cached(key, table)
        return table
