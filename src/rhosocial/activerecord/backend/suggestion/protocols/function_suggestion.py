# src/rhosocial/activerecord/backend/suggestion/protocols/function_suggestion.py
"""FunctionSuggestionSupport -- the SQL function catalogue a backend renders."""
from typing import Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..definitions import FunctionSuggestion


@runtime_checkable
class FunctionSuggestionSupport(Protocol):
    """A dialect's SQL function catalogue.

    This answers "which functions can I call here, and which are available",
    which is a value, not a capability flag -- hence a suggestion rather than
    a ``supports_*`` switch.
    """

    def suggest_functions(self) -> "FunctionSuggestion":
        """Return the function catalogue this dialect renders."""
        ...  # pragma: no cover
