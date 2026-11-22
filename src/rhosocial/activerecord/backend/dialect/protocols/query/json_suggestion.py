"""JSONSuggestionSupport -- backend's JSON access operator suggestion."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class JSONSuggestionSupport(Protocol):
    def suggest_json_access_operator(self) -> str:
        """The JSON access operator, e.g. ``"->"``."""
        ...  # pragma: no cover
