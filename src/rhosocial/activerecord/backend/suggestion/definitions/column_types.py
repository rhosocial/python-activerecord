# src/rhosocial/activerecord/backend/suggestion/definitions/column_types.py
"""Value definitions for the column-type suggestion methods."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Type, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.column_types.column_types import ColumnBase


@dataclass(frozen=True)
class ColumnTypeSuggestion:
    """The column class suggested for each framework-modelled Python type."""

    table: Dict[Any, Optional[Type["ColumnBase"]]]


@dataclass(frozen=True)
class ExtraColumnTypeSuggestion:
    """Column classes for this backend's own value types."""

    table: Dict[Any, Type["ColumnBase"]]


__all__ = ["ColumnTypeSuggestion", "ExtraColumnTypeSuggestion"]
