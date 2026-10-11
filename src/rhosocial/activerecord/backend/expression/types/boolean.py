# src/rhosocial/activerecord/backend/expression/types/boolean.py
"""BOOLEAN / BIT type."""

from __future__ import annotations

from ._base import DataType


class BooleanType(DataType):
    """BOOLEAN / BOOL — truth value."""

    name = "boolean"

    SPELLINGS = ("boolean", "bool")

    def __init__(self, dialect=None, *, spelling: str = "boolean"):
        super().__init__(dialect)
        self.spelling = spelling

