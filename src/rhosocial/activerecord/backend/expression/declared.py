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
from .bases import BaseExpression, SQLValue

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class _Annotation(SQLValue):
    """Shared state for the declared-result nodes: the node being annotated.

    One field, one job. It is deliberately **not** the general wrapper shape
    these replace -- that held a ``FunctionCall`` and derived its operations by
    walking two MROs to find the boundary between them, because it had to serve
    every type at once. One surface per class removes the need for any of it.

    ``BaseExpression`` is a base, not merely called from ``__init__``. These
    were duck-typed nodes: they rendered, and nothing else. So ``kind()`` was
    absent -- and an annotation produced by ``as_text()`` could not be
    serialized at all, because a node with no kind has no name an artifact can
    carry. Inheriting is what makes them nodes rather than things that happen
    to have ``to_sql``.
    """

    @classmethod
    def surface_of(cls) -> type:
        """The surface this annotation carries.

        Read off the bases rather than declared beside them: the surface *is*
        the third base, and a field repeating it is a second place to be wrong.
        CASE and CAST need the name to build their combined classes, which is
        why the question is asked of the class rather than of an instance.
        """
        for base in cls.__bases__:
            if base.__name__.endswith("Surface"):
                return base
        raise TypeError(
            f"{cls.__name__} carries no *Surface base; an annotation must name "
            f"the surface its declared result has"
        )

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
    TextSurface,
):
    """Declared to yield text: ``NULLIF(name, blank).as_text()``."""




class NumberAnnotation(
    _Annotation,
    DeclaredValueType,
    NumericSurface,
):
    """Declared to yield a fractional number."""




class IntegerAnnotation(
    _Annotation,
    DeclaredValueType,
    NumericSurface,
):
    """Declared to yield a whole number."""




class TemporalAnnotation(
    _Annotation,
    DeclaredValueType,
    TemporalSurface,
):
    """Declared to yield a date, a time or a date-time.

    No ``StringPatternPredicateMixin``: a date is not text, so ``like`` is not an
    operation any of them offers.
    """




class BooleanAnnotation(
    _Annotation,
    DeclaredValueType,
    BooleanSurface,
):
    """Declared to yield a truth value.

    This names the value, not a projection. SQL Server has no boolean scalar
    type, so a predicate cannot appear in a select list there; where one is
    needed the dialect has to produce a zero-or-one column.
    """




class ArrayAnnotation(
    _Annotation,
    DeclaredValueType,
    ArraySurface,
):
    """Declared to yield a sequence."""




class JSONAnnotation(
    _Annotation,
    DeclaredValueType,
    JSONSurface,
):
    """Declared to yield a JSON document."""




class UUIDAnnotation(
    _Annotation,
    DeclaredValueType,
    OpaqueSurface,
):
    """Declared to yield a UUID."""




class BinaryAnnotation(
    _Annotation,
    DeclaredValueType,
    OpaqueSurface,
):
    """Declared to yield bytes."""




class XMLAnnotation(
    _Annotation,
    DeclaredValueType,
    XMLSurface,
):
    """Declared to yield an XML document.

    Not comparable: ``<`` between two XML documents is not a question any
    backend answers the same way, so the node does not offer it.
    """




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
