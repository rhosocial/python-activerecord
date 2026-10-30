# src/rhosocial/activerecord/backend/expression/functions/system.py
"""System information function nodes.

``CURRENT_USER`` / ``SESSION_USER`` / ``SYSTEM_USER`` are three names for what
the standard treats as closely related session facts, and it is not settled
which each backend answers with which -- SQL Server's ``SYSTEM_USER`` and
``SESSION_USER`` return different accounts, and ``SUSER_SNAME()`` is the
spelling that matches ``CURRENT_USER``. Each therefore gets its own class so a
backend can answer for one and not the others, and the spelling difference is
the formatter's business rather than a second node's reason to exist.

They are niladic, which is a **rendering** fact, not a structural one: the
standard writes these without parentheses and MySQL's ``NOW`` needs them while
its ``CURRENT_TIMESTAMP`` may omit them. So the class carries no arguments and
the dialect decides the parentheses.
"""

from typing import TYPE_CHECKING

from ..bases import SQLValue
from ..mixins import (
    AliasableMixin,
    ComparisonMixin,
    NotANumberMixin,
    StringPatternPredicateMixin,
    StringToIntegerMixin,
    StringValueMixin,
    TypeCastingMixin,
)

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


class CurrentUserFunction(
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``CURRENT_USER`` -- the account the session is authenticated as.

    Text, and the full string surface rather than a numeric one: this is
    something a caller compares against and searches, so ``.like()`` belongs on
    it and ``.sqrt()`` does not.
    """


    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_current_user_function"


class SessionUserFunction(
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``SESSION_USER`` -- the account the session was opened under."""


    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_session_user_function"


class SystemUserFunction(
    AliasableMixin,
    ComparisonMixin,
    StringToIntegerMixin,
    StringPatternPredicateMixin,
    StringValueMixin,
    TypeCastingMixin,
    NotANumberMixin,
    SQLValue,
):
    """``SYSTEM_USER`` -- the account the operating system recorded.

    Not the same account as :class:`SessionUserFunction` on every backend, and
    the class is here so that a backend which answers differently can say so
    rather than have the difference hidden behind one shared spelling.
    """


    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this expression."""
        return "format_system_user_function"


__all__ = [
    "CurrentUserFunction",
    "SessionUserFunction",
    "SystemUserFunction",
    "current_user",
    "session_user",
    "system_user",
]


def current_user(dialect: "SQLDialectBase") -> "CurrentUserFunction":
    """``CURRENT_USER`` -- the account the session is authenticated as.

    Args:
        dialect: The SQL dialect instance.

    Returns:
        A :class:`CurrentUserFunction`.
    """
    return CurrentUserFunction(dialect)


def session_user(dialect: "SQLDialectBase") -> "SessionUserFunction":
    """``SESSION_USER`` -- the account the session was opened under.

    Args:
        dialect: The SQL dialect instance.

    Returns:
        A :class:`SessionUserFunction`.
    """
    return SessionUserFunction(dialect)


def system_user(dialect: "SQLDialectBase") -> "SystemUserFunction":
    """``SYSTEM_USER`` -- the account the operating system recorded.

    Args:
        dialect: The SQL dialect instance.

    Returns:
        A :class:`SystemUserFunction`.
    """
    return SystemUserFunction(dialect)
