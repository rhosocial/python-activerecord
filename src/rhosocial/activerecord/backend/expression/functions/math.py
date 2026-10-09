# src/rhosocial/activerecord/backend/expression/functions/math.py
"""Math function factories."""

from typing import Union, Optional, TYPE_CHECKING, overload

from ..bases import BaseExpression
from ..column_types import IntegerColumn, NumericColumn
from ..core import FunctionCall, Literal

if TYPE_CHECKING:  # pragma: no cover
    from ..core import IntegerValueExpression, NumericValueExpression
    from ...dialect import SQLDialectBase


#: ABS, ROUND, CEIL, FLOOR and TRUNCATE keep a whole number whole, so their
#: result depends on the input: the same call is an integer for an int column
#: and possibly a fraction for a float one. Overloads say so in the type rather
#: than leaving the caller to read an attribute back off the instance.
@overload
def abs_(dialect: "SQLDialectBase", expr: IntegerColumn) -> "IntegerValueExpression": ...


@overload
def abs_(dialect: "SQLDialectBase", expr: NumericColumn) -> "NumericValueExpression": ...


@overload
def abs_(dialect: "SQLDialectBase", expr: "BaseExpression") -> Union[
    "IntegerValueExpression", "NumericValueExpression"
]: ...


def abs_(dialect: "SQLDialectBase", expr: "BaseExpression") -> Union[
    "IntegerValueExpression", "NumericValueExpression"
]:
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
    from ..core import IntegerValueExpression, NumericValueExpression

    target_expr = expr
    call = FunctionCall(dialect, "ABS", target_expr)
    # ABS of a whole number is a whole number, and of a fraction may not be.
    # The column says which before anything runs, so this is a question about
    # the type rather than about an attribute read back from the instance.
    if isinstance(expr, IntegerColumn):
        return IntegerValueExpression(dialect, call)
    return NumericValueExpression(dialect, call)


#: ABS, ROUND, CEIL, FLOOR and TRUNCATE keep a whole number whole, so their
#: result depends on the input: the same call is an integer for an int column
#: and possibly a fraction for a float one. Overloads say so in the type rather
#: than leaving the caller to read an attribute back off the instance.
@overload
def round_(dialect: "SQLDialectBase", expr: IntegerColumn,
            decimals: Optional[int] = ...) -> "IntegerValueExpression": ...


@overload
def round_(dialect: "SQLDialectBase", expr: NumericColumn,
            decimals: Optional[int] = ...) -> "NumericValueExpression": ...


@overload
def round_(dialect: "SQLDialectBase", expr: "BaseExpression",
            decimals: Optional[int] = ...) -> Union[
    "IntegerValueExpression", "NumericValueExpression"
]: ...


def round_(
    dialect: "SQLDialectBase", expr: "BaseExpression", decimals: Optional[int] = None
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
    from ..core import IntegerValueExpression, NumericValueExpression

    target_expr = expr
    args = [target_expr]
    if decimals is not None:
        args.append(Literal(dialect, decimals))
    call = FunctionCall(dialect, "ROUND", *args)
    if isinstance(expr, IntegerColumn):
        return IntegerValueExpression(dialect, call)
    return NumericValueExpression(dialect, call)


#: ABS, ROUND, CEIL, FLOOR and TRUNCATE keep a whole number whole, so their
#: result depends on the input: the same call is an integer for an int column
#: and possibly a fraction for a float one. Overloads say so in the type rather
#: than leaving the caller to read an attribute back off the instance.
@overload
def ceil(dialect: "SQLDialectBase", expr: IntegerColumn) -> "IntegerValueExpression": ...


@overload
def ceil(dialect: "SQLDialectBase", expr: NumericColumn) -> "NumericValueExpression": ...


@overload
def ceil(dialect: "SQLDialectBase", expr: "BaseExpression") -> Union[
    "IntegerValueExpression", "NumericValueExpression"
]: ...


def ceil(dialect: "SQLDialectBase", expr: "BaseExpression") -> "FunctionCall":
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
    target_expr = expr
    from ..core import IntegerValueExpression, NumericValueExpression

    call = FunctionCall(dialect, "CEIL", target_expr)
    if isinstance(expr, IntegerColumn):
        return IntegerValueExpression(dialect, call)
    return NumericValueExpression(dialect, call)


#: ABS, ROUND, CEIL, FLOOR and TRUNCATE keep a whole number whole, so their
#: result depends on the input: the same call is an integer for an int column
#: and possibly a fraction for a float one. Overloads say so in the type rather
#: than leaving the caller to read an attribute back off the instance.
@overload
def floor(dialect: "SQLDialectBase", expr: IntegerColumn) -> "IntegerValueExpression": ...


@overload
def floor(dialect: "SQLDialectBase", expr: NumericColumn) -> "NumericValueExpression": ...


@overload
def floor(dialect: "SQLDialectBase", expr: "BaseExpression") -> Union[
    "IntegerValueExpression", "NumericValueExpression"
]: ...


def floor(dialect: "SQLDialectBase", expr: "BaseExpression") -> "FunctionCall":
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
    target_expr = expr
    from ..core import IntegerValueExpression, NumericValueExpression

    call = FunctionCall(dialect, "FLOOR", target_expr)
    if isinstance(expr, IntegerColumn):
        return IntegerValueExpression(dialect, call)
    return NumericValueExpression(dialect, call)


def sqrt(dialect: "SQLDialectBase", expr: "BaseExpression") -> "NumericValueExpression":
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
    target_expr = expr
    from ..core import NumericValueExpression

    return NumericValueExpression(
        dialect, FunctionCall(dialect, "SQRT", target_expr))


def power(
    dialect: "SQLDialectBase", base: "BaseExpression", exponent: "BaseExpression"
) -> "NumericValueExpression":
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
    base_expr = base
    exp_expr = exponent
    from ..core import NumericValueExpression

    return NumericValueExpression(
        dialect, FunctionCall(dialect, "POWER", base_expr, exp_expr))


def exp(dialect: "SQLDialectBase", expr: "BaseExpression") -> "NumericValueExpression":
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
    target_expr = expr
    from ..core import NumericValueExpression

    return NumericValueExpression(
        dialect, FunctionCall(dialect, "EXP", target_expr))


def log(
    dialect: "SQLDialectBase",
    expr: "BaseExpression",
    base: Optional["BaseExpression"] = None,
) -> "NumericValueExpression":
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

    Contract:
        ``LOG(expr)`` is the **natural** logarithm and ``LOG(expr, base)`` takes
        the base second. Measured 2026-10-09, the backends split on both edges:
        the one-argument ``log`` is base 10 on PostgreSQL and natural on
        MySQL, MariaDB, ClickHouse, SQL Server, BigQuery, Firebird and SQLite,
        and the two-argument order is ``(base, expr)`` on PostgreSQL, MySQL,
        MariaDB, Oracle, Firebird and Snowflake while this order matches SQL
        Server, ClickHouse and BigQuery. Backends override the rendering; the
        meaning is fixed here so the override stays a spelling difference and
        never a semantic one.
    """
    target_expr = expr
    if base is not None:
        base_expr = base
        from ..core import NumericValueExpression

        return NumericValueExpression(
            dialect, FunctionCall(dialect, "LOG", target_expr, base_expr))
    from ..core import NumericValueExpression

    return NumericValueExpression(
        dialect, FunctionCall(dialect, "LOG", target_expr))


def sin(dialect: "SQLDialectBase", expr: "BaseExpression") -> "NumericValueExpression":
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
    target_expr = expr
    from ..core import NumericValueExpression

    return NumericValueExpression(
        dialect, FunctionCall(dialect, "SIN", target_expr))


def cos(dialect: "SQLDialectBase", expr: "BaseExpression") -> "NumericValueExpression":
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
    target_expr = expr
    from ..core import NumericValueExpression

    return NumericValueExpression(
        dialect, FunctionCall(dialect, "COS", target_expr))


def tan(dialect: "SQLDialectBase", expr: "BaseExpression") -> "NumericValueExpression":
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
    target_expr = expr
    from ..core import NumericValueExpression

    return NumericValueExpression(
        dialect, FunctionCall(dialect, "TAN", target_expr))


def mod(
    dialect: "SQLDialectBase",
    dividend: "BaseExpression",
    divisor: "BaseExpression",
) -> "NumericValueExpression":
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
    dividend_expr = dividend
    divisor_expr = divisor
    from ..core import NumericValueExpression

    return NumericValueExpression(
        dialect, FunctionCall(dialect, "MOD", dividend_expr, divisor_expr))


def sign(dialect: "SQLDialectBase", expr: "BaseExpression") -> "NumericValueExpression":
    """
    Creates a SIGN function call.

    The value is -1, 0 or 1, but the **result type follows the backend**
    (measured 2026-10-09): PostgreSQL answers an integer argument with
    ``double precision`` and a numeric one with ``numeric``, so the node is
    tagged numeric rather than integer.

    Usage rules:
    - To generate SIGN(column): sign(dialect, Column(dialect, "column"))
    - To generate SIGN(?): sign(dialect, -42)

    Args:
        dialect: The SQL dialect instance
        expr: The numeric expression

    Returns:
        A FunctionCall instance representing the SIGN function
    """
    target_expr = expr
    from ..core import NumericValueExpression

    return NumericValueExpression(
        dialect, FunctionCall(dialect, "SIGN", target_expr))


#: ABS, ROUND, CEIL, FLOOR and TRUNCATE keep a whole number whole, so their
#: result depends on the input: the same call is an integer for an int column
#: and possibly a fraction for a float one. Overloads say so in the type rather
#: than leaving the caller to read an attribute back off the instance.
@overload
def truncate(dialect: "SQLDialectBase", expr: IntegerColumn,
             precision: Optional[int] = ...) -> "IntegerValueExpression": ...


@overload
def truncate(dialect: "SQLDialectBase", expr: NumericColumn,
             precision: Optional[int] = ...) -> "NumericValueExpression": ...


@overload
def truncate(dialect: "SQLDialectBase", expr: "BaseExpression",
             precision: Optional[int] = ...) -> Union[
    "IntegerValueExpression", "NumericValueExpression"
]: ...


def truncate(
    dialect: "SQLDialectBase", expr: "BaseExpression", precision: Optional[int] = None
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

    Contract:
        Truncation toward zero, distinct from :func:`round` on a negative
        value. The core name stays ``TRUNCATE``; the rendered name is the
        backend's (measured 2026-10-09): ``TRUNC`` on PostgreSQL, Oracle,
        Firebird, BigQuery, SQLite and ClickHouse, ``TRUNCATE`` on MySQL,
        MariaDB and Snowflake, and SQL Server has no scalar truncate at all,
        spelling it ``ROUND(x, n, 1)``. MariaDB's own ``TRUNC`` returns NULL for
        a numeric call -- present from 12.2, absent before -- so a gate there
        has to key on the rendered name rather than the function name.
    """
    from ..core import IntegerValueExpression, NumericValueExpression

    target_expr = expr
    args = [target_expr]
    if precision is not None:
        args.append(Literal(dialect, precision))
    call = FunctionCall(dialect, "TRUNCATE", *args)
    if isinstance(expr, IntegerColumn):
        return IntegerValueExpression(dialect, call)
    return NumericValueExpression(dialect, call)
