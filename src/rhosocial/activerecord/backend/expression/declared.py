# src/rhosocial/activerecord/backend/expression/declared.py
"""Declared result types -- for the operations whose result the source cannot settle.

Most operations know what they yield and say so by being their own class:
``col.length()`` is a :class:`~...expression.functions.string.CharLengthFunction`
and nothing needs to tell it. A few cannot, and the standard gives the example
itself -- ``NULLIF(x, y)`` yields ``x`` when the two differ and NULL when they do
not, so whether the answer is text or a number depends on the data.

For those, the caller states it, and this is where that statement lives:
``NULLIF(name, blank).as_text()`` is text, and ``.upper()`` may follow it while
``.sqrt()`` may not.

**These are annotations, not wrappers.** The node underneath is left exactly as
it was -- the statement was already correct, and what was missing was the
knowledge of what it yields -- so rendering delegates to it and the SQL does not
change. The difference from the general value classes this replaces is that each
of these carries **one** surface and does none of the forwarding they did: there
is no second hierarchy to walk and no MRO intersection to compute, because
nothing here holds a call.

Each class is its own, so ``as_text()`` returns a class a type checker can read
as text. Returning a common base would leave the checker unable to tell, which
would be the whole point of the method lost.
"""

from typing import TYPE_CHECKING

from .advanced_functions import DeclaredValueType
from .surfaces import (
    ArraySurface,
    BooleanSurface,
    JSONSurface,
    NumericSurface,
    OpaqueSurface,
    TemporalSurface,
    TextSurface,
    XMLSurface,
)
from .bases import BaseExpression
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ArrayMixin,
    ComparisonMixin,
    DateTimeMixin,
    JSONAccessorMixin,
    NotANumberMixin,
    NotComparableMixin,
    NullTestMixin,
    NumericValueMixin,
    StringPatternPredicateMixin,
    StringToIntegerMixin,
    StringValueMixin,
    TemporalArithmeticMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    BooleanLogicMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class _Annotation:
    """Shared state for the declared-result nodes: the node being annotated.

    One field, one job. It is deliberately **not** the general wrapper shape
    these replace -- that held a ``FunctionCall`` and derived its operations by
    walking two MROs to find the boundary between them, because it had to serve
    every type at once. One surface per class removes the need for any of it.
    """

    kind_name: str = ""

    #: The surface this annotation carries, named rather than inferred. A node
    #: that adopts the annotation's operations has to reach the surface too, and
    #: walking the MRO for it would be the reflection this package does not do:
    #: the surface is a fact about the annotation, so the annotation says so.
    surface: type = None

    def __init__(self, dialect: "SQLDialectBase", source: BaseExpression):
        # BaseExpression directly, not super(): the surfaces below are mixin
        # carriers ending at SQLValue, and going through super() would chain
        # into whichever of them happens to declare __init__.
        BaseExpression.__init__(self, dialect)
        self.source = source

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_declared_result"


class TextAnnotation(
    _Annotation,
    DeclaredValueType,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
):
    """Declared to yield text: ``NULLIF(name, blank).as_text()``."""

    surface = TextSurface

    kind_name = "text_annotation"


class NumberAnnotation(
    _Annotation,
    DeclaredValueType,
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
):
    """Declared to yield a fractional number."""

    surface = NumericSurface

    kind_name = "number_annotation"


class IntegerAnnotation(
    _Annotation,
    DeclaredValueType,
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
):
    """Declared to yield a whole number."""

    surface = NumericSurface

    kind_name = "integer_annotation"


class TemporalAnnotation(
    _Annotation,
    DeclaredValueType,
    AliasableMixin,
    ComparisonMixin,
    DateTimeMixin,
    TemporalArithmeticMixin,
    TypeCastingMixin,
):
    """Declared to yield a date, a time or a date-time.

    No ``StringPatternPredicateMixin``: a date is not text, so ``like`` is not an
    operation any of them offers.
    """

    surface = TemporalSurface

    kind_name = "temporal_annotation"


class BooleanAnnotation(
    _Annotation,
    DeclaredValueType,
    AliasableMixin,
    ComparisonMixin,
    BooleanLogicMixin,
    TypeCastingMixin,
    NotANumberMixin,
):
    """Declared to yield a truth value.

    This names the value, not a projection. SQL Server has no boolean scalar
    type, so a predicate cannot appear in a select list there; where one is
    needed the dialect has to produce a zero-or-one column.
    """

    surface = BooleanSurface

    kind_name = "boolean_annotation"


class ArrayAnnotation(
    _Annotation,
    DeclaredValueType,
    AliasableMixin,
    ComparisonMixin,
    ArrayMixin,
    TypeCastingMixin,
    NotANumberMixin,
):
    """Declared to yield a sequence."""

    surface = ArraySurface

    kind_name = "array_annotation"


class JSONAnnotation(
    _Annotation,
    DeclaredValueType,
    AliasableMixin,
    ComparisonMixin,
    JSONAccessorMixin,
    TypeCastingMixin,
):
    """Declared to yield a JSON document."""

    surface = JSONSurface

    kind_name = "json_annotation"


class UUIDAnnotation(
    _Annotation,
    DeclaredValueType,
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    NotANumberMixin,
):
    """Declared to yield a UUID."""

    surface = OpaqueSurface

    kind_name = "uuid_annotation"


class BinaryAnnotation(
    _Annotation,
    DeclaredValueType,
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    NotANumberMixin,
):
    """Declared to yield bytes."""

    surface = OpaqueSurface

    kind_name = "binary_annotation"


class XMLAnnotation(
    _Annotation,
    DeclaredValueType,
    AliasableMixin,
    NotComparableMixin,
    NullTestMixin,
    TypeCastingMixin,
    NotANumberMixin,
):
    """Declared to yield an XML document.

    Not comparable: ``<`` between two XML documents is not a question any
    backend answers the same way, so the node does not offer it.
    """

    surface = XMLSurface

    kind_name = "xml_annotation"


__all__ = [
    "TextAnnotation",
    "NumberAnnotation",
    "IntegerAnnotation",
    "TemporalAnnotation",
    "BooleanAnnotation",
    "ArrayAnnotation",
    "JSONAnnotation",
    "UUIDAnnotation",
    "BinaryAnnotation",
    "XMLAnnotation",
]
