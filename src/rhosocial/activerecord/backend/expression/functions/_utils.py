# src/rhosocial/activerecord/backend/expression/functions/_utils.py
"""Private utility functions for the functions package."""

from typing import Union, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import Column, Literal

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def _convert_to_expression(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], handle_numeric_literals: bool = True
) -> "BaseExpression":
    """
    Helper function to convert an input value to an appropriate BaseExpression.

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert. Can be a BaseExpression, string, or numeric value
        handle_numeric_literals: Whether to treat numeric values as literals (True) or as column names (False)

    Returns:
        A BaseExpression instance (BaseExpression, Literal, or Column)
    """
    if isinstance(expr, BaseExpression):
        return expr
    elif handle_numeric_literals and isinstance(expr, (int, float)):
        return Literal(dialect, expr)
    else:
        return Column(dialect, expr)
