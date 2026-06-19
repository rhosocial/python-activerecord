# src/rhosocial/activerecord/backend/expression/types/integer.py
"""Integer SQL type family."""

from __future__ import annotations

from typing import Set

from ._base import DataType


class TinyIntType(DataType):
    """TINYINT / INT1 (8-bit)."""

    def _default_sql(self) -> str:
        return "TINYINT"


class SmallIntType(DataType):
    """SMALLINT / INT2 (16-bit)."""

    def _default_sql(self) -> str:
        return "SMALLINT"


class IntType(DataType):
    """INT (shorthand for INTEGER, SQL standard)."""
    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'IntegerType'}

    def _default_sql(self) -> str:
        return "INT"


class IntegerType(DataType):
    """INTEGER / INT4 (32-bit)."""
    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'IntType'}

    def _default_sql(self) -> str:
        return "INTEGER"


class BigIntType(DataType):
    """BIGINT / INT8 (64-bit)."""

    def _default_sql(self) -> str:
        return "BIGINT"
