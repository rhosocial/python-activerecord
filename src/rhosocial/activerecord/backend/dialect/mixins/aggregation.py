# src/rhosocial/activerecord/backend/dialect/mixins/aggregation.py
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.advanced_functions import OrderedSetAggregation


class OrderedSetAggregationMixin:
    """Mixin for ordered-set aggregate function support (WITHIN GROUP (ORDER BY ...))."""

    def supports_ordered_set_aggregation(self) -> bool:
        """Whether ordered-set aggregate functions are supported."""
        return False

    def format_ordered_set_aggregation(self, aggregation: "OrderedSetAggregation") -> Tuple[str, Tuple]:
        """
        Formats an ordered-set aggregate function call.

        Args:
            aggregation: OrderedSetAggregation object to format

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
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

        # Apply type casts if any (before alias)
        if aggregation.cast_types:
            for target_type in aggregation.cast_types:
                sql, all_params_tuple = self.format_cast_expression(sql, target_type, tuple(all_params), None)
                all_params = list(all_params_tuple)

        # Apply alias if any (after type casts)
        if aggregation.alias:
            sql = f"{sql} AS {self.format_identifier(aggregation.alias)}"

        return sql, tuple(all_params)
