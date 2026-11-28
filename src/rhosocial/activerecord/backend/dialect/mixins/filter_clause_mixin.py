# .../mixins/filter_clause_mixin.py
"""Per-feature mixin for FilterClauseSupport. Members/order/signature mirror the protocol."""

from typing import Any, List, Optional, Tuple, TYPE_CHECKING
from ...expression import bases
from ...expression.objects.qualified_identifier import QualifiedIdentifier
from ...expression.functions.cast_expression import CastExpression
from ...expression.sources.subquery import Subquery
from ...expression.value_types.wildcards import AllColumnsWildcard
from ...expression.value_types.literals import Identifier
from ...expression.bases.mixins import AliasableMixin
from ...expression.operators.operators import (
    ArithmeticOperation,
    BinaryExpression,
    RawSQL,
    SQLOperation,
    ConcatenationOperation,
    UnaryExpression,
)
from .function import FunctionCallMixin

class FilterClauseMixin:
    def supports_filter_clause(self) -> bool:
            """Whether FILTER clause on aggregate functions is supported.

            Defaults to False; dialects that support it override this.
            """
            return False

    def format_filter_clause(self, expr: "FilterClause") -> "Tuple[str, tuple]":
            """Format a FILTER clause.

            Args:
                expr: "FilterClause" containing the condition.

            Returns:
                Tuple of (SQL string, parameters tuple) for the rendered clause.

            Raises:
                UnsupportedFeatureError: If FILTER clauses are unsupported.
            """
            from ..exceptions import UnsupportedFeatureError

            if not self.supports_filter_clause():
                raise UnsupportedFeatureError(self.name, "FILTER clause")

            condition_sql, condition_params = expr.condition.to_sql()
            return f"FILTER (WHERE {condition_sql})", condition_params
