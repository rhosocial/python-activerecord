# src/rhosocial/activerecord/backend/suggestion/definitions/data_adapters.py
"""Value definitions for the data-adapter suggestion methods."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple, Type, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...type_adapter import SQLTypeAdapter


@dataclass(frozen=True)
class DataAdapterSuggestion:
    """Suggested ``(adapter, driver type)`` per Python type needing conversion."""

    table: Dict[Type, Tuple["SQLTypeAdapter", Type]]


@dataclass(frozen=True)
class ExtraDataAdapterSuggestion:
    """Adapter suggestions for this backend's own value types."""

    table: Dict[Type, Tuple["SQLTypeAdapter", Type]]


__all__ = ["DataAdapterSuggestion", "ExtraDataAdapterSuggestion"]
