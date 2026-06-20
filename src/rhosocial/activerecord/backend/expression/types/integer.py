# src/rhosocial/activerecord/backend/expression/types/integer.py
"""Integer SQL type family."""

from __future__ import annotations

from ._base import DataType


class TinyIntType(DataType):
    """TINYINT / INT1 (8-bit)."""


class SmallIntType(DataType):
    """SMALLINT / INT2 (16-bit)."""


class IntType(DataType):
    """INT (shorthand for INTEGER, SQL standard)."""


class IntegerType(DataType):
    """INTEGER / INT4 (32-bit)."""


class BigIntType(DataType):
    """BIGINT / INT8 (64-bit)."""
