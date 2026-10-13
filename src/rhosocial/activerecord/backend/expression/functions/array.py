# src/rhosocial/activerecord/backend/expression/functions/array.py
"""Array function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import (
    Column,
    ArrayValue,
    IntegerValue,
    FunctionCall,
    Literal,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def array_agg(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "FunctionCall":
    """Creates an ARRAY_AGG aggregate function call.

    The result is always an array -- gathering values produces a list of them,
    whatever the gathered type was -- so this wraps in
    :class:`ArrayValue` rather than reading a type off the argument.
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return ArrayValue(
        dialect,
        FunctionCall(dialect, "ARRAY_AGG", target_expr, is_distinct=is_distinct, alias=alias, is_aggregate=True),
    )


def unnest(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "ArrayValue":
    """Creates an UNNEST function call."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return ArrayValue(dialect, FunctionCall(dialect, 'UNNEST', target_expr))


def array_length(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], dimension: int = 1
) -> "IntegerValue":
    """Creates an ARRAY_LENGTH function call."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    dimension_expr = Literal(dialect, dimension)
    return IntegerValue(dialect, FunctionCall(dialect, 'ARRAY_LENGTH', target_expr, dimension_expr))
