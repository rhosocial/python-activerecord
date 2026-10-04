# src/rhosocial/activerecord/backend/expression/functions/aggregate.py
"""Aggregate function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..aggregates import AggregateFunctionCall
from ..column_types import IntegerColumn
from ..core import (
    Column,
    WildcardExpression,
    IntegerValueExpression,
    NumericValueExpression,
)
from ..operators import RawSQLExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def _typed(call: AggregateFunctionCall, target: BaseExpression):
    """Wrap *call* in the value class matching *target*, when there is one.

    A reduction answers with the kind of thing it was given: the minimum of an
    integer is an integer, the minimum of a string is a string. The column class
    already says which that is, so it is read off the class. ``COUNT`` is the
    exception and always wraps in :class:`IntegerValueExpression`, because a
    count is a count whatever it counted.

    A target that says nothing -- a ``Literal``, an ``AnyColumn`` -- leaves the
    call untyped. That is the honest answer: the database decides, and the
    caller who needs a specific type says so with ``cast()``.
    """
    if isinstance(target, IntegerColumn):
        return IntegerValueExpression(call._dialect, call)
    return call


def count(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"] = "*",
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "AggregateFunctionCall":
    """
    Creates a COUNT aggregate function call.

    Usage rules:
    - To generate COUNT(*), pass "*" as a string: count(dialect, "*")
    - To generate COUNT(*), pass a WildcardExpression: count(dialect, WildcardExpression(dialect))
    - To generate COUNT(column), pass a Column object: count(dialect, Column(dialect, "column_name"))
    - To generate COUNT(?), pass a literal value: count(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to count. Defaults to "*" to generate COUNT(*).
              If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        is_distinct: Whether to use DISTINCT keyword
        alias: Optional alias for the result

    Returns:
        An AggregateFunctionCall instance representing the COUNT function
    """
    # Check if the passed expression is the string "*"
    if expr == "*" and isinstance(expr, str):
        target_expr = RawSQLExpression(dialect, "*")
    # Check if the passed expression is a WildcardExpression
    elif isinstance(expr, WildcardExpression):
        target_expr = expr
    else:
        target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return IntegerValueExpression(
        dialect,
        AggregateFunctionCall(dialect, "COUNT", target_expr, is_distinct=is_distinct, alias=alias),
    )


def sum_(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "AggregateFunctionCall":
    """
    Creates a SUM aggregate function call.

    Usage rules:
    - To generate SUM(column), pass a Column object: sum_(dialect, Column(dialect, "column_name"))
    - To generate SUM(?), pass a literal value: sum_(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to sum. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        is_distinct: Whether to use DISTINCT keyword
        alias: Optional alias for the result

    Returns:
        An AggregateFunctionCall instance representing the SUM function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return _typed(
        AggregateFunctionCall(
            dialect,
            "SUM",
            target_expr,
            is_distinct=is_distinct,
            alias=alias,
        ),
        target_expr,
    )


def avg(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    is_distinct: bool = False,
    alias: Optional[str] = None,
) -> "AggregateFunctionCall":
    """
    Creates an AVG aggregate function call.

    Usage rules:
    - To generate AVG(column), pass a Column object: avg(dialect, Column(dialect, "column_name"))
    - To generate AVG(?), pass a literal value: avg(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to average. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        is_distinct: Whether to use DISTINCT keyword
        alias: Optional alias for the result

    Returns:
        An AggregateFunctionCall instance representing the AVG function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return NumericValueExpression(
        dialect,
        AggregateFunctionCall(dialect, "AVG", target_expr, is_distinct=is_distinct, alias=alias),
    )


def min_(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], alias: Optional[str] = None
) -> "AggregateFunctionCall":
    """
    Creates a MIN aggregate function call.

    Usage rules:
    - To generate MIN(column), pass a Column object: min_(dialect, Column(dialect, "column_name"))
    - To generate MIN(?), pass a literal value: min_(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to find minimum of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        alias: Optional alias for the result

    Returns:
        An AggregateFunctionCall instance representing the MIN function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return _typed(AggregateFunctionCall(dialect, "MIN", target_expr, alias=alias), target_expr)


def max_(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], alias: Optional[str] = None
) -> "AggregateFunctionCall":
    """
    Creates a MAX aggregate function call.

    Usage rules:
    - To generate MAX(column), pass a Column object: max_(dialect, Column(dialect, "column_name"))
    - To generate MAX(?), pass a literal value: max_(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to find maximum of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        alias: Optional alias for the result

    Returns:
        An AggregateFunctionCall instance representing the MAX function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return _typed(AggregateFunctionCall(dialect, "MAX", target_expr, alias=alias), target_expr)
