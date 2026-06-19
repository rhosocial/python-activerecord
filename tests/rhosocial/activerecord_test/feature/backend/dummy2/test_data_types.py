# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_data_types.py
"""Tests for the DataType expression system.

Covers:
- Default SQL rendering (no dialect)
- Value-object equality / hashing
- Synonym-based equivalence (``is_equivalent``)
- CustomType fallback
- Dialect-based rendering via TypeFormattingSupport
- Type parsing via TypeParsingSupport
"""

import pytest
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BlobType,
    BooleanType,
    CharType,
    CustomType,
    DataType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    IntType,
    IntervalType,
    JsonBType,
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


class TestDefaultSQL:
    """Default SQL rendering (no dialect, uses _default_sql())."""

    def test_integer_types(self):
        assert IntegerType().to_sql() == ("INTEGER", ())
        assert TinyIntType().to_sql() == ("TINYINT", ())
        assert SmallIntType().to_sql() == ("SMALLINT", ())
        assert BigIntType().to_sql() == ("BIGINT", ())
        assert IntType().to_sql() == ("INT", ())

    def test_numeric_types(self):
        assert FloatType().to_sql() == ("FLOAT", ())
        assert FloatType(24).to_sql() == ("FLOAT(24)", ())
        assert RealType().to_sql() == ("REAL", ())
        assert DoubleType().to_sql() == ("DOUBLE PRECISION", ())
        assert DecimalType().to_sql() == ("DECIMAL", ())
        assert DecimalType(10).to_sql() == ("DECIMAL(10)", ())
        assert DecimalType(10, 2).to_sql() == ("DECIMAL(10,2)", ())

    def test_string_types(self):
        assert CharType().to_sql() == ("CHAR", ())
        assert CharType(10).to_sql() == ("CHAR(10)", ())
        assert VarCharType().to_sql() == ("VARCHAR", ())
        assert VarCharType(255).to_sql() == ("VARCHAR(255)", ())
        assert TextType().to_sql() == ("TEXT", ())

    def test_boolean_type(self):
        assert BooleanType().to_sql() == ("BOOLEAN", ())

    def test_binary_type(self):
        assert BlobType().to_sql() == ("BLOB", ())

    def test_datetime_types(self):
        assert DateType().to_sql() == ("DATE", ())
        assert TimeType().to_sql() == ("TIME", ())
        assert TimeType(6).to_sql() == ("TIME(6)", ())
        assert TimeTzType().to_sql() == ("TIME WITH TIME ZONE", ())
        assert TimeTzType(3).to_sql() == ("TIME(3) WITH TIME ZONE", ())
        assert DateTimeType().to_sql() == ("DATETIME", ())
        assert DateTimeType(3).to_sql() == ("DATETIME(3)", ())
        assert TimestampType().to_sql() == ("TIMESTAMP", ())
        assert TimestampType(3).to_sql() == ("TIMESTAMP(3)", ())
        assert TimestampTzType().to_sql() == ("TIMESTAMP WITH TIME ZONE", ())
        assert TimestampTzType(3).to_sql() == ("TIMESTAMP(3) WITH TIME ZONE", ())
        assert IntervalType().to_sql() == ("INTERVAL", ())
        assert IntervalType("YEAR TO MONTH").to_sql() == ("INTERVAL YEAR TO MONTH", ())

    def test_json_types(self):
        assert JsonType().to_sql() == ("JSON", ())
        assert JsonBType().to_sql() == ("JSONB", ())

    def test_custom_type(self):
        assert CustomType("GEOMETRY").to_sql() == ("GEOMETRY", ())
        assert CustomType("VARCHAR(255)").to_sql() == ("VARCHAR(255)", ())


class TestEqualityAndHashing:
    """Value-object equality / hashing."""

    def test_equal_types(self):
        assert IntegerType() == IntegerType()
        assert VarCharType(255) == VarCharType(255)
        assert DecimalType(10, 2) == DecimalType(10, 2)
        assert FloatType() == FloatType()
        assert CustomType("UUID") == CustomType("UUID")

    def test_not_equal_different_params(self):
        assert VarCharType(255) != VarCharType(100)
        assert DecimalType(10, 2) != DecimalType(10, 3)
        assert FloatType(24) != FloatType(53)
        assert TimestampType(3) != TimestampType(6)

    def test_not_equal_different_types(self):
        assert IntegerType() != VarCharType(255)
        assert BooleanType() != IntegerType()
        assert JsonType() != JsonBType()

    def test_hashing(self):
        assert hash(IntegerType()) == hash(IntegerType())
        assert hash(VarCharType(255)) == hash(VarCharType(255))
        s = {IntegerType(), VarCharType(255), IntegerType()}
        assert len(s) == 2


class TestSynonymEquivalence:
    """Cross-class synonym checks."""

    def test_int_integer_equivalence(self):
        assert IntType().is_equivalent(IntegerType())
        assert IntegerType().is_equivalent(IntType())

    def test_varchar_character_varying_equivalence(self):
        assert VarCharType(255).is_equivalent(
            type("CharacterVaryingType", (VarCharType,), {})()
        )

    def test_json_jsonb_equivalence(self):
        assert JsonType().is_equivalent(JsonBType())
        assert JsonBType().is_equivalent(JsonType())

    def test_same_type_is_equivalent(self):
        assert IntegerType().is_equivalent(IntegerType())
        t1 = IntegerType()
        t2 = IntegerType()
        assert t1.is_equivalent(t2)


class TestCustomTypeFallback:
    """CustomType as fallback for unknown types."""

    def test_custom_type_repr(self):
        ct = CustomType("SOME_UNKNOWN_TYPE")
        assert ct._type_params() == ("SOME_UNKNOWN_TYPE",)
        assert ct.to_sql() == ("SOME_UNKNOWN_TYPE", ())

    def test_parse_unknown_fallback(self):
        """When no dialect is available, parse_data_type_str returns CustomType."""
        result = DataType.parse_data_type_str(None, "UNKNOWN_TYPE")
        assert isinstance(result, CustomType)
        assert result.raw == "UNKNOWN_TYPE"


class TestDialectRendering:
    """SQLite dialect rendering via TypeFormattingSupport."""

    @pytest.fixture
    def dialect(self):
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
        return SQLiteDialect(version=(3, 45, 0))

    def test_render_via_dialect(self, dialect):
        integer_type = IntegerType()
        sql, _ = integer_type.to_sql(dialect)
        assert sql == "INTEGER"

    def test_render_varchar(self, dialect):
        v = VarCharType(255)
        sql, _ = v.to_sql(dialect)
        assert sql == "VARCHAR(255)"

    def test_render_decimal(self, dialect):
        d = DecimalType(10, 2)
        sql, _ = d.to_sql(dialect)
        assert sql == "DECIMAL(10,2)"

    def test_render_datetime(self, dialect):
        dt = DateTimeType(3)
        sql, _ = dt.to_sql(dialect)
        assert sql == "DATETIME(3)"

    def test_typeformatting_protocol_check(self, dialect):
        from rhosocial.activerecord.backend.dialect.protocols import (
            TypeFormattingSupport,
            TypeParsingSupport,
        )
        assert isinstance(dialect, TypeFormattingSupport)
        assert isinstance(dialect, TypeParsingSupport)


class TestTypeParsing:
    """SQLite type affinity parsing via TypeParsingSupport."""

    @pytest.fixture
    def dialect(self):
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
        return SQLiteDialect(version=(3, 45, 0))

    def test_parse_integer(self, dialect):
        t = DataType.parse_data_type_str(dialect, "INTEGER")
        assert isinstance(t, IntegerType)

    def test_parse_bigint(self, dialect):
        t = DataType.parse_data_type_str(dialect, "BIGINT")
        assert isinstance(t, BigIntType)

    def test_parse_smallint(self, dialect):
        t = DataType.parse_data_type_str(dialect, "SMALLINT")
        assert isinstance(t, SmallIntType)

    def test_parse_tinyint(self, dialect):
        t = DataType.parse_data_type_str(dialect, "TINYINT")
        assert isinstance(t, TinyIntType)

    def test_parse_varchar(self, dialect):
        t = DataType.parse_data_type_str(dialect, "VARCHAR(255)")
        assert isinstance(t, VarCharType)
        assert t.length == 255

    def test_parse_char(self, dialect):
        t = DataType.parse_data_type_str(dialect, "CHAR(10)")
        assert isinstance(t, CharType)
        assert t.length == 10

    def test_parse_text(self, dialect):
        t = DataType.parse_data_type_str(dialect, "TEXT")
        assert isinstance(t, TextType)

    def test_parse_float(self, dialect):
        t = DataType.parse_data_type_str(dialect, "FLOAT")
        assert isinstance(t, FloatType)

    def test_parse_real(self, dialect):
        t = DataType.parse_data_type_str(dialect, "REAL")
        assert isinstance(t, RealType)

    def test_parse_double(self, dialect):
        t = DataType.parse_data_type_str(dialect, "DOUBLE")
        assert isinstance(t, DoubleType)

    def test_parse_decimal(self, dialect):
        t = DataType.parse_data_type_str(dialect, "DECIMAL(10,2)")
        assert isinstance(t, DecimalType)
        assert t.precision == 10
        assert t.scale == 2

    def test_parse_boolean(self, dialect):
        t = DataType.parse_data_type_str(dialect, "BOOLEAN")
        assert isinstance(t, BooleanType)

    def test_parse_blob(self, dialect):
        t = DataType.parse_data_type_str(dialect, "BLOB")
        assert isinstance(t, BlobType)

    def test_parse_date(self, dialect):
        t = DataType.parse_data_type_str(dialect, "DATE")
        assert isinstance(t, DateType)

    def test_parse_datetime(self, dialect):
        t = DataType.parse_data_type_str(dialect, "DATETIME")
        assert isinstance(t, DateTimeType)

    def test_parse_timestamp(self, dialect):
        t = DataType.parse_data_type_str(dialect, "TIMESTAMP")
        assert isinstance(t, TimestampType)

    def test_parse_unknown_fallback(self, dialect):
        t = DataType.parse_data_type_str(dialect, "SOME_UNKNOWN_TYPE")
        assert isinstance(t, CustomType)
        assert t.raw == "SOME_UNKNOWN_TYPE"

    def test_parse_varchar_without_length(self, dialect):
        t = DataType.parse_data_type_str(dialect, "VARCHAR")
        assert isinstance(t, VarCharType)
        assert t.length is None
