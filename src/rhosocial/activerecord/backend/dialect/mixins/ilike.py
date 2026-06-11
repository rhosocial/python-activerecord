# src/rhosocial/activerecord/backend/dialect/mixins/ilike.py
from typing import Any, Tuple

from ..exceptions import UnsupportedFeatureError
from ...expression.bases import ToSQLProtocol


class ILIKEMixin:
    """Mixin for ILIKE (case-insensitive LIKE) support."""

    def supports_ilike(self) -> bool:
        """Whether ILIKE operator is supported."""
        return False

    def format_ilike_expression(self, column: Any, pattern: str, negate: bool = False) -> Tuple[str, Tuple]:
        """
        Format ILIKE expression (case-insensitive pattern matching).

        Default implementation uses LOWER() function for databases without native ILIKE.
        Override this method for databases with native ILIKE support (e.g., PostgreSQL).
        """
        if not self.supports_ilike():
            from ..exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(self.name, "ILIKE")

        # Default implementation for databases without native ILIKE
        # Uses LOWER(column) LIKE LOWER(pattern)
        if isinstance(column, str):
            col_sql = self.format_identifier(column)
        elif isinstance(column, ToSQLProtocol):
            # Expression object
            col_sql, _ = column.to_sql()
        else:
            # Fallback to string representation
            col_sql = str(column)

        # Use LOWER() for case-insensitive comparison
        ph = self.get_parameter_placeholder()
        if negate:
            sql = f"LOWER({col_sql}) NOT LIKE LOWER({ph})"
        else:
            sql = f"LOWER({col_sql}) LIKE LOWER({ph})"

        return sql, (pattern.lower(),)
