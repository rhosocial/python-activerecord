# src/rhosocial/activerecord/backend/suggestion/protocols/data_type_suggestion.py
"""DataTypeSuggestionSupport -- the DDL-side type suggestion (second layer).

The core declares only the shape of the answer: a table keyed by the 24
framework-modelled Python types (``FRAMEWORK_PYTHON_TYPES``), each mapped to
the ``DataType`` a bare field should be declared with. Every key must be
answered -- the framework promises a bare field always has a declaration.

Each backend supplies its own 24-key table; the core supplies no implementation.
The suggestion is a value (a ``DataType``), not SQL -- formatting stays in the
capability-side ``DataTypeSupport``.
"""
from typing import Dict, Optional, Protocol, TYPE_CHECKING, runtime_checkable
from ..definitions import DataTypeSuggestion, ExtraDataTypeSuggestion, SubstituteAdviceSuggestion, SubstituteTypeSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.expression.types._base import DataType


@runtime_checkable
class DataTypeSuggestionSupport(Protocol):
    """The storage-type suggestion table for the 24 framework types."""

    def suggest_data_types(self) -> 'DataTypeSuggestion':
        """The declaration suggested for each framework-modelled type.

        Keys must cover ``FRAMEWORK_PYTHON_TYPES`` (24 entries); every key must
        be answered. Values are ``DataType`` instances carrying the parameters
        a column needs. Return a fresh dict; values are read-only templates.
        """
        ...  # pragma: no cover


    def suggest_substitute_types(self) -> 'SubstituteTypeSuggestion':
        """Concept-name -> class this backend stores when it cannot render the concept."""
        ...  # pragma: no cover

    def suggest_substitute_advice(self, name: str) -> 'SubstituteAdviceSuggestion':
        """Extra caveat for a substituted concept (empty when lossless)."""
        ...  # pragma: no cover

    def suggest_extra_data_types(self) -> 'ExtraDataTypeSuggestion':
        """Suggestions for this backend's own Python types."""
        ...  # pragma: no cover
