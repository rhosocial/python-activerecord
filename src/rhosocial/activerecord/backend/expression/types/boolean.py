# src/rhosocial/activerecord/backend/expression/types/boolean.py
"""BOOLEAN / BIT type."""

from __future__ import annotations

from ._base import DataType


class BooleanType(DataType):
    """BOOLEAN / BOOL — truth value."""
