# src/rhosocial/activerecord/backend/expression_/functions.py
"""
Standalone factory functions for creating SQL expression objects.
"""
from typing import Union, Optional, TYPE_CHECKING

from . import bases
from . import aggregates
from . import core
from . import operators

# if TYPE_CHECKING:
#     from ..dialect import SQLDialectBase


# --- Aggregate Function Factories ---

def count(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"] = "*", is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """Creates a COUNT aggregate function call."""
    if expr == '*':
        target_expr = operators.RawSQLExpression(dialect, '*')
    else:
        target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "COUNT", target_expr, is_distinct=is_distinct, alias=alias)

def sum_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """Creates a SUM aggregate function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "SUM", target_expr, is_distinct=is_distinct, alias=alias)

def avg(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """Creates an AVG aggregate function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "AVG", target_expr, is_distinct=is_distinct, alias=alias)

def min_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """Creates a MIN aggregate function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "MIN", target_expr, alias=alias)

def max_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall":
    """Creates a MAX aggregate function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return aggregates.AggregateFunctionCall(dialect, "MAX", target_expr, alias=alias)


# --- Scalar Function Factories ---

def lower(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a LOWER scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return core.FunctionCall(dialect, "LOWER", target_expr)

def upper(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates an UPPER scalar function call."""
    target_expr = expr if isinstance(expr, bases.BaseExpression) else core.Column(dialect, expr)
    return core.FunctionCall(dialect, "UPPER", target_expr)

def concat(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a CONCAT scalar function call."""
    target_exprs = [e if isinstance(e, bases.BaseExpression) else core.Column(dialect, e) for e in exprs]
    return core.FunctionCall(dialect, "CONCAT", *target_exprs)

def coalesce(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall":
    """Creates a COALESCE scalar function call."""
    target_exprs = [e if isinstance(e, bases.BaseExpression) else core.Column(dialect, e) for e in exprs]
    return core.FunctionCall(dialect, "COALESCE", *target_exprs)
