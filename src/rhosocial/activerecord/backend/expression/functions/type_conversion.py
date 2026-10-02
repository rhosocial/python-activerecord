# src/rhosocial/activerecord/backend/expression/functions/type_conversion.py
"""Type conversion function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression, SQLValueExpression
from ..value_types import DATETIME, NUMERIC, STRING, wrap_as
from ..core import Column, FunctionCall, Literal

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..types._base import DataType


def cast(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    target_type: "DataType",
) -> "SQLValueExpression":
    """
    Creates a type cast around an expression.

    ``CAST(expr AS type)`` is a proper AST node (``CastExpression``) that
    wraps the given expression; the cast() method on the expression builds
    exactly this node.

    Usage rules:
    - To generate CAST(column AS type), pass a Column object and a type:
      cast(dialect, Column(dialect, "column_name"), IntegerType(dialect))
    - To generate CAST("col" AS type), pass the column name as a string.

    Args:
        dialect: The SQL dialect instance
        expr: The expression to cast. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        target_type: The type to cast to, as a DataType instance. A string is
            refused: the type position of a cast cannot take a bound
            parameter, so a string there is SQL code rather than SQL data.

    Returns:
        A new CastExpression node wrapping the given expression

    Raises:
        TypeError: If target_type is not a DataType.
    """
    from ..core import CastExpression, Column

    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    return CastExpression(dialect, target_expr, target_type)


def to_char(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "FunctionCall":
    """
    Creates a TO_CHAR function call.

    Usage rules:
    - To generate TO_CHAR(column), pass a Column object:
      to_char(dialect, Column(dialect, "date_col"))
    - To generate TO_CHAR(column, format), pass a format string:
      to_char(dialect, Column(dialect, "date_col"), "YYYY-MM-DD")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to character. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        format: Optional format string for conversion.

    Returns:
        A FunctionCall instance representing the TO_CHAR function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    if format is not None:
        format_expr = Literal(dialect, format)
        return wrap_as(dialect, FunctionCall(dialect, "TO_CHAR", target_expr, format_expr), STRING)
    return wrap_as(dialect, FunctionCall(dialect, "TO_CHAR", target_expr), STRING)


def to_number(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "FunctionCall":
    """
    Creates a TO_NUMBER function call.

    Usage rules:
    - To generate TO_NUMBER(column), pass a Column object:
      to_number(dialect, Column(dialect, "char_col"))
    - To generate TO_NUMBER(column, format), pass a format string:
      to_number(dialect, Column(dialect, "char_col"), "9999")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to number. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        format: Optional format string for conversion.

    Returns:
        A FunctionCall instance representing the TO_NUMBER function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    if format is not None:
        format_expr = Literal(dialect, format)
        return wrap_as(dialect, FunctionCall(dialect, "TO_NUMBER", target_expr, format_expr), NUMERIC)
    return wrap_as(dialect, FunctionCall(dialect, "TO_NUMBER", target_expr), NUMERIC)


def to_date(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "FunctionCall":
    """
    Creates a TO_DATE function call.

    Usage rules:
    - To generate TO_DATE(column), pass a Column object:
      to_date(dialect, Column(dialect, "char_col"))
    - To generate TO_DATE(column, format), pass a format string:
      to_date(dialect, Column(dialect, "char_col"), "YYYY-MM-DD")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to date. If a string is passed, it's treated as a column name.
              If a BaseExpression is passed, it's used as-is.
        format: Optional format string for conversion.

    Returns:
        A FunctionCall instance representing the TO_DATE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    if format is not None:
        format_expr = Literal(dialect, format)
        return wrap_as(dialect, FunctionCall(dialect, "TO_DATE", target_expr, format_expr), DATETIME)
    return wrap_as(dialect, FunctionCall(dialect, "TO_DATE", target_expr), DATETIME)
