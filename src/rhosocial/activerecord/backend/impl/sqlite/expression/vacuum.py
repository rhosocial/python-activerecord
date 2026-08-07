# src/rhosocial/activerecord/backend/impl/sqlite/expression/vacuum.py
"""
SQLite-specific VACUUM and ANALYZE expressions.

This module provides SQLiteVacuumExpression and SQLiteAnalyzeExpression.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from ....expression.bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase

__all__ = ["SQLiteVacuumExpression", "SQLiteAnalyzeExpression"]


class SQLiteVacuumExpression(BaseExpression):
    """SQLite VACUUM statement expression.

    VACUUM reclaims storage by rebuilding the database file. It is a
    SQLite-specific statement, not part of the SQL standard.

    SQLite VACUUM syntax:
        VACUUM [schema] [INTO 'filename']

    ``VACUUM INTO 'filename'`` copies the vacuumed database to a new file
    and is supported since SQLite 3.27.0.

    Examples:
        # Vacuum the whole database
        vacuum = SQLiteVacuumExpression(dialect)

        # Vacuum a specific attached schema
        vacuum = SQLiteVacuumExpression(dialect, schema="aux")

        # Write the vacuumed database to a new file (SQLite 3.27.0+)
        vacuum = SQLiteVacuumExpression(dialect, into="backup.db")
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: Optional[str] = None,
        into: Optional[str] = None,
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        """Initialize a VACUUM expression.

        Args:
            dialect: The SQL dialect instance.
            schema: Optional schema (attached database) to vacuum.
            into: Optional output filename for ``VACUUM INTO`` (SQLite 3.27.0+).
            dialect_options: Additional database-specific options.

        Raises:
            ValueError: If both schema and into are specified.
        """
        if schema and into:
            raise ValueError("VACUUM cannot combine a schema with the INTO filename")
        super().__init__(dialect)
        self.schema = schema
        self.into = into
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> SQLQueryAndParams:
        """Generate SQL for the VACUUM statement.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        return self._dialect.format_vacuum_statement(self)


class SQLiteAnalyzeExpression(BaseExpression):
    """SQLite ANALYZE statement expression.

    ANALYZE collects statistics used by the query planner to generate
    efficient execution plans. It is a SQLite-specific statement.

    SQLite ANALYZE syntax:
        ANALYZE

    Args:
        dialect: The SQL dialect instance.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> SQLQueryAndParams:
        """Format the ANALYZE statement.

        Returns:
            Tuple of ('ANALYZE', empty parameters tuple).
        """
        return self._dialect.format_analyze_statement(self)