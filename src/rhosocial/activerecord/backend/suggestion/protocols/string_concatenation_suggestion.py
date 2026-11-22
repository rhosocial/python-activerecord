"""StringConcatenationSuggestionSupport -- concatenation form suggestion."""
from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class StringConcatenationSuggestionSupport(Protocol):
    def suggest_concatenation_function(self) -> Optional[str]:
        """Function name for concatenation, or None for the ``||`` operator."""
        ...  # pragma: no cover
