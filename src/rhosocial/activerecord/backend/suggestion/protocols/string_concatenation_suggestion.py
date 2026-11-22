"""StringConcatenationSuggestionSupport -- concatenation form suggestion."""
from typing import Optional, Protocol, runtime_checkable
from ..definitions import ConcatenationFunctionSuggestion


@runtime_checkable
class StringConcatenationSuggestionSupport(Protocol):
    def suggest_concatenation_function(self) -> 'ConcatenationFunctionSuggestion':
        """Function name for concatenation, or None for the ``||`` operator."""
        ...  # pragma: no cover
