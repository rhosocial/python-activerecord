# src/rhosocial/activerecord/backend/impl/sqlite/mixins/reindex.py
"""
SQLite-specific Reindex implementation.

This module provides the SQLiteReindexMixin class.
"""

from typing import Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from ..expression.reindex import SQLiteReindexExpression


class SQLiteReindexMixin:
    """Mixin for SQLite REINDEX statement support.

    Implements the SQLiteReindexSupport protocol, providing methods for
    REINDEX capability detection and SQL formatting.
    """

    def supports_reindex(self) -> bool:
        """SQLite supports REINDEX statement."""
        return True

    def supports_reindex_expressions(self) -> bool:
        """SQLite 3.53.0+ supports REINDEX EXPRESSIONS."""
        return self.version >= (3, 53, 0)

    def format_reindex_statement(self, expr: "SQLiteReindexExpression") -> Tuple[str, tuple]:
        """Format REINDEX statement for SQLite.

        SQLite REINDEX syntax:
        - REINDEX                          -- Rebuild all indexes
        - REINDEX table               -- Rebuild all indexes on table
        - REINDEX index               -- Rebuild specific index
        - REINDEX EXPRESSIONS              -- Rebuild all expression indexes (3.53.0+)

        Args:
            expr: SQLiteReindexExpression object

        Returns:
            Tuple of (SQL string, empty parameters tuple)

        Raises:
            UnsupportedFeatureError: If REINDEX EXPRESSIONS is requested on
                SQLite versions below 3.53.0.
        """
        if expr.expressions:
            if not self.supports_reindex_expressions():
                raise UnsupportedFeatureError(
                    self.name, "REINDEX EXPRESSIONS", "REINDEX EXPRESSIONS requires SQLite 3.53.0 or later."
                )
            return "REINDEX EXPRESSIONS", ()

        if expr.index:
            return f"REINDEX {self.format_identifier(expr.index)}", ()

        if expr.table:
            return f"REINDEX {self.format_identifier(expr.table)}", ()

        return "REINDEX", ()

