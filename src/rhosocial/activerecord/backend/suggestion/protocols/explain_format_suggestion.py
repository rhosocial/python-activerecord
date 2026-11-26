# src/rhosocial/activerecord/backend/suggestion/protocols/explain_format_suggestion.py
"""ExplainFormatSuggestionSupport -- the EXPLAIN format a backend recommends."""
from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..definitions import ExplainFormatSuggestion


@runtime_checkable
class ExplainFormatSuggestionSupport(Protocol):
    """A dialect's preferred EXPLAIN output format."""

    def suggest_explain_format(self) -> "ExplainFormatSuggestion":
        """Return the EXPLAIN format this dialect recommends."""
        ...  # pragma: no cover
