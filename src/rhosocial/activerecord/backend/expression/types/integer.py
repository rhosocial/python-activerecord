# src/rhosocial/activerecord/backend/expression/types/integer.py
"""Integer SQL type family."""

from __future__ import annotations

from ._base import DataType


class TinyIntType(DataType):
    """TINYINT / INT1 (8-bit)."""

    name = "tinyint"


class SmallIntType(DataType):
    """SMALLINT / INT2 (16-bit)."""

    name = "smallint"


class IntType(DataType):
    """INT (shorthand for INTEGER, SQL standard)."""

    name = "int"

    @classmethod
    def synonyms(cls) -> set[str]:
        return {"IntegerType"}


class IntegerType(DataType):
    """INTEGER / INT4 (32-bit)."""

    name = "integer"

    @classmethod
    def synonyms(cls) -> set[str]:
        return {"IntType"}


class BigIntType(DataType):
    """BIGINT / INT8 (64-bit)."""

    name = "bigint"
