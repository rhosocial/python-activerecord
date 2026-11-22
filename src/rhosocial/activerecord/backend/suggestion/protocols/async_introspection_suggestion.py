"""AsyncIntrospectionSuggestionSupport -- async mirror of the scopes suggestion."""
from typing import List, Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.introspection.types import IntrospectionScope


@runtime_checkable
class AsyncIntrospectionSuggestionSupport(Protocol):
    def suggest_introspection_scopes(self) -> List["IntrospectionScope"]:
        """The introspection scopes this backend offers (async)."""
        ...  # pragma: no cover
