"""IntrospectionSuggestionSupport -- backend's supported introspection scopes."""
from typing import List, Protocol, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.introspection.types import IntrospectionScope


@runtime_checkable
class IntrospectionSuggestionSupport(Protocol):
    def suggest_introspection_scopes(self) -> List["IntrospectionScope"]:
        """The introspection scopes this backend offers."""
        ...  # pragma: no cover
