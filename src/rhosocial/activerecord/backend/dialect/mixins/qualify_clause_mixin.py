# .../mixins/qualify_clause_mixin.py
"""Per-feature mixin for QualifyClauseSupport. Members/order/signature mirror the protocol."""

from typing import TYPE_CHECKING, Any, List, Tuple
from ...expression.bases.bases import ToSQLProtocol
from ...expression.query_parts.query_parts import SortDirection

class QualifyClauseMixin:
    def supports_qualify_clause(self) -> bool:
            """Whether QUALIFY clause is supported.

            Defaults to False; dialects that support it override this.
            """
            return False

    def format_qualify_clause(self, expr: "QualifyClause") -> Tuple[str, tuple]:
            """Format a QUALIFY expr.

            Args:
                expr: QualifyClause exposing a ``condition`` expression.

            Returns:
                Tuple of (SQL string, parameters tuple).

            Raises:
                UnsupportedFeatureError: If QUALIFY clauses are unsupported.
            """
            from ..exceptions import UnsupportedFeatureError

            if not self.supports_qualify_clause():
                raise UnsupportedFeatureError(self.name, "QUALIFY expr")

            condition_sql, condition_params = expr.condition.to_sql()
            return f"QUALIFY {condition_sql}", condition_params
