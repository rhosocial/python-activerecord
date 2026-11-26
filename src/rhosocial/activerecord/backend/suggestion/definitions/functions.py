# src/rhosocial/activerecord/backend/suggestion/definitions/functions.py
"""Value definition for the SQL-function catalogue suggestion."""
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class FunctionSuggestion:
    """The SQL functions this dialect renders.

    ``functions`` maps a function name to the backend's own availability value.
    Most backends answer with a bool; a backend that tracks version windows may
    answer with a richer record. The shape is deliberately backend-owned: this
    is a catalogue, not a capability flag, so it must not be flattened into a
    ``supports_*`` answer.
    """

    functions: Mapping[str, Any]
    state: str = "actions"
