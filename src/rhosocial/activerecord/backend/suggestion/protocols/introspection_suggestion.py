"""IntrospectionSuggestionSupport -- backend's supported introspection scopes."""
from typing import List, Protocol, TYPE_CHECKING, runtime_checkable
from ..definitions import IntrospectionScopeSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.introspection.types import IntrospectionScope


@runtime_checkable
class IntrospectionSuggestionSupport(Protocol):
    def suggest_introspection_scopes(self) -> 'IntrospectionScopeSuggestion':
        """The introspection scopes this backend offers."""
        ...  # pragma: no cover
