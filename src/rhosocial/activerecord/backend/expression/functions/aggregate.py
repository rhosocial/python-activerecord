# src/rhosocial/activerecord/backend/expression/functions/aggregate.py
"""Aggregate function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..aggregates import AggregateFunctionCall
from ..core import Column, Literal, WildcardExpression
from ..operators import RawSQLExpression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


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
    return AggregateFunctionCall(dialect, "COUNT", target_expr, is_distinct=is_distinct, alias=alias)


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
    return AggregateFunctionCall(dialect, "SUM", target_expr, is_distinct=is_distinct, alias=alias)


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
    return AggregateFunctionCall(dialect, "AVG", target_expr, is_distinct=is_distinct, alias=alias)


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
    return AggregateFunctionCall(dialect, "MIN", target_expr, alias=alias)


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
    return AggregateFunctionCall(dialect, "MAX", target_expr, alias=alias)
