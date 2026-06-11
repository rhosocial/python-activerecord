# src/rhosocial/activerecord/backend/dialect/mixins/filter_clause.py
from typing import Tuple

from ..exceptions import UnsupportedFeatureError


class FilterClauseMixin:
    """Mixin for aggregate FILTER clause support."""

    def supports_filter_clause(self) -> bool:
        """Whether FILTER (WHERE ...) clause is supported in aggregate functions."""
        return False

    def format_filter_clause(self, condition_sql: str, condition_params: tuple) -> Tuple[str, Tuple]:
        """
        Format a FILTER (WHERE ...) clause.

        Args:
            condition_sql: SQL string for the WHERE condition.
            condition_params: Parameters for the WHERE condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        if not self.supports_filter_clause():
            raise UnsupportedFeatureError(self.name, "FILTER clause in aggregate functions")

        return f"FILTER (WHERE {condition_sql})", condition_params
