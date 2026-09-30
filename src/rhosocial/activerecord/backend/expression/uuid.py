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

from typing import Any, Optional, TYPE_CHECKING

from .bases import SQLValueExpression
from .mixins import AliasableMixin, ComparisonMixin, TypeCastingMixin

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


class UUIDGenerationExpression(
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValueExpression,
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
        return "format_uuid_generation"


class UUIDConstantExpression(
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValueExpression,
):
    """The ``nil`` or ``max`` UUID constant.

    Args:
        which: ``"nil"`` (all zeroes) or ``"max"`` (all ones). Nothing else
            is accepted — a typo must not silently render a literal.
    """

    _KINDS = ("nil", "max")

    def __init__(
        self,
        dialect: "SQLDialectBase",
        which: str,
        *,
        alias: Optional[str] = None,
    ):
        super().__init__(dialect)
        normalised = str(which).lower()
        if normalised not in self._KINDS:
            raise ValueError(
                f"which must be one of {self._KINDS}, got {which!r}"
            )
        self.which = normalised
        self.alias = alias

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_uuid_constant"


class UUIDCastExpression(
    AliasableMixin,
    ComparisonMixin,
    TypeCastingMixin,
    SQLValueExpression,
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
        expression: Any,
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
    "UUIDCastExpression",
]
