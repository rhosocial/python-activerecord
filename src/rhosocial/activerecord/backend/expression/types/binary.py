# src/rhosocial/activerecord/backend/expression/types/binary.py
"""Binary / blob SQL types."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ._base import DataType


class BlobType(DataType):
    """BLOB / BYTEA / VARBINARY — binary large object."""

    name = "blob"


class BinaryType(DataType):
    """BINARY(n) — fixed-length byte string."""

    name = "binary"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.length = length

    def _type_params(self) -> tuple:
        return (self.length,)


class VarBinaryType(DataType):
    """VARBINARY(n) — variable-length byte string."""

    name = "varbinary"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 dialect_options: Optional[Dict[str, Any]] = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.length = length

    def _type_params(self) -> tuple:
        return (self.length,)
