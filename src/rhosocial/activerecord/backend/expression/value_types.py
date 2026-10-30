# src/rhosocial/activerecord/backend/expression/value_types.py
"""A *value type*: what a node yields, and what can be done to it.

A ``*Value`` class states what an operation's result *is*. Text can be searched
and sliced, a number can be added to and has a square root, a date can have days
taken from it -- and the class that says so is named for the type, not for the
node, because the type is a property of the result rather than of whatever
produced it.

Fetching a column is an operation too, so a column reference is one of these
plus the column's name: :class:`~...expression.column_types.NumericColumn` and
:class:`NumericValue` declare the same thing about the same kind of thing, and
the only difference between them is that one knows where to read from. That is
why there are not two families. It is also why these classes were once called
*surfaces* -- a name for "the operations, with the value part removed" -- which
described what had been taken away rather than what was left.

What is deliberately **not** here:

* no ``__init__`` -- a value type declares what operations exist, not how a node
  is built. A node binds its dialect through :class:`BaseExpression` directly.
* no ``to_sql`` -- a value type cannot render, because it is not a node. A node
  renders itself through its own ``format_method``; see
  :class:`~...expression.advanced_functions.DeclaredValueType` for how a node
  that also names a value type keeps its own rendering.
* no forwarding -- the value types do not walk MROs to find each other. That
  existed for a wrapper holding a call; a node holding nothing does not need it.
* no value -- the value at a position belongs to
  :class:`~...expression.core.Literal`, and a value type never carries one.
"""

from abc import ABC, abstractmethod

from .bases import SQLValue
from .mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ArrayMixin,
    BooleanLogicMixin,
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
)


class TextValue(
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
    ABC,
):
    """Text: comparable, searchable, sliceable, convertible to a number.

    ``StringToIntegerMixin`` is here because ``length()`` and ``bit_length()``
    read a string and answer with a number -- they are operations *on* text whose
    result is not text, which is not the same as not offering them.
    """

    @property
    @abstractmethod
    def format_method(self) -> str:
        """Never implemented: a surface is not a node and cannot render.

        Declared abstract in every surface for two reasons. The registrar skips
        a class with unimplemented abstract methods, so a surface never enters
        the kind whitelist as a name nothing can produce. And a node that forgets
        its own ``format_method`` fails when its class is built rather than when
        it is rendered -- a mistake at import rather than at query time.
        """
        raise NotImplementedError


class NumericValue(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    SQLValue,
    ABC,
):
    """A number: arithmetic, comparison, and the algebraic and transcendental roots.

    The same surface serves whole numbers and fractions, because it is the
    operations that are the same; what differs is what a node *claims* to be,
    and that is said by the node's own kind rather than by a second surface.
    """

    @property
    @abstractmethod
    def format_method(self) -> str:
        """Never implemented: a surface is not a node and cannot render.

        Declared abstract in every surface for two reasons. The registrar skips
        a class with unimplemented abstract methods, so a surface never enters
        the kind whitelist as a name nothing can produce. And a node that forgets
        its own ``format_method`` fails when its class is built rather than when
        it is rendered -- a mistake at import rather than at query time.
        """
        raise NotImplementedError


class TemporalValue(
    AliasableMixin,
    ComparisonMixin,
    DateTimeMixin,
    TemporalArithmeticMixin,
    TypeCastingMixin,
    SQLValue,
    ABC,
):
    """A date, a time, a date-time or a span of one.

    No ``StringPatternPredicateMixin``: a date is not text, so ``like`` is not an
    operation any of them offers. No ``ArithmeticMixin`` either -- a temporal node
    is combined by ``date_add``/``date_sub``, not by ``+``, because what the
    ``+`` means depends on which side is the interval.
    """

    @property
    @abstractmethod
    def format_method(self) -> str:
        """Never implemented: a surface is not a node and cannot render.

        Declared abstract in every surface for two reasons. The registrar skips
        a class with unimplemented abstract methods, so a surface never enters
        the kind whitelist as a name nothing can produce. And a node that forgets
        its own ``format_method`` fails when its class is built rather than when
        it is rendered -- a mistake at import rather than at query time.
        """
        raise NotImplementedError


class BooleanValue(
    AliasableMixin,
    ComparisonMixin,
    BooleanLogicMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
    ABC,
):
    """A truth value: three-valued logic over ``AND``/``OR``/``NOT``."""

    @property
    @abstractmethod
    def format_method(self) -> str:
        """Never implemented: a surface is not a node and cannot render.

        Declared abstract in every surface for two reasons. The registrar skips
        a class with unimplemented abstract methods, so a surface never enters
        the kind whitelist as a name nothing can produce. And a node that forgets
        its own ``format_method`` fails when its class is built rather than when
        it is rendered -- a mistake at import rather than at query time.
        """
        raise NotImplementedError


class ArrayValue(
    AliasableMixin,
    ComparisonMixin,
    ArrayMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
    ABC,
):
    """A sequence: its elements, its length, its positions."""

    @property
    @abstractmethod
    def format_method(self) -> str:
        """Never implemented: a surface is not a node and cannot render.

        Declared abstract in every surface for two reasons. The registrar skips
        a class with unimplemented abstract methods, so a surface never enters
        the kind whitelist as a name nothing can produce. And a node that forgets
        its own ``format_method`` fails when its class is built rather than when
        it is rendered -- a mistake at import rather than at query time.
        """
        raise NotImplementedError


class JSONValue(
    AliasableMixin,
    ComparisonMixin,
    JSONAccessorMixin,
    TypeCastingMixin,
    SQLValue,
    ABC,
):
    """A JSON document: path access, extraction, the array and object forms.

    No arithmetic: a JSON document is not a number however it is written, and
    offering ``+`` on one would be a question no backend answers.
    """

    @property
    @abstractmethod
    def format_method(self) -> str:
        """Never implemented: a surface is not a node and cannot render.

        Declared abstract in every surface for two reasons. The registrar skips
        a class with unimplemented abstract methods, so a surface never enters
        the kind whitelist as a name nothing can produce. And a node that forgets
        its own ``format_method`` fails when its class is built rather than when
        it is rendered -- a mistake at import rather than at query time.
        """
        raise NotImplementedError


class OpaqueValue(
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
    ABC,
):
    """Something whose operations are only comparison and conversion.

    One surface for UUIDs and for binary blocks, because their operations are the
    same set -- equal, ordered, convertible -- and differ only in what the value
    *is*, which is the node's kind rather than the surface's business. Splitting
    them would imply a difference in what can be done to them, and there is none.
    """

    @property
    @abstractmethod
    def format_method(self) -> str:
        """Never implemented: a surface is not a node and cannot render.

        Declared abstract in every surface for two reasons. The registrar skips
        a class with unimplemented abstract methods, so a surface never enters
        the kind whitelist as a name nothing can produce. And a node that forgets
        its own ``format_method`` fails when its class is built rather than when
        it is rendered -- a mistake at import rather than at query time.
        """
        raise NotImplementedError


class XMLValue(
    AliasableMixin,
    NotComparableMixin,
    NullTestMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
    ABC,
):
    """An XML document: the null tests and conversion, but not comparison.

    ``<`` between two XML documents is not a question any backend answers the
    same way, so the surface declines it rather than offering something whose
    answer would vary by engine.
    """

    @property
    @abstractmethod
    def format_method(self) -> str:
        """Never implemented: a surface is not a node and cannot render.

        Declared abstract in every surface for two reasons. The registrar skips
        a class with unimplemented abstract methods, so a surface never enters
        the kind whitelist as a name nothing can produce. And a node that forgets
        its own ``format_method`` fails when its class is built rather than when
        it is rendered -- a mistake at import rather than at query time.
        """
        raise NotImplementedError


__all__ = [
    "TextValue",
    "NumericValue",
    "TemporalValue",
    "BooleanValue",
    "ArrayValue",
    "JSONValue",
    "OpaqueValue",
    "XMLValue",
]
