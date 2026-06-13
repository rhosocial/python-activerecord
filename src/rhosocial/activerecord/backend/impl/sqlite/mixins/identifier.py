# src/rhosocial/activerecord/backend/impl/sqlite/mixins/identifier.py
"""
SQLite-specific Identifier implementation.

This module provides the SQLiteIdentifierMixin class.
"""

from typing import Optional, Tuple


class SQLiteIdentifierMixin:
    """SQLite-specific identifier and column formatting."""

    def get_parameter_placeholder(self, _position: int = 0) -> str:
        """SQLite uses '?' for placeholders."""
        return "?"

    def format_identifier(self, identifier: str) -> str:
        """Format identifier using SQLite's double quote quoting mechanism."""
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    def format_column(
        self, name: str, table: Optional[str] = None, alias: Optional[str] = None, schema_name: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format column reference for SQLite.

        SQLite does not support schema-qualified column references in
        the three-segment form (schema.table.column), so schema_name
        is silently ignored.
        """
        if table:
            col_sql = f"{self.format_identifier(table)}.{self.format_identifier(name)}"
        else:
            col_sql = self.format_identifier(name)

        if alias:
            col_sql = f"{col_sql} AS {self.format_identifier(alias)}"

        return col_sql, ()

    def format_wildcard(self, table: Optional[str] = None, schema_name: Optional[str] = None) -> Tuple[str, Tuple]:
        """Format wildcard expression (* or table.* or schema.table.*)."""
        if schema_name and table:
            wildcard_sql = f"{self.format_identifier(schema_name)}.{self.format_identifier(table)}.*"
        elif table:
            wildcard_sql = f"{self.format_identifier(table)}.*"
        else:
            wildcard_sql = "*"
        return wildcard_sql, ()


# =============================================================================
# SQLiteDateTimeMixin — datetime expression formatting
# =============================================================================

