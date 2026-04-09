# src/rhosocial/activerecord/backend/impl/sqlite/functions/math_enhanced.py
"""
SQLite enhanced math function factories.

Additional mathematical functions beyond the basic math module.
Includes: round, pow, power, sqrt, mod, ceil, floor, truncate, max, min, avg

Functions: round_, pow, power, sqrt, mod, ceil, floor, trunc, max_, min_, avg
"""

from typing import Union, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase


def _convert_to_expression(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
) -> "bases.BaseExpression":
    """
    Helper function to convert an input value to an appropriate BaseExpression.

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert

    Returns:
        A BaseExpression instance
    """
    if isinstance(expr, bases.BaseExpression):
        return expr
    elif isinstance(expr, (int, float)):
        return core.Literal(dialect, expr)
    elif isinstance(expr, str):
        # Try to parse as number first
        try:
            return core.Literal(dialect, float(expr) if '.' in expr else int(expr))
        except ValueError:
            # Not a number, treat as column name
            return core.Column(dialect, expr)
    else:
        return core.Column(dialect, expr)


def round_(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
    precision: int = 0,
) -> "core.FunctionCall":
    """
    Creates a ROUND function call.

    Rounds a numeric value to the specified number of decimal places.

    Usage:
        - round_(dialect, Column("price")) -> ROUND("price")
        - round_(dialect, Column("price"), 2) -> ROUND("price", 2)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression to round
        precision: Number of decimal places (default 0)

    Returns:
        A FunctionCall instance representing the ROUND function
    """
    target_expr = _convert_to_expression(dialect, expr)
    precision_expr = core.Literal(dialect, precision)
    return core.FunctionCall(dialect, "ROUND", target_expr, precision_expr)


def pow(
    dialect: "SQLDialectBase",
    base: Union[str, "bases.BaseExpression"],
    exponent: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a POW function call.

    Returns the value of base raised to the power of exponent.

    Usage:
        - pow(dialect, 2, 3) -> POW(2, 3)
        - pow(dialect, Column("x"), 2) -> POW("x", 2)

    Args:
        dialect: The SQL dialect instance
        base: The base value
        exponent: The exponent value

    Returns:
        A FunctionCall instance representing the POW function
    """
    base_expr = _convert_to_expression(dialect, base)
    exp_expr = _convert_to_expression(dialect, exponent)
    return core.FunctionCall(dialect, "POW", base_expr, exp_expr)


def power(
    dialect: "SQLDialectBase",
    base: Union[str, "bases.BaseExpression"],
    exponent: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a POWER function call (alias for POW).

    Returns the value of base raised to the power of exponent.

    Usage:
        - power(dialect, 2, 3) -> POWER(2, 3)
        - power(dialect, Column("x"), 2) -> POWER("x", 2)

    Args:
        dialect: The SQL dialect instance
        base: The base value
        exponent: The exponent value

    Returns:
        A FunctionCall instance representing the POWER function
    """
    base_expr = _convert_to_expression(dialect, base)
    exp_expr = _convert_to_expression(dialect, exponent)
    return core.FunctionCall(dialect, "POWER", base_expr, exp_expr)


def sqrt(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a SQRT function call.

    Returns the square root of the argument.

    Usage:
        - sqrt(dialect, 16) -> SQRT(16)
        - sqrt(dialect, Column("value")) -> SQRT("value")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the SQRT function
    """
    target_expr = _convert_to_expression(dialect, expr)
    return core.FunctionCall(dialect, "SQRT", target_expr)


def mod(
    dialect: "SQLDialectBase",
    dividend: Union[str, "bases.BaseExpression"],
    divisor: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a MOD function call.

    Returns the remainder of dividend divided by divisor.

    Usage:
        - mod(dialect, 10, 3) -> MOD(10, 3)
        - mod(dialect, Column("total"), Column("count")) -> MOD("total", "count")

    Args:
        dialect: The SQL dialect instance
        dividend: The dividend value
        divisor: The divisor value

    Returns:
        A FunctionCall instance representing the MOD function
    """
    dividend_expr = _convert_to_expression(dialect, dividend)
    divisor_expr = _convert_to_expression(dialect, divisor)
    return core.FunctionCall(dialect, "MOD", dividend_expr, divisor_expr)


def ceil(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a CEIL function call (SQLite 3.44.0+).

    Returns the smallest integer greater than or equal to the argument.

    Usage:
        - ceil(dialect, 3.14) -> CEIL(3.14)
        - ceil(dialect, Column("value")) -> CEIL("value")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the CEIL function
    """
    target_expr = _convert_to_expression(dialect, expr)
    return core.FunctionCall(dialect, "CEIL", target_expr)


def floor(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a FLOOR function call (SQLite 3.44.0+).

    Returns the largest integer less than or equal to the argument.

    Usage:
        - floor(dialect, 3.14) -> FLOOR(3.14)
        - floor(dialect, Column("value")) -> FLOOR("value")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the FLOOR function
    """
    target_expr = _convert_to_expression(dialect, expr)
    return core.FunctionCall(dialect, "FLOOR", target_expr)


def trunc(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a TRUNC function call.

    Returns the integer part of a number (truncates toward zero).

    Usage:
        - trunc(dialect, 3.14) -> TRUNC(3.14)
        - trunc(dialect, Column("value")) -> TRUNC("value")

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the TRUNC function
    """
    target_expr = _convert_to_expression(dialect, expr)
    return core.FunctionCall(dialect, "TRUNC", target_expr)


def max_(
    dialect: "SQLDialectBase",
    expr1: Union[str, "bases.BaseExpression"],
    expr2: Union[str, "bases.BaseExpression"],
    *more: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a MAX function call.

    Returns the maximum value among the arguments.

    Usage:
        - max_(dialect, 1, 2) -> MAX(1, 2)
        - max_(dialect, Column("a"), Column("b")) -> MAX("a", "b")

    Args:
        dialect: The SQL dialect instance
        expr1: First expression
        expr2: Second expression
        *more: Additional expressions

    Returns:
        A FunctionCall instance representing the MAX function
    """
    exprs = [_convert_to_expression(dialect, expr1), _convert_to_expression(dialect, expr2)]
    for m in more:
        exprs.append(_convert_to_expression(dialect, m))
    return core.FunctionCall(dialect, "MAX", *exprs)


def min_(
    dialect: "SQLDialectBase",
    expr1: Union[str, "bases.BaseExpression"],
    expr2: Union[str, "bases.BaseExpression"],
    *more: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates a MIN function call.

    Returns the minimum value among the arguments.

    Usage:
        - min_(dialect, 1, 2) -> MIN(1, 2)
        - min_(dialect, Column("a"), Column("b")) -> MIN("a", "b")

    Args:
        dialect: The SQL dialect instance
        expr1: First expression
        expr2: Second expression
        *more: Additional expressions

    Returns:
        A FunctionCall instance representing the MIN function
    """
    exprs = [_convert_to_expression(dialect, expr1), _convert_to_expression(dialect, expr2)]
    for m in more:
        exprs.append(_convert_to_expression(dialect, m))
    return core.FunctionCall(dialect, "MIN", *exprs)


def avg(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """
    Creates an AVG aggregate function call.

    Returns the average value of all non-NULL values in a group.

    Usage:
        - avg(dialect, Column("price")) -> AVG("price")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to average

    Returns:
        A FunctionCall instance representing the AVG function
    """
    target_expr = _convert_to_expression(dialect, expr)
    return core.FunctionCall(dialect, "AVG", target_expr)


__all__ = [
    "round_",
    "pow",
    "power",
    "sqrt",
    "mod",
    "ceil",
    "floor",
    "trunc",
    "max_",
    "min_",
    "avg",
]