# .../mixins/ordered_set_aggregation_mixin.py
"""Per-feature mixin for OrderedSetAggregationSupport. Members/order/signature mirror the protocol."""

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

class OrderedSetAggregationMixin:
    def supports_ordered_set_aggregation(self) -> bool:
            """Whether ordered-set aggregate functions are supported.

            Defaults to False; dialects that render ``WITHIN GROUP`` override this
            to return True.
            """
            return False

    def format_ordered_set_aggregation(self, expr: "OrderedSetAggregation") -> "Tuple[str, tuple]":
            """Format an ordered-set aggregate function call.

            Args:
                expr: "OrderedSetAggregation" object to format.

            Returns:
                Tuple of (SQL string, parameters tuple) for the formatted expression.

            Raises:
                UnsupportedFeatureError: If the dialect does not support ordered-set
                    aggregate functions.
            """
            from ..exceptions import UnsupportedFeatureError

            if not self.supports_ordered_set_aggregation():
                raise UnsupportedFeatureError(self.name, "ordered-set aggregate functions")

            # Format function arguments
            func_args_sql, func_args_params = [], []
            for arg in expr.args:
                arg_sql, arg_params = arg.to_sql()
                func_args_sql.append(arg_sql)
                func_args_params.extend(arg_params)

            # Get the ORDER BY SQL from the OrderByClause object
            order_by_sql, order_by_params = expr.order_by.to_sql()
            sql = f"{expr.func_name.upper()}({', '.join(func_args_sql)}) WITHIN GROUP ({order_by_sql})"

            all_params = func_args_params + list(order_by_params)

            if expr.alias:
                sql = f"{sql} AS {self.format_identifier(expr.alias)}"

            return sql, tuple(all_params)
