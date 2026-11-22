# src/rhosocial/activerecord/backend/suggestion/protocols/data_adapter_suggestion.py
"""DataAdapterSuggestionSupport -- the third leg of the type triad.

A bare field's Python value reaches the driver through a value adapter. The
backend answers which adapter (and driver target type) it suggests for each
Python type; core defines only the interface and supplies no default table.

Unlike the two SQL-structure tables (``suggest_data_types`` /
``suggest_column_types``, keyed by all 24 framework-modelled types), this
table is sparse: types a driver binds natively without conversion (``str``,
``int``, ``float``, ``bytes``) are absent, and their absence means "pass
through untouched". A missing adapter for a type that needs one is an
omission the field's declared ``UseAdapter`` can cover.
"""
from typing import Dict, Tuple, Type, TYPE_CHECKING, runtime_checkable

from typing import Protocol
from ..definitions import DataAdapterSuggestion, ExtraDataAdapterSuggestion

if TYPE_CHECKING:  # pragma: no cover
    from ..type_adapter import SQLTypeAdapter


@runtime_checkable
class DataAdapterSuggestionSupport(Protocol):
    """Adapter suggestions for a backend, keyed by Python value type."""

    def suggest_data_adapters(self) -> 'DataAdapterSuggestion':
        """Suggested ``(adapter, driver type)`` per Python type needing conversion.

        Return a fresh dict. Keys are Python value types; a key absent from
        the table means the driver accepts that value natively.
        """
        ...  # pragma: no cover

    def suggest_extra_data_adapters(self) -> 'ExtraDataAdapterSuggestion':
        """Suggestions for this backend's own value types.

        Keys must be disjoint from the framework-modelled type list.
        """
        ...  # pragma: no cover
