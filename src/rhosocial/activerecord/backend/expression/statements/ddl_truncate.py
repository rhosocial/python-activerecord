# src/rhosocial/activerecord/backend/expression/statements/ddl_truncate.py
"""TRUNCATE statement expression."""

from typing import Any, Dict, Optional, TYPE_CHECKING

from ..bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class TruncateExpression(BaseExpression):
    """
    Represents a TRUNCATE TABLE statement supporting SQL standard and database-specific features.

    The TRUNCATE statement provides a fast way to delete all rows from a table.
    It's functionally similar to DELETE without a WHERE clause but is often more efficient
    as it doesn't log individual row deletions. Some databases also support
    additional options like RESTART IDENTITY to reset auto-increment counters.

    Basic syntax:
        TRUNCATE [TABLE] table_name

    Examples:
        # Basic truncate
        truncate_expr = TruncateExpression(dialect, table_name="users")

        # Truncate with restart identity (PostgreSQL)
        truncate_expr = TruncateExpression(
            dialect,
            table_name="users",
            restart_identity=True
        )

        # Truncate with cascade (PostgreSQL)
        truncate_expr = TruncateExpression(
            dialect,
            table_name="orders",
            cascade=True
        )
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        restart_identity: bool = False,  # RESTART IDENTITY option (PostgreSQL)
        cascade: bool = False,  # CASCADE option (PostgreSQL)
        *,  # Force keyword arguments
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize a TRUNCATE expression with the specified parameters.

        Args:
            dialect: The SQL dialect instance that determines query generation rules
            table_name: Name of the table to truncate
            restart_identity: Whether to restart identity counters (PostgreSQL-specific)
            cascade: Whether to truncate dependent tables as well (PostgreSQL-specific)
            dialect_options: Additional database-specific parameters
        """
        super().__init__(dialect)
        self.table_name = table_name
        self.restart_identity = restart_identity  # For PostgreSQL-style RESTART IDENTITY
        self.cascade = cascade  # For PostgreSQL-style CASCADE
        self.dialect_options = dialect_options or {}

    def to_sql(self) -> "SQLQueryAndParams":
        """
        Generate the SQL string and parameters for this TRUNCATE expression.

        This method delegates the SQL generation to the configured dialect, allowing for
        database-specific variations in TRUNCATE syntax.

        Returns:
            A tuple containing:
            - str: The complete TRUNCATE SQL string
            - tuple: The parameter values for prepared statement execution (usually empty)
        """
        return self.dialect.format_truncate_statement(self)
