# src/rhosocial/activerecord/backend/expression/uuid.py
"""UUID value expressions.

Two things about UUIDs are worth separating, because they vary wildly across
databases while the request does not:

* **Generating** one. Eight backends spell this eight different ways
  (``gen_random_uuid()``, ``UUID()``, ``NEWID()``, ``SYS_GUID()``,
  ``UUID_STRING()``, ``GENERATE_UUID()``, ``generateUUIDv4()``, ``GEN_UUID()``),
  and one (SQLite) has no such function at all.
* **Storing** one. A handful have a native type; the rest emulate it
  (``BINARY(16)``, ``CHAR(16) CHARACTER SET OCTETS``, ``RAW(16)``, ``TEXT``).

This module covers the first. The second belongs to the DDL layer
(:mod:`...expression.types`) and is deliberately not referenced here: a
:class:`UUIDExpression` means "a UUID value", identically on every backend.

A dialect participates by implementing :class:`UUIDSupport`. A dialect with
no way to generate a UUID returns ``False`` from
``supports_uuid_generation()`` and rendering then raises
:class:`~...dialect.exceptions.UnsupportedFeatureError` — the caller falls
back to generating one in Python, which is what ``UUIDMixin`` does today.
"""

from enum import Enum
from typing import Optional, TYPE_CHECKING

from .bases import SQLValue
from .mixins import AliasableMixin, ComparisonMixin, TypeCastingMixin

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .bases import BaseExpression


class UuidConstantKind(str, Enum):
    """The two UUID constants that can be written as a literal.

    Nothing else is accepted, so this is the whole legal set: a typo must not
    silently render a constant that was not asked for.
    """

    NIL = "nil"
    MAX = "max"

    #: A member *is* the word it carries: str() and f-string interpolation must
    #: yield the value, not ``ClassName.MEMBER``, or the rendered SQL and the
    #: artifact would carry the Python spelling. ``(str, Enum)`` alone does not
    #: give that -- ``Enum.__str__`` wins -- so it is stated here once.
    __str__ = str.__str__


class UUIDGenerationExpression(
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValue,
):
    """A fresh UUID, rendered as a native zero-argument function call.

    Example:
        >>> from rhosocial.activerecord.backend.expression import UUIDGenerationExpression
        >>> expr = UUIDGenerationExpression(dialect)          # doctest: +SKIP
        >>> expr.to_sql()                                     # doctest: +SKIP
        ('gen_random_uuid()', ())

    The SQL differs per backend; the node does not. A dialect that cannot
    generate a UUID raises :class:`UnsupportedFeatureError` at render time
    rather than emitting another backend's function.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_uuid_generation_expression"


class UUIDConstantExpression(
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValue,
):
    """The ``nil`` or ``max`` UUID constant.

    Args:
        which: ``"nil"`` (all zeroes) or ``"max"`` (all ones). Nothing else
            is accepted — a typo must not silently render a literal.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        which: "UuidConstantKind",
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        # The raw value is carried, not interpreted: whether it names a
        # constant is a question for the formatter, which is the only place a
        # refusal (``TypeError``) belongs. Keeping it uncoerced is also what
        # lets the node round-trip: the artifact carries a string, and a
        # normalised enum here would come back as a plain string and compare
        # unequal by type.
        self.which = which
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_uuid_constant_expression"


class UUIDCastFunction(
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValue,
):
    """Convert a textual value to a UUID, rejecting malformed input.

    Portable SQL cannot express this: each backend has its own conversion
    (a cast, a try-cast, a dedicated function) and they differ in whether
    they raise on bad input. The node states the intent; the dialect decides
    the spelling.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        expression: "BaseExpression",
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.expression = expression
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_uuid_cast"


__all__ = [
    "UUIDGenerationExpression",
    "UUIDConstantExpression",
    "UUIDCastFunction",
]
