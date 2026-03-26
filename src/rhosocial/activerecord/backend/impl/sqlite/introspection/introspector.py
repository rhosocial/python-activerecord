# src/rhosocial/activerecord/backend/impl/sqlite/introspection/introspector.py
"""
SQLite concrete introspector.

Implements AbstractIntrospector for SQLite databases using PRAGMA commands
and the sqlite_master / sqlite_schema system table for metadata queries.

The introspector is exposed via ``backend.introspector`` and also provides
SQLite-specific access through ``backend.introspector.pragma``.

Key behaviours:
  - Version-aware: uses ``PRAGMA table_list`` (3.37+) or ``sqlite_master``
  - Extended column info: uses ``PRAGMA table_xinfo`` (3.26+)
  - ``_parse_*`` methods are pure Python — shared by sync and async paths
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional

from rhosocial.activerecord.backend.introspection.base import AbstractIntrospector
from rhosocial.activerecord.backend.introspection.executor import IntrospectorExecutor
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
)
from rhosocial.activerecord.backend.expression.introspection import (
    DatabaseInfoExpression,
    TableListExpression,
    ColumnInfoExpression,
    IndexInfoExpression,
    ForeignKeyExpression,
    ViewListExpression,
    ViewInfoExpression,
    TriggerListExpression,
)
from .pragma_introspector import PragmaIntrospector


class SQLiteIntrospector(AbstractIntrospector):
    """Introspector for SQLite backends.

    In addition to the standard AbstractIntrospector interface, exposes the
    `.pragma` sub-introspector for direct PRAGMA access::

        # Standard API
        tables = backend.introspector.list_tables()

        # SQLite-specific
        mode = backend.introspector.pragma.get("journal_mode")
        backend.introspector.pragma.set("journal_mode", "WAL")
        errors = backend.introspector.pragma.integrity_check()
    """

    def __init__(self, backend: Any, executor: IntrospectorExecutor) -> None:
        super().__init__(backend, executor)
        self._pragma_instance: Optional[PragmaIntrospector] = None

    # ------------------------------------------------------------------ #
    # Sub-introspector: PRAGMA
    # ------------------------------------------------------------------ #

    @property
    def pragma(self) -> PragmaIntrospector:
        """SQLite-specific PRAGMA sub-introspector (lazily created)."""
        if self._pragma_instance is None:
            self._pragma_instance = PragmaIntrospector(self._backend, self._executor)
        return self._pragma_instance

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

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
    # SQL generation overrides
    # SQLite uses PRAGMA for most introspection, so we override the default
    # Expression-based builders where necessary.
    # ------------------------------------------------------------------ #

    def _build_table_list_sql(
        self,
        schema: Optional[str],
        include_system: bool,
        include_views: bool = True,
        table_type: Optional[str] = None,
    ):
        target_db = schema or self._get_default_schema()
        expr = (
            TableListExpression(self.dialect)
            .schema(target_db)
            .include_system(include_system)
            .include_views(include_views)
        )
        if table_type:
            expr = expr.table_type(table_type)
        return expr.to_sql()

    def _build_column_info_sql(self, table_name: str, schema: Optional[str]):
        target_db = schema or self._get_default_schema()
        return (
            ColumnInfoExpression(self.dialect, table_name)
            .schema(target_db)
            .include_hidden(False)
            .to_sql()
        )

    def _build_index_info_sql(self, table_name: str, schema: Optional[str]):
        target_db = schema or self._get_default_schema()
        return IndexInfoExpression(self.dialect, table_name).schema(target_db).to_sql()

    def _build_foreign_key_sql(self, table_name: str, schema: Optional[str]):
        target_db = schema or self._get_default_schema()
        return ForeignKeyExpression(self.dialect, table_name).schema(target_db).to_sql()

    def _build_view_list_sql(self, schema: Optional[str], include_system: bool):
        target_db = schema or self._get_default_schema()
        return (
            ViewListExpression(self.dialect)
            .schema(target_db)
            .include_system(include_system)
            .to_sql()
        )

    def _build_view_info_sql(self, view_name: str, schema: Optional[str]):
        target_db = schema or self._get_default_schema()
        return ViewInfoExpression(self.dialect, view_name).schema(target_db).to_sql()

    def _build_trigger_list_sql(
        self, table_name: Optional[str], schema: Optional[str]
    ):
        target_db = schema or self._get_default_schema()
        expr = TriggerListExpression(self.dialect).schema(target_db)
        if table_name:
            expr = expr.for_table(table_name)
        return expr.to_sql()

    # ------------------------------------------------------------------ #
    # list_* overrides — SQLite sometimes needs extra queries (e.g. index
    # columns require a nested PRAGMA index_info call).
    # ------------------------------------------------------------------ #

    def list_indexes(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[IndexInfo]:
        """List indexes for a table.

        Overrides the base implementation to perform the nested
        ``PRAGMA index_info`` query required by SQLite.
        """
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        target_db = schema or self._get_default_schema()
        key = self._make_cache_key(
            IntrospectionScope.INDEX, table_name, schema=schema
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        sql, params = self._build_index_info_sql(table_name, schema)
        rows = self._executor.execute(sql, params)
        result = self._parse_indexes_with_columns(rows, table_name, target_db)
        self._set_cached(key, result)
        return result

    async def list_indexes_async(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[IndexInfo]:
        """Async version of list_indexes()."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        target_db = schema or self._get_default_schema()
        key = self._make_cache_key(
            IntrospectionScope.INDEX, table_name, schema=schema
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        sql, params = self._build_index_info_sql(table_name, schema)
        rows = await self._executor.execute_async(sql, params)
        result = await self._parse_indexes_with_columns_async(
            rows, table_name, target_db
        )
        self._set_cached(key, result)
        return result

    def _parse_indexes_with_columns(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> List[IndexInfo]:
        """Build IndexInfo objects, fetching column details via nested PRAGMA."""
        indexes = []
        for row in rows:
            idx_name = row["name"]
            col_sql = f"PRAGMA {schema}.index_info('{idx_name}')"
            col_rows = self._executor.execute(col_sql, ())
            indexes.append(
                self._build_index_info(row, col_rows, table_name, schema)
            )
        return indexes

    async def _parse_indexes_with_columns_async(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> List[IndexInfo]:
        """Async version — fetches index column details via nested PRAGMA."""
        indexes = []
        for row in rows:
            idx_name = row["name"]
            col_sql = f"PRAGMA {schema}.index_info('{idx_name}')"
            col_rows = await self._executor.execute_async(col_sql, ())
            indexes.append(
                self._build_index_info(row, col_rows, table_name, schema)
            )
        return indexes

    @staticmethod
    def _build_index_info(
        row: Dict[str, Any],
        col_rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> IndexInfo:
        columns = [
            IndexColumnInfo(name=cr["name"], ordinal_position=cr["seqno"] + 1)
            for cr in col_rows
            if cr["name"]
        ]
        return IndexInfo(
            name=row["name"],
            table_name=table_name,
            schema=schema,
            is_unique=row["unique"] == 1,
            is_primary=row["origin"] == "pk",
            index_type=IndexType.BTREE,
            columns=columns,
        )

    # ------------------------------------------------------------------ #
    # Parse methods — pure Python, no I/O
    # ------------------------------------------------------------------ #

    def _parse_database_info(
        self, rows: List[Dict[str, Any]]
    ) -> DatabaseInfo:
        version_tuple = self._get_sqlite_version()
        version_str = sqlite3.sqlite_version
        db_name = self._get_default_schema()

        db_path = None
        if self._backend._connection:
            conn = self._backend._connection
            # aiosqlite wraps the real sqlite3 connection
            inner = getattr(conn, "_connection", conn)
            db_path = getattr(inner, "database", None) or getattr(inner, "name", None)

        size_bytes = None
        if db_path and db_path != ":memory:" and os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)

        return DatabaseInfo(
            name=db_name,
            version=version_str,
            version_tuple=version_tuple,
            vendor="SQLite",
            size_bytes=size_bytes,
        )

    def _parse_tables(
        self, rows: List[Dict[str, Any]], schema: Optional[str]
    ) -> List[TableInfo]:
        target_db = schema or self._get_default_schema()
        if self.dialect.supports_table_list_pragma():
            return self._parse_table_list_pragma(rows, target_db)
        return self._parse_table_list_master(rows, target_db)

    def _parse_table_list_pragma(
        self, rows: List[Dict[str, Any]], database: str
    ) -> List[TableInfo]:
        """Parse ``PRAGMA table_list`` results (SQLite 3.37+)."""
        tables = []
        for row in rows:
            parsed_type = self._parse_table_type(row.get("type", "table"))
            if parsed_type is None:
                continue
            tables.append(
                TableInfo(name=row["name"], schema=database, table_type=parsed_type)
            )
        return tables

    def _parse_table_list_master(
        self, rows: List[Dict[str, Any]], database: str
    ) -> List[TableInfo]:
        """Parse ``sqlite_master`` / ``sqlite_schema`` results."""
        tables = []
        for row in rows:
            name = row["name"]
            row_type = row["type"]
            is_system = name.startswith("sqlite_")

            if row_type == "view":
                t_type = TableType.VIEW
            elif is_system:
                t_type = TableType.SYSTEM_TABLE
            else:
                t_type = TableType.BASE_TABLE

            tables.append(TableInfo(name=name, schema=database, table_type=t_type))
        return tables

    @staticmethod
    def _parse_table_type(type_str: str) -> Optional[TableType]:
        return {
            "table": TableType.BASE_TABLE,
            "view": TableType.VIEW,
            "virtual": TableType.EXTERNAL,
            "shadow": TableType.SYSTEM_TABLE,
        }.get(type_str.lower())

    def _parse_columns(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
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
            columns.append(
                ColumnInfo(
                    name=row["name"],
                    table_name=table_name,
                    schema=schema,
                    ordinal_position=row["cid"] + 1,
                    data_type=raw_type.split("(")[0].upper(),
                    data_type_full=raw_type,
                    nullable=nullable,
                    default_value=row.get("dflt_value"),
                    is_primary_key=row["pk"] > 0,
                )
            )
        return columns

    def _parse_indexes(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> List[IndexInfo]:
        # This path is used when the caller invokes the base-class
        # list_indexes(); it does not fetch column details.
        # SQLiteIntrospector.list_indexes() overrides to use the nested query.
        return [
            IndexInfo(
                name=row["name"],
                table_name=table_name,
                schema=schema,
                is_unique=row["unique"] == 1,
                is_primary=row["origin"] == "pk",
                index_type=IndexType.BTREE,
                columns=[],
            )
            for row in rows
        ]

    def _parse_foreign_keys(
        self,
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
    ) -> List[ForeignKeyInfo]:
        action_map = {
            "NO ACTION": ReferentialAction.NO_ACTION,
            "RESTRICT": ReferentialAction.RESTRICT,
            "CASCADE": ReferentialAction.CASCADE,
            "SET NULL": ReferentialAction.SET_NULL,
            "SET DEFAULT": ReferentialAction.SET_DEFAULT,
        }
        fk_map: Dict[int, ForeignKeyInfo] = {}
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
        self,
        rows: List[Dict[str, Any]],
        view_name: str,
        schema: str,
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

    # ------------------------------------------------------------------ #
    # get_table_info override — uses direct _parse, avoids redundant
    # list_tables() call and populates columns/indexes/FKs in one sweep.
    # ------------------------------------------------------------------ #

    def get_table_info(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[TableInfo]:
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope
        import copy

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

    async def get_table_info_async(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[TableInfo]:
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope
        import copy

        key = self._make_cache_key(
            IntrospectionScope.TABLE, table_name, schema=schema
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached

        tables = await self.list_tables_async(schema)
        table = next((t for t in tables if t.name == table_name), None)
        if table is None:
            return None

        # Copy to avoid mutating the object stored in the list_tables_async() cache
        table = copy.copy(table)
        table.columns = await self.list_columns_async(table_name, schema)
        table.indexes = await self.list_indexes_async(table_name, schema)
        table.foreign_keys = await self.list_foreign_keys_async(table_name, schema)
        self._set_cached(key, table)
        return table
