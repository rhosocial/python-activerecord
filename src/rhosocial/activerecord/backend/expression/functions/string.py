# src/rhosocial/activerecord/backend/expression/functions/string.py
"""String function factories."""

from typing import Union, Optional, TYPE_CHECKING

from .. import values
from ..bases import BaseExpression, SQLValue
from ..core import (
    FunctionCall,
    Literal,
)
from ..mixins import (
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NotANumberMixin,
    NumericValueMixin,
    StringPatternPredicateMixin,
    StringToIntegerMixin,
    StringValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
)
from ..operators import ConcatenationOperation

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..advanced_functions import (
        LpadFunction,
        RepeatFunction,
        RpadFunction,
        TrimExpression,
    )


#: The length units ``CharLengthFunction`` admits (spec 4.2).
CHAR_LENGTH_UNITS = ("char", "octet", "bit")


class UpperFunction(
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``UPPER(operand)`` as a node.

    A derived string is still a string, so the node carries the string value
    surface and the chain continues: ``col.upper().substr(1, 3)`` is
    ``SUBSTRING(UPPER(col), 1, 3)``.

    The spelling is the dialect's decision, not the caller's: SQLite's
    ``upper`` only folds ASCII, which is a fact about that backend rather than
    a different operation.
    """

    def __init__(self, dialect: "SQLDialectBase", operand: "BaseExpression"):
        super().__init__(dialect)
        self.operand = operand

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_upper_function"


class LowerFunction(
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``LOWER(operand)`` as a node — the mirror of :class:`UpperFunction`."""

    def __init__(self, dialect: "SQLDialectBase", operand: "BaseExpression"):
        super().__init__(dialect)
        self.operand = operand

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_lower_function"


class CharLengthFunction(
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    SQLValue,
):
    """``CHAR_LENGTH(operand)`` — the length of a string, counted in *unit*.

    **The ``unit`` never enters the SQL.** It records the semantic the caller
    wants (``char`` / ``octet`` / ``bit``); mapping that semantic onto a
    backend's spelling is backend-layer work. This is the trap the catalog
    names (spec wire #33): ``LENGTH`` is not the same question on every
    backend — MySQL's and ClickHouse's are bytes, PostgreSQL's and SQLite's
    are characters, and SQL Server's ``LEN`` counts UTF-16 code units — so a
    bare ``length`` kind would silently pin one answer. The node states the
    unit, and the backend formatter decides whether its spelling can honour
    it.

    The count is a whole number, so the node carries the integer surface and
    not the string one: ``col.length().upper()`` is refused where it is
    written.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        operand: "BaseExpression",
        unit: str = "char",
    ):
        if unit not in CHAR_LENGTH_UNITS:
            raise ValueError(
                f"unknown length unit {unit!r}: the units are "
                f"{list(CHAR_LENGTH_UNITS)}"
            )
        super().__init__(dialect)
        self.operand = operand
        self.unit = unit

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_char_length_function"


# The mixin sets below are the result types, spelled out per class. They used to
# be inherited once by ``StringValue`` / ``IntegerValue``, which each factory
# returned as a wrapper around a ``FunctionCall``. A node that is its own class
# carries them directly, so there is no second hierarchy to forward from -- which
# is what let ``WrappedCallMixin`` and its MRO-intersection walk go.


class _FunctionOperands:
    """Declared-operand normalisation for the text function nodes below.

    Each node says what its operands *mean* -- text, or a whole number -- and
    this is where a bare host value becomes the node that says so. Normalising
    here rather than only in the factory means constructing a node directly is
    safe as well, and a wrong operand fails at construction instead of surfacing
    as an ``AttributeError`` from the formatter.

    A base class rather than two module functions, so the helpers are reachable
    as ``self._text(...)`` and appear in ``dir()``.

    The two variadic functions below are the exception and do not use this:
    ``CONCAT`` and ``COALESCE`` take operands of any type, so there is no
    single node to normalise them into.
    """

    @staticmethod
    def _text(dialect: "SQLDialectBase", value):
        """*value* as a text operand: a node if it is one, typed otherwise."""
        from .. import values

        return values.StringValue.of(dialect, value)

    @staticmethod
    def _count(dialect: "SQLDialectBase", value):
        """*value* as a whole-number operand: a node if it is one, typed otherwise."""
        from .. import values

        return values.IntegerValue.of(dialect, value)


class ConcatFunction(
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``CONCAT(a, b, ...)`` -- the operands joined end to end.

    Offered instead of ``||``, whose meaning is not concatenation everywhere:
    in MySQL it is logical OR by default, so an operator reachable from a text
    column would quietly produce a boolean there. See :func:`concat_op` for the
    operator, which exists but is not reachable from text.
    """

    kind_name = "concat_function"

    def __init__(self, dialect: "SQLDialectBase", *operands):
        from ..core import Literal

        super().__init__(dialect)
        self.operands = [o if isinstance(o, BaseExpression) else Literal(dialect, o) for o in operands]

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_concat_function"


class CoalesceFunction(
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``COALESCE(a, b, ...)`` -- the first operand that is not NULL.

    The result type follows the operands, which is why it is not settled here:
    ``COALESCE(col, 0)`` is a number and ``COALESCE(a, b)`` is whatever ``a``
    is. The class therefore carries the text surface because that is the common
    case, and a caller who needs another surface says so with
    :class:`~...expression.mixins.ResultTypeMixin` -- the one situation the mixin
    exists for, since the source cannot answer it.
    """

    kind_name = "coalesce_function"

    def __init__(self, dialect: "SQLDialectBase", *operands):
        from ..core import Literal

        super().__init__(dialect)
        self.operands = [o if isinstance(o, BaseExpression) else Literal(dialect, o) for o in operands]

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_coalesce_function"


class SubstringExpression(
    _FunctionOperands,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``SUBSTRING(text FROM start [FOR length])`` -- a slice of the text.

    An *expression* and not a function: the standard's grammar produces it as a
    scalar expression primary with ``FROM`` / ``FOR`` keywords rather than as a
    comma-separated argument list (catalog 3.4), which is also why backends
    disagree on the spelling and the formatter picks it.

    ``start`` is 1-based and ``length`` counts forward. Both edges were measured
    across the ten backends (2026-10-09) and are refused rather than rendered:
    a position below 1 is consumed by the length on PostgreSQL, SQL Server,
    Firebird and SQLite, yields an empty string on MySQL, MariaDB and
    ClickHouse, and is read as 1 on Oracle; a negative length is an error on
    some backends, an empty string on MySQL/MariaDB, NULL on Oracle, and
    something unrelated again on ClickHouse.
    """

    kind_name = "substring_expression"

    def __init__(self, dialect: "SQLDialectBase", target, start, length=None):
        # Both positions are integer-valued, and a bound is only checkable when
        # the value is *known* here. A typed value node states its number, so it
        # is checked; any other expression -- a column, a parameter -- does not,
        # and whether it lands in range is the server's answer. Asking
        # ``isinstance`` against the declared base is the whole test: no probing
        # for an attribute that may or may not be there.
        target = self._text(dialect, target)
        start = self._count(dialect, start)
        length = None if length is None else self._count(dialect, length)
        if isinstance(start, values.TypedValue) and start.value < 1:
            raise ValueError(
                f"substring(): start must be >= 1 (positions are 1-based), got {start.value!r}"
            )
        if isinstance(length, values.TypedValue) and length.value < 0:
            raise ValueError(f"substring(): length must be >= 0, got {length.value!r}")
        super().__init__(dialect)
        self.target = target
        self.start = start
        self.length = length

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_substring_expression"


class OverlayExpression(
    _FunctionOperands,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``OVERLAY(text PLACING replacement FROM start [FOR length])``.

    An *expression* rather than a function, for the same grammar reason as
    :class:`SubstringExpression`: the standard spells it with ``PLACING`` and
    ``FROM`` keywords, and that spelling is what distinguishes it from
    ``SUBSTRING`` where a backend has both.
    """

    kind_name = "overlay_expression"

    def __init__(self, dialect: "SQLDialectBase", target, replacement, start, length=None):
        target = self._text(dialect, target)
        replacement = self._text(dialect, replacement)
        start = self._count(dialect, start)
        length = None if length is None else self._count(dialect, length)
        target = self._text(dialect, target)
        replacement = self._text(dialect, replacement)
        start = self._count(dialect, start)
        length = None if length is None else self._count(dialect, length)
        super().__init__(dialect)
        self.target = target
        self.replacement = replacement
        self.start = start
        self.length = length

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_overlay_expression"


class PositionExpression(
    _FunctionOperands,
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    SQLValue,
):
    """The 1-based position of a substring, or 0 when it is absent.

    One class for two spellings because they answer the same question:
    ``STRPOS(haystack, needle)`` takes the haystack first, while
    ``POSITION(needle IN haystack)`` takes the needle first and is a scalar
    expression primary rather than a function (catalog 3.4). :attr:`spelling`
    says which was asked for, so the arguments stay in **this** class's order
    (haystack, needle) whichever way the SQL reads.

    0 for "not found" is what most backends answer; ``NULL`` is the SQL
    standard's own answer, and a backend that disagrees overrides the formatter
    rather than the node.
    """

    kind_name = "position_expression"

    #: The spellings this node can be asked for. The base renders both as a
    #: function call; a backend needing ``POSITION(needle IN haystack)`` as the
    #: standard writes it overrides the formatter.
    SPELLINGS = ("STRPOS", "POSITION")

    def __init__(self, dialect: "SQLDialectBase", haystack, needle, spelling: str = "STRPOS"):
        if spelling not in self.SPELLINGS:
            raise ValueError(f"unknown position spelling {spelling!r}: the spellings are {list(self.SPELLINGS)}")
        haystack = self._text(dialect, haystack)
        needle = self._text(dialect, needle)
        haystack = self._text(dialect, haystack)
        needle = self._text(dialect, needle)
        super().__init__(dialect)
        self.haystack = haystack
        self.needle = needle
        self.spelling = spelling

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_position_expression"


class ReplaceFunction(
    _FunctionOperands,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``REPLACE(text, pattern, replacement)`` -- every occurrence replaced.

    The pattern is a **literal**, not a regular expression; that is what
    separates this from the ``REGEXP_REPLACE`` family, and it is a difference in
    what the function means rather than in how it is spelled, which is why they
    are not one class with a ``spelling``.
    """

    kind_name = "replace_function"

    def __init__(self, dialect: "SQLDialectBase", target, pattern, replacement):
        target = self._text(dialect, target)
        pattern = self._text(dialect, pattern)
        replacement = self._text(dialect, replacement)
        target = self._text(dialect, target)
        pattern = self._text(dialect, pattern)
        replacement = self._text(dialect, replacement)
        super().__init__(dialect)
        self.target = target
        self.pattern = pattern
        self.replacement = replacement

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_replace_function"


class InitcapFunction(
    _FunctionOperands,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``INITCAP(text)`` -- first letter of each word upper, the rest lower."""

    kind_name = "initcap_function"

    def __init__(self, dialect: "SQLDialectBase", target):
        target = self._text(dialect, target)
        super().__init__(dialect)
        self.target = target

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_initcap_function"


class LeftFunction(
    _FunctionOperands,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``LEFT(text, n)`` -- the first *n* characters.

    ``n >= 0`` and everything above it is portable: 0 is the empty string and
    more than the length is the whole text on every backend. Below 0 they
    answer four different ways -- PostgreSQL and ClickHouse drop the trailing
    ``|n|`` characters, MySQL, MariaDB and Snowflake return an empty string,
    SQL Server and Firebird raise, and BigQuery raises -- so a negative count is
    refused here rather than rendered four ways.
    """

    kind_name = "left_function"

    def __init__(self, dialect: "SQLDialectBase", target, count):
        # See SubstringExpression: checkable when the count is stated, the
        # server's business otherwise.
        if isinstance(count, values.TypedValue) and count.value < 0:
            raise ValueError(f"left(): n must be >= 0, got {count.value!r}")
        target = self._text(dialect, target)
        count = self._count(dialect, count)
        target = self._text(dialect, target)
        count = self._count(dialect, count)
        target = self._text(dialect, target)
        count = self._count(dialect, count)
        super().__init__(dialect)
        self.target = target
        self.count = count

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_left_function"


class RightFunction(
    _FunctionOperands,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``RIGHT(text, n)`` -- the last *n* characters.

    The same ``n >= 0`` contract as :class:`LeftFunction`, and refused for the
    same reason: the backends do not agree below zero.
    """

    kind_name = "right_function"

    def __init__(self, dialect: "SQLDialectBase", target, count):
        # See SubstringExpression.
        if isinstance(count, values.TypedValue) and count.value < 0:
            raise ValueError(f"right(): n must be >= 0, got {count.value!r}")
        target = self._text(dialect, target)
        count = self._count(dialect, count)
        super().__init__(dialect)
        self.target = target
        self.count = count

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_right_function"


class ReverseFunction(
    _FunctionOperands,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``REVERSE(text)`` -- the characters in the other order."""

    kind_name = "reverse_function"

    def __init__(self, dialect: "SQLDialectBase", target):
        target = self._text(dialect, target)
        super().__init__(dialect)
        self.target = target

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_reverse_function"


class TranslateFunction(
    _FunctionOperands,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``TRANSLATE(text, from, to)`` -- character-by-character substitution.

    Positional, not a search-and-replace: the *n*th character of *from* becomes
    the *n*th of *to*. That is also what separates it from ``REPLACE``, which
    replaces a whole substring.
    """

    kind_name = "translate_function"

    def __init__(self, dialect: "SQLDialectBase", target, from_chars, to_chars):
        target = self._text(dialect, target)
        from_chars = self._text(dialect, from_chars)
        to_chars = self._text(dialect, to_chars)
        target = self._text(dialect, target)
        from_chars = self._text(dialect, from_chars)
        to_chars = self._text(dialect, to_chars)
        super().__init__(dialect)
        self.target = target
        self.from_chars = from_chars
        self.to_chars = to_chars

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_translate_function"


class SpaceFunction(
    _FunctionOperands,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``SPACE(n)`` -- *n* spaces.

    One operand, so it is its own class rather than a text literal that happens
    to hold blanks: the node says what produced it, which is what lets a backend
    without ``SPACE`` compose the blanks some other way.
    """

    kind_name = "space_function"

    def __init__(self, dialect: "SQLDialectBase", count):
        count = self._count(dialect, count)
        count = self._count(dialect, count)
        super().__init__(dialect)
        self.count = count

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_space_function"


class ChrFunction(
    _FunctionOperands,
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``CHR(code)`` -- the character the code names.

    The standard's function; ``ASCII`` is its inverse, and the two are kept
    apart because the code space is not symmetric across backends (Oracle's
    ``CHR`` is database-specific above 255 while its ``ASCII`` only reads the
    first byte).
    """

    kind_name = "chr_function"

    def __init__(self, dialect: "SQLDialectBase", code):
        code = self._count(dialect, code)
        code = self._count(dialect, code)
        super().__init__(dialect)
        self.code = code

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_chr_function"


class AsciiFunction(
    _FunctionOperands,
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    SQLValue,
):
    """``ASCII(text)`` -- the code of the first character."""

    kind_name = "ascii_function"

    def __init__(self, dialect: "SQLDialectBase", target):
        target = self._text(dialect, target)
        super().__init__(dialect)
        self.target = target

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_ascii_function"


class OctetLengthFunction(
    _FunctionOperands,
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    SQLValue,
):
    """``OCTET_LENGTH(text)`` -- the length in bytes.

    A different question from :class:`~...expression.functions.string.CharLengthFunction`,
    which counts characters, and the two disagree wherever a character is more
    than one byte. Kept separate rather than folded into a ``unit`` parameter
    because both spellings exist in the standard and a caller asking for one
    wants that one.
    """

    kind_name = "octet_length_function"

    def __init__(self, dialect: "SQLDialectBase", target):
        target = self._text(dialect, target)
        super().__init__(dialect)
        self.target = target

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_octet_length_function"


class BitLengthFunction(
    _FunctionOperands,
    AliasableMixin,
    ArithmeticMixin,
    ComparisonMixin,
    NumericValueMixin,
    TranscendentalMixin,
    TypeCastingMixin,
    SQLValue,
):
    """``BIT_LENGTH(text)`` -- the length in bits."""

    kind_name = "bit_length_function"

    def __init__(self, dialect: "SQLDialectBase", target):
        target = self._text(dialect, target)
        super().__init__(dialect)
        self.target = target

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_bit_length_function"


def concat(dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]) -> "ConcatFunction":
    """
    Creates a CONCAT scalar function call.

    Usage rules:
    - To generate CONCAT(column1, column2, ...), pass Column objects: concat(dialect, Column(...), Column(...))
    - To generate CONCAT(?, ?, ...), pass literal values: concat(dialect, "value1", "value2")

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to concatenate. If strings are passed, they're treated as literal values.
                If BaseExpressions are passed, they're used as-is.

    Returns:
        A FunctionCall instance representing the CONCAT function
    """
    target_exprs = [e if isinstance(e, BaseExpression) else Literal(dialect, e) for e in exprs]
    return ConcatFunction(dialect, *target_exprs)


def coalesce(dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]) -> "CoalesceFunction":
    """
    Creates a COALESCE scalar function call.

    Usage rules:
    - To generate COALESCE(column1, column2, ...), pass Column objects: coalesce(dialect, Column(...), Column(...))
    - To generate COALESCE(?, ?, ...), pass literal values: coalesce(dialect, "value1", "value2")

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to coalesce. If strings are passed, they're treated as literal values.
                If BaseExpressions are passed, they're used as-is.

    Returns:
        A FunctionCall instance representing the COALESCE function
    """
    target_exprs = [e if isinstance(e, BaseExpression) else Literal(dialect, e) for e in exprs]
    return CoalesceFunction(dialect, *target_exprs)


def length(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    unit: str = "char",
) -> "CharLengthFunction":
    """
    Creates a CHAR_LENGTH node.

    Usage rules:
    - To generate LENGTH(column), pass a Column object: length(dialect, Column(dialect, "column_name"))
    - To generate LENGTH(?), pass a literal value: length(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to measure length of. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        unit: The unit the length is asked in (``char`` / ``octet`` / ``bit``).
              It is recorded on the node and **never enters the SQL**; a
              backend whose spelling cannot honour it overrides the formatter.

    Returns:
        A :class:`CharLengthFunction` node.
    """
    target_expr = values.StringValue.of(dialect, expr)
    return CharLengthFunction(dialect, target_expr, unit=unit)


def substring(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    start: Union[int, "BaseExpression"],
    length: Optional[Union[int, "BaseExpression"]] = None,
) -> "SubstringExpression":
    """
    Creates a SUBSTRING scalar function call.

    Usage rules:
    - To generate SUBSTRING(column, start, length), pass a Column object as expr and integers for start/length:
      substring(dialect, Column(dialect, "column_name"), 1, 5)
    - To generate SUBSTRING(?, ?, ?), pass literal values: substring(dialect, "text", 1, 5)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract substring from. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        start: Starting position for extraction. If an integer is passed, it's treated as a literal value.
        length: Optional ending position or length. If provided, it's treated as a literal value.

    Returns:
        A FunctionCall instance representing the SUBSTRING function

    Raises:
        ValueError: A literal *start* below 1, or a literal *length* below 0.

    Contract:
        ``start`` is 1-based and ``length`` counts forward. Both edges were
        measured across the ten backends (2026-10-09) and are refused here
        rather than rendered, because the backends do not agree on what an
        out-of-range argument means: a position below 1 is consumed by the
        length on PostgreSQL, SQL Server, Firebird and SQLite, yields an empty
        string on MySQL, MariaDB and ClickHouse, and is read as 1 on Oracle; a
        negative length is an error on some backends, an empty string on
        MySQL/MariaDB, NULL on Oracle and something unrelated again on
        ClickHouse.
    """
    target_expr = values.StringValue.of(dialect, expr)
    start_expr = values.IntegerValue.of(dialect, start)
    # An absent length stays None rather than becoming Literal(None): the
    # formatter drops a trailing None, and a node holding NULL would render a
    # fourth argument instead.
    length_expr = None if length is None else values.IntegerValue.of(dialect, length)
    return SubstringExpression(dialect, target_expr, start_expr, length_expr)


def trim(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    chars: Optional[Union[str, "BaseExpression"]] = None,
    direction: str = "BOTH",
) -> "TrimExpression":
    """
    Creates a TRIM node.

    Usage rules:
    - To generate TRIM(BOTH FROM column), pass a Column object: trim(dialect, Column(dialect, "column_name"))
    - To generate TRIM(BOTH chars FROM ?), pass literal values: trim(dialect, "text", " ", "BOTH")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to trim. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        chars: Optional single character to trim. If provided, treated as
            literal value if string.
        direction: Direction of trim operation (BOTH, LEADING, TRAILING). Default is BOTH.

    Returns:
        A :class:`~...expression.advanced_functions.TrimExpression` node, which
        the dialect renders through its ``format_trim_expression`` hook.

    Raises:
        ValueError: An unknown *direction*, or a trim set that is not exactly
            one character.

    Contract:
        The trim set is **one character**, which is what SQL:2016 feature
        E021-09 (``trim(<char> from ...)``) defines and what every backend
        agrees on. A multi-character set means three different things in the
        wild -- a character set on PostgreSQL, SQL Server, ClickHouse and
        Snowflake, a whole string repeated on MySQL, MariaDB and Firebird, and
        ``ORA-30001`` on Oracle -- so it is refused at construction instead of
        rendered into whichever of the three the backend happens to implement.
        The node, not a raw SQL string, is what makes the dialect's spelling a
        formatter's decision: SQLite overrides the hook because it parses no
        ``trim(... from ...)`` syntax at all.
    """
    # Validate direction: only allow known trim directions.
    valid_directions = frozenset({"BOTH", "LEADING", "TRAILING"})
    if direction not in valid_directions:
        raise ValueError(f"Invalid trim direction '{direction}': must be one of {valid_directions}")
    if isinstance(chars, str) and len(chars) != 1:
        raise ValueError(
            f"Invalid trim set {chars!r}: must be exactly one character -- SQL:2016 "
            "feature E021-09 defines trim(<char> from ...), and a multi-character "
            "set means three different things across the backends"
        )

    from ..advanced_functions import TrimExpression

    target_expr = values.StringValue.of(dialect, expr)
    chars_expr: Optional[BaseExpression] = None
    if chars is not None:
        chars_expr = values.StringValue.of(dialect, chars)
    return TrimExpression(dialect, target_expr, chars_expr, direction)


def replace(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    pattern: Union[str, "BaseExpression"],
    replacement: Union[str, "BaseExpression"],
) -> "FunctionCall":
    """
    Creates a REPLACE scalar function call.

    Usage rules:
    - To generate REPLACE(column, pattern, replacement), pass Column objects:
      replace(dialect, Column(dialect, "column_name"), "old", "new")
    - To generate REPLACE(?, ?, ?), pass literal values: replace(dialect, "text", "old", "new")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to perform replacement on. If a string is passed, it's treated as a literal value.
        pattern: Pattern to find. If a string is passed, it's treated as a literal value.
        replacement: Replacement value. If a string is passed, it's treated as a literal value.

    Returns:
        A FunctionCall instance representing the REPLACE function
    """
    target_expr = values.StringValue.of(dialect, expr)
    pattern_expr = values.StringValue.of(dialect, pattern)
    replacement_expr = values.StringValue.of(dialect, replacement)
    return ReplaceFunction(dialect, target_expr, pattern_expr, replacement_expr)


def upper(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "UpperFunction":
    """
    Creates an UPPER scalar function node.

    Usage rules:
    - To generate UPPER(column), pass a Column object: upper(dialect, Column(dialect, "column_name"))
    - To generate UPPER(?), pass a literal value: upper(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to uppercase. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        An :class:`UpperFunction` node.
    """
    target_expr = values.StringValue.of(dialect, expr)
    return UpperFunction(dialect, target_expr)


def lower(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "LowerFunction":
    """
    Creates a LOWER scalar function node.

    Usage rules:
    - To generate LOWER(column), pass a Column object: lower(dialect, Column(dialect, "column_name"))
    - To generate LOWER(?), pass a literal value: lower(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to lowercase. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A :class:`LowerFunction` node.
    """
    target_expr = values.StringValue.of(dialect, expr)
    return LowerFunction(dialect, target_expr)


def initcap(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "InitcapFunction":
    """
    Creates an INITCAP scalar function call (title case).

    Usage rules:
    - To generate INITCAP(column), pass a Column object: initcap(dialect, Column(dialect, "column_name"))
    - To generate INITCAP(?), pass a literal value: initcap(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to convert to title case. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the INITCAP function
    """
    target_expr = values.StringValue.of(dialect, expr)
    return InitcapFunction(dialect, target_expr)


def left(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], n: int) -> "LeftFunction":
    """
    Creates a LEFT scalar function call.

    Usage rules:
    - To generate LEFT(column, n), pass a Column object: left(dialect, Column(dialect, "column_name"), 5)
    - To generate LEFT(?, n), pass a literal value: left(dialect, "text", 5)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract left portion from. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        n: Number of characters to extract from the left.

    Returns:
        A FunctionCall instance representing the LEFT function

    Raises:
        ValueError: If *n* is negative.

    Contract:
        ``n >= 0``, and everything above it is portable: 0 is the empty string
        and more than the length is the whole string on every backend. Below 0
        the backends answer four different ways -- PostgreSQL and ClickHouse
        drop the trailing ``|n|`` characters, MySQL, MariaDB and Snowflake
        return an empty string, SQL Server and Firebird raise, and BigQuery
        raises -- so a negative count is refused rather than rendered.
    """
    target_expr = values.StringValue.of(dialect, expr)
    n_expr = values.IntegerValue.of(dialect, n)
    return LeftFunction(dialect, target_expr, n_expr)


def right(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], n: int) -> "RightFunction":
    """
    Creates a RIGHT scalar function call.

    Usage rules:
    - To generate RIGHT(column, n), pass a Column object: right(dialect, Column(dialect, "column_name"), 5)
    - To generate RIGHT(?, n), pass a literal value: right(dialect, "text", 5)

    Args:
        dialect: The SQL dialect instance
        expr: The expression to extract right portion from. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        n: Number of characters to extract from the right.

    Returns:
        A FunctionCall instance representing the RIGHT function

    Raises:
        ValueError: If *n* is negative.

    Contract:
        The mirror of :func:`left` -- ``n >= 0``, 0 is the empty string, more
        than the length is the whole string, and a negative count is refused
        because no two backends agree on it (see :func:`left`).
    """
    target_expr = values.StringValue.of(dialect, expr)
    n_expr = values.IntegerValue.of(dialect, n)
    return RightFunction(dialect, target_expr, n_expr)


def lpad(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], length: int, pad: Optional[str] = None
) -> "LpadFunction":
    """
    Creates a left-padding node.

    Usage rules:
    - To generate LPAD(column, length, pad), pass a Column object:
      lpad(dialect, Column(dialect, "column_name"), 10, "0")
    - To generate LPAD(?, length, pad), pass a literal value: lpad(dialect, "text", 10, "0")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to pad. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        length: Total length after padding.
        pad: Optional padding string, non-empty. Defaults to a single space.

    Returns:
        A :class:`~...expression.advanced_functions.LpadFunction` node, which
        the dialect renders through ``format_lpad_expression`` -- a spelling
        where the function exists (PostgreSQL, MySQL, MariaDB, Oracle,
        Firebird, ClickHouse, Snowflake, BigQuery) and an emulation composed
        from ordinary nodes where it does not (SQLite).

    Raises:
        ValueError: A negative *length*, or an empty *pad*.

    Contract:
        ``length >= 0`` and the pad is non-empty; an omitted pad means one
        space, and it is always passed explicitly because the backends differ
        on whether the argument is optional at all (MySQL raises 1582 without
        it, MariaDB fills with spaces). An empty pad is refused: measured
        2026-10-09, it leaves the string alone on PostgreSQL/Firebird/Snowflake,
        returns an empty string on MySQL 8.0, the untouched string on MySQL 26
        (the same server, two answers), NULL on MariaDB/Oracle and pads with
        spaces on ClickHouse.
    """
    if isinstance(length, int) and length < 0:
        raise ValueError(f"lpad(): length must be >= 0, got {length!r}")
    if isinstance(pad, str) and pad == "":
        raise ValueError(
            "lpad(): empty pad string is refused -- backends disagree on what it "
            "means (untouched string, empty string or NULL)"
        )
    target_expr = values.StringValue.of(dialect, expr)
    length_expr = values.IntegerValue.of(dialect, length)
    pad_expr = values.StringValue.of(dialect, " " if pad is None else pad)
    from ..advanced_functions import LpadFunction

    return LpadFunction(dialect, target_expr, length_expr, pad_expr)


def rpad(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], length: int, pad: Optional[str] = None
) -> "RpadFunction":
    """
    Creates a right-padding node.

    Usage rules:
    - To generate RPAD(column, length, pad), pass a Column object:
      rpad(dialect, Column(dialect, "column_name"), 10, " ")
    - To generate RPAD(?, length, pad), pass a literal value: rpad(dialect, "text", 10, " ")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to pad. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        length: Total length after padding.
        pad: Optional padding string, non-empty. Defaults to a single space.

    Returns:
        A :class:`~...expression.advanced_functions.RpadFunction` node,
        rendered through ``format_rpad_expression`` -- a spelling where the
        function exists and a one-branch emulation where it does not.

    Raises:
        ValueError: A negative *length*, or an empty *pad*.

    Contract:
        The mirror of :func:`lpad`: ``length >= 0``, a non-empty pad, an
        omitted pad spelled out as one space, and an empty pad refused.
    """
    if isinstance(length, int) and length < 0:
        raise ValueError(f"rpad(): length must be >= 0, got {length!r}")
    if isinstance(pad, str) and pad == "":
        raise ValueError(
            "rpad(): empty pad string is refused -- backends disagree on what it "
            "means (untouched string, empty string or NULL)"
        )
    target_expr = values.StringValue.of(dialect, expr)
    length_expr = values.IntegerValue.of(dialect, length)
    pad_expr = values.StringValue.of(dialect, " " if pad is None else pad)
    from ..advanced_functions import RpadFunction

    return RpadFunction(dialect, target_expr, length_expr, pad_expr)


def reverse(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "ReverseFunction":
    """
    Creates a REVERSE scalar function call.

    Usage rules:
    - To generate REVERSE(column), pass a Column object: reverse(dialect, Column(dialect, "column_name"))
    - To generate REVERSE(?), pass a literal value: reverse(dialect, "literal_value")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to reverse. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.

    Returns:
        A FunctionCall instance representing the REVERSE function
    """
    target_expr = values.StringValue.of(dialect, expr)
    return ReverseFunction(dialect, target_expr)


def strpos(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], substring: Union[str, "BaseExpression"]
) -> "PositionExpression":
    """
    Creates a STRPOS scalar function call (position of substring).

    Usage rules:
    - To generate STRPOS(column, substring), pass Column objects:
      strpos(dialect, Column(dialect, "column_name"), "substr")
    - To generate STRPOS(?, ?), pass literal values: strpos(dialect, "text", "substr")

    Args:
        dialect: The SQL dialect instance
        expr: The expression to search in. If a string is passed, it's treated as a literal value.
              If a BaseExpression is passed, it's used as-is.
        substring: Substring to find. If a string is passed, it's treated as a literal value.

    Returns:
        A FunctionCall instance representing the STRPOS function
    """
    target_expr = values.StringValue.of(dialect, expr)
    substr_expr = values.StringValue.of(dialect, substring)
    return PositionExpression(dialect, target_expr, substr_expr, spelling="STRPOS")


def concat_op(
    dialect: "SQLDialectBase", *exprs: Union[str, "BaseExpression"]
) -> "ConcatenationOperation":
    """Creates a string concatenation using the ``||`` operator.

    Deliberately not offered as a ``StringValueMixin`` method. ``||`` does not
    mean concatenation everywhere — in MySQL it is logical OR by default — so
    an operation reachable from a string column would silently produce a
    boolean on some backends. Use :func:`concat`, whose meaning is the same
    everywhere.

    Usage rules:
    - To generate column1 || column2, pass Column objects:
      concat_op(dialect, Column(dialect, "col1"), Column(dialect, "col2"))
    - To generate ? || ?, pass literal values: concat_op(dialect, "value1", "value2")
    - To generate complex concatenations: concat_op(dialect, col1, lit1, col2, lit2)

    Args:
        dialect: The SQL dialect instance
        *exprs: Variable number of expressions to concatenate using || operator

    Returns:
        A :class:`~...expression.operators.ConcatenationOperation` node, whose
        kind states the intent and whose rendering this dialect chooses.
    """
    if len(exprs) < 2:
        raise ValueError("Concatenation operation requires at least 2 expressions")

    # Convert all expressions to BaseExpression objects
    target_exprs = [e if isinstance(e, BaseExpression) else Literal(dialect, e) for e in exprs]

    # Start with the first two expressions
    result = ConcatenationOperation(dialect, target_exprs[0], target_exprs[1])

    # Chain additional expressions
    for i in range(2, len(target_exprs)):
        result = ConcatenationOperation(dialect, result, target_exprs[i])

    return result


def chr_(dialect: "SQLDialectBase", code: Union[int, "BaseExpression"]) -> "ChrFunction":
    """
    Creates a CHR function call.

    SQL:2003 standard function converting integer code to character.

    Usage rules:
    - To generate CHR(column): chr_(dialect, Column(dialect, "code"))
    - To generate CHR(65): chr_(dialect, 65)  # Returns 'A'

    Args:
        dialect: The SQL dialect instance
        code: The character code (integer)

    Returns:
        A FunctionCall instance representing the CHR function
    """
    code_expr = values.IntegerValue.of(dialect, code)
    return ChrFunction(dialect, code_expr)


def ascii(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "AsciiFunction":
    """
    Creates an ASCII function call.

    SQL:2003 standard function returning the ASCII code of the first character.

    Usage rules:
    - To generate ASCII(column): ascii(dialect, Column(dialect, "char"))
    - To generate ASCII('A'): ascii(dialect, "A")  # Returns 65

    Args:
        dialect: The SQL dialect instance
        expr: The string expression

    Returns:
        A FunctionCall instance representing the ASCII function
    """
    target_expr = values.StringValue.of(dialect, expr)
    return AsciiFunction(dialect, target_expr)


def octet_length(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "OctetLengthFunction":
    """
    Creates an OCTET_LENGTH function call.

    SQL:2003 standard function returning the byte length of a string.

    Usage rules:
    - To generate OCTET_LENGTH(column): octet_length(dialect, Column(dialect, "text"))
    - To generate OCTET_LENGTH('hello'): octet_length(dialect, "hello")

    Args:
        dialect: The SQL dialect instance
        expr: The string expression

    Returns:
        A FunctionCall instance representing the OCTET_LENGTH function
    """
    target_expr = values.StringValue.of(dialect, expr)
    return OctetLengthFunction(dialect, target_expr)


def bit_length(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"]) -> "BitLengthFunction":
    """
    Creates a BIT_LENGTH function call.

    SQL:2003 standard function returning the bit length of a string.

    Usage rules:
    - To generate BIT_LENGTH(column): bit_length(dialect, Column(dialect, "text"))
    - To generate BIT_LENGTH('hello'): bit_length(dialect, "hello")

    Args:
        dialect: The SQL dialect instance
        expr: The string expression

    Returns:
        A FunctionCall instance representing the BIT_LENGTH function
    """
    target_expr = values.StringValue.of(dialect, expr)
    return BitLengthFunction(dialect, target_expr)


def position(
    dialect: "SQLDialectBase", substring: Union[str, "BaseExpression"], expr: Union[str, "BaseExpression"]
) -> "PositionExpression":
    """
    Creates a POSITION function call.

    SQL:2003 standard function finding substring position (1-based).

    Usage rules:
    - To generate POSITION('abc' IN column): position(dialect, "abc", Column(dialect, "text"))
    - To generate POSITION('world' IN 'hello world'): position(dialect, "world", "hello world")

    Args:
        dialect: The SQL dialect instance
        substring: The substring to find
        expr: The string to search in

    Returns:
        A FunctionCall instance representing the POSITION function
    """
    substr_expr = values.StringValue.of(dialect, substring)
    target_expr = values.StringValue.of(dialect, expr)
    return PositionExpression(dialect, target_expr, substr_expr, spelling="POSITION")


def overlay(
    dialect: "SQLDialectBase",
    expr: Union[str, "BaseExpression"],
    replacement: Union[str, "BaseExpression"],
    start: int,
    length: Optional[int] = None,
) -> "OverlayExpression":
    """
    Creates an OVERLAY function call.

    SQL:2003 standard function replacing a substring.

    Usage rules:
    - To generate OVERLAY(column PLACING 'xxx' FROM 1): overlay(dialect, Column("text"), "xxx", 1)
    - To generate OVERLAY(column PLACING 'xx' FROM 1 FOR 2): overlay(dialect, Column("text"), "xx", 1, 2)

    Args:
        dialect: The SQL dialect instance
        expr: The source string
        replacement: The replacement string
        start: Starting position (1-based)
        length: Optional length to replace

    Returns:
        A FunctionCall instance representing the OVERLAY function
    """
    target_expr = values.StringValue.of(dialect, expr)
    replace_expr = values.StringValue.of(dialect, replacement)
    start_expr = values.IntegerValue.of(dialect, start)
    length_expr = values.IntegerValue.of(dialect, length) if length is not None else None
    return OverlayExpression(dialect, target_expr, replace_expr, start_expr, length_expr)


def translate(
    dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], from_chars: str, to_chars: str
) -> "TranslateFunction":
    """
    Creates a TRANSLATE function call.

    SQL:2003 standard function for character-by-character replacement.

    Usage rules:
    - To generate TRANSLATE(column, 'abc', 'xyz'): translate(dialect, Column("text"), "abc", "xyz")
    - To generate TRANSLATE('hello', 'el', 'ip'): translate(dialect, "hello", "el", "ip")

    Args:
        dialect: The SQL dialect instance
        expr: The source string
        from_chars: Characters to replace
        to_chars: Replacement characters

    Returns:
        A FunctionCall instance representing the TRANSLATE function
    """
    target_expr = values.StringValue.of(dialect, expr)
    from_expr = values.StringValue.of(dialect, from_chars)
    to_chars_expr = values.StringValue.of(dialect, to_chars)
    return TranslateFunction(dialect, target_expr, from_expr, to_chars_expr)


def repeat(dialect: "SQLDialectBase", expr: Union[str, "BaseExpression"], count: int) -> "RepeatFunction":
    """
    Creates a repetition node.

    Usage rules:
    - To generate REPEAT(column, 3): repeat(dialect, Column("text"), 3)
    - To generate REPEAT('ab', 5): repeat(dialect, "ab", 5)

    Args:
        dialect: The SQL dialect instance
        expr: The string to repeat
        count: Number of repetitions

    Returns:
        A :class:`~...expression.advanced_functions.RepeatFunction` node,
        rendered through ``format_repeat_expression`` -- a spelling where the
        function exists (PostgreSQL, MySQL, MariaDB, ClickHouse, BigQuery) and
        an emulation composed from ordinary nodes where it does not (SQLite,
        Oracle, Firebird).

    Contract:
        ``count >= 0`` repeats, and a negative count is the **empty string**
        rather than a refusal -- the native answer on PostgreSQL, MySQL,
        MariaDB and ClickHouse alike, measured 2026-10-09. SQL Server's
        ``REPLICATE`` answers NULL for a negative count and Oracle, Firebird
        and SQLite have no such function at all, so the meaning is settled
        once here instead of once per backend.
    """
    if isinstance(count, int) and count < 0:
        return values.StringValue(dialect, "")
    target_expr = values.StringValue.of(dialect, expr)
    count_expr = values.IntegerValue.of(dialect, count)
    from ..advanced_functions import RepeatFunction

    return RepeatFunction(dialect, target_expr, count_expr)


def space(dialect: "SQLDialectBase", count: int) -> "SpaceFunction":
    """
    Creates a SPACE function call.

    SQL standard function generating spaces.

    Usage rules:
    - To generate SPACE(5): space(dialect, 5)  # Returns '     '

    Args:
        dialect: The SQL dialect instance
        count: Number of spaces

    Returns:
        A FunctionCall instance representing the SPACE function
    """
    return SpaceFunction(dialect, values.IntegerValue.of(dialect, count))
