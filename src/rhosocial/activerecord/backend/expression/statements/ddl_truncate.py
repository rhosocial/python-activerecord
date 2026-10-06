# src/rhosocial/activerecord/backend/expression/statements/ddl_truncate.py
"""TRUNCATE statement expression."""

from typing import Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..objects import Table

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
        table: "Table",
        restart_identity: bool = False,  # RESTART IDENTITY option (PostgreSQL)
        cascade: bool = False,  # CASCADE option (PostgreSQL)
    ):
        """
        Initialize a TRUNCATE expression with the specified parameters.

        Args:
            dialect: The SQL dialect instance that determines query generation rules
            table: The Table being truncated; a schema-qualified table carries
                its own namespace, so no separate schema argument is needed
            restart_identity: Whether to restart identity counters (PostgreSQL-specific)
            cascade: Whether to truncate dependent tables as well (PostgreSQL-specific)

        Raises:
            TypeError: If the table is not a Table
        """
        super().__init__(dialect)
        self.table = table
        self.restart_identity = restart_identity  # For PostgreSQL-style RESTART IDENTITY
        self.cascade = cascade  # For PostgreSQL-style CASCADE

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_truncate_statement"
