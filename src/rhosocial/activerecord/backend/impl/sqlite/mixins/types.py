# src/rhosocial/activerecord/backend/impl/sqlite/mixins/types.py
"""SQLite DataType formatting and parsing mixin."""

from __future__ import annotations

import re

from rhosocial.activerecord.backend.dialect.mixins.ddl_type import DDLTypeMixin
from rhosocial.activerecord.backend.dialect.protocols import DDLTypeSupport
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType as CoreBlobType,
    BooleanType,
    CharType,
    CustomType,
    DataType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    IntType,
    IntervalType,
    JsonBType,
    JsonType,
    SmallIntType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    TinyIntType,
    VarCharType,
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

    def format_data_type_sqlite_integer(self, data_type: SQLiteIntegerType) -> Tuple[str, tuple]:
        return "INTEGER", ()

    def format_data_type_sqlite_text(self, data_type: SQLiteTextType) -> Tuple[str, tuple]:
        length = getattr(data_type, "length", None)
        return (f"TEXT({length})" if length is not None else "TEXT"), ()

    def format_data_type_sqlite_real(self, data_type: SQLiteRealType) -> Tuple[str, tuple]:
        return "REAL", ()

    def format_data_type_sqlite_numeric(self, data_type: SQLiteNumericType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_sqlite_blob(self, data_type: SQLiteBlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    # --- Core types (pure names) rendered per SQLite affinity ---

    def format_data_type_integer(self, data_type: IntegerType) -> Tuple[str, tuple]:
        return "INTEGER", ()

    def format_data_type_text(self, data_type: TextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_real(self, data_type: RealType) -> Tuple[str, tuple]:
        return "REAL", ()

    def format_data_type_blob(self, data_type: CoreBlobType) -> Tuple[str, tuple]:
        return "BLOB", ()

    def format_data_type_bigint(self, data_type: BigIntType) -> Tuple[str, tuple]:
        return "INTEGER", ()

    def format_data_type_smallint(self, data_type: SmallIntType) -> Tuple[str, tuple]:
        return "INTEGER", ()

    def format_data_type_varchar(self, data_type: VarCharType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_char(self, data_type: CharType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_float(self, data_type: FloatType) -> Tuple[str, tuple]:
        return "REAL", ()

    def format_data_type_decimal(self, data_type: DecimalType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_boolean(self, data_type: BooleanType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_date(self, data_type: DateType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_datetime(self, data_type: DateTimeType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_timestamp(self, data_type: TimestampType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_time(self, data_type: TimeType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_tinyint(self, data_type: TinyIntType) -> Tuple[str, tuple]:
        return "INTEGER", ()

    def format_data_type_int(self, data_type: IntType) -> Tuple[str, tuple]:
        return "INTEGER", ()

    def format_data_type_double(self, data_type: DoubleType) -> Tuple[str, tuple]:
        return "REAL", ()

    def format_data_type_timetz(self, data_type: TimeTzType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_timestamptz(self, data_type: TimestampTzType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_interval(self, data_type: IntervalType) -> Tuple[str, tuple]:
        return "NUMERIC", ()

    def format_data_type_json(self, data_type: JsonType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_jsonb(self, data_type: JsonBType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_custom(self, data_type: CustomType) -> Tuple[str, tuple]:
        return data_type.raw, ()

    # ------------------------------------------------------------------
    # DDLTypeSupport — parsing
    # ------------------------------------------------------------------

    # SQLite type affinity groups for parsing
    _INTEGER_TYPES = re.compile(
        r"^(?:INT|INTEGER|BIGINT|SMALLINT|TINYINT|MEDIUMINT|INT2|INT8)\b",
        re.IGNORECASE,
    )
    _TEXT_TYPES = re.compile(
        r"^(?:TEXT|CHAR|VARCHAR|NVARCHAR|CHARACTER\s+VARYING|NCHAR|CLOB)\b",
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
        # Strip UNSIGNED prefix for broader matching (SQLite ignores unsigned)
        if stripped.upper().startswith("UNSIGNED "):
            stripped = stripped[len("UNSIGNED "):].strip()
        upper = stripped.upper()

        # INTEGER affinity
        if self._INTEGER_TYPES.match(upper):
            return SQLiteIntegerType(self)

        # TEXT affinity — try to extract length parameter
        if self._TEXT_TYPES.match(upper):
            length = None
            m = re.search(r"\((\d+)\)", stripped)
            if m:
                length = int(m.group(1))
            return SQLiteTextType(length, self)

        # REAL affinity
        if self._REAL_TYPES.match(upper):
            precision = None
            m = re.search(r"\((\d+)\)", stripped)
            if m:
                precision = int(m.group(1))
            return SQLiteRealType(precision, self)

        # NUMERIC affinity — try to extract precision/scale
        if self._NUMERIC_TYPES.match(upper):
            nums = re.findall(r"\d+", stripped)
            if len(nums) >= 2:
                return SQLiteNumericType(int(nums[0]), int(nums[1]), self)
            if len(nums) == 1:
                return SQLiteNumericType(int(nums[0]), self)
            return SQLiteNumericType(self)

        # BLOB affinity
        if self._BLOB_TYPES.match(upper):
            return SQLiteBlobType(self)

        return CustomType(stripped)
