# src/rhosocial/activerecord/backend/impl/sqlite/introspection/type_parser.py
"""SQLite's type-spelling parser (read direction, introspection-only).

Temporary, backend-local helper: parsing a server-reported type spelling back
into a DataType is not an expression-construction concern and is not yet
formalised in the protocol layer. Lives under SQLite introspection, used only
when reading back a column's declared type; NOT a dialect protocol member.
"""

from typing import Optional

from ....expression.types import CustomType, DataType
from ....textscan import integer_runs, leading_word, parenthesised
from ..expression.types import (
    SQLiteBlobType, SQLiteIntegerType, SQLiteNumericType, SQLiteRealType, SQLiteTextType,
)


def _leads_with(text: str, spellings: frozenset) -> bool:
    """Whether the first whole word of *text* is one of *spellings*.

    A word boundary is what keeps ``CHAR`` from claiming ``CHARACTER`` and
    ``TIME`` from claiming ``TIMESTAMP``; reading the leading word and
    comparing it whole gives the same answer without a pattern.
    """
    return leading_word(text) in spellings


def _single_precision(text: str) -> Optional[int]:
    """The number in the first parenthesis that holds nothing but digits."""
    inner = parenthesised(text)
    if inner is not None and inner.isdecimal():
        return int(inner)
    return None


class SQLiteTypeParser:
    """Parse a raw SQLite type spelling into a DataType, bound to a dialect."""

    _INTEGER_TYPES = frozenset({
        "INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "MEDIUMINT",
        "INT1", "INT2", "INT4", "INT8",
    })
    _TEXT_TYPES = frozenset({
        "TEXT", "CHAR", "CHARACTER", "CHARACTER VARYING",
        "VARCHAR", "NVARCHAR", "NCHAR", "CLOB",
    })
    _REAL_TYPES = frozenset({"REAL", "FLOAT", "DOUBLE"})
    _NUMERIC_TYPES = frozenset({
        "NUMERIC", "DECIMAL", "DEC", "BOOLEAN", "BOOL", "DATE", "DATETIME",
        "TIMESTAMP", "TIME",
    })
    _BLOB_TYPES = frozenset({"BLOB", "BYTEA", "BINARY", "VARBINARY"})

    def __init__(self, dialect):
        self.dialect = dialect

    def parse(self, raw: str) -> DataType:
        stripped = raw.strip()
        if stripped.upper().startswith("UNSIGNED "):
            stripped = stripped[len("UNSIGNED "):].strip()
        upper = stripped.upper()
        if _leads_with(upper, self._INTEGER_TYPES):
            return SQLiteIntegerType(self.dialect)
        if _leads_with(upper, self._TEXT_TYPES):
            length = _single_precision(stripped)
            return SQLiteTextType(self.dialect, length)
        if _leads_with(upper, self._REAL_TYPES):
            precision = _single_precision(stripped)
            return SQLiteRealType(self.dialect, precision)
        if _leads_with(upper, self._NUMERIC_TYPES):
            nums = integer_runs(stripped)
            if len(nums) >= 2: return SQLiteNumericType(self.dialect, int(nums[0]), int(nums[1]))
            if len(nums) == 1: return SQLiteNumericType(self.dialect, int(nums[0]))
            return SQLiteNumericType(self.dialect)
        if _leads_with(upper, self._BLOB_TYPES):
            return SQLiteBlobType(self.dialect)
        return CustomType(self.dialect, raw=stripped)
