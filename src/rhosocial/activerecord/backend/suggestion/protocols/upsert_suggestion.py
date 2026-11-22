"""UpsertSuggestionSupport -- backend's UPSERT syntax form suggestion."""
from typing import Protocol, runtime_checkable
from ..definitions import UpsertSyntaxSuggestion


@runtime_checkable
class UpsertSuggestionSupport(Protocol):
    def suggest_upsert_syntax_type(self) -> 'UpsertSyntaxSuggestion':
        """The UPSERT syntax form, e.g. ``"ON CONFLICT"``."""
        ...  # pragma: no cover
