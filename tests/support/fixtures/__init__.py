# tests/support/fixtures/__init__.py
"""Shared L1 fixture definitions for this repository's tests."""

from .sqlite import (
    TABLE_DEFINITIONS,
    TRIGGER_DEFINITION,
    VIEW_DEFINITION,
    IndexesDefinition,
    TriggerDefinition,
    ViewDefinition,
)

__all__ = [
    "TABLE_DEFINITIONS",
    "TRIGGER_DEFINITION",
    "VIEW_DEFINITION",
    "IndexesDefinition",
    "TriggerDefinition",
    "ViewDefinition",
]
