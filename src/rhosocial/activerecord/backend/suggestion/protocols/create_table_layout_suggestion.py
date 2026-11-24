# src/rhosocial/activerecord/backend/suggestion/protocols/create_table_layout_suggestion.py
"""CreateTableLayoutSuggestionSupport -- how a backend lays out CREATE TABLE.

A backend answer is a value (frozen dataclass), pure and zero-I/O: it reports
whether indexes and comments can be inlined into a single CREATE TABLE
statement or must be emitted as separate statements. The caller owns the plan.
"""
from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..definitions import CreateTableLayoutSuggestion


@runtime_checkable
class CreateTableLayoutSuggestionSupport(Protocol):
    """A dialect's preferred CREATE TABLE statement layout."""

    def suggest_create_table_layout(self) -> "CreateTableLayoutSuggestion":
        """Return the inline/split layout this backend can render."""
        ...  # pragma: no cover
