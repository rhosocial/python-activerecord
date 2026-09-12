# src/rhosocial/activerecord/backend/dialect/mixins/filter_clause.py
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements.filter_clause import FilterClauseExpression


class FilterClauseMixin:
    """Mixin for aggregate FILTER clause support."""

    def supports_filter_clause(self) -> bool:
        """Whether FILTER (WHERE ...) clause is supported in aggregate functions."""
        return False

    def format_filter_clause(self, expr: "FilterClauseExpression") -> Tuple[str, Tuple]:
        """
        Format a FILTER (WHERE ...) clause.

        Args:
            expr: FilterClauseExpression wrapping the condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        if not self.supports_filter_clause():
            raise UnsupportedFeatureError(self.name, "FILTER clause in aggregate functions")

        condition_sql, condition_params = expr.condition.to_sql()
        return f"FILTER (WHERE {condition_sql})", condition_params
