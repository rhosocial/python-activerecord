# src/rhosocial/activerecord/backend/suggestion/protocols/text_encoding_suggestion.py
"""TextEncodingSuggestionSupport -- the charset and collation a backend recommends."""
from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..definitions import TextEncodingSuggestion


@runtime_checkable
class TextEncodingSuggestionSupport(Protocol):
    """A dialect's preferred character set and collation."""

    def suggest_text_encoding(self) -> "TextEncodingSuggestion":
        """Return the charset/collation this dialect recommends."""
        ...  # pragma: no cover
