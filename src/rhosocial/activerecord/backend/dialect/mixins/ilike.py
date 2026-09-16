# src/rhosocial/activerecord/backend/dialect/mixins/ilike.py
"""Dialect mixin for ILIKE (case-insensitive LIKE) expression support.

Provides capability detection plus a portable LOWER()-based fallback for
dialects that lack a native ILIKE operator.
"""
from typing import Tuple, TYPE_CHECKING

from ...expression.bases import ToSQLProtocol

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.predicates import ILIKEExpression


class ILIKEMixin:
    """Mixin for ILIKE (case-insensitive LIKE) support.

    Dialects with a native ILIKE operator override
    :meth:`format_ilike_expression`; the default emits a LOWER()-based
    comparison.
    """

    def supports_ilike(self) -> bool:
        """Whether ILIKE operator is supported. Defaults to False."""
        return False

    def format_ilike_expression(self, expr: "ILIKEExpression") -> Tuple[str, Tuple]:
        """Format an ILIKE expression (case-insensitive pattern matching).

        The default implementation uses LOWER() so it works on dialects without
        a native ILIKE operator. Override this method for databases that have
        native ILIKE support (e.g. PostgreSQL).

        Args:
            expr: The :class:`ILIKEExpression` node to render. The node stores
                its own ``column``, ``pattern`` and ``negate`` data; the
                formatter takes no extra arguments so it can be dispatched
                uniformly as ``formatter(expr)``.

        Returns:
            Tuple of (SQL string, parameters tuple) for the expression.

        Raises:
            UnsupportedFeatureError: If the dialect does not support ILIKE.
        """
        if not self.supports_ilike():
            from ..exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(self.name, "ILIKE")

        # Default implementation for databases without native ILIKE
        # Uses LOWER(column) LIKE LOWER(pattern)
        column = expr.column
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
        if expr.negate:
            sql = f"LOWER({col_sql}) NOT LIKE LOWER({ph})"
        else:
            sql = f"LOWER({col_sql}) LIKE LOWER({ph})"

        return sql, (expr.pattern.lower(),)
