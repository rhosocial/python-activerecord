# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_data_types.py
"""Tests for the DataType expression system.

Covers:
- Default type rendering via DataTypeMixin/dialect
- Value-object equality / hashing
- Type identity (there is no separate equivalence question)
- CustomType fallback
- Dialect-based rendering via TypeFormattingSupport
- Type parsing via TypeParsingSupport
"""

import pytest
from rhosocial.activerecord.backend.expression.types import (
    ArrayType,
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
    XmlType,
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
        assert IntegerType(dialect=dialect).to_sql() == ("INTEGER", ())
        assert TinyIntType(dialect=dialect).to_sql() == ("TINYINT", ())
        assert SmallIntType(dialect=dialect).to_sql() == ("SMALLINT", ())
        assert BigIntType(dialect=dialect).to_sql() == ("BIGINT", ())
        assert IntegerType(dialect=dialect, spelling="int").to_sql() == ("INT", ())

    def test_numeric_types(self, dialect):
        assert FloatType(dialect=dialect).to_sql() == ("FLOAT", ())
        assert FloatType(dialect, 24).to_sql() == ("FLOAT(24)", ())
        assert RealType(dialect=dialect).to_sql() == ("REAL", ())
        assert DoubleType(dialect=dialect).to_sql() == ("DOUBLE PRECISION", ())
        assert DecimalType(dialect=dialect).to_sql() == ("DECIMAL", ())
        assert DecimalType(dialect, 10).to_sql() == ("DECIMAL(10)", ())
        assert DecimalType(dialect, 10, 2).to_sql() == ("DECIMAL(10,2)", ())

    def test_string_types(self, dialect):
        assert CharType(dialect=dialect).to_sql() == ("CHAR", ())
        assert CharType(dialect, 10).to_sql() == ("CHAR(10)", ())
        assert VarCharType(dialect=dialect).to_sql() == ("VARCHAR", ())
        assert VarCharType(dialect, 255).to_sql() == ("VARCHAR(255)", ())
        assert TextType(dialect=dialect).to_sql() == ("TEXT", ())

    def test_boolean_type(self, dialect):
        assert BooleanType(dialect=dialect).to_sql() == ("BOOLEAN", ())

    def test_binary_type(self, dialect):
        assert BlobType(dialect=dialect).to_sql() == ("BLOB", ())

    def test_datetime_types(self, dialect):
        assert DateType(dialect=dialect).to_sql() == ("DATE", ())
        assert TimeType(dialect=dialect).to_sql() == ("TIME", ())
        assert TimeType(dialect, 6).to_sql() == ("TIME(6)", ())
        assert TimeTzType(dialect=dialect).to_sql() == ("TIME WITH TIME ZONE", ())
        assert TimeTzType(dialect, 3).to_sql() == ("TIME(3) WITH TIME ZONE", ())
        assert DateTimeType(dialect=dialect).to_sql() == ("DATETIME", ())
        assert DateTimeType(dialect, 3).to_sql() == ("DATETIME(3)", ())
        assert TimestampType(dialect=dialect).to_sql() == ("TIMESTAMP", ())
        assert TimestampType(dialect, 3).to_sql() == ("TIMESTAMP(3)", ())
        assert TimestampTzType(dialect=dialect).to_sql() == ("TIMESTAMP WITH TIME ZONE", ())
        assert TimestampTzType(dialect, 3).to_sql() == ("TIMESTAMP(3) WITH TIME ZONE", ())
        assert IntervalType(dialect=dialect).to_sql() == ("INTERVAL", ())
        assert IntervalType(dialect, "YEAR TO MONTH").to_sql() == ("INTERVAL YEAR TO MONTH", ())

    def test_json_types(self, dialect):
        assert JsonType(dialect=dialect).to_sql() == ("JSON", ())
        assert JsonBType(dialect=dialect).to_sql() == ("JSONB", ())

    def test_custom_type(self, dialect):
        assert CustomType(dialect, "GEOMETRY").to_sql() == ("GEOMETRY", ())
        assert CustomType(dialect, "VARCHAR(255)").to_sql() == ("VARCHAR(255)", ())


# ---------------------------------------------------------------------------
# Value-object equality / hashing
# ---------------------------------------------------------------------------


class TestEqualityAndHashing:
    """Value-object equality / hashing."""

    def test_equal_types(self):
        assert IntegerType() == IntegerType()
        assert VarCharType(None, 255) == VarCharType(None, 255)
        assert DecimalType(None, 10, 2) == DecimalType(None, 10, 2)
        assert FloatType() == FloatType()
        assert CustomType(None, "UUID") == CustomType(None, "UUID")

    def test_not_equal_different_params(self):
        assert VarCharType(None, 255) != VarCharType(None, 100)
        assert DecimalType(None, 10, 2) != DecimalType(None, 10, 3)
        assert FloatType(None, 24) != FloatType(None, 53)
        assert TimestampType(None, 3) != TimestampType(None, 6)

    def test_not_equal_different_types(self):
        assert IntegerType() != VarCharType(None, 255)
        assert BooleanType() != IntegerType()
        assert JsonType() != JsonBType()

    def test_hashing(self):
        assert hash(IntegerType()) == hash(IntegerType())
        assert hash(VarCharType(None, 255)) == hash(VarCharType(None, 255))
        s = {IntegerType(), VarCharType(None, 255), IntegerType()}
        assert len(s) == 2


# ---------------------------------------------------------------------------
# Equivalence
# ---------------------------------------------------------------------------


class TestTypeIdentity:
    """Type comparison is identity, not a looser "equivalent" question.

    There is no ``is_equivalent`` and no ``synonyms()``: two declarations are
    the same type when they are the same class with the same logical content,
    which is what ``==`` already means for a value object.
    """

    def test_same_type_is_equal(self):
        assert VarCharType(None, 255) == VarCharType(None, 255)
        assert IntegerType() == IntegerType()

    def test_a_spelling_is_not_part_of_the_type(self):
        """``INT`` and ``INTEGER`` are the same type, and they are the same
        *value* — so ``==`` says they match.

        The tempting alternative is to count the spelling, on the argument that
        ``CREATE TABLE t (a INT)`` and ``CREATE TABLE t (a INTEGER)`` are
        different scripts. They are, but the schema differ does not compare two
        scripts: it compares what a database *reports now* against what was
        declared, and a database reports its own house spelling regardless of
        which word was typed. PostgreSQL reports ``character varying(30)`` for
        every ``varchar(30)`` column that exists. Counting the spelling would
        therefore report a change on every long-form column that was never
        touched — a false positive on the one comparison that has to be right.

        The difference is not lost: it is in the rendered SQL, and
        ``spelling`` round-trips through ``get_params()`` for serialization.
        """
        assert IntegerType() == IntegerType(spelling="int")
        assert hash(IntegerType()) == hash(IntegerType(spelling="int"))

    def test_different_classes_are_never_equal(self):
        assert JsonType() != JsonBType()
        assert IntegerType() != VarCharType(None, 255)

    def test_unsigned_is_part_of_the_declaration(self):
        """Signed and unsigned are the same *class* — the range is what the
        parameter carries — so they are told apart by ``==``, not by type."""
        assert IntegerType() != IntegerType(unsigned=True)


# ---------------------------------------------------------------------------
# Signedness on the floating-point and exact fixed-point concepts
# ---------------------------------------------------------------------------


class TestNumericUnsignedField:
    """``unsigned`` on ``DecimalType``, ``FloatType`` and ``DoubleType``.

    The same field, on the same terms, as the four integer widths: **width is a
    class, signedness is a field**. ``FLOAT(p)`` exists for every ``p``, so a
    (width x signedness) grid cannot live in a linear chain, and the flag rides
    on the instance instead.

    It has to ride there, because MySQL's manual says of the numeric types what
    it says of the integers — "Floating point and fixed-point types also can be
    ``UNSIGNED``" — so ``DECIMAL(10,2) UNSIGNED`` and ``DECIMAL(10,2)`` are two
    different columns on MySQL and MariaDB alike. A concept that cannot hold the
    flag cannot tell them apart, and the schema differ reports no change for a
    change the database will make: measured on all fifteen wired MariaDB servers,
    ``decimal(10,2) unsigned zerofill`` introspected as ``DecimalType(10, 2)``.

    Which backend honours the flag and which refuses it is that vendor's own
    question; what is checked *here* is the part that is the framework's — the
    field exists, it is in ``PARAMETERS`` (so it reaches ``==`` and ``__hash__``),
    and it is strictly typed, because it becomes a type modifier in the rendered
    DDL and ``unsigned=1`` must not become ``UNSIGNED``.
    """

    CONCEPTS = (DecimalType, FloatType, DoubleType)

    @pytest.mark.parametrize("klass", CONCEPTS, ids=lambda k: k.__name__)
    def test_signed_and_unsigned_are_different_columns(self, klass):
        assert klass() != klass(unsigned=True)
        assert hash(klass()) != hash(klass(unsigned=True))
        assert klass() == klass(unsigned=False)
        assert klass(unsigned=False) != klass(unsigned=True)

    @pytest.mark.parametrize("klass", CONCEPTS, ids=lambda k: k.__name__)
    def test_the_field_is_declared_as_identity(self, klass):
        """``PARAMETERS`` is what ``identity()`` reads, so this is the whole of
        "the differ can see it".  ``unsigned`` is *appended* to the tuple, never
        inserted ahead of ``precision``/``scale``: the order is load-bearing for
        ``__hash__``, and reordering it would change every hash of every instance.
        """
        assert klass.PARAMETERS[-1] == "unsigned"
        assert "unsigned" in klass.PARAMETERS
        assert klass().identity()[-1] is False
        assert klass(unsigned=True).identity()[-1] is True

    @pytest.mark.parametrize("klass", CONCEPTS, ids=lambda k: k.__name__)
    def test_unsigned_is_a_real_bool_not_a_truthy_test(self, klass):
        """It becomes ``UNSIGNED`` in the DDL, so ``1`` is not ``True``.

        A truthy check would silently accept ``1``, ``"yes"`` and any other
        object, and the *first* of those is the dangerous one: it renders
        ``UNSIGNED`` for a field the caller wrote as a display width or a
        count, and nothing about the resulting DDL says the declaration was
        reinterpreted.
        """
        for wrong in (1, 0, "yes", "", None, [], object()):
            with pytest.raises(TypeError, match="unsigned must be a bool"):
                klass(unsigned=wrong)

    @pytest.mark.parametrize("klass", CONCEPTS, ids=lambda k: k.__name__)
    def test_the_other_fields_are_untouched(self, klass):
        """Adding a third parameter must not have disturbed the first two.

        ``precision``/``scale`` still read, still compare, and still hold their
        declared defaults. ``DoubleType`` carries no precision of its own — that
        is D6, ``REAL``/``DOUBLE PRECISION``/``FLOAT`` being three verified
        different storages rather than one concept at three precisions — so the
        assertion is about the fields a concept *does* have.
        """
        assert klass().unsigned is False
        if "precision" in klass.PARAMETERS:
            assert klass().precision is None
            assert klass(precision=24).precision == 24
        if "scale" in klass.PARAMETERS:
            assert klass().scale is None
            assert klass(precision=10, scale=2).identity()[:2] == (10, 2)

    def test_the_three_concepts_still_take_their_dialect_first(self):
        """``dialect`` is the first positional parameter, on all three.

        A signature that put ``precision`` first would fail *silently*: the
        dialect object would be stored as the precision and the error would only
        appear at render time, in SQL.  That is the whole reason this is asserted
        rather than assumed — and it is asserted on the three that gained a
        keyword-only parameter, because that is where the positional/keyword
        boundary moved.
        """
        sentinel = _dummy_dialect()
        assert DecimalType(sentinel, 24).precision == 24
        assert DecimalType(sentinel, 24).dialect is sentinel
        assert DecimalType(sentinel, 24).unsigned is False
        assert DecimalType(sentinel, 24).spelling == "decimal"
        assert DecimalType(sentinel, 24, 2).scale == 2
        assert FloatType(sentinel, 24).precision == 24
        assert FloatType(sentinel, 24).dialect is sentinel
        assert FloatType(sentinel, 24).unsigned is False
        # ``DoubleType`` has no second positional, and must not grow one: the
        # dialect is the only positional, exactly as before.
        assert DoubleType(sentinel).dialect is sentinel
        assert DoubleType(sentinel).unsigned is False


# ---------------------------------------------------------------------------
# CustomType fallback
# ---------------------------------------------------------------------------


class TestCustomTypeFallback:
    """CustomType as fallback for unknown types."""

    @pytest.fixture
    def dialect(self):
        return _dummy_dialect()

    def test_custom_type_eq_hash(self, dialect):
        ct1 = CustomType(dialect, "SOME_UNKNOWN_TYPE")
        ct2 = CustomType(None, "SOME_UNKNOWN_TYPE")
        ct3 = CustomType(None, "OTHER_TYPE")
        assert ct1 == ct2
        assert ct1 != ct3
        assert hash(ct1) == hash(ct2)
        assert hash(ct1) != hash(ct3)
        assert ct1.to_sql() == ("SOME_UNKNOWN_TYPE", ())  # bound at construction

    def test_parse_unknown_fallback(self, dialect):
        """When no dialect is available, parse_data_type_str returns CustomType."""
        result = DataType.parse_data_type_str(None, "UNKNOWN_TYPE")
        assert isinstance(result, CustomType)
        assert result.raw == "UNKNOWN_TYPE"


# ---------------------------------------------------------------------------
# Dialect-based rendering
# ---------------------------------------------------------------------------


class TestDialectRendering:
    """SQLite dialect rendering via DataTypeSupport."""

    @pytest.fixture
    def dialect(self):
        return _sqlite_dialect()

    def test_render_via_dialect(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteIntegerType,
        )
        integer_type = SQLiteIntegerType(dialect)
        sql, _ = integer_type.to_sql()
        assert sql == "INTEGER"

    def test_render_varchar(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteTextType,
        )
        v = SQLiteTextType(dialect, 255)
        sql, _ = v.to_sql()
        assert sql == "TEXT(255)"

    def test_render_decimal(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteNumericType,
        )
        d = SQLiteNumericType(dialect, 10, 2)
        sql, _ = d.to_sql()
        assert sql == "NUMERIC"

    def test_render_datetime(self, dialect):
        from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
            SQLiteNumericType,
        )
        dt = SQLiteNumericType(dialect=dialect)
        sql, _ = dt.to_sql()
        assert sql == "NUMERIC"

    def test_data_type_protocol_check(self, dialect):
        from rhosocial.activerecord.backend.dialect.protocols import (
            DataTypeSupport,
            DDLTypeSupport,
        )
        assert isinstance(dialect, DataTypeSupport)
        assert DDLTypeSupport is DataTypeSupport


# ---------------------------------------------------------------------------
# Array container contract
# ---------------------------------------------------------------------------


class TestArrayTypeContract:
    """``ArrayType`` refuses to exist without something to be an array of."""

    def test_element_type_is_required(self):
        with pytest.raises(TypeError, match="requires an element_type"):
            ArrayType(None)

    def test_element_type_must_be_a_data_type(self):
        with pytest.raises(TypeError, match="must be a DataType instance"):
            ArrayType(None, "integer")

    def test_dimensions_must_be_a_positive_int(self):
        with pytest.raises(ValueError, match="dimensions must be an int >= 1"):
            ArrayType(None, IntegerType(), 0)
        with pytest.raises(ValueError, match="dimensions must be an int >= 1"):
            ArrayType(None, IntegerType(), 1.5)

    def test_dimensions_default_to_one(self):
        assert ArrayType(None, IntegerType()).dimensions == 1


# ---------------------------------------------------------------------------
# XmlType
# ---------------------------------------------------------------------------


class TestXmlType:
    """XML is a modelled concept, distinct from both JSON and Text."""

    @pytest.fixture
    def dialect(self):
        return _dummy_dialect()

    def test_name_is_xml(self):
        assert XmlType().name == "xml"

    def test_renders_through_its_dialect(self, dialect):
        assert dialect.format_data_type(XmlType(dialect)) == ("XML", ())

    def test_equality_and_hash(self):
        assert XmlType() == XmlType()
        assert hash(XmlType()) == hash(XmlType())

    def test_not_a_subclass_of_json_or_text(self):
        """The distinction is real: SQL/XML and SQL/JSON differ in operations,
        standards and in which backends implement which. XML is likewise not
        TextType — SQL Server's ``xml`` is binary, Oracle's stores an infoset."""
        assert not issubclass(XmlType, JsonType)
        assert not issubclass(XmlType, TextType)
        assert XmlType() != JsonType()
        assert XmlType() != TextType()

    def test_backends_without_xml_name_their_substitute(self):
        """Every dialect must take a position on ``xml`` — render it, or name
        the substitute. Silence is the one answer that is not allowed."""
        from rhosocial.activerecord.backend.impl.sqlite.dialect import (
            SQLiteDialect,
        )

        sqlite = SQLiteDialect()
        assert "xml" not in sqlite.supports_data_types()
        assert "xml" in sqlite.suggested_data_types()


# ---------------------------------------------------------------------------
# Type parsing
# ---------------------------------------------------------------------------


class TestTypeParsing:
    """SQLite type affinity parsing via DataTypeSupport."""

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
