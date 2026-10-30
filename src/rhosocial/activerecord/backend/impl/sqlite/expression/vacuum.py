# src/rhosocial/activerecord/backend/impl/sqlite/expression/vacuum.py
"""
SQLite-specific VACUUM and ANALYZE expressions.

This module provides SQLiteVacuumStatement and SQLiteAnalyzeStatement.
"""

from typing import Optional, TYPE_CHECKING

from ....expression.bases import BaseExpression

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase

__all__ = ["SQLiteVacuumStatement", "SQLiteAnalyzeStatement"]


class SQLiteVacuumStatement(BaseExpression):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression.

        Declared rather than reached through a ``to_sql`` override: the node
        names its formatter and the dialect supplies it. A node that calls the
        dialect itself keeps the lookup inside the node, which is the direction
        this architecture removes.
        """
        return "format_vacuum_statement"
    """SQLite VACUUM statement expression.

    VACUUM reclaims storage by rebuilding the database file. It is a
    SQLite-specific statement, not part of the SQL standard.

    SQLite VACUUM syntax:
        VACUUM [schema] [INTO 'filename']

    ``VACUUM INTO 'filename'`` copies the vacuumed database to a new file
    and is supported since SQLite 3.27.0.

    Examples:
        # Vacuum the whole database
        vacuum = SQLiteVacuumStatement(dialect)

        # Vacuum a specific attached schema
        vacuum = SQLiteVacuumStatement(dialect, schema="aux")

        # Write the vacuumed database to a new file (SQLite 3.27.0+)
        vacuum = SQLiteVacuumStatement(dialect, into="backup.db")
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: Optional[str] = None,
        into: Optional[str] = None,
    ):
        """Initialize a VACUUM expression.

        Args:
            dialect: The SQL dialect instance.
            schema: Optional schema (attached database) to vacuum.
            into: Optional output filename for ``VACUUM INTO`` (SQLite 3.27.0+).

        Raises:
            ValueError: If both schema and into are specified.
        """
        if schema and into:
            raise ValueError("VACUUM cannot combine a schema with the INTO filename")
        super().__init__(dialect)
        self.schema = schema
        self.into = into
class SQLiteAnalyzeStatement(BaseExpression):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression.

        Declared rather than reached through a ``to_sql`` override: the node
        names its formatter and the dialect supplies it. A node that calls the
        dialect itself keeps the lookup inside the node, which is the direction
        this architecture removes.
        """
        return "format_analyze_statement"
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
    ):
        super().__init__(dialect)
