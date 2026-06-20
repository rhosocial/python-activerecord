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


class TestSameTypeEquivalence:
    """Synonym-free equivalence — generic types are no longer synonyms."""

    def test_same_type_is_equivalent(self):
        assert VarCharType(255).is_equivalent(VarCharType(255))
        assert IntegerType().is_equivalent(IntegerType())
        t1 = IntegerType()
        t2 = IntegerType()
        assert t1.is_equivalent(t2)

    def test_different_classes_not_equivalent(self):
        assert not IntType().is_equivalent(IntegerType())
        assert not JsonType().is_equivalent(JsonBType())


class TestCustomTypeFallback:
    """CustomType as fallback for unknown types."""

    def test_custom_type_eq_hash(self):
        ct1 = CustomType("SOME_UNKNOWN_TYPE")
        ct2 = CustomType("SOME_UNKNOWN_TYPE")
        ct3 = CustomType("OTHER_TYPE")
        assert ct1 == ct2
        assert ct1 != ct3
        assert hash(ct1) == hash(ct2)
        assert hash(ct1) != hash(ct3)
        assert ct1.to_sql() == ("SOME_UNKNOWN_TYPE", ())

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

    def test_typeformatting_protocol_check(self, dialect):
        from rhosocial.activerecord.backend.dialect.protocols import (
            TypeFormattingSupport,
            TypeParsingSupport,
        )
        assert isinstance(dialect, TypeFormattingSupport)
        assert isinstance(dialect, TypeParsingSupport)


class TestTypeParsing:
    """SQLite type affinity parsing via TypeParsingSupport.

    SQLite uses five type affinities.  All concrete type strings within
    an affinity family map to the same ``SQLite*Type`` class, but the
    parser preserves length / precision / scale parameters where present.
    """

    @pytest.fixture
    def dialect(self):
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
        return SQLiteDialect(version=(3, 45, 0))

    # ---- INTEGER affinity ----

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

    # ---- TEXT affinity ----

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

    # ---- REAL affinity ----

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

    # ---- NUMERIC affinity ----

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

    # ---- BLOB affinity ----

    def test_parse_blob(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteBlobType,
        )
        t = DataType.parse_data_type_str(dialect, "BLOB")
        assert isinstance(t, SQLiteBlobType)

    # ---- fallback ----

    def test_parse_unknown_fallback(self, dialect):
        t = DataType.parse_data_type_str(dialect, "SOME_UNKNOWN_TYPE")
        assert isinstance(t, CustomType)
        assert t.raw == "SOME_UNKNOWN_TYPE"
