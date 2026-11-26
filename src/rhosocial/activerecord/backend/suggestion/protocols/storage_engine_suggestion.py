# src/rhosocial/activerecord/backend/suggestion/protocols/storage_engine_suggestion.py
"""StorageEngineSuggestionSupport -- the storage engine a backend recommends."""
from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..definitions import StorageEngineSuggestion


@runtime_checkable
class StorageEngineSuggestionSupport(Protocol):
    """A dialect's preferred storage engine for an ordinary table."""

    def suggest_storage_engine(self) -> "StorageEngineSuggestion":
        """Return the storage engine this dialect recommends."""
        ...  # pragma: no cover
