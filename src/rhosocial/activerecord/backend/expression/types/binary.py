# src/rhosocial/activerecord/backend/expression/types/binary.py
"""Binary / blob SQL types."""

from __future__ import annotations

from typing import Optional

from ._base import DataType


class BlobType(DataType):
    """BLOB / BYTEA — binary large object.

    ``BYTEA`` is PostgreSQL's name for the same unbounded byte storage.
    """

    name = "blob"

    SPELLINGS = ("blob", "bytea")

    def __init__(self, dialect=None, *, spelling: str = "blob"):
        super().__init__(dialect)
        self.spelling = spelling


class BinaryType(DataType):
    """BINARY(n) — fixed-length byte string."""

    name = "binary"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.length = length

    PARAMETERS = ("length",)

class VarBinaryType(DataType):
    """VARBINARY(n) — variable-length byte string."""

    name = "varbinary"

    length: Optional[int] = None

    def __init__(self, dialect=None, length: Optional[int] = None,
                 ):
        super().__init__(dialect)
        self.length = length

    PARAMETERS = ("length",)
