# src/rhosocial/activerecord/backend/impl/sqlite/functions/math.py
"""
SQLite math function factories.

Functions: random_func, abs_sql, sign, total
"""

from typing import Union, TYPE_CHECKING
from rhosocial.activerecord.backend.expression import bases
from rhosocial.activerecord.backend.expression.column_types import Column
from rhosocial.activerecord.backend.expression.functions import FunctionCall
from rhosocial.activerecord.backend.expression.value_types import Parameter

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def random_func(dialect: "SQLDialectBase") -> "FunctionCall":
    """
    Creates a RANDOM function call.

    Returns a random integer between -9223372036854775808 and +9223372036854775807.

    Usage:
        - random_func(dialect) -> RANDOM()

    Args:
        dialect: The SQL dialect instance

    Returns:
        A FunctionCall instance representing the RANDOM function
    """
    return FunctionCall(dialect, "RANDOM")


def abs_sql(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "FunctionCall":
    """
    Creates an ABS function call.

    Note: This is named abs_sql to avoid conflict with Python's abs.
    Common functions module uses abs_ for the same purpose.

    Usage:
        - abs_sql(dialect, Column("value")) -> ABS("value")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the ABS function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else Parameter(dialect, expr)
    return FunctionCall(dialect, "ABS", target_expr)


def sign(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "FunctionCall":
    """
    Creates a SIGN function call (SQLite 3.44.0+).

    Returns -1, 0, or 1 depending on whether the argument is negative, zero, or positive.

    Usage:
        - sign(dialect, Column("value")) -> SIGN("value")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the SIGN function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else Parameter(dialect, expr)
    return FunctionCall(dialect, "SIGN", target_expr)


def total(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "FunctionCall":
    """
    Creates a TOTAL aggregate function call.

    SQLite-specific function that returns the sum of all non-NULL values,
    or 0.0 if there are no non-NULL values (unlike SUM which returns NULL).

    Usage:
        - total(dialect, Column("amount")) -> TOTAL("amount")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to total

    Returns:
        A FunctionCall instance representing the TOTAL function
    """
    target_expr = expr if isinstance(expr, bases.BaseExpression) else Column(dialect, expr)
    return FunctionCall(dialect, "TOTAL", target_expr)


__all__ = [
    "random_func",
    "abs_sql",
    "sign",
    "total",
]
