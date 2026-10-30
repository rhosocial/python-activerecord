# src/rhosocial/activerecord/backend/expression/functions/math.py
"""Math function factories."""

import decimal
from abc import abstractmethod
from typing import Union, Optional, TYPE_CHECKING, overload

from ..advanced_functions import DeclaredValueType
from ..bases import BaseExpression
from ..column_types import IntegerColumn, NumericColumn
from ..core import FunctionCall, Literal

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


#: ABS, ROUND, CEIL, FLOOR and TRUNCATE keep a whole number whole, so their
#: result depends on the input: the same call is an integer for an int column
#: and possibly a fraction for a float one. Overloads say so in the type rather
#: than leaving the caller to read an attribute back off the instance.
from ..value_types import (
    NumericValue,
)

class _MathOperands:
    """Declared-operand normalisation for the math nodes below.

    A numeric operand is normalised here rather than only in the factory, so
    constructing a node directly is safe too and a wrong operand fails at
    construction instead of surfacing as an ``AttributeError`` from the
    formatter.

    An ``int`` stays an integer and everything else becomes an exact decimal:
    collapsing both to a float would turn ``MOD(x, 3)`` into a floating-point
    modulus.
    """

    @staticmethod
    def _number(dialect: "SQLDialectBase", value):
        from .. import values

        if value is None:
            return None
        if isinstance(value, BaseExpression):
            return value
        if isinstance(value, int):
            return Literal(dialect, value)
        return Literal(dialect, decimal.Decimal(str(value)))


class _MathFunction(
    _MathOperands,
    DeclaredValueType,
    NumericValue,
):
    """Shared base for the math nodes that always answer with a number.

    :attr:`arguments` is the operand list as the formatter writes it, so a
    backend that spells a function with its operands in another order reorders
    the list rather than the node's fields.
    """

    #: The function name this node writes. Overridden per subclass.
    function_name: str = ""

    def __init__(self, dialect: "SQLDialectBase", *arguments):
        # BaseExpression directly, not super(): the value types below are mixin
        # carriers ending at SQLValue, and going through super() would chain into
        # whichever of them happens to declare __init__.
        BaseExpression.__init__(self, dialect)
        self.arguments = [self._number(dialect, a) for a in arguments]

    @property
    @abstractmethod
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression.

        Abstract so the shared bases are not mistaken for nodes: each subclass
        names the formatter for its own kind, and a base that guessed from its
        own name would name a formatter that does not exist.
        """
        raise NotImplementedError


class _FamilyPreservingMathFunction(_MathFunction):
    """Shared base for the five that keep a whole number whole.

    ``ABS``, ``ROUND``, ``CEIL``, ``FLOOR`` and ``TRUNCATE`` of an integer are
    integers, and of a fraction may not be, so the class is chosen by the
    **column** before anything runs. The integral class below subclasses this
    one rather than repeating it, so ``isinstance(node, AbsoluteFunction)``
    holds either way.
    """

    @classmethod
    def for_operand(cls, dialect: "SQLDialectBase", operand_class, *arguments):
        """The integral or the numeric class, per the operand's declared family."""
        return (
            cls.integral(dialect, *arguments)
            if issubclass(operand_class, IntegerColumn)
            else cls(dialect, *arguments)
        )


class AbsoluteFunction(_FamilyPreservingMathFunction):
    """``ABS(operand)`` -- the operand's magnitude.

    Of a whole number a whole number, and of a fraction a fraction, so the
    result type follows the operand rather than the function.
    """

    function_name = "ABS"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_absolute_function"

    @classmethod
    def integral(cls, dialect, *arguments):
        """The whole-number variant, for an integer operand."""
        return AbsoluteIntegerFunction(dialect, *arguments)


class AbsoluteIntegerFunction(
    AbsoluteFunction,
    DeclaredValueType,
    NumericValue,
):
    """``ABS`` of an integer -- still an integer."""


class RoundFunction(_FamilyPreservingMathFunction):
    """``ROUND(operand[, scale])`` -- rounded to a scale.

    Keeps a whole number whole, which is why ``ROUND(2.0)`` is 2 and not 2.0 on
    a backend that says so.
    """

    function_name = "ROUND"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_round_function"

    @classmethod
    def integral(cls, dialect, *arguments):
        """The whole-number variant, for an integer operand."""
        return RoundIntegerFunction(dialect, *arguments)


class RoundIntegerFunction(
    RoundFunction,
    DeclaredValueType,
    NumericValue,
):
    """``ROUND`` of an integer -- still an integer."""


class CeilFunction(_FamilyPreservingMathFunction):
    """``CEIL(operand)`` -- the smallest whole number not below it."""

    function_name = "CEIL"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_ceil_function"

    @classmethod
    def integral(cls, dialect, *arguments):
        """The whole-number variant, for an integer operand."""
        return CeilIntegerFunction(dialect, *arguments)


class CeilIntegerFunction(
    CeilFunction,
    DeclaredValueType,
    NumericValue,
):
    """``CEIL`` of an integer -- the integer itself, unchanged."""


class FloorFunction(_FamilyPreservingMathFunction):
    """``FLOOR(operand)`` -- the largest whole number not above it."""

    function_name = "FLOOR"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_floor_function"

    @classmethod
    def integral(cls, dialect, *arguments):
        """The whole-number variant, for an integer operand."""
        return FloorIntegerFunction(dialect, *arguments)


class FloorIntegerFunction(
    FloorFunction,
    DeclaredValueType,
    NumericValue,
):
    """``FLOOR`` of an integer -- the integer itself, unchanged."""


class TruncateFunction(_FamilyPreservingMathFunction):
    """``TRUNCATE(operand[, precision])`` -- cut off, not rounded.

    Distinct from :class:`RoundFunction` because they disagree on a negative
    half: ``-1.5`` rounds to ``-2`` and truncates to ``-1``. Backends answer that
    one way or the other and a dialect that cannot say which overrides the
    formatter rather than pretending they agree.
    """

    function_name = "TRUNCATE"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_truncate_function"

    @classmethod
    def integral(cls, dialect, *arguments):
        """The whole-number variant, for an integer operand."""
        return TruncateIntegerFunction(dialect, *arguments)


class TruncateIntegerFunction(
    TruncateFunction,
    DeclaredValueType,
    NumericValue,
):
    """``TRUNCATE`` of an integer -- still an integer."""


class SquareRootFunction(_MathFunction):
    """``SQRT(operand)`` -- the square root.

    Numeric even for a perfect square, because a caller who asked for a root has
    not said the answer is whole, and widening is the safe direction.
    """

    function_name = "SQRT"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_square_root_function"


class PowerFunction(_MathFunction):
    """``POWER(base, exponent)`` -- the base raised to the exponent.

    Compound interest makes this meaningful for a monetary amount, so it belongs
    with the algebraic operations rather than the transcendental ones.
    """

    function_name = "POWER"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_power_function"


class ExponentialFunction(_MathFunction):
    """``EXP(operand)`` -- e raised to the operand."""

    function_name = "EXP"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_exponential_function"


class LogarithmFunction(_MathFunction):
    """``LOG(operand[, base])`` -- the exponent that gives the operand.

    :attr:`arguments` holds the base last when one is given, which is the order
    the function reads them in; a backend that wants the base first reorders the
    list in its formatter.
    """

    function_name = "LOG"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_logarithm_function"


class SineFunction(_MathFunction):
    """``SIN(operand)`` -- the sine, in radians."""

    function_name = "SIN"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_sine_function"


class CosineFunction(_MathFunction):
    """``COS(operand)`` -- the cosine, in radians."""

    function_name = "COS"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_cosine_function"


class TangentFunction(_MathFunction):
    """``TAN(operand)`` -- the tangent, in radians."""

    function_name = "TAN"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_tangent_function"


class ModuloFunction(_MathFunction):
    """``MOD(dividend, divisor)`` -- the remainder.

    An integer modulus when both operands are integers, which is why the
    operands keep their own families rather than being widened here.
    """

    function_name = "MOD"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_modulo_function"


class SignFunction(_MathFunction):
    """``SIGN(operand)`` -- -1, 0 or 1 by which way the operand points.

    Always a whole number whatever it is handed, which is the one function here
    whose result does not follow its operand's family.
    """

    function_name = "SIGN"

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_sign_function"


@overload
def abs_(dialect: "SQLDialectBase", expr: IntegerColumn) -> "AbsoluteIntegerFunction": ...


@overload
def abs_(dialect: "SQLDialectBase", expr: NumericColumn) -> "AbsoluteFunction": ...


@overload
def abs_(dialect: "SQLDialectBase", expr: "BaseExpression") -> Union[
    "AbsoluteIntegerFunction", "AbsoluteFunction"
]: ...


def abs_(dialect: "SQLDialectBase", expr: "BaseExpression") -> Union[
    "AbsoluteIntegerFunction", "AbsoluteFunction"
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

    target_expr = expr
    # ABS of a whole number is a whole number, and of a fraction may not be.
    # The column says which before anything runs, so this is a question about
    # the type rather than about an attribute read back from the instance.
    return AbsoluteFunction.for_operand(dialect, type(expr), target_expr)


#: ABS, ROUND, CEIL, FLOOR and TRUNCATE keep a whole number whole, so their
#: result depends on the input: the same call is an integer for an int column
#: and possibly a fraction for a float one. Overloads say so in the type rather
#: than leaving the caller to read an attribute back off the instance.
@overload
def round_(dialect: "SQLDialectBase", expr: IntegerColumn,
            decimals: Optional[int] = ...) -> "RoundIntegerFunction": ...


@overload
def round_(dialect: "SQLDialectBase", expr: NumericColumn,
            decimals: Optional[int] = ...) -> "RoundFunction": ...


@overload
def round_(dialect: "SQLDialectBase", expr: "BaseExpression",
            decimals: Optional[int] = ...) -> Union[
    "RoundIntegerFunction", "RoundFunction"
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

    target_expr = expr
    args = [target_expr]
    if decimals is not None:
        args.append(decimals if isinstance(decimals, BaseExpression) else Literal(dialect, decimals))
    return RoundFunction.for_operand(dialect, type(expr), *args)


#: ABS, ROUND, CEIL, FLOOR and TRUNCATE keep a whole number whole, so their
#: result depends on the input: the same call is an integer for an int column
#: and possibly a fraction for a float one. Overloads say so in the type rather
#: than leaving the caller to read an attribute back off the instance.
@overload
def ceil(dialect: "SQLDialectBase", expr: IntegerColumn) -> "CeilIntegerFunction": ...


@overload
def ceil(dialect: "SQLDialectBase", expr: NumericColumn) -> "CeilFunction": ...


@overload
def ceil(dialect: "SQLDialectBase", expr: "BaseExpression") -> Union[
    "CeilIntegerFunction", "CeilFunction"
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

    return CeilFunction.for_operand(dialect, type(expr), target_expr)


#: ABS, ROUND, CEIL, FLOOR and TRUNCATE keep a whole number whole, so their
#: result depends on the input: the same call is an integer for an int column
#: and possibly a fraction for a float one. Overloads say so in the type rather
#: than leaving the caller to read an attribute back off the instance.
@overload
def floor(dialect: "SQLDialectBase", expr: IntegerColumn) -> "FloorIntegerFunction": ...


@overload
def floor(dialect: "SQLDialectBase", expr: NumericColumn) -> "FloorFunction": ...


@overload
def floor(dialect: "SQLDialectBase", expr: "BaseExpression") -> Union[
    "FloorIntegerFunction", "FloorFunction"
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

    return FloorFunction.for_operand(dialect, type(expr), target_expr)


def sqrt(dialect: "SQLDialectBase", expr: "BaseExpression") -> "FloorFunction":
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
    return SquareRootFunction(dialect, target_expr)


def power(
    dialect: "SQLDialectBase", base: "BaseExpression", exponent: "BaseExpression"
) -> "FloorFunction":
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
    return PowerFunction(dialect, base_expr, exp_expr)


def exp(dialect: "SQLDialectBase", expr: "BaseExpression") -> "FloorFunction":
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
    return ExponentialFunction(dialect, target_expr)


def log(
    dialect: "SQLDialectBase",
    expr: "BaseExpression",
    base: Optional["BaseExpression"] = None,
) -> "FloorFunction":
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
        return LogarithmFunction(dialect, target_expr, base)
    return LogarithmFunction(dialect, target_expr)


def sin(dialect: "SQLDialectBase", expr: "BaseExpression") -> "FloorFunction":
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
    return SineFunction(dialect, target_expr)


def cos(dialect: "SQLDialectBase", expr: "BaseExpression") -> "FloorFunction":
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
    return CosineFunction(dialect, target_expr)


def tan(dialect: "SQLDialectBase", expr: "BaseExpression") -> "FloorFunction":
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
    return TangentFunction(dialect, target_expr)


def mod(
    dialect: "SQLDialectBase",
    dividend: "BaseExpression",
    divisor: "BaseExpression",
) -> "FloorFunction":
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
    return ModuloFunction(dialect, dividend_expr, divisor_expr)


def sign(dialect: "SQLDialectBase", expr: "BaseExpression") -> "FloorFunction":
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
    return SignFunction(dialect, target_expr)


#: ABS, ROUND, CEIL, FLOOR and TRUNCATE keep a whole number whole, so their
#: result depends on the input: the same call is an integer for an int column
#: and possibly a fraction for a float one. Overloads say so in the type rather
#: than leaving the caller to read an attribute back off the instance.
@overload
def truncate(dialect: "SQLDialectBase", expr: IntegerColumn,
             precision: Optional[int] = ...) -> "TruncateIntegerFunction": ...


@overload
def truncate(dialect: "SQLDialectBase", expr: NumericColumn,
             precision: Optional[int] = ...) -> "TruncateFunction": ...


@overload
def truncate(dialect: "SQLDialectBase", expr: "BaseExpression",
             precision: Optional[int] = ...) -> Union[
    "TruncateIntegerFunction", "TruncateFunction"
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

    target_expr = expr
    args = [target_expr]
    if precision is not None:
        args.append(precision if isinstance(precision, BaseExpression) else Literal(dialect, precision))
    return TruncateFunction.for_operand(dialect, type(expr), *args)
