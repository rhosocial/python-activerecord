# src/rhosocial/activerecord/backend/impl/sqlite/mixins/introspection.py
"""
SQLite-specific Introspection implementation.

This module provides the SQLiteIntrospectionCapabilityMixin class.
"""

from typing import List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.introspection import (
        DatabaseInfoExpression,
        TableListExpression,
        TableInfoExpression,
        ColumnInfoExpression,
        IndexInfoExpression,
        ForeignKeyExpression,
        ViewListExpression,
        ViewInfoExpression,
        TriggerListExpression,
        TriggerInfoExpression,
    )
    from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

class SQLiteIntrospectionCapabilityMixin:
    """SQLite introspection capability declaration.

    This mixin implements the IntrospectionSupport protocol by declaring
    which introspection features SQLite supports based on version.
    The actual introspection implementation is in the backend layer
    via SQLiteIntrospectionMixin from the introspection module.

    Dialects only declare capabilities (supports_* methods), they do not
    implement the actual introspection methods.

    Version requirements for SQLite introspection features:
    - PRAGMA table_list: SQLite 3.37.0+ (fallback to sqlite_master query)
    - PRAGMA table_xinfo: SQLite 3.26.0+ (includes hidden columns)
    - PRAGMA table_info: All versions
    - PRAGMA index_list/index_info: All versions
    - PRAGMA foreign_key_list: SQLite 3.6.19+
    """

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """SQLite supports introspection."""
        return True

    def supports_database_info(self) -> bool:
        """SQLite supports database info."""
        return True

    def supports_table_introspection(self) -> bool:
        """SQLite supports table introspection."""
        return True

    def supports_column_introspection(self) -> bool:
        """SQLite supports column introspection.

        PRAGMA table_info is available in all versions.
        PRAGMA table_xinfo (with hidden column support) needs 3.26.0+.
        """
        return True

    def supports_index_introspection(self) -> bool:
        """SQLite supports index introspection."""
        return True

    def supports_foreign_key_introspection(self) -> bool:
        """SQLite supports foreign key introspection.

        PRAGMA foreign_key_list was added in SQLite 3.6.19 (2009-10-14).
        Note: Foreign key constraints are disabled by default and must be
        enabled via 'PRAGMA foreign_keys = ON'.
        """
        version = self.version
        return version >= (3, 6, 19)

    def supports_view_introspection(self) -> bool:
        """SQLite supports view introspection."""
        return True

    def supports_trigger_introspection(self) -> bool:
        """SQLite supports trigger introspection."""
        return True

    # ========== Runtime Statistics ==========

    def supports_runtime_stats(self) -> bool:
        """SQLite does not support runtime statistics introspection."""
        return False

    def supports_table_stats(self) -> bool:
        """SQLite does not support table statistics introspection."""
        return False

    def supports_index_stats(self) -> bool:
        """SQLite does not support index statistics introspection."""
        return False

    def supports_unused_indexes_detection(self) -> bool:
        """SQLite does not support unused indexes detection."""
        return False

    # ========== Structure Information ==========

    def supports_partition_info(self) -> bool:
        """SQLite does not support partition information (no partitions in SQLite)."""
        return False

    def supports_object_dependencies(self) -> bool:
        """SQLite does not support object dependencies introspection."""
        return False

    def supports_extensions(self) -> bool:
        """SQLite supports extension introspection via pragma_module_list."""
        return True

    # ========== DDL Extraction ==========

    def supports_ddl_extraction(self) -> bool:
        """SQLite supports DDL extraction via sqlite_master."""
        return True

    def supports_ddl_extraction_native(self) -> bool:
        """SQLite does not have native DDL extraction (requires assembly)."""
        return False

    # ========== Fine-grained Capability Detection ==========

    def supports_table_list_pragma(self) -> bool:
        """PRAGMA table_list requires SQLite 3.37.0+.

        Returns:
            True if PRAGMA table_list is available.
            If False, fallback to sqlite_master query.
        """
        return self.version >= (3, 37, 0)

    def supports_table_xinfo_pragma(self) -> bool:
        """PRAGMA table_xinfo (includes hidden columns) requires SQLite 3.26.0+.

        Returns:
            True if PRAGMA table_xinfo is available.
            If False, use PRAGMA table_info instead.
        """
        return self.version >= (3, 26, 0)

    def get_supported_introspection_scopes(self) -> List["IntrospectionScope"]:
        """Get list of supported introspection scopes."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        scopes = [
            IntrospectionScope.DATABASE,
            IntrospectionScope.TABLE,
            IntrospectionScope.COLUMN,
            IntrospectionScope.INDEX,
            IntrospectionScope.VIEW,
            IntrospectionScope.TRIGGER,
        ]
        # Foreign key introspection requires SQLite 3.6.19+
        if self.supports_foreign_key_introspection():
            scopes.append(IntrospectionScope.FOREIGN_KEY)
        return scopes

    # ========== Query Formatting ==========

    def format_database_info_query(self, expr: "DatabaseInfoExpression") -> Tuple[str, tuple]:
        """Format database information query.

        SQLite doesn't have a specific query for database info, so we use
        sqlite_version() and count tables in sqlite_master.

        Args:
            expr: Database info expression with parameters.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        sql = "SELECT sqlite_version() AS version"
        return (sql, ())

    def format_table_list_query(self, expr: "TableListExpression") -> Tuple[str, tuple]:
        """Format table list query.

        For SQLite 3.37.0+, use PRAGMA table_list.
        For older versions, query sqlite_master table.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        schema = params.get("schema") or "main"
        include_views = params.get("include_views", True)
        include_system = params.get("include_system", False)
        table_type = params.get("table_type")

        # Use PRAGMA table_list only when system tables are requested,
        # since PRAGMA cannot filter them out at the SQL level.
        # For user-only queries, sqlite_master provides native filtering.
        if self.supports_table_list_pragma() and include_system:
            sql = f"PRAGMA {schema}.table_list"
            return (sql, ())

        # Fallback to sqlite_master query (also used for include_system=False
        # because sqlite_master supports NOT LIKE filtering natively)
        sql = "SELECT name, type FROM sqlite_master WHERE type IN ('table'"
        if include_views:
            sql += ", 'view'"
        sql += ")"

        # Exclude system tables unless requested
        if not include_system:
            sql += " AND name NOT LIKE 'sqlite_%'"

        # Filter by table type if specified
        if table_type:
            if table_type == "BASE TABLE":
                sql += " AND type = 'table'"
            elif table_type == "VIEW":
                sql += " AND type = 'view'"

        sql += " ORDER BY name"
        return (sql, ())

    def format_table_info_query(self, expr: "TableInfoExpression") -> Tuple[str, tuple]:
        """Format single table information query.

        Query sqlite_master for table details.

        Args:
            expr: Table info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema") or "main"

        sql = f"SELECT name, type, sql FROM {schema}.sqlite_master WHERE name = ?"
        return (sql, (table_name,))

    def format_column_info_query(self, expr: "ColumnInfoExpression") -> Tuple[str, tuple]:
        """Format column information query.

        For SQLite 3.26.0+, can use PRAGMA table_xinfo to include hidden columns.
        Otherwise, use PRAGMA table_info.

        Args:
            expr: Column info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        include_hidden = params.get("include_hidden", False)
        schema = params.get("schema") or "main"

        # Use table_xinfo for hidden columns if supported and requested
        if include_hidden and self.supports_table_xinfo_pragma():
            sql = f"PRAGMA {schema}.table_xinfo({self.format_identifier(table_name)})"
        else:
            sql = f"PRAGMA {schema}.table_info({self.format_identifier(table_name)})"

        return (sql, ())

    def format_index_info_query(self, expr: "IndexInfoExpression") -> Tuple[str, tuple]:
        """Format index information query.

        Use PRAGMA index_list to get indexes for a table.

        Args:
            expr: Index info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema") or "main"

        sql = f"PRAGMA {schema}.index_list({self.format_identifier(table_name)})"
        return (sql, ())

    def format_foreign_key_query(self, expr: "ForeignKeyExpression") -> Tuple[str, tuple]:
        """Format foreign key information query.

        Use PRAGMA foreign_key_list to get foreign keys for a table.

        Args:
            expr: Foreign key expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema") or "main"

        sql = f"PRAGMA {schema}.foreign_key_list({self.format_identifier(table_name)})"
        return (sql, ())

    def format_view_list_query(self, expr: "ViewListExpression") -> Tuple[str, tuple]:  # noqa: F821
        """Format view list query.

        Query sqlite_master for views.

        Args:
            expr: View list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        schema = params.get("schema") or "main"
        include_system = params.get("include_system", False)

        sql = f"SELECT name FROM {schema}.sqlite_master WHERE type = 'view'"

        # Exclude system views unless requested
        if not include_system:
            sql += " AND name NOT LIKE 'sqlite_%'"

        sql += " ORDER BY name"
        return (sql, ())

    def format_view_info_query(self, expr: "ViewInfoExpression") -> Tuple[str, tuple]:  # noqa: F821
        """Format single view information query.

        Query sqlite_master for view details.

        Args:
            expr: View info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        view_name = params.get("view_name", "")
        schema = params.get("schema") or "main"

        sql = f"SELECT name, sql FROM {schema}.sqlite_master WHERE type = 'view' AND name = ?"
        return (sql, (view_name,))

    def format_trigger_list_query(self, expr: "TriggerListExpression") -> Tuple[str, tuple]:  # noqa: F821
        """Format trigger list query.

        Query sqlite_master for triggers, optionally filtered by table.

        Args:
            expr: Trigger list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name")
        schema = params.get("schema") or "main"

        sql = f"SELECT name, tbl_name, sql FROM {schema}.sqlite_master WHERE type = 'trigger'"
        if table_name:
            sql += " AND tbl_name = ?"
            return (sql, (table_name,))

        sql += " ORDER BY name"
        return (sql, ())

    def format_trigger_info_query(self, expr: "TriggerInfoExpression") -> Tuple[str, tuple]:  # noqa: F821
        """Format single trigger information query.

        Query sqlite_master for trigger details.

        Args:
            expr: Trigger info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        trigger_name = params.get("trigger_name", "")
        schema = params.get("schema") or "main"

        sql = f"SELECT name, tbl_name, sql FROM {schema}.sqlite_master WHERE type = 'trigger' AND name = ?"
        return (sql, (trigger_name,))

