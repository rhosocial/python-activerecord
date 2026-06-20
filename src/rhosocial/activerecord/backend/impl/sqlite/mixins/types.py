# src/rhosocial/activerecord/backend/impl/sqlite/mixins/types.py
"""SQLite DataType formatting and parsing mixin."""

from __future__ import annotations

import re

from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin
from rhosocial.activerecord.backend.dialect.protocols import DDLTypeSupport
from rhosocial.activerecord.backend.expression.types import (
    CustomType,
    DataType,
)

from ..expression.types import (
    SQLiteBlobType,
    SQLiteIntegerType,
    SQLiteNumericType,
    SQLiteRealType,
    SQLiteTextType,
)


class SQLiteTypeSupportMixin(DDLTypeMixin, DDLTypeSupport):
    """SQLite DataType formatting and parsing.

    Implements ``DDLTypeSupport`` so the dialect can render ``DataType``
    expressions to SQL strings and parse raw SQL type strings back into
    ``DataType`` instances.

    SQLite has a simple type system based on five type affinities (TEXT,
    NUMERIC, INTEGER, REAL, BLOB).  This mixin maps the standard SQL types
    to their SQLite representation.
    """

    # ------------------------------------------------------------------
    # DDLTypeSupport — formatting
    # ------------------------------------------------------------------

    @DDLTypeMixin.handles(SQLiteIntegerType)
    def format_data_type_integer(self, data_type: SQLiteIntegerType) -> str:
        return "INTEGER"

    @DDLTypeMixin.handles(SQLiteTextType)
    def format_data_type_text(self, data_type: SQLiteTextType) -> str:
        return f"TEXT({data_type.length})" if data_type.length is not None else "TEXT"

    @DDLTypeMixin.handles(SQLiteRealType)
    def format_data_type_real(self, data_type: SQLiteRealType) -> str:
        return "REAL"

    @DDLTypeMixin.handles(SQLiteNumericType)
    def format_data_type_numeric(self, data_type: SQLiteNumericType) -> str:
        return "NUMERIC"

    @DDLTypeMixin.handles(SQLiteBlobType)
    def format_data_type_blob(self, data_type: SQLiteBlobType) -> str:
        return "BLOB"

    # ------------------------------------------------------------------
    # DDLTypeSupport — parsing
    # ------------------------------------------------------------------

    # SQLite type affinity groups for parsing
    _INTEGER_TYPES = re.compile(
        r"^(?:INT|INTEGER|BIGINT|SMALLINT|TINYINT|MEDIUMINT)\b",
        re.IGNORECASE,
    )
    _TEXT_TYPES = re.compile(
        r"^(?:TEXT|CHAR|VARCHAR|CHARACTER\s+VARYING|CLOB)\b",
        re.IGNORECASE,
    )
    _REAL_TYPES = re.compile(
        r"^(?:REAL|FLOAT|DOUBLE)\b",
        re.IGNORECASE,
    )
    _NUMERIC_TYPES = re.compile(
        r"^(?:NUMERIC|DECIMAL|BOOLEAN|DATE|DATETIME|TIMESTAMP|TIME)\b",
        re.IGNORECASE,
    )
    _BLOB_TYPES = re.compile(
        r"^(?:BLOB|BYTEA|BINARY|VARBINARY)\b",
        re.IGNORECASE,
    )

    def parse_type(self, raw: str) -> DataType:
        """Parse a raw SQL type string according to SQLite type affinity.

        SQLite uses five type affinities:
        - INTEGER: INT, INTEGER, BIGINT, SMALLINT, TINYINT, etc.
        - TEXT: TEXT, CHAR, VARCHAR, CLOB, etc.
        - REAL: REAL, FLOAT, DOUBLE, etc.
        - NUMERIC: NUMERIC, DECIMAL, BOOLEAN, DATE, DATETIME, etc.
        - BLOB: BLOB, BYTEA, etc.

        Returns the corresponding ``SQLite*Type`` for the matched affinity.
        Unknown type strings return ``CustomType``.
        """
        from ..expression.types import (
            SQLiteBlobType,
            SQLiteIntegerType,
            SQLiteNumericType,
            SQLiteRealType,
            SQLiteTextType,
        )

        stripped = raw.strip()
        upper = stripped.upper()

        # INTEGER affinity
        if self._INTEGER_TYPES.match(upper):
            return SQLiteIntegerType()

        # TEXT affinity — try to extract length parameter
        if self._TEXT_TYPES.match(upper):
            length = None
            m = re.search(r"\((\d+)\)", stripped)
            if m:
                length = int(m.group(1))
            return SQLiteTextType(length)

        # REAL affinity
        if self._REAL_TYPES.match(upper):
            precision = None
            m = re.search(r"\((\d+)\)", stripped)
            if m:
                precision = int(m.group(1))
            return SQLiteRealType(precision)

        # NUMERIC affinity — try to extract precision/scale
        if self._NUMERIC_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            if len(nums) >= 2:
                return SQLiteNumericType(int(nums[0]), int(nums[1]))
            if len(nums) == 1:
                return SQLiteNumericType(int(nums[0]))
            return SQLiteNumericType()

        # BLOB affinity
        if self._BLOB_TYPES.match(upper):
            return SQLiteBlobType()

        return CustomType(stripped)
