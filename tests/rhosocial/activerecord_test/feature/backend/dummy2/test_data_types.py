# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_data_types.py
"""Tests for the DataType expression system.

Covers:
- Default type rendering via DDLTypeMixin/dialect
- Value-object equality / hashing
- Synonym-based equivalence
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


def _sqlite_dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
    return SQLiteDialect(version=(3, 45, 0))


def _dummy_dialect():
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    return DummyDialect()


# ---------------------------------------------------------------------------
# Default rendering via dialect
# ---------------------------------------------------------------------------


class TestDefaultRendering:
    """Core type rendering via dialect."""

    @pytest.fixture
    def dialect(self):
        return _dummy_dialect()

    def test_integer_types(self, dialect):
        assert IntegerType().to_sql(dialect) == ("INTEGER", ())
        assert TinyIntType().to_sql(dialect) == ("TINYINT", ())
        assert SmallIntType().to_sql(dialect) == ("SMALLINT", ())
        assert BigIntType().to_sql(dialect) == ("BIGINT", ())
        assert IntType().to_sql(dialect) == ("INT", ())

    def test_numeric_types(self, dialect):
        assert FloatType().to_sql(dialect) == ("FLOAT", ())
        assert FloatType(24).to_sql(dialect) == ("FLOAT(24)", ())
        assert RealType().to_sql(dialect) == ("REAL", ())
        assert DoubleType().to_sql(dialect) == ("DOUBLE PRECISION", ())
        assert DecimalType().to_sql(dialect) == ("DECIMAL", ())
        assert DecimalType(10).to_sql(dialect) == ("DECIMAL(10)", ())
        assert DecimalType(10, 2).to_sql(dialect) == ("DECIMAL(10,2)", ())

    def test_string_types(self, dialect):
        assert CharType().to_sql(dialect) == ("CHAR", ())
        assert CharType(10).to_sql(dialect) == ("CHAR(10)", ())
        assert VarCharType().to_sql(dialect) == ("VARCHAR", ())
        assert VarCharType(255).to_sql(dialect) == ("VARCHAR(255)", ())
        assert TextType().to_sql(dialect) == ("TEXT", ())

    def test_boolean_type(self, dialect):
        assert BooleanType().to_sql(dialect) == ("BOOLEAN", ())

    def test_binary_type(self, dialect):
        assert BlobType().to_sql(dialect) == ("BLOB", ())

    def test_datetime_types(self, dialect):
        assert DateType().to_sql(dialect) == ("DATE", ())
        assert TimeType().to_sql(dialect) == ("TIME", ())
        assert TimeType(6).to_sql(dialect) == ("TIME(6)", ())
        assert TimeTzType().to_sql(dialect) == ("TIME WITH TIME ZONE", ())
        assert TimeTzType(3).to_sql(dialect) == ("TIME(3) WITH TIME ZONE", ())
        assert DateTimeType().to_sql(dialect) == ("DATETIME", ())
        assert DateTimeType(3).to_sql(dialect) == ("DATETIME(3)", ())
        assert TimestampType().to_sql(dialect) == ("TIMESTAMP", ())
        assert TimestampType(3).to_sql(dialect) == ("TIMESTAMP(3)", ())
        assert TimestampTzType().to_sql(dialect) == ("TIMESTAMP WITH TIME ZONE", ())
        assert TimestampTzType(3).to_sql(dialect) == ("TIMESTAMP(3) WITH TIME ZONE", ())
        assert IntervalType().to_sql(dialect) == ("INTERVAL", ())
        assert IntervalType("YEAR TO MONTH").to_sql(dialect) == ("INTERVAL YEAR TO MONTH", ())

    def test_json_types(self, dialect):
        assert JsonType().to_sql(dialect) == ("JSON", ())
        assert JsonBType().to_sql(dialect) == ("JSONB", ())

    def test_custom_type(self, dialect):
        assert CustomType("GEOMETRY").to_sql(dialect) == ("GEOMETRY", ())
        assert CustomType("VARCHAR(255)").to_sql(dialect) == ("VARCHAR(255)", ())


# ---------------------------------------------------------------------------
# Value-object equality / hashing
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Equivalence
# ---------------------------------------------------------------------------


class TestSameTypeEquivalence:
    """Equivalence checks based on synonyms."""

    def test_same_type_is_equivalent(self):
        assert VarCharType(255).is_equivalent(VarCharType(255))
        assert IntegerType().is_equivalent(IntegerType())

    def test_synonym_classes_are_equivalent(self):
        assert IntType().is_equivalent(IntegerType())
        assert IntegerType().is_equivalent(IntType())

    def test_different_classes_not_equivalent(self):
        assert not JsonType().is_equivalent(JsonBType())
        assert not IntegerType().is_equivalent(VarCharType(255))


# ---------------------------------------------------------------------------
# CustomType fallback
# ---------------------------------------------------------------------------


class TestCustomTypeFallback:
    """CustomType as fallback for unknown types."""

    @pytest.fixture
    def dialect(self):
        return _dummy_dialect()

    def test_custom_type_eq_hash(self, dialect):
        ct1 = CustomType("SOME_UNKNOWN_TYPE")
        ct2 = CustomType("SOME_UNKNOWN_TYPE")
        ct3 = CustomType("OTHER_TYPE")
        assert ct1 == ct2
        assert ct1 != ct3
        assert hash(ct1) == hash(ct2)
        assert hash(ct1) != hash(ct3)
        assert ct1.to_sql(dialect) == ("SOME_UNKNOWN_TYPE", ())

    def test_parse_unknown_fallback(self, dialect):
        """When no dialect is available, parse_data_type_str returns CustomType."""
        result = DataType.parse_data_type_str(None, "UNKNOWN_TYPE")
        assert isinstance(result, CustomType)
        assert result.raw == "UNKNOWN_TYPE"


# ---------------------------------------------------------------------------
# Dialect-based rendering
# ---------------------------------------------------------------------------


class TestDialectRendering:
    """SQLite dialect rendering via DDLTypeSupport."""

    @pytest.fixture
    def dialect(self):
        return _sqlite_dialect()

    def test_render_via_dialect(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteIntegerType,
        )
        integer_type = SQLiteIntegerType()
        sql, _ = integer_type.to_sql(dialect)
        assert sql == "INTEGER"

    def test_render_varchar(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteTextType,
        )
        v = SQLiteTextType(255)
        sql, _ = v.to_sql(dialect)
        assert sql == "TEXT(255)"

    def test_render_decimal(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteNumericType,
        )
        d = SQLiteNumericType(10, 2)
        sql, _ = d.to_sql(dialect)
        assert sql == "NUMERIC"

    def test_render_datetime(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteNumericType,
        )
        dt = SQLiteNumericType()
        sql, _ = dt.to_sql(dialect)
        assert sql == "NUMERIC"

    def test_ddl_type_protocol_check(self, dialect):
        from rhosocial.activerecord.backend.dialect.protocols import DDLTypeSupport
        assert isinstance(dialect, DDLTypeSupport)


# ---------------------------------------------------------------------------
# Type parsing
# ---------------------------------------------------------------------------


class TestTypeParsing:
    """SQLite type affinity parsing via DDLTypeSupport."""

    @pytest.fixture
    def dialect(self):
        return _sqlite_dialect()

    def test_parse_integer(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteIntegerType,
        )
        t = DataType.parse_data_type_str(dialect, "INTEGER")
        assert isinstance(t, SQLiteIntegerType)

    def test_parse_bigint(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteIntegerType,
        )
        t = DataType.parse_data_type_str(dialect, "BIGINT")
        assert isinstance(t, SQLiteIntegerType)

    def test_parse_smallint(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteIntegerType,
        )
        t = DataType.parse_data_type_str(dialect, "SMALLINT")
        assert isinstance(t, SQLiteIntegerType)

    def test_parse_tinyint(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteIntegerType,
        )
        t = DataType.parse_data_type_str(dialect, "TINYINT")
        assert isinstance(t, SQLiteIntegerType)

    def test_parse_varchar(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteTextType,
        )
        t = DataType.parse_data_type_str(dialect, "VARCHAR(255)")
        assert isinstance(t, SQLiteTextType)
        assert t.length == 255

    def test_parse_char(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteTextType,
        )
        t = DataType.parse_data_type_str(dialect, "CHAR(10)")
        assert isinstance(t, SQLiteTextType)
        assert t.length == 10

    def test_parse_text(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteTextType,
        )
        t = DataType.parse_data_type_str(dialect, "TEXT")
        assert isinstance(t, SQLiteTextType)
        assert t.length is None

    def test_parse_varchar_without_length(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteTextType,
        )
        t = DataType.parse_data_type_str(dialect, "VARCHAR")
        assert isinstance(t, SQLiteTextType)
        assert t.length is None

    def test_parse_float(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteRealType,
        )
        t = DataType.parse_data_type_str(dialect, "FLOAT")
        assert isinstance(t, SQLiteRealType)

    def test_parse_real(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteRealType,
        )
        t = DataType.parse_data_type_str(dialect, "REAL")
        assert isinstance(t, SQLiteRealType)

    def test_parse_double(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteRealType,
        )
        t = DataType.parse_data_type_str(dialect, "DOUBLE")
        assert isinstance(t, SQLiteRealType)

    def test_parse_decimal(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteNumericType,
        )
        t = DataType.parse_data_type_str(dialect, "DECIMAL(10,2)")
        assert isinstance(t, SQLiteNumericType)
        assert t.precision == 10
        assert t.scale == 2

    def test_parse_boolean(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteNumericType,
        )
        t = DataType.parse_data_type_str(dialect, "BOOLEAN")
        assert isinstance(t, SQLiteNumericType)

    def test_parse_date(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteNumericType,
        )
        t = DataType.parse_data_type_str(dialect, "DATE")
        assert isinstance(t, SQLiteNumericType)

    def test_parse_datetime(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteNumericType,
        )
        t = DataType.parse_data_type_str(dialect, "DATETIME")
        assert isinstance(t, SQLiteNumericType)

    def test_parse_timestamp(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteNumericType,
        )
        t = DataType.parse_data_type_str(dialect, "TIMESTAMP")
        assert isinstance(t, SQLiteNumericType)

    def test_parse_blob(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteBlobType,
        )
        t = DataType.parse_data_type_str(dialect, "BLOB")
        assert isinstance(t, SQLiteBlobType)

    def test_parse_unknown_fallback(self, dialect):
        t = DataType.parse_data_type_str(dialect, "SOME_UNKNOWN_TYPE")
        assert isinstance(t, CustomType)
        assert t.raw == "SOME_UNKNOWN_TYPE"
