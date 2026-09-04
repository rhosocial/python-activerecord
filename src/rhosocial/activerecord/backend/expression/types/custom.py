# src/rhosocial/activerecord/backend/expression/types/custom.py
"""CustomType fallback for unrecognised or dialect-specific types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType


class CustomType(DataType):
    """Fallback for unrecognised or backend-specific type strings.

    Preserves the raw SQL type string verbatim so round-trips stay
    lossless even when the framework does not know the type.

    .. warning::

       ``raw`` is emitted **verbatim** into generated DDL — it bypasses all
       validation and escaping. Only pass trusted, hard-coded type strings
       (e.g. ``CustomType("GEOMETRY")``). Never interpolate external input,
       configuration values or database-introspection output into ``raw``:
       that is a SQL injection vector.
    """

    raw: str

    def __init__(self, dialect=None, *, raw: str):
        super().__init__(dialect)
        self.raw = raw

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.raw == other.raw

    def __hash__(self) -> int:
        return hash((type(self), self.raw))
