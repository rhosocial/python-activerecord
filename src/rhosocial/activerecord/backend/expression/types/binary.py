# src/rhosocial/activerecord/backend/expression/types/binary.py
"""Binary / blob SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType


class BlobType(DataType):
    """BLOB / BYTEA / VARBINARY — binary large object."""

    name = "blob"


class BinaryType(DataType):
    """BINARY(n) — fixed-length byte string."""

    name = "binary"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.length = length

    def _type_params(self) -> tuple:
        return (self.length,)


class VarBinaryType(DataType):
    """VARBINARY(n) — variable-length byte string."""

    name = "varbinary"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.length = length

    def _type_params(self) -> tuple:
        return (self.length,)
