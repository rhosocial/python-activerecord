# src/rhosocial/activerecord/backend/expression/types/custom.py
"""CustomType fallback for unrecognised or dialect-specific types."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._base import DataType


class CustomType(DataType):
    """Fallback for unrecognised or backend-specific type strings.

    Preserves the raw SQL type string verbatim so round-trips stay
    lossless even when the framework does not know the type.
    """

    name = "custom"

    raw: str

    def __init__(self, dialect=None, raw: str = "",
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.raw = raw

    def _type_params(self) -> tuple:
        return (self.raw,)
