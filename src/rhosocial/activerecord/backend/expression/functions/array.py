# src/rhosocial/activerecord/backend/expression/functions/array.py
"""Array function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..aggregates import AggregateFunctionCall
from ..core import Column, FunctionCall, Literal

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def array_agg(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "AggregateFunctionCall":
    """Creates an ARRAY_AGG aggregate function call."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return AggregateFunctionCall(dialect, "ARRAY_AGG", target_expr, is_distinct=is_distinct, alias=alias)


def unnest(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """Creates an UNNEST function call."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return FunctionCall(dialect, "UNNEST", target_expr)


def array_length(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], dimension: int = 1
) -> "FunctionCall":
    """Creates an ARRAY_LENGTH function call."""
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    dimension_expr = Literal(dialect, dimension)
    return FunctionCall(dialect, "ARRAY_LENGTH", target_expr, dimension_expr)
