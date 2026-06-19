# src/rhosocial/activerecord/backend/expression/types/custom.py
"""CustomType fallback for unrecognised or dialect-specific types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType


class CustomType(DataType):
    """Fallback for unrecognised or backend-specific type strings.

    Preserves the raw SQL type string verbatim so round-trips stay
    lossless even when the framework does not know the type.
    """

    raw: str

    def __init__(self, raw: str, dialect=None):
        super().__init__(dialect)
        self.raw = raw

    def _type_params(self) -> tuple:
        return (self.raw,)

    def _default_sql(self) -> str:
        return self.raw
