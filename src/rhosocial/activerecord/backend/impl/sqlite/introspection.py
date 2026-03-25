# src/rhosocial/activerecord/backend/impl/sqlite/introspection.py
"""
SQLite introspection implementation.

This module provides SQLite-specific introspection capabilities,
using PRAGMA commands and sqlite_master table for metadata queries.
"""

import os
import sqlite3
from typing import Dict, List, Optional

from rhosocial.activerecord.backend.introspection.mixins import IntrospectionMixin, AsyncIntrospectionMixin
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


class SQLiteIntrospectionMixin(IntrospectionMixin):
    """SQLite introspection implementation.

    Uses SQLite PRAGMA commands and sqlite_master table for database
    introspection. Provides comprehensive metadata access including
    tables, columns, indexes, foreign keys, views, and triggers.

    Key features:
    - Version-aware introspection (PRAGMA table_list for 3.37.0+)
    - Extended column info (table_xinfo for 3.26.0+)
    - Schema support through attached databases

    This mixin accesses backend's connection and configuration directly
    through 'self', without needing an external backend parameter.
    """

    def _execute_introspection_query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute introspection query and return results as list of dicts.

        Args:
            sql: SQL query string.
            params: Query parameters.
        """
        cursor = self._get_cursor()
        try:
            cursor.execute(sql, params)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        finally:
            cursor.close()

    def _get_database_name(self) -> str:
        """Get database name from config.

        For SQLite, the database name in PRAGMA statements should be 'main'
        for the primary database, or the name of an attached database.
        The file path is NOT used as the database name in PRAGMA statements.
        """
        # SQLite always uses 'main' for the primary database
        # If schema is specified (for attached databases), use that
        return "main"

    def _get_sqlite_version(self) -> tuple:
        """Get SQLite version as tuple."""
        version_str = sqlite3.sqlite_version
        version_parts = version_str.split(".")
        return (
            int(version_parts[0]),
            int(version_parts[1]) if len(version_parts) > 1 else 0,
            int(version_parts[2]) if len(version_parts) > 2 else 0,
        )

    # ========== Query Methods Implementation ==========

    def _query_database_info(self) -> DatabaseInfo:
        """Query SQLite database information."""
        version_tuple = self._get_sqlite_version()
        version_str = sqlite3.sqlite_version

        db_name = self._get_database_name()
        db_path = getattr(self._connection, "name", None) if self._connection else None

        size_bytes = None
        if db_path and os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)

        return DatabaseInfo(
            name=db_name,
            version=version_str,
            version_tuple=version_tuple,
            vendor="SQLite",
            size_bytes=size_bytes,
        )

    def _query_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """Query table list."""
        target_db = schema or self._get_database_name()
        version = self._get_sqlite_version()

        # Use PRAGMA table_list for SQLite 3.37.0+
        if version >= (3, 37, 0):
            return self._list_tables_pragma(target_db, include_system, table_type)

        # Fall back to sqlite_master query for older versions
        return self._list_tables_master(target_db, include_system, table_type)

    def _list_tables_pragma(
        self, database: str, include_system: bool, table_type: Optional[str] = None
    ) -> List[TableInfo]:
        """List tables using PRAGMA table_list (SQLite 3.37.0+)."""
        sql = f"PRAGMA {database}.table_list"
        rows = self._execute_introspection_query(sql)

        tables = []
        for row in rows:
            # Skip internal tables unless requested
            if not include_system and row.get("name", "").startswith("sqlite_"):
                continue

            parsed_type = self._parse_table_type(row.get("type", "table"))
            if parsed_type is None:
                continue

            # Filter by table_type if specified
            if table_type:
                type_map = {
                    "BASE TABLE": TableType.BASE_TABLE,
                    "VIEW": TableType.VIEW,
                }
                if parsed_type != type_map.get(table_type):
                    continue

            tables.append(
                TableInfo(
                    name=row["name"],
                    schema=database,
                    table_type=parsed_type,
                )
            )

        return tables

    def _list_tables_master(
        self, database: str, include_system: bool, table_type: Optional[str] = None
    ) -> List[TableInfo]:
        """List tables using sqlite_master query."""
        sql = f"""
            SELECT name, type FROM {database}.sqlite_master
            WHERE type IN ('table', 'view')
        """
        if not include_system:
            sql += " AND name NOT LIKE 'sqlite_%'"

        if table_type:
            if table_type == "BASE TABLE":
                sql += " AND type = 'table'"
            elif table_type == "VIEW":
                sql += " AND type = 'view'"

        sql += " ORDER BY name"

        rows = self._execute_introspection_query(sql)

        tables = []
        for row in rows:
            # Determine if this is a system table (starts with sqlite_)
            is_system = row["name"].startswith("sqlite_")
            if row["type"] == "view":
                parsed_type = TableType.VIEW
            elif is_system:
                parsed_type = TableType.SYSTEM_TABLE
            else:
                parsed_type = TableType.BASE_TABLE

            # Filter by table_type
            if table_type:
                type_map = {
                    "BASE TABLE": TableType.BASE_TABLE,
                    "VIEW": TableType.VIEW,
                }
                if parsed_type != type_map.get(table_type):
                    continue

            tables.append(
                TableInfo(
                    name=row["name"],
                    schema=database,
                    table_type=parsed_type,
                )
            )

        # SQLite < 3.37.0: Manually add known system tables
        # sqlite_master table does not contain system table records, so they must be added manually
        if include_system and self._get_sqlite_version() < (3, 37, 0):
            existing_names = {t.name for t in tables}
            known_system_tables = self._get_known_system_tables(database)
            for sys_table in known_system_tables:
                if sys_table.name not in existing_names:
                    # Apply table_type filter
                    if table_type:
                        type_map = {
                            "BASE TABLE": TableType.BASE_TABLE,
                            "VIEW": TableType.VIEW,
                        }
                        if sys_table.table_type != type_map.get(table_type):
                            continue
                    tables.append(sys_table)
            # Re-sort the tables
            tables.sort(key=lambda t: t.name)

        return tables

    def _get_known_system_tables(self, database: str) -> List[TableInfo]:
        """Get known SQLite system tables for older versions.

        SQLite < 3.37.0 does not include system tables in sqlite_master.
        This method returns the standard SQLite system tables that actually exist.

        Args:
            database: Database name (e.g., 'main').

        Returns:
            List of TableInfo for existing system tables.
        """
        # Basic system tables (available in all versions)
        # sqlite_schema is the official name for sqlite_master (SQLite 3.33.0+)
        # sqlite_master is an alias for sqlite_schema, both refer to the same table
        system_tables = [
            TableInfo(
                name="sqlite_schema",
                schema=database,
                table_type=TableType.SYSTEM_TABLE,
            ),
        ]

        # Check if sqlite_stat1 exists (created after ANALYZE)
        try:
            self._execute_introspection_query(
                "SELECT 1 FROM sqlite_stat1 LIMIT 1"
            )
            system_tables.append(
                TableInfo(
                    name="sqlite_stat1",
                    schema=database,
                    table_type=TableType.SYSTEM_TABLE,
                )
            )
        except Exception:
            pass  # sqlite_stat1 does not exist

        # Check if sqlite_sequence exists (created after using AUTOINCREMENT)
        try:
            self._execute_introspection_query(
                "SELECT 1 FROM sqlite_sequence LIMIT 1"
            )
            system_tables.append(
                TableInfo(
                    name="sqlite_sequence",
                    schema=database,
                    table_type=TableType.SYSTEM_TABLE,
                )
            )
        except Exception:
            pass  # sqlite_sequence does not exist

        return system_tables

    def _parse_table_type(self, type_str: str) -> Optional[TableType]:
        """Parse SQLite table type string to TableType enum."""
        type_map = {
            "table": TableType.BASE_TABLE,
            "view": TableType.VIEW,
            "virtual": TableType.EXTERNAL,
            "shadow": TableType.SYSTEM_TABLE,
        }
        return type_map.get(type_str.lower())

    def _query_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[TableInfo]:
        """Query table information."""
        tables = self._query_tables(schema, False)
        table = next((t for t in tables if t.name == table_name), None)
        if not table:
            return None

        table.columns = self._query_columns(table_name, schema)
        table.indexes = self._query_indexes(table_name, schema)
        table.foreign_keys = self._query_foreign_keys(table_name, schema)

        return table

    def _query_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """Query column list for a table."""
        target_db = schema or self._get_database_name()
        version = self._get_sqlite_version()

        # SQLite PRAGMA doesn't support parameterized queries
        # Table name must be interpolated directly
        # Note: table_name should come from trusted sources (database introspection)
        # Use table_xinfo for SQLite 3.26.0+ (includes hidden columns)
        if version >= (3, 26, 0):
            sql = f"PRAGMA {target_db}.table_xinfo('{table_name}')"
        else:
            sql = f"PRAGMA {target_db}.table_info('{table_name}')"

        rows = self._execute_introspection_query(sql)

        columns = []
        for row in rows:
            # Skip hidden columns (primary key columns in WITHOUT ROWID tables)
            hidden = row.get("hidden", 0)
            if hidden > 0:
                continue

            nullable = ColumnNullable.NULLABLE if row["notnull"] == 0 else ColumnNullable.NOT_NULL

            col = ColumnInfo(
                name=row["name"],
                table_name=table_name,
                schema=target_db,
                ordinal_position=row["cid"] + 1,
                data_type=row["type"].split("(")[0].upper() if row["type"] else "TEXT",
                data_type_full=row["type"] or "TEXT",
                nullable=nullable,
                default_value=row.get("dflt_value"),
                is_primary_key=row["pk"] > 0,
            )
            columns.append(col)

        return columns

    def _query_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """Query index list for a table."""
        target_db = schema or self._get_database_name()

        # SQLite PRAGMA doesn't support parameterized queries
        sql = f"PRAGMA {target_db}.index_list('{table_name}')"
        rows = self._execute_introspection_query(sql)

        indexes = []
        for row in rows:
            idx_name = row["name"]
            is_unique = row["unique"] == 1
            is_primary = row["origin"] == "pk"

            # Get index columns
            col_sql = f"PRAGMA {target_db}.index_info('{idx_name}')"
            col_rows = self._execute_introspection_query(col_sql)

            columns = [
                IndexColumnInfo(
                    name=cr["name"],
                    ordinal_position=cr["seqno"] + 1,
                )
                for cr in col_rows
                if cr["name"]
            ]

            indexes.append(
                IndexInfo(
                    name=idx_name,
                    table_name=table_name,
                    schema=target_db,
                    is_unique=is_unique,
                    is_primary=is_primary,
                    index_type=IndexType.BTREE,  # SQLite uses B-tree
                    columns=columns,
                )
            )

        return indexes

    def _query_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """Query foreign key list for a table."""
        target_db = schema or self._get_database_name()

        # SQLite PRAGMA doesn't support parameterized queries
        sql = f"PRAGMA {target_db}.foreign_key_list('{table_name}')"
        rows = self._execute_introspection_query(sql)

        # Group by foreign key id
        fk_map: Dict[int, ForeignKeyInfo] = {}

        for row in rows:
            fk_id = row["id"]

            if fk_id not in fk_map:
                # SQLite uses simple string names for actions
                action_map = {
                    "NO ACTION": ReferentialAction.NO_ACTION,
                    "RESTRICT": ReferentialAction.RESTRICT,
                    "CASCADE": ReferentialAction.CASCADE,
                    "SET NULL": ReferentialAction.SET_NULL,
                    "SET DEFAULT": ReferentialAction.SET_DEFAULT,
                }

                on_update = action_map.get(row.get("on_update", "NO ACTION").upper(), ReferentialAction.NO_ACTION)
                on_delete = action_map.get(row.get("on_delete", "NO ACTION").upper(), ReferentialAction.NO_ACTION)

                fk_map[fk_id] = ForeignKeyInfo(
                    name=f"fk_{table_name}_{fk_id}",
                    table_name=table_name,
                    schema=target_db,
                    referenced_table=row["table"],
                    on_update=on_update,
                    on_delete=on_delete,
                    columns=[],
                    referenced_columns=[],
                )

            fk_map[fk_id].columns.append(row["from"])
            fk_map[fk_id].referenced_columns.append(row["to"])

        return list(fk_map.values())

    def _query_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """Query view list."""
        target_db = schema or self._get_database_name()

        sql = f"""
            SELECT name, sql FROM {target_db}.sqlite_master
            WHERE type = 'view'
        """
        if not include_system:
            sql += " AND name NOT LIKE 'sqlite_%'"

        sql += " ORDER BY name"

        rows = self._execute_introspection_query(sql)

        return [
            ViewInfo(
                name=row["name"],
                schema=target_db,
                definition=row.get("sql"),
            )
            for row in rows
        ]

    def _query_view_info(self, view_name: str, schema: Optional[str] = None) -> Optional[ViewInfo]:
        """Query view information."""
        views = self._query_views(schema, False)
        return next((v for v in views if v.name == view_name), None)

    def _query_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """Query trigger list."""
        target_db = schema or self._get_database_name()

        sql = f"""
            SELECT name, tbl_name, sql FROM {target_db}.sqlite_master
            WHERE type = 'trigger'
        """
        params = ()

        if table_name:
            sql += " AND tbl_name = ?"
            params = (table_name,)

        sql += " ORDER BY name"

        rows = self._execute_introspection_query(sql, params)

        return [
            TriggerInfo(
                name=row["name"],
                table_name=row["tbl_name"],
                schema=target_db,
                definition=row.get("sql"),
            )
            for row in rows
        ]


class SQLiteAsyncIntrospectionMixin(AsyncIntrospectionMixin):
    """Async SQLite introspection implementation.

    Uses SQLite PRAGMA commands and sqlite_master table for database
    introspection. Provides comprehensive metadata access including
    tables, columns, indexes, foreign keys, views, and triggers.

    This is the async version of SQLiteIntrospectionMixin, using aiosqlite
    for asynchronous database operations.

    Key features:
    - Version-aware introspection (PRAGMA table_list for 3.37.0+)
    - Extended column info (table_xinfo for 3.26.0+)
    - Schema support through attached databases

    This mixin accesses backend's connection and configuration directly
    through 'self', without needing an external backend parameter.
    """

    async def _execute_introspection_query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """Execute introspection query and return results as list of dicts.

        Args:
            sql: SQL query string.
            params: Query parameters.
        """
        cursor = await self._get_cursor()
        try:
            await cursor.execute(sql, params)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = []
            rows = await cursor.fetchall()
            for row in rows:
                results.append(dict(zip(columns, row)))
            return results
        finally:
            await cursor.close()

    def _get_database_name(self) -> str:
        """Get database name from config.

        For SQLite, the database name in PRAGMA statements should be 'main'
        for the primary database, or the name of an attached database.
        The file path is NOT used as the database name in PRAGMA statements.
        """
        # SQLite always uses 'main' for the primary database
        # If schema is specified (for attached databases), use that
        return "main"

    def _get_sqlite_version(self) -> tuple:
        """Get SQLite version as tuple."""
        version_str = sqlite3.sqlite_version
        version_parts = version_str.split(".")
        return (
            int(version_parts[0]),
            int(version_parts[1]) if len(version_parts) > 1 else 0,
            int(version_parts[2]) if len(version_parts) > 2 else 0,
        )

    # ========== Query Methods Implementation ==========

    async def _query_database_info(self) -> DatabaseInfo:
        """Query SQLite database information."""
        version_tuple = self._get_sqlite_version()
        version_str = sqlite3.sqlite_version

        db_name = self._get_database_name()
        # For aiosqlite, connection object has _connection attribute pointing to the underlying sqlite3 connection
        db_path = None
        if self._connection:
            # aiosqlite.Connection wraps the actual sqlite3 connection
            if hasattr(self._connection, "_connection"):
                db_path = getattr(self._connection._connection, "name", None)
            else:
                db_path = getattr(self._connection, "name", None)

        size_bytes = None
        if db_path and os.path.exists(db_path):
            size_bytes = os.path.getsize(db_path)

        return DatabaseInfo(
            name=db_name,
            version=version_str,
            version_tuple=version_tuple,
            vendor="SQLite",
            size_bytes=size_bytes,
        )

    async def _query_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """Query table list."""
        target_db = schema or self._get_database_name()
        version = self._get_sqlite_version()

        # Use PRAGMA table_list for SQLite 3.37.0+
        if version >= (3, 37, 0):
            return await self._list_tables_pragma(target_db, include_system, table_type)

        # Fall back to sqlite_master query for older versions
        return await self._list_tables_master(target_db, include_system, table_type)

    async def _list_tables_pragma(
        self, database: str, include_system: bool, table_type: Optional[str] = None
    ) -> List[TableInfo]:
        """List tables using PRAGMA table_list (SQLite 3.37.0+)."""
        sql = f"PRAGMA {database}.table_list"
        rows = await self._execute_introspection_query(sql)

        tables = []
        for row in rows:
            # Skip internal tables unless requested
            if not include_system and row.get("name", "").startswith("sqlite_"):
                continue

            parsed_type = self._parse_table_type(row.get("type", "table"))
            if parsed_type is None:
                continue

            # Filter by table_type if specified
            if table_type:
                type_map = {
                    "BASE TABLE": TableType.BASE_TABLE,
                    "VIEW": TableType.VIEW,
                }
                if parsed_type != type_map.get(table_type):
                    continue

            tables.append(
                TableInfo(
                    name=row["name"],
                    schema=database,
                    table_type=parsed_type,
                )
            )

        return tables

    async def _list_tables_master(
        self, database: str, include_system: bool, table_type: Optional[str] = None
    ) -> List[TableInfo]:
        """List tables using sqlite_master query."""
        sql = f"""
            SELECT name, type FROM {database}.sqlite_master
            WHERE type IN ('table', 'view')
        """
        if not include_system:
            sql += " AND name NOT LIKE 'sqlite_%'"

        if table_type:
            if table_type == "BASE TABLE":
                sql += " AND type = 'table'"
            elif table_type == "VIEW":
                sql += " AND type = 'view'"

        sql += " ORDER BY name"

        rows = await self._execute_introspection_query(sql)

        tables = []
        for row in rows:
            # Determine if this is a system table (starts with sqlite_)
            is_system = row["name"].startswith("sqlite_")
            if row["type"] == "view":
                parsed_type = TableType.VIEW
            elif is_system:
                parsed_type = TableType.SYSTEM_TABLE
            else:
                parsed_type = TableType.BASE_TABLE

            # Filter by table_type
            if table_type:
                type_map = {
                    "BASE TABLE": TableType.BASE_TABLE,
                    "VIEW": TableType.VIEW,
                }
                if parsed_type != type_map.get(table_type):
                    continue

            tables.append(
                TableInfo(
                    name=row["name"],
                    schema=database,
                    table_type=parsed_type,
                )
            )

        # SQLite < 3.37.0: Manually add known system tables
        # sqlite_master table does not contain system table records, so they must be added manually
        if include_system and self._get_sqlite_version() < (3, 37, 0):
            existing_names = {t.name for t in tables}
            known_system_tables = await self._get_known_system_tables(database)
            for sys_table in known_system_tables:
                if sys_table.name not in existing_names:
                    # Apply table_type filter
                    if table_type:
                        type_map = {
                            "BASE TABLE": TableType.BASE_TABLE,
                            "VIEW": TableType.VIEW,
                        }
                        if sys_table.table_type != type_map.get(table_type):
                            continue
                    tables.append(sys_table)
            # Re-sort the tables
            tables.sort(key=lambda t: t.name)

        return tables

    async def _get_known_system_tables(self, database: str) -> List[TableInfo]:
        """Get known SQLite system tables for older versions.

        SQLite < 3.37.0 does not include system tables in sqlite_master.
        This method returns the standard SQLite system tables that actually exist.

        Args:
            database: Database name (e.g., 'main').

        Returns:
            List of TableInfo for existing system tables.
        """
        # Basic system tables (available in all versions)
        # sqlite_schema is the official name for sqlite_master (SQLite 3.33.0+)
        # sqlite_master is an alias for sqlite_schema, both refer to the same table
        system_tables = [
            TableInfo(
                name="sqlite_schema",
                schema=database,
                table_type=TableType.SYSTEM_TABLE,
            ),
        ]

        # Check if sqlite_stat1 exists (created after ANALYZE)
        try:
            await self._execute_introspection_query(
                "SELECT 1 FROM sqlite_stat1 LIMIT 1"
            )
            system_tables.append(
                TableInfo(
                    name="sqlite_stat1",
                    schema=database,
                    table_type=TableType.SYSTEM_TABLE,
                )
            )
        except Exception:
            pass  # sqlite_stat1 does not exist

        # Check if sqlite_sequence exists (created after using AUTOINCREMENT)
        try:
            await self._execute_introspection_query(
                "SELECT 1 FROM sqlite_sequence LIMIT 1"
            )
            system_tables.append(
                TableInfo(
                    name="sqlite_sequence",
                    schema=database,
                    table_type=TableType.SYSTEM_TABLE,
                )
            )
        except Exception:
            pass  # sqlite_sequence does not exist

        return system_tables

    def _parse_table_type(self, type_str: str) -> Optional[TableType]:
        """Parse SQLite table type string to TableType enum."""
        type_map = {
            "table": TableType.BASE_TABLE,
            "view": TableType.VIEW,
            "virtual": TableType.EXTERNAL,
            "shadow": TableType.SYSTEM_TABLE,
        }
        return type_map.get(type_str.lower())

    async def _query_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[TableInfo]:
        """Query table information."""
        tables = await self._query_tables(schema, False)
        table = next((t for t in tables if t.name == table_name), None)
        if not table:
            return None

        table.columns = await self._query_columns(table_name, schema)
        table.indexes = await self._query_indexes(table_name, schema)
        table.foreign_keys = await self._query_foreign_keys(table_name, schema)

        return table

    async def _query_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """Query column list for a table."""
        target_db = schema or self._get_database_name()
        version = self._get_sqlite_version()

        # SQLite PRAGMA doesn't support parameterized queries
        # Table name must be interpolated directly
        # Note: table_name should come from trusted sources (database introspection)
        # Use table_xinfo for SQLite 3.26.0+ (includes hidden columns)
        if version >= (3, 26, 0):
            sql = f"PRAGMA {target_db}.table_xinfo('{table_name}')"
        else:
            sql = f"PRAGMA {target_db}.table_info('{table_name}')"

        rows = await self._execute_introspection_query(sql)

        columns = []
        for row in rows:
            # Skip hidden columns (primary key columns in WITHOUT ROWID tables)
            hidden = row.get("hidden", 0)
            if hidden > 0:
                continue

            nullable = ColumnNullable.NULLABLE if row["notnull"] == 0 else ColumnNullable.NOT_NULL

            col = ColumnInfo(
                name=row["name"],
                table_name=table_name,
                schema=target_db,
                ordinal_position=row["cid"] + 1,
                data_type=row["type"].split("(")[0].upper() if row["type"] else "TEXT",
                data_type_full=row["type"] or "TEXT",
                nullable=nullable,
                default_value=row.get("dflt_value"),
                is_primary_key=row["pk"] > 0,
            )
            columns.append(col)

        return columns

    async def _query_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """Query index list for a table."""
        target_db = schema or self._get_database_name()

        # SQLite PRAGMA doesn't support parameterized queries
        sql = f"PRAGMA {target_db}.index_list('{table_name}')"
        rows = await self._execute_introspection_query(sql)

        indexes = []
        for row in rows:
            idx_name = row["name"]
            is_unique = row["unique"] == 1
            is_primary = row["origin"] == "pk"

            # Get index columns
            col_sql = f"PRAGMA {target_db}.index_info('{idx_name}')"
            col_rows = await self._execute_introspection_query(col_sql)

            columns = [
                IndexColumnInfo(
                    name=cr["name"],
                    ordinal_position=cr["seqno"] + 1,
                )
                for cr in col_rows
                if cr["name"]
            ]

            indexes.append(
                IndexInfo(
                    name=idx_name,
                    table_name=table_name,
                    schema=target_db,
                    is_unique=is_unique,
                    is_primary=is_primary,
                    index_type=IndexType.BTREE,  # SQLite uses B-tree
                    columns=columns,
                )
            )

        return indexes

    async def _query_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """Query foreign key list for a table."""
        target_db = schema or self._get_database_name()

        # SQLite PRAGMA doesn't support parameterized queries
        sql = f"PRAGMA {target_db}.foreign_key_list('{table_name}')"
        rows = await self._execute_introspection_query(sql)

        # Group by foreign key id
        fk_map: Dict[int, ForeignKeyInfo] = {}

        for row in rows:
            fk_id = row["id"]

            if fk_id not in fk_map:
                # SQLite uses simple string names for actions
                action_map = {
                    "NO ACTION": ReferentialAction.NO_ACTION,
                    "RESTRICT": ReferentialAction.RESTRICT,
                    "CASCADE": ReferentialAction.CASCADE,
                    "SET NULL": ReferentialAction.SET_NULL,
                    "SET DEFAULT": ReferentialAction.SET_DEFAULT,
                }

                on_update = action_map.get(row.get("on_update", "NO ACTION").upper(), ReferentialAction.NO_ACTION)
                on_delete = action_map.get(row.get("on_delete", "NO ACTION").upper(), ReferentialAction.NO_ACTION)

                fk_map[fk_id] = ForeignKeyInfo(
                    name=f"fk_{table_name}_{fk_id}",
                    table_name=table_name,
                    schema=target_db,
                    referenced_table=row["table"],
                    on_update=on_update,
                    on_delete=on_delete,
                    columns=[],
                    referenced_columns=[],
                )

            fk_map[fk_id].columns.append(row["from"])
            fk_map[fk_id].referenced_columns.append(row["to"])

        return list(fk_map.values())

    async def _query_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """Query view list."""
        target_db = schema or self._get_database_name()

        sql = f"""
            SELECT name, sql FROM {target_db}.sqlite_master
            WHERE type = 'view'
        """
        if not include_system:
            sql += " AND name NOT LIKE 'sqlite_%'"

        sql += " ORDER BY name"

        rows = await self._execute_introspection_query(sql)

        return [
            ViewInfo(
                name=row["name"],
                schema=target_db,
                definition=row.get("sql"),
            )
            for row in rows
        ]

    async def _query_view_info(self, view_name: str, schema: Optional[str] = None) -> Optional[ViewInfo]:
        """Query view information."""
        views = await self._query_views(schema, False)
        return next((v for v in views if v.name == view_name), None)

    async def _query_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """Query trigger list."""
        target_db = schema or self._get_database_name()

        sql = f"""
            SELECT name, tbl_name, sql FROM {target_db}.sqlite_master
            WHERE type = 'trigger'
        """
        params = ()

        if table_name:
            sql += " AND tbl_name = ?"
            params = (table_name,)

        sql += " ORDER BY name"

        rows = await self._execute_introspection_query(sql, params)

        return [
            TriggerInfo(
                name=row["name"],
                table_name=row["tbl_name"],
                schema=target_db,
                definition=row.get("sql"),
            )
            for row in rows
        ]
