# src/rhosocial/activerecord/backend/expression/functions/type_conversion.py
"""Type conversion function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..bases import BaseExpression, SQLValueExpression
from ..core import (
    Column,
    TimestampValueExpression,
    NumericValueExpression,
    StringValueExpression,
    FunctionCall,
    Literal,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..types._base import DataType


#: Value class -> the class standing for both a CAST and that value class.
#: Populated on first use by :func:`_cast_class_for`.
_CAST_VALUE_CLASSES = {}


def _cast_class_for(value_class):
    """The class standing for both a CAST and *value_class*.

    Built once per value class and kept, so ``type(x)`` does not differ between
    two casts that produce the same thing.

    ``CastExpression`` comes first: it supplies the node's own state and
    ``format_method``. ``DeclaredValueType`` supplies the rendering, because the
    value class's own ``to_sql`` is a wrapper delegating to a node this does not
    hold.
    """
    from ..advanced_functions import DeclaredValueType
    from ..core import CastExpression

    try:
        return _CAST_VALUE_CLASSES[value_class]
    except KeyError:
        combined = type(
            f"Cast{value_class.__name__}",
            (CastExpression, DeclaredValueType, value_class),
            {
                "__doc__": (
                    f"A CAST to a type this value class represents, so it is "
                    f"a {value_class.__name__}."
                )
            },
        )
        _CAST_VALUE_CLASSES[value_class] = combined
        return combined


def _value_class_for(target_type):
    """The value class *target_type* casts to, or ``None`` if it has none.

    A cast takes its answer from the target type, which is the only place it can
    come from: ``CAST(x AS t)`` is a ``t`` whatever ``x`` held. There is no
    lookup from a type *name* any more -- the name carries no type of its own to
    be right about, and a ``DataType`` instance is what identifies the type.

    Resolution walks the MRO, so ``IntegerType`` and the three narrower integer
    widths resolve as whole numbers through the class they share, and a backend's
    own type resolves through whichever core type it derives from.

    ``None`` is a real answer. A user-defined type has no value class to offer:
    promising JSON navigation on a type nobody here has heard of would be worse
    than saying nothing, so the cast comes back untyped and the caller says what
    they meant with ``as_*``.
    """
    global _TYPE_VALUE_CLASSES
    if _TYPE_VALUE_CLASSES is None:
        _TYPE_VALUE_CLASSES = _type_value_classes()

    for klass in type(target_type).__mro__:
        value_class = _TYPE_VALUE_CLASSES.get(klass)
        if value_class is not None:
            return value_class
    return None


def _type_value_classes():
    """The ``DataType`` class -> value class table, built on first use.

    Deferred because :mod:`..types` and :mod:`..core` both import from this
    package's expression module, so neither can be imported at module scope here.
    """
    from .. import core
    from ..types import (
        ArrayType,
        BigIntType,
        BinaryType,
        BlobType,
        BooleanType,
        CharType,
        CustomType,
        DateTimeType,
        DateType,
        DecimalType,
        DoubleType,
        EnumType,
        FloatType,
        IntegerType,
        IntervalType,
        JsonBType,
        JsonType,
        RealType,
        SmallIntType,
        TextType,
        TimeType,
        TimeTzType,
        TimestampType,
        TimestampTzType,
        TinyIntType,
        UUIDType,
        VarBinaryType,
        VarCharType,
        XmlType,
    )

    return {
        # Whole numbers, whatever the width.
        IntegerType: core.IntegerValueExpression,
        TinyIntType: core.IntegerValueExpression,
        SmallIntType: core.IntegerValueExpression,
        BigIntType: core.IntegerValueExpression,
        # Fractional numbers.
        DecimalType: core.NumericValueExpression,
        FloatType: core.NumericValueExpression,
        RealType: core.NumericValueExpression,
        DoubleType: core.NumericValueExpression,
        # Text. An enum is text: its values are labels.
        CharType: core.StringValueExpression,
        VarCharType: core.StringValueExpression,
        TextType: core.StringValueExpression,
        EnumType: core.StringValueExpression,
        # Bytes.
        BinaryType: core.BinaryValueExpression,
        VarBinaryType: core.BinaryValueExpression,
        BlobType: core.BinaryValueExpression,
        BooleanType: core.BooleanValueExpression,
        # Documents.
        JsonType: core.JSONValueExpression,
        JsonBType: core.JSONValueExpression,
        # An XML document: a value with its own surface, not a string.
        XmlType: core.XMLValueExpression,
        # Sequences.
        ArrayType: core.ArrayValueExpression,
        # A UUID is a UUID.
        UUIDType: core.UUIDValueExpression,
        # Temporal. Each gets its own class because they are four types; a
        # timestamp is not a date, and CURRENT_DATE() is not
        # CURRENT_TIMESTAMP().
        DateType: core.DateValueExpression,
        DateTimeType: core.TimestampValueExpression,
        TimestampType: core.TimestampValueExpression,
        TimestampTzType: core.TimestampValueExpression,
        TimeType: core.TimeValueExpression,
        TimeTzType: core.TimeValueExpression,
        IntervalType: core.IntervalValueExpression,
    }


_TYPE_VALUE_CLASSES = None


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
        A new CastExpression node wrapping the given expression, typed by the
        target type -- see below.

    Raises:
        TypeError: If target_type is not a DataType.
    """
    from ..advanced_functions import DeclaredValueType
    from ..core import CastExpression, Column

    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    node = CastExpression(dialect, target_expr, target_type)
    value_class = _value_class_for(target_type)
    if value_class is None:
        return node
    # A cast is the one place a result's type is stated by something other than
    # the input: CAST(x AS t) is a t by definition, whatever x was. So the node
    # is built as an instance of that class -- it is not a wrapper holding one,
    # hence DeclaredValueType's rendering rather than the wrapper's delegation.
    combined = _cast_class_for(value_class)
    # The state is already set by CastExpression.__init__ above; re-point the
    # instance's class rather than rebuilding it, so nothing is re-validated.
    node.__class__ = combined
    return node


def to_char(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "StringValueExpression":
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
        A StringValueExpression wrapping TO_CHAR
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    if format is not None:
        format_expr = Literal(dialect, format)
        return StringValueExpression(dialect, FunctionCall(dialect, 'TO_CHAR', target_expr, format_expr))
    return StringValueExpression(dialect, FunctionCall(dialect, 'TO_CHAR', target_expr))


def to_number(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "NumericValueExpression":
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
        A NumericValueExpression wrapping TO_NUMBER
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    if format is not None:
        format_expr = Literal(dialect, format)
        return NumericValueExpression(dialect, FunctionCall(dialect, 'TO_NUMBER', target_expr, format_expr))
    return NumericValueExpression(dialect, FunctionCall(dialect, 'TO_NUMBER', target_expr))


def to_date(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "TimestampValueExpression":
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
        A TimestampValueExpression wrapping TO_DATE
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    if format is not None:
        format_expr = Literal(dialect, format)
        return TimestampValueExpression(dialect, FunctionCall(dialect, 'TO_DATE', target_expr, format_expr))
    return TimestampValueExpression(dialect, FunctionCall(dialect, 'TO_DATE', target_expr))
