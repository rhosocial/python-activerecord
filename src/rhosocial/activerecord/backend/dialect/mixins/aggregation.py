# src/rhosocial/activerecord/backend/dialect/mixins/aggregation.py
"""Dialect mixin for ordered-set aggregate functions using ``WITHIN GROUP``."""
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.advanced_functions import OrderedSetAggregation


class OrderedSetAggregationMixin:
    """Mixin adding support for ordered-set aggregate expressions.

    Ordered-set aggregates (e.g. ``PERCENTILE_CONT``, ``MODE``) take their
    ordering via a ``WITHIN GROUP (ORDER BY ...)`` clause instead of ordinary
    function arguments.
    """

    def supports_ordered_set_aggregation(self) -> bool:
        """Whether ordered-set aggregate functions are supported.

        Defaults to False; dialects that render ``WITHIN GROUP`` override this
        to return True.
        """
        return False

    def format_ordered_set_aggregation(self, aggregation: "OrderedSetAggregation") -> Tuple[str, Tuple]:
        """Format an ordered-set aggregate function call.

        Args:
            aggregation: OrderedSetAggregation object to format.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.

        Raises:
            UnsupportedFeatureError: If the dialect does not support ordered-set
                aggregate functions.
        """
        if not self.supports_ordered_set_aggregation():
            raise UnsupportedFeatureError(self.name, "ordered-set aggregate functions")

        # Format function arguments
        func_args_sql, func_args_params = [], []
        for arg in aggregation.args:
            arg_sql, arg_params = arg.to_sql()
            func_args_sql.append(arg_sql)
            func_args_params.extend(arg_params)

        # Get the ORDER BY SQL from the OrderByClause object
        order_by_sql, order_by_params = aggregation.order_by.to_sql()
        sql = f"{aggregation.func_name.upper()}({', '.join(func_args_sql)}) WITHIN GROUP ({order_by_sql})"

        all_params = func_args_params + list(order_by_params)

        if aggregation.alias:
            sql = f"{sql} AS {self.format_identifier(aggregation.alias)}"

        return sql, tuple(all_params)
