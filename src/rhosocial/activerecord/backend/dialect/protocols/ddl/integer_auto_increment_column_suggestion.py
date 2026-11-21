# src/rhosocial/activerecord/backend/dialect/protocols/ddl/integer_auto_increment_column_suggestion.py
"""IntegerAutoIncrementColumnSuggestionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`.

This is a **backend suggestion** capability: the dialect answers how an
integer auto-increment column is declared on its server. It answers only the
storage question -- the primary key is a separate model declaration and an
independent column constraint, so "auto-increment but not a primary key" is
expressible.
"""

from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....suggestion import IntegerAutoIncrementColumnSuggestion
    from ....expression.types._base import DataType


@runtime_checkable
class IntegerAutoIncrementColumnSuggestionSupport(Protocol):
    """A dialect's suggested DDL for an integer auto-increment column."""

    def suggest_integer_auto_increment_column(
        self, default_type: "DataType"
    ) -> "IntegerAutoIncrementColumnSuggestion":
        """Suggest the type + auto-increment mechanism for this dialect.

        ``default_type`` is the framework's integer type for the field; a
        dialect may return it as-is or substitute its own (e.g. PostgreSQL's
        SERIAL pseudo-type). The returned suggestion's ``auto_increment`` is
        an expression node, ``False`` (type already absorbs the attribute),
        or ``None`` (plain type, no auto-increment).
        """
        ...  # pragma: no cover
