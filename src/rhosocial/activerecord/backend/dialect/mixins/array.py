# src/rhosocial/activerecord/backend/dialect/mixins/array.py
"""Dialect mixin for array type construction and subscript access support."""
from typing import Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.advanced_functions import ArrayExpression


class ArrayMixin:
    """Mixin adding support for array types and array expressions.

    Covers the ``ARRAY[...]`` constructor and subscript access, each toggled
    by its own ``supports_*`` capability probe.
    """

    def supports_array_type(self) -> bool:
        """Whether array types are supported.

        Defaults to False.
        """
        return False

    def supports_array_constructor(self) -> bool:
        """Whether ARRAY constructor is supported.

        Defaults to False.
        """
        return False

    def supports_array_access(self) -> bool:
        """Whether array subscript access is supported.

        Defaults to False.
        """
        return False

    def format_array_expression(self, expr: "ArrayExpression") -> Tuple[str, Tuple]:
        """Format an array expression.

        Renders either the ``ARRAY[...]`` constructor or a subscript access
        ``(base[index])`` form depending on ``expr.operation``.

        Args:
            expr: ArrayExpression object to format.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        all_params = ()

        if expr.operation.upper() == "CONSTRUCTOR" and expr.elements is not None:
            element_parts = []
            all_params = []
            for elem in expr.elements:
                elem_sql, elem_params = elem.to_sql()
                element_parts.append(elem_sql)
                all_params.extend(elem_params)
            sql = f"ARRAY[{', '.join(element_parts)}]"
            all_params = tuple(all_params)
        elif expr.operation.upper() == "ACCESS" and expr.base_expr and expr.index_expr:
            base_sql, base_params = expr.base_expr.to_sql()
            index_sql, index_params = expr.index_expr.to_sql()
            sql = f"({base_sql}[{index_sql}])"
            all_params = base_params + index_params
        else:
            # Default case for unsupported operations
            sql = "ARRAY[]"

        if expr.alias:
            sql = f"{sql} AS {self.format_identifier(expr.alias)}"

        return sql, all_params
