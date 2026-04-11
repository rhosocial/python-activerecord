# src/rhosocial/activerecord/backend/expression/functions/window.py
"""Window function factories."""

from typing import Union, Optional, Any, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import Column, Literal
from ..advanced_functions import WindowFunctionCall

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def row_number(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "WindowFunctionCall":
    """Creates a ROW_NUMBER window function call."""
    return WindowFunctionCall(dialect, "ROW_NUMBER", alias=alias)


def rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "WindowFunctionCall":
    """Creates a RANK window function call."""
    return WindowFunctionCall(dialect, "RANK", alias=alias)


def dense_rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "WindowFunctionCall":
    """Creates a DENSE_RANK window function call."""
    return WindowFunctionCall(dialect, "DENSE_RANK", alias=alias)


def lag(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    offset: int = 1,
    default: Optional[Any] = None,
    alias: Optional[str] = None,
) -> "WindowFunctionCall":
    """
    Creates a LAG window function call.

    Usage rules:
    - To generate LAG(column, offset, default), pass a Column object: lag(dialect, Column(dialect, "column_name"), 1, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to lag. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        offset: Number of rows to look back. Default is 1.
        default: Default value if lag goes beyond the partition. Optional.
        alias: Optional alias for the result.

    Returns:
        A WindowFunctionCall instance representing the LAG function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    args = [target_expr, Literal(dialect, offset)]
    if default is not None:
        args.append(Literal(dialect, default))
    return WindowFunctionCall(dialect, "LAG", args=args, alias=alias)


def lead(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    offset: int = 1,
    default: Optional[Any] = None,
    alias: Optional[str] = None,
) -> "WindowFunctionCall":
    """
    Creates a LEAD window function call.

    Usage rules:
    - To generate LEAD(column, offset, default), pass a Column object:
      lead(dialect, Column(dialect, "column_name"), 1, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to lead. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        offset: Number of rows to look ahead. Default is 1.
        default: Default value if lead goes beyond the partition. Optional.
        alias: Optional alias for the result.

    Returns:
        A WindowFunctionCall instance representing the LEAD function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    args = [target_expr, Literal(dialect, offset)]
    if default is not None:
        args.append(Literal(dialect, default))
    return WindowFunctionCall(dialect, "LEAD", args=args, alias=alias)


def first_value(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], alias: Optional[str] = None
) -> "WindowFunctionCall":
    """
    Creates a FIRST_VALUE window function call.

    Usage rules:
    - To generate FIRST_VALUE(column), pass a Column object: first_value(dialect, Column(dialect, "column_name"))

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get first value of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        alias: Optional alias for the result.

    Returns:
        A WindowFunctionCall instance representing the FIRST_VALUE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return WindowFunctionCall(dialect, "FIRST_VALUE", args=[target_expr], alias=alias)


def last_value(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], alias: Optional[str] = None
) -> "WindowFunctionCall":
    """
    Creates a LAST_VALUE window function call.

    Usage rules:
    - To generate LAST_VALUE(column), pass a Column object: last_value(dialect, Column(dialect, "column_name"))

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get last value of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        alias: Optional alias for the result.

    Returns:
        A WindowFunctionCall instance representing the LAST_VALUE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return WindowFunctionCall(dialect, "LAST_VALUE", args=[target_expr], alias=alias)


def nth_value(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], n: int, alias: Optional[str] = None
) -> "WindowFunctionCall":
    """
    Creates an NTH_VALUE window function call.

    Usage rules:
    - To generate NTH_VALUE(column, n), pass a Column object: nth_value(dialect, Column(dialect, "column_name"), 2)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get nth value of. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        n: Position of the value to retrieve (1-indexed).
        alias: Optional alias for the result.

    Returns:
        A WindowFunctionCall instance representing the NTH_VALUE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    n_expr = Literal(dialect, n)
    return WindowFunctionCall(dialect, "NTH_VALUE", args=[target_expr, n_expr], alias=alias)
