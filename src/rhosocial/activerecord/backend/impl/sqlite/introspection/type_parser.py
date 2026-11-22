# src/rhosocial/activerecord/backend/impl/sqlite/introspection/type_parser.py
"""SQLite's type-spelling parser (read direction, introspection-only).

Temporary, backend-local helper: parsing a server-reported type spelling back
into a DataType is not an expression-construction concern and is not yet
formalised in the protocol layer. Lives under SQLite introspection, used only
when reading back a column's declared type; NOT a dialect protocol member.
"""
import re

from ....expression.types import CustomType, DataType
from ..expression.types import (
    SQLiteBlobType, SQLiteIntegerType, SQLiteNumericType, SQLiteRealType, SQLiteTextType,
)


class SQLiteTypeParser:
    """Parse a raw SQLite type spelling into a DataType, bound to a dialect."""

    _INTEGER_TYPES = re.compile(
        r"^(?:INT|INTEGER|BIGINT|SMALLINT|TINYINT|MEDIUMINT|INT1|INT2|INT4|INT8)\b", re.IGNORECASE)
    _TEXT_TYPES = re.compile(
        r"^(?:TEXT|CHAR|CHARACTER|CHARACTER\s+VARYING|VARCHAR|NVARCHAR|NCHAR|CLOB)\b", re.IGNORECASE)
    _REAL_TYPES = re.compile(r"^(?:REAL|FLOAT|DOUBLE)\b", re.IGNORECASE)
    _NUMERIC_TYPES = re.compile(
        r"^(?:NUMERIC|DECIMAL|DEC|BOOLEAN|BOOL|DATE|DATETIME|TIMESTAMP|TIME)\b", re.IGNORECASE)
    _BLOB_TYPES = re.compile(r"^(?:BLOB|BYTEA|BINARY|VARBINARY)\b", re.IGNORECASE)

    def __init__(self, dialect):
        self.dialect = dialect

    def parse(self, raw: str) -> DataType:
        stripped = raw.strip()
        if stripped.upper().startswith("UNSIGNED "):
            stripped = stripped[len("UNSIGNED "):].strip()
        upper = stripped.upper()
        if self._INTEGER_TYPES.match(upper):
            return SQLiteIntegerType(self.dialect)
        if self._TEXT_TYPES.match(upper):
            m = re.search(r"\((\d+)\)", stripped)
            return SQLiteTextType(self.dialect, int(m.group(1)) if m else None)
        if self._REAL_TYPES.match(upper):
            m = re.search(r"\((\d+)\)", stripped)
            return SQLiteRealType(self.dialect, int(m.group(1)) if m else None)
        if self._NUMERIC_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            if len(nums) >= 2: return SQLiteNumericType(self.dialect, int(nums[0]), int(nums[1]))
            if len(nums) == 1: return SQLiteNumericType(self.dialect, int(nums[0]))
            return SQLiteNumericType(self.dialect)
        if self._BLOB_TYPES.match(upper):
            return SQLiteBlobType(self.dialect)
        return CustomType(self.dialect, raw=stripped)
