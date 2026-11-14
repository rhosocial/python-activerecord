# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/capabilities/test_cap_type_mixin.py
"""SQLite DataType formatting and parsing surface tests."""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.types import (
    BigIntType,
    BooleanType,
    CharType,
    CustomType,
    DateTimeType,
    DateType,
    DecimalType,
    DoubleType,
    FloatType,
    IntegerType,
    IntervalType,
    JsonBType,
    JsonType,
    RealType,
    SmallIntType,
    TextType,
    TimestampType,
    TimestampTzType,
    TimeType,
    TimeTzType,
    TinyIntType,
    VarCharType,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
    SQLiteBlobType,
    SQLiteIntegerType,
    SQLiteNumericType,
    SQLiteRealType,
    SQLiteTextType,
)

DIALECT = SQLiteDialect(version=(3, 53, 0))


def test_simple_type_renderings():
    assert DIALECT.format_data_type_integer(IntegerType(DIALECT, spelling="integer")) == (
        "INTEGER",
        (),
    )
    assert DIALECT.format_data_type_integer(IntegerType(DIALECT, spelling="int")) == (
        "INT",
        (),
    )
    assert DIALECT.format_data_type_bigint(BigIntType(DIALECT)) == ("INTEGER", ())
    assert DIALECT.format_data_type_smallint(SmallIntType(DIALECT)) == ("INTEGER", ())
    assert DIALECT.format_data_type_tinyint(TinyIntType(DIALECT)) == ("INTEGER", ())
    assert DIALECT.format_data_type_text(TextType(DIALECT)) == ("TEXT", ())
    assert DIALECT.format_data_type_varchar(VarCharType(DIALECT, 20)) == ("TEXT", ())
    assert DIALECT.format_data_type_char(CharType(DIALECT, 20)) == ("TEXT", ())
    assert DIALECT.format_data_type_real(RealType(DIALECT)) == ("REAL", ())
    assert DIALECT.format_data_type_float(FloatType(DIALECT)) == ("REAL", ())
    assert DIALECT.format_data_type_double(DoubleType(DIALECT)) == ("REAL", ())
    assert DIALECT.format_data_type_decimal(DecimalType(DIALECT)) == ("NUMERIC", ())
    assert DIALECT.format_data_type_blob(SQLiteBlobType(DIALECT)) == ("BLOB", ())
    assert DIALECT.format_data_type_boolean(BooleanType(DIALECT)) == ("NUMERIC", ())
    assert DIALECT.format_data_type_date(DateType(DIALECT)) == ("NUMERIC", ())
    assert DIALECT.format_data_type_datetime(DateTimeType(DIALECT)) == ("NUMERIC", ())
    assert DIALECT.format_data_type_timestamp(TimestampType(DIALECT)) == ("NUMERIC", ())
    assert DIALECT.format_data_type_time(TimeType(DIALECT)) == ("NUMERIC", ())
    assert DIALECT.format_data_type_timetz(TimeTzType(DIALECT)) == ("NUMERIC", ())
    assert DIALECT.format_data_type_timestamptz(TimestampTzType(DIALECT)) == (
        "NUMERIC",
        (),
    )
    assert DIALECT.format_data_type_interval(IntervalType(DIALECT)) == ("NUMERIC", ())
    assert DIALECT.format_data_type_json(JsonType(DIALECT)) == ("TEXT", ())
    assert DIALECT.format_data_type_jsonb(JsonBType(DIALECT)) == ("TEXT", ())
    assert DIALECT.format_data_type_custom(CustomType(DIALECT, raw="CUSTOM")) == (
        "CUSTOM",
        (),
    )


def test_sqlite_native_types():
    assert DIALECT.format_data_type_sqlite_integer(SQLiteIntegerType(DIALECT)) == (
        "INTEGER",
        (),
    )
    assert DIALECT.format_data_type_sqlite_text(SQLiteTextType(DIALECT, 10)) == (
        "TEXT(10)",
        (),
    )
    assert DIALECT.format_data_type_sqlite_text(SQLiteTextType(DIALECT)) == ("TEXT", ())
    assert DIALECT.format_data_type_sqlite_real(SQLiteRealType(DIALECT)) == ("REAL", ())
    assert DIALECT.format_data_type_sqlite_numeric(SQLiteNumericType(DIALECT)) == (
        "NUMERIC",
        (),
    )
    assert DIALECT.format_data_type_sqlite_blob(SQLiteBlobType(DIALECT)) == ("BLOB", ())


@pytest.mark.parametrize(
    "method, value, word",
    [
        ("format_data_type_integer", IntegerType(DIALECT, unsigned=True), "INTEGER"),
        ("format_data_type_bigint", BigIntType(DIALECT, unsigned=True), "INTEGER"),
        ("format_data_type_smallint", SmallIntType(DIALECT, unsigned=True), "INTEGER"),
        ("format_data_type_tinyint", TinyIntType(DIALECT, unsigned=True), "INTEGER"),
        ("format_data_type_real", RealType(DIALECT, unsigned=True), "REAL"),
        ("format_data_type_float", FloatType(DIALECT, unsigned=True), "REAL"),
        ("format_data_type_double", DoubleType(DIALECT, unsigned=True), "REAL"),
        ("format_data_type_decimal", DecimalType(DIALECT, unsigned=True), "NUMERIC"),
    ],
)
def test_unsigned_refusals(method, value, word):
    with pytest.raises(UnsupportedFeatureError, match=word):
        getattr(DIALECT, method)(value)


def test_unsigned_non_bool_is_type_error():
    with pytest.raises(TypeError, match="unsigned must be a bool"):
        DIALECT.format_data_type_integer(IntegerType(DIALECT, unsigned="yes"))
    with pytest.raises(TypeError, match="unsigned must be a bool"):
        DIALECT.format_data_type_real(RealType(DIALECT, unsigned="yes"))


def test_invalid_spellings_are_refused():
    with pytest.raises(TypeError, match="cannot render"):
        DIALECT.format_data_type_integer(IntegerType(DIALECT, spelling="serial"))
    with pytest.raises(TypeError, match="cannot render"):
        DIALECT.format_data_type_varchar(VarCharType(DIALECT, spelling="nvarchar"))
    with pytest.raises(TypeError, match="cannot render"):
        DIALECT.format_data_type_decimal(DecimalType(DIALECT, spelling="money"))


def test_parse_type_affinity_branches():
    assert isinstance(DIALECT.parse_type("UNSIGNED INTEGER"), SQLiteIntegerType)
    assert isinstance(DIALECT.parse_type("VARCHAR(20)"), SQLiteTextType)
    assert DIALECT.parse_type("VARCHAR(20)").length == 20
    assert isinstance(DIALECT.parse_type("REAL(10)"), SQLiteRealType)
    assert isinstance(DIALECT.parse_type("REAL"), SQLiteRealType)
    assert isinstance(DIALECT.parse_type("DECIMAL(10, 2)"), SQLiteNumericType)
    assert isinstance(DIALECT.parse_type("DECIMAL(10)"), SQLiteNumericType)
    assert isinstance(DIALECT.parse_type("DECIMAL"), SQLiteNumericType)
    assert isinstance(DIALECT.parse_type("BLOB"), SQLiteBlobType)
    assert isinstance(DIALECT.parse_type("MYSTERY"), CustomType)
