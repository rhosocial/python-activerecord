# src/rhosocial/activerecord/backend/expression/functions/type_conversion.py
"""Type conversion function factories."""

from typing import Union, Optional, TYPE_CHECKING

from ..advanced_functions import DeclaredValueType
from ..bases import BaseExpression, SQLValue
from ..core import (
    Column,
    Literal,
)
from ..value_types import (
    NumericValue,
    TemporalValue,
    TextValue,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..types._base import DataType


#: Annotation class -> the class standing for both a CAST and that annotation.
#: Populated on first use by :func:`_cast_class_for`.
_CAST_ANNOTATION_CLASSES = {}

class _ConversionOperand:
    """Operand normalisation shared by the three conversion nodes.

    What each of them converts is arbitrary -- a number, a date, a string, a
    JSON document -- so there is no typed value node to normalise into, and a
    bare host value becomes the untyped literal. When the array and JSON value
    types land, this is the one place that changes.

    ``format`` is both the parameter's name and the attribute's name because
    get_params() resolves the two by name: an attribute spelled differently is a
    node whose parameters cannot be read back.
    """

    @staticmethod
    def _operand(dialect: "SQLDialectBase", value):
        from ..core import Literal

        if value is None:
            return None
        return value if isinstance(value, BaseExpression) else Literal(dialect, value)


class ToCharFunction(
    _ConversionOperand,
    DeclaredValueType,
    TextValue,
):
    """``TO_CHAR(value[, format])`` -- the value written as text.

    Text, because that is the whole point: this is how a number or a date
    reaches a report column, so the text value_type follows and the numeric one
    does not.

    :attr:`format` is a mask, and it is optional in a way that matters -- absent
    means the backend's default rendering, which is not the same as an explicit
    mask. So it is ``None`` rather than an empty string when not given.
    """


    def __init__(self, dialect: "SQLDialectBase", target, format=None):
        # BaseExpression directly, not super(): NumericValue is a *wrapper*.
        BaseExpression.__init__(self, dialect)
        self.target = self._operand(dialect, target)
        self.format = self._operand(dialect, format)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_to_char_function"


class ToNumberFunction(
    _ConversionOperand,
    DeclaredValueType,
    NumericValue,
):
    """``TO_NUMBER(value[, format])`` -- text read back as a number.

    An exact decimal where the backend produces one, so ``Decimal`` rather than
    ``float`` is the reading that loses nothing; a backend that answers with a
    double is answering a different question and says so in its formatter.
    """


    def __init__(self, dialect: "SQLDialectBase", target, format=None):
        # BaseExpression directly, not super(): NumericValue is a *wrapper*.
        BaseExpression.__init__(self, dialect)
        self.target = self._operand(dialect, target)
        self.format = self._operand(dialect, format)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_to_number_function"


class ToDateFunction(
    _ConversionOperand,
    DeclaredValueType,
    TemporalValue,
):
    """``TO_DATE(value[, format])`` -- text read back as a **date**.

    A date and not a timestamp, which is what every backend's ``TO_DATE``
    actually produces. It used to be typed as a timestamp, so the time-of-day
    operations were offered on a value that has no time of day -- a defect the
    type was in a position to prevent and did not.

    :attr:`format` is the mask that says which part of the string is which
    field, so it is the difference between ``'2026-10-17'`` and ``'17/10/2026'``
    being the same day.
    """


    def __init__(self, dialect: "SQLDialectBase", target, format=None):
        # BaseExpression directly, not super(): DateValue is a *wrapper* whose
        # __init__ takes the call it delegates to, and this node has no call --
        # it renders itself. DeclaredValueType is what keeps that from mattering.
        BaseExpression.__init__(self, dialect)
        self.target = self._operand(dialect, target)
        self.format = self._operand(dialect, format)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_to_date_function"


def _cast_class_for(annotation):
    """The class standing for both a CAST and *annotation*.

    Built once per annotation and kept, so ``type(x)`` does not differ between
    two casts that produce the same thing.

    ``CastExpression`` comes first: it supplies the node's own state and
    ``format_method``. ``DeclaredValueType`` supplies the rendering. The third
    base is the annotation's **value_type**, not the annotation: ``CastExpression``
    already derives from ``DeclaredValueType`` and so does the annotation, and
    asking for both leaves two orders to satisfy and no linearization. The
    value_type adds only mixins, so it settles -- and it keeps the annotation's own
    ``format_method`` out of reach, which is what a cast wants: it holds a type,
    not a node.
    """
    from ..core import CastExpression

    value_type = annotation.value_type_of()
    try:
        return _CAST_ANNOTATION_CLASSES[annotation]
    except KeyError:
        from ..advanced_functions import DeclaredValueType

        combined = type(
            f"Cast{value_type.__name__}",
            (CastExpression, DeclaredValueType, value_type),
            {
                "__doc__": (
                    f"A CAST to a type this annotation represents, so it is "
                    f"a {annotation.__name__}."
                )
            },
        )
        _CAST_ANNOTATION_CLASSES[annotation] = combined
        return combined


def _annotation_for(target_type):
    """The annotation *target_type* casts to, or ``None`` if it has none.

    A cast takes its answer from the target type, which is the only place it can
    come from: ``CAST(x AS t)`` is a ``t`` whatever ``x`` held. There is no
    lookup from a type *name* any more -- the name carries no type of its own to
    be right about, and a ``DataType`` instance is what identifies the type.

    Resolution walks the MRO, so ``IntegerType`` and the three narrower integer
    widths resolve as whole numbers through the class they share, and a backend's
    own type resolves through whichever core type it derives from.

    ``None`` is a real answer. A user-defined type has no annotation to offer:
    promising JSON navigation on a type nobody here has heard of would be worse
    than saying nothing, so the cast comes back untyped and the caller says what
    they meant with ``as_*``.
    """
    global _TYPE_ANNOTATIONS
    if _TYPE_ANNOTATIONS is None:
        _TYPE_ANNOTATIONS = _type_annotations()

    for klass in type(target_type).__mro__:
        annotation = _TYPE_ANNOTATIONS.get(klass)
        if annotation is not None:
            return annotation
    return None


def _type_annotations():
    """The ``DataType`` class -> annotation table, built on first use.

    Deferred because :mod:`..types` and :mod:`..core` both import from this
    package's expression module, so neither can be imported at module scope here.
    """
    from ..declared import (
        ArrayAnnotation,
        BinaryAnnotation,
        BooleanAnnotation,
        IntegerAnnotation,
        JSONAnnotation,
        NumberAnnotation,
        TemporalAnnotation,
        TextAnnotation,
        UUIDAnnotation,
        XMLAnnotation,
    )
    from ..types import (
        ArrayType,
        BigIntType,
        BinaryType,
        BlobType,
        BooleanType,
        CharType,
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
        IntegerType: IntegerAnnotation,
        TinyIntType: IntegerAnnotation,
        SmallIntType: IntegerAnnotation,
        BigIntType: IntegerAnnotation,
        # Fractional numbers.
        DecimalType: NumberAnnotation,
        FloatType: NumberAnnotation,
        RealType: NumberAnnotation,
        DoubleType: NumberAnnotation,
        # Text. An enum is text: its values are labels.
        CharType: TextAnnotation,
        VarCharType: TextAnnotation,
        TextType: TextAnnotation,
        EnumType: TextAnnotation,
        # Bytes.
        BinaryType: BinaryAnnotation,
        VarBinaryType: BinaryAnnotation,
        BlobType: BinaryAnnotation,
        BooleanType: BooleanAnnotation,
        # Documents.
        JsonType: JSONAnnotation,
        JsonBType: JSONAnnotation,
        # An XML document: a value with its own value_type, not a string.
        XmlType: XMLAnnotation,
        # Sequences.
        ArrayType: ArrayAnnotation,
        # A UUID is a UUID.
        UUIDType: UUIDAnnotation,
        # Temporal. A date, a time and a date-time carry the same operations, so
        # they share one annotation; what differs between them is what the node
        # declares, and CAST states exactly that much.
        DateType: TemporalAnnotation,
        DateTimeType: TemporalAnnotation,
        TimestampType: TemporalAnnotation,
        TimestampTzType: TemporalAnnotation,
        TimeType: TemporalAnnotation,
        TimeTzType: TemporalAnnotation,
        IntervalType: TemporalAnnotation,
    }


_TYPE_ANNOTATIONS = None


def cast(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    target_type: "DataType",
) -> "SQLValue":
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
    from ..core import CastExpression, Column

    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    node = CastExpression(dialect, target_expr, target_type)
    annotation = _annotation_for(target_type)
    if annotation is None:
        return node
    # A cast is the one place a result's type is stated by something other than
    # the input: CAST(x AS t) is a t by definition, whatever x was. So the node
    # is built as an instance of that class, and carries the annotation's
    # operations rather than holding one.
    combined = _cast_class_for(annotation)
    # The state is already set by CastExpression.__init__ above; re-point the
    # instance's class rather than rebuilding it, so nothing is re-validated.
    node.__class__ = combined
    return node


def to_char(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "ToCharFunction":
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
        A StringValue wrapping TO_CHAR
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    format_expr = Literal(dialect, format) if format is not None else None
    return ToCharFunction(dialect, target_expr, format_expr)


def to_number(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "ToNumberFunction":
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
        A NumericValue wrapping TO_NUMBER
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    format_expr = Literal(dialect, format) if format is not None else None
    return ToNumberFunction(dialect, target_expr, format_expr)


def to_date(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], format: Optional[str] = None
) -> "ToDateFunction":
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
        A TimestampValue wrapping TO_DATE
    """
    target_expr = expr if isinstance(expr, BaseExpression) else Column(dialect, expr)
    format_expr = Literal(dialect, format) if format is not None else None
    return ToDateFunction(dialect, target_expr, format_expr)
