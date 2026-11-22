# src/rhosocial/activerecord/backend/suggestion/definitions/data_types.py
"""Value definitions for the DDL data-type suggestion methods."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.types._base import DataType


@dataclass(frozen=True)
class DataTypeSuggestion:
    """The storage declaration suggested for each framework-modelled Python type."""

    table: Dict[type, Optional["DataType"]]


@dataclass(frozen=True)
class ExtraDataTypeSuggestion:
    """Storage declarations for this backend's own value classes."""

    table: Dict[type, "DataType"]


@dataclass(frozen=True)
class SubstituteTypeSuggestion:
    """Concept-name -> class this backend stores when it cannot render the concept."""

    mapping: Dict[str, type]


@dataclass(frozen=True)
class SubstituteAdviceSuggestion:
    """Extra caveat for a substituted concept (empty when lossless)."""

    advice: str


__all__ = [
    "DataTypeSuggestion",
    "ExtraDataTypeSuggestion",
    "SubstituteTypeSuggestion",
    "SubstituteAdviceSuggestion",
]
