"""JSONSuggestionSupport -- backend's JSON access operator suggestion."""
from typing import Protocol, runtime_checkable
from ..definitions import JSONAccessOperatorSuggestion


@runtime_checkable
class JSONSuggestionSupport(Protocol):
    def suggest_json_access_operator(self) -> 'JSONAccessOperatorSuggestion':
        """The JSON access operator, e.g. ``"->"``."""
        ...  # pragma: no cover
