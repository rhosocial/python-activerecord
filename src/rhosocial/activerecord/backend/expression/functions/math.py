# src/rhosocial/activerecord/backend/expression/functions/math.py
"""Math function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression
from ..core import FunctionCall, Literal
from ._utils import _convert_to_expression

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def abs_(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates an ABS scalar function call.

    Usage rules:
    - To generate ABS(column), pass a Column object: abs_(dialect, Column(dialect, "column_name"))
    - To generate ABS(?), pass a numeric value: abs_(dialect, -5)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get absolute value of. If a numeric value (int/float)
              is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the ABS function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "ABS", target_expr)


def round_(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], decimals: Optional[int] = None
) -> "FunctionCall":
    """
    Creates a ROUND scalar function call.

    Usage rules:
    - To generate ROUND(column), pass a Column object: round_(dialect, Column(dialect, "column_name"))
    - To generate ROUND(?, decimals), pass a numeric value: round_(dialect, 3.14159, 2)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to round. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        decimals: Optional number of decimal places to round to. If provided, treated as literal value.

    Returns:
        A FunctionCall instance representing the ROUND function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    if decimals is not None:
        decimals_expr = Literal(dialect, decimals)
        return FunctionCall(dialect, "ROUND", target_expr, decimals_expr)
    return FunctionCall(dialect, "ROUND", target_expr)


def ceil(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a CEIL scalar function call.

    Usage rules:
    - To generate CEIL(column), pass a Column object: ceil(dialect, Column(dialect, "column_name"))
    - To generate CEIL(?), pass a numeric value: ceil(dialect, 3.14)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get ceiling of. If a numeric value (int/float) is passed,
              it's treated as a literal value. If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the CEIL function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "CEIL", target_expr)


def floor(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a FLOOR scalar function call.

    Usage rules:
    - To generate FLOOR(column), pass a Column object: floor(dialect, Column(dialect, "column_name"))
    - To generate FLOOR(?), pass a numeric value: floor(dialect, 3.99)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get floor of. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the FLOOR function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "FLOOR", target_expr)


def sqrt(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a SQRT scalar function call.

    Usage rules:
    - To generate SQRT(column), pass a Column object: sqrt(dialect, Column(dialect, "column_name"))
    - To generate SQRT(?), pass a numeric value: sqrt(dialect, 16)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get square root of. If a numeric value (int/float) is passed,
              it's treated as a literal value. If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the SQRT function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "SQRT", target_expr)


def power(
    dialect: "SQLDialectBase", base: Union[str, "BaseExpression"], exponent: Union[str, "BaseExpression"]
) -> "FunctionCall":
    """
    Creates a POWER scalar function call.

    Usage rules:
    - To generate POWER(column, exp), pass Column objects:
      power(dialect, Column(dialect, "base_col"), Column(dialect, "exp_col"))
    - To generate POWER(?, ?), pass numeric values: power(dialect, 2, 3)

    Args:
        dialect: The SQL dialect instance
        base: The base value. If a numeric value (int/float) is passed,
              it's treated as a literal value. If a BaseExpression is passed, it's used as-is.
        exponent: The exponent value. If a numeric value (int/float) is passed,
                  it's treated as a literal value. If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the POWER function
    """
    base_expr = _convert_to_expression(dialect, base, handle_numeric_literals=True)
    exp_expr = _convert_to_expression(dialect, exponent, handle_numeric_literals=True)
    return FunctionCall(dialect, "POWER", base_expr, exp_expr)


def exp(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates an EXP scalar function call.

    Usage rules:
    - To generate EXP(column), pass a Column object: exp(dialect, Column(dialect, "column_name"))
    - To generate EXP(?), pass a numeric value: exp(dialect, 1)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get exponential of. If a numeric value (int/float) is passed,
              it's treated as a literal value. If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the EXP function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "EXP", target_expr)


def log(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    base: Optional[Union[str, "BaseExpression"]] = None,
) -> "FunctionCall":
    """
    Creates a LOG scalar function call.

    Usage rules:
    - To generate LOG(column), pass a Column object: log(dialect, Column(dialect, "column_name"))
    - To generate LOG(?, base), pass numeric values: log(dialect, 100, 10)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get logarithm of. If a numeric value (int/float) is passed,
              it's treated as a literal value. If a BaseExpression is passed, it's used as-is.
        base: Optional base for the logarithm. If provided, treated as a literal value if numeric.

    Returns:
        A FunctionCall instance representing the LOG function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    if base is not None:
        base_expr = _convert_to_expression(dialect, base, handle_numeric_literals=True)
        return FunctionCall(dialect, "LOG", target_expr, base_expr)
    return FunctionCall(dialect, "LOG", target_expr)


def sin(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a SIN scalar function call.

    Usage rules:
    - To generate SIN(column), pass a Column object: sin(dialect, Column(dialect, "column_name"))
    - To generate SIN(?), pass a numeric value: sin(dialect, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get sine of. If a numeric value (int/float) is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the SIN function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "SIN", target_expr)


def cos(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a COS scalar function call.

    Usage rules:
    - To generate COS(column), pass a Column object: cos(dialect, Column(dialect, "column_name"))
    - To generate COS(?), pass a numeric value: cos(dialect, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get cosine of. If a numeric value (int/float) is passed,
              it's treated as a literal value. If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the COS function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "COS", target_expr)


def tan(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a TAN scalar function call.

    Usage rules:
    - To generate TAN(column), pass a Column object: tan(dialect, Column(dialect, "column_name"))
    - To generate TAN(?), pass a numeric value: tan(dialect, 0)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to get tangent of. If a numeric value (int/float) is passed,
              it's treated as a literal value. If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the TAN function
    """
    target_expr = _convert_to_expression(dialect, expr, handle_numeric_literals=True)
    return FunctionCall(dialect, "TAN", target_expr)


def mod(
    dialect: "SQLDialectBase",
    dividend: Union[int, float, "BaseExpression"],
    divisor: Union[int, float, "BaseExpression"],
) -> "FunctionCall":
    """
    Creates a MOD function call (modulo operation).

    SQL:2003 standard modulo function.

    Usage rules:
    - To generate MOD(column, divisor): mod(dialect, Column(dialect, "column"), 10)
    - To generate MOD(?, ?): mod(dialect, 100, 7)

    Args:
        dialect: The SQL dialect instance
        dividend: The number to be divided
        divisor: The number to divide by

    Returns:
        A FunctionCall instance representing the MOD function
    """
    dividend_expr = dividend if isinstance(dividend, BaseExpression) else Literal(dialect, dividend)
    divisor_expr = divisor if isinstance(divisor, BaseExpression) else Literal(dialect, divisor)
    return FunctionCall(dialect, "MOD", dividend_expr, divisor_expr)


def sign(dialect: "SQLDialectBase", expr: Union[int, float, "BaseExpression"]) -> "FunctionCall":
    """
    Creates a SIGN function call.

    SQL:2003 standard function returning -1, 0, or 1.

    Usage rules:
    - To generate SIGN(column): sign(dialect, Column(dialect, "column"))
    - To generate SIGN(?): sign(dialect, -42)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the SIGN function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    return FunctionCall(dialect, "SIGN", target_expr)


def truncate(
    dialect: "SQLDialectBase", expr: Union[int, float, "BaseExpression"], precision: Optional[int] = None
) -> "FunctionCall":
    """
    Creates a TRUNCATE function call.

    SQL:2008 standard function to truncate a number to specified precision.

    Usage rules:
    - To generate TRUNCATE(column): truncate(dialect, Column(dialect, "column"))
    - To generate TRUNCATE(column, 2): truncate(dialect, Column(dialect, "column"), 2)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression to truncate
        precision: Optional number of decimal places (default is 0)

    Returns:
        A FunctionCall instance representing the TRUNCATE function
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Literal(dialect, expr)
    if precision is not None:
        precision_expr = Literal(dialect, precision)
        return FunctionCall(dialect, "TRUNCATE", target_expr, precision_expr)
    return FunctionCall(dialect, "TRUNCATE", target_expr)
