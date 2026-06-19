# src/rhosocial/activerecord/backend/impl/sqlite/mixins/types.py
"""SQLite DataType formatting and parsing mixin."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Tuple, Type

from rhosocial.activerecord.backend.dialect.protocols import (
    TypeFormattingSupport,
    TypeParsingSupport,
)
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType,
    BooleanType,
    CharType,
    DataType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    IntervalType,
    JsonType,
    RealType,
    SmallIntType,
    TextType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    TinyIntType,
    VarCharType,
)

if TYPE_CHECKING:
    from ..expression.types import SQLiteIntegerType, SQLiteTextType


class SQLiteTypeSupportMixin(TypeFormattingSupport, TypeParsingSupport):
    """SQLite DataType formatting and parsing.

    Implements both ``TypeFormattingSupport`` and ``TypeParsingSupport`` so
    the dialect can render ``DataType`` expressions to SQL strings and parse
    raw SQL type strings back into ``DataType`` instances.

    SQLite has a simple type system based on five type affinities (TEXT,
    NUMERIC, INTEGER, REAL, BLOB).  This mixin maps the standard SQL types
    to their SQLite representation.
    """

    # ------------------------------------------------------------------
    # TypeFormattingSupport
    # ------------------------------------------------------------------

    def render_type(self, data_type: DataType) -> str:
        for type_class, suffix in self.supports_data_types():
            if isinstance(data_type, type_class):
                formatter = getattr(self, f"format_data_type_{suffix}", None)
                if formatter is not None:
                    return formatter(data_type)
        return data_type._default_sql()

    def supports_data_types(self) -> List[Tuple[Type[DataType], str]]:
        return [
            # SQLite-specific types
            # (SQLiteIntegerType, "sqliteintegertype"),
            # (SQLiteTextType, "sqlitetexttype"),
            # Integer family
            (TinyIntType, "tiny_int"),
            (SmallIntType, "small_int"),
            (IntegerType, "integer"),
            (BigIntType, "big_int"),
            # Numeric family
            (FloatType, "float"),
            (RealType, "real"),
            (DoubleType, "double"),
            (DecimalType, "decimal"),
            # String family
            (CharType, "char"),
            (VarCharType, "var_char"),
            (TextType, "text"),
            # Boolean
            (BooleanType, "boolean"),
            # Binary
            (BlobType, "blob"),
            # Date/time
            (DateType, "date"),
            (TimeType, "time"),
            (TimeTzType, "time_tz"),
            (DateTimeType, "date_time"),
            (TimestampType, "timestamp"),
            (TimestampTzType, "timestamp_tz"),
            (IntervalType, "interval"),
            # JSON
            (JsonType, "json"),
        ]

    def format_data_type_tiny_int(self, data_type: TinyIntType) -> str:
        return data_type._default_sql()

    def format_data_type_small_int(self, data_type: SmallIntType) -> str:
        return data_type._default_sql()

    def format_data_type_integer(self, data_type: IntegerType) -> str:
        return data_type._default_sql()

    def format_data_type_big_int(self, data_type: BigIntType) -> str:
        return data_type._default_sql()

    def format_data_type_float(self, data_type: FloatType) -> str:
        return "REAL"

    def format_data_type_real(self, data_type: RealType) -> str:
        return "REAL"

    def format_data_type_double(self, data_type: DoubleType) -> str:
        return data_type._default_sql()

    def format_data_type_decimal(self, data_type: DecimalType) -> str:
        return data_type._default_sql()

    def format_data_type_char(self, data_type: CharType) -> str:
        return data_type._default_sql()

    def format_data_type_var_char(self, data_type: VarCharType) -> str:
        return data_type._default_sql()

    def format_data_type_text(self, data_type: TextType) -> str:
        return data_type._default_sql()

    def format_data_type_boolean(self, data_type: BooleanType) -> str:
        return data_type._default_sql()

    def format_data_type_blob(self, data_type: BlobType) -> str:
        return data_type._default_sql()

    def format_data_type_date(self, data_type: DateType) -> str:
        return data_type._default_sql()

    def format_data_type_time(self, data_type: TimeType) -> str:
        return data_type._default_sql()

    def format_data_type_time_tz(self, data_type: TimeTzType) -> str:
        return data_type._default_sql()

    def format_data_type_date_time(self, data_type: DateTimeType) -> str:
        return data_type._default_sql()

    def format_data_type_timestamp(self, data_type: TimestampType) -> str:
        return data_type._default_sql()

    def format_data_type_timestamp_tz(self, data_type: TimestampTzType) -> str:
        return data_type._default_sql()

    def format_data_type_interval(self, data_type: IntervalType) -> str:
        return data_type._default_sql()

    def format_data_type_json(self, data_type: JsonType) -> str:
        return data_type._default_sql()

    # ------------------------------------------------------------------
    # TypeParsingSupport
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
        """
        stripped = raw.strip()
        upper = stripped.upper()

        if self._INTEGER_TYPES.match(upper):
            # Map to the most appropriate integer type
            if upper.startswith("BIGINT") or upper.startswith("INT8"):
                return BigIntType()
            if upper.startswith("SMALLINT") or upper.startswith("INT2"):
                return SmallIntType()
            if upper.startswith("TINYINT") or upper.startswith("INT1"):
                return TinyIntType()
            if upper.startswith("MEDIUMINT") or upper.startswith("INT3"):
                return IntegerType()
            return IntegerType()

        if self._TEXT_TYPES.match(upper):
            # Parse length from VARCHAR(n) / CHAR(n)
            length_match = re.search(r"\((\d+)\)", stripped)
            length = int(length_match.group(1)) if length_match else None

            if upper.startswith("CHARACTER VARYING"):
                from rhosocial.activerecord.backend.expression.types import CharacterVaryingType
                return CharacterVaryingType(length)
            if upper.startswith("VARCHAR"):
                if length is not None:
                    return VarCharType(length)
                return VarCharType()
            if upper.startswith("CHAR") or upper.startswith("NCHAR"):
                return CharType(length)
            return TextType()

        if self._REAL_TYPES.match(upper):
            if upper.startswith("DOUBLE"):
                return DoubleType()
            if upper.startswith("FLOAT"):
                # Try to parse precision
                precision_match = re.search(r"\((\d+)\)", stripped)
                precision = int(precision_match.group(1)) if precision_match else None
                return FloatType(precision)
            return RealType()

        if self._NUMERIC_TYPES.match(upper):
            if upper.startswith("BOOLEAN"):
                return BooleanType()
            if upper.startswith("DATE"):
                # DATE can be DATE only or part of DATETIME
                if upper == "DATE" or stripped.upper() == "DATE":
                    return DateType()
                return DateTimeType()
            if upper.startswith("DATETIME"):
                precision_match = re.search(r"\((\d+)\)", stripped)
                precision = int(precision_match.group(1)) if precision_match else None
                return DateTimeType(precision)
            if upper.startswith("TIMESTAMP"):
                precision_match = re.search(r"\((\d+)\)", stripped)
                precision = int(precision_match.group(1)) if precision_match else None
                if "WITH TIME ZONE" in upper:
                    return TimestampTzType(precision)
                return TimestampType(precision)
            if upper.startswith("TIME"):
                precision_match = re.search(r"\((\d+)\)", stripped)
                precision = int(precision_match.group(1)) if precision_match else None
                if "WITH TIME ZONE" in upper:
                    return TimeTzType(precision)
                return TimeType(precision)
            if upper.startswith("DECIMAL") or upper.startswith("NUMERIC"):
                # Parse DECIMAL(p, s) or DECIMAL(p)
                nums = re.findall(r"\d+", stripped)
                if len(nums) >= 2:
                    return DecimalType(int(nums[0]), int(nums[1]))
                if len(nums) == 1:
                    return DecimalType(int(nums[0]))
                return DecimalType()
            # Fallback for other NUMERIC affinity types
            from rhosocial.activerecord.backend.expression.types import CustomType
            return CustomType(stripped)

        if self._BLOB_TYPES.match(upper):
            return BlobType()

        # Fallback: preserve unknown types
        from rhosocial.activerecord.backend.expression.types import CustomType
        return CustomType(stripped)
