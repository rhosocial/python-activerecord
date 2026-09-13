# src/rhosocial/activerecord/backend/dialect/mixins/filter_clause.py
"""Aggregate FILTER clause mixin.

Provides the capability probe and formatter for the SQL ``FILTER (WHERE ...)``
clause used with aggregate functions.
"""
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements.filter_clause import FilterClauseExpression


class FilterClauseMixin:
    """Format aggregate FILTER clauses.

    Subclasses opt in by overriding :meth:`supports_filter_clause`.
    """

    def supports_filter_clause(self) -> bool:
        """Whether FILTER (WHERE ...) in aggregate functions is supported.

        Defaults to False.
        """
        return False

    def format_filter_clause(self, expr: "FilterClauseExpression") -> Tuple[str, Tuple]:
        """Format a FILTER (WHERE ...) clause.

        Args:
            expr: FilterClauseExpression wrapping the condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.

        Raises:
            UnsupportedFeatureError: If the dialect does not support the
                FILTER clause.
        """
        if not self.supports_filter_clause():
            raise UnsupportedFeatureError(self.name, "FILTER clause in aggregate functions")

        condition_sql, condition_params = expr.condition.to_sql()
        return f"FILTER (WHERE {condition_sql})", condition_params
