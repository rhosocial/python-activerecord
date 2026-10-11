# tests/rhosocial/activerecord_test/feature/backend/test_cast_type_safety.py
"""The type position of a cast cannot take a bound parameter.

A type name is a grammar production, not an expression, so every database
renders it straight into the statement. That makes a cast target the one place
in a query where a user-supplied string becomes SQL code rather than SQL data.
These tests pin the two guarantees that close it: a cast takes a DataType, and a
raw type name is a validated grammar rather than free text.
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.types import (
    CustomType,
    DecimalType,
    IntegerType,
    TextType,
)
from rhosocial.activerecord.backend.expression.type_name import (
    InvalidTypeNameError,
    is_valid_type_name,
    validate_type_name,
)
from rhosocial.activerecord.backend.expression.advanced_functions import (
    JSONTextExpression,
    JSONDocumentExpression,
)
from rhosocial.activerecord.backend.expression.core import (
    NumericValueExpression,
    IntegerValueExpression,
    StringValueExpression,
    BooleanValueExpression,
    BinaryValueExpression,
    UUIDValueExpression,
    JSONValueExpression,
    ArrayValueExpression,
    TimestampValueExpression,
    DateValueExpression,
    TimeValueExpression,
    IntervalValueExpression,
)

#: Payloads that turn a cast target into a second statement, a subquery, or a
#: comment. Each one would be harmless as a bound value, which is exactly the
#: point: the type position is the only place it would not be.
PAYLOADS = [
    "INTEGER); DROP TABLE users; --",
    "INTEGER, (SELECT password FROM users)",
    "INTEGER; DELETE FROM accounts",
    "INTEGER'",
    'INTEGER"',
    "INTEGER -- comment",
    "INTEGER/*comment*/",
    "INTEGER\n; DROP TABLE t",
    "",
    ",,,",
    "   ",
]

#: Type names real databases accept, including the multi-word and
#: schema-qualified spellings that a careless character filter would reject.
VALID_NAMES = [
    "INTEGER",
    "VARCHAR(255)",
    "NUMERIC(10,2)",
    "Decimal(38, 10)",
    "text[]",
    "int[][]",
    "myschema.mytype",
    "my_schema.my_type",
    "double precision",
    "character varying(20)",
    "character large object",
    "timestamp(3) with time zone",
    "time(6) without time zone",
    "TIMESTAMP WITH TIME ZONE",
    "unsigned int",
    "hstore",
    "ltree",
    "vector",
]

@pytest.fixture
def sqlite_dialect():
    """A dialect of the backend this file runs against.

    Built locally rather than shared so the file can be collected by any
    backend's test directory without depending on that backend's fixtures.
    """
    return SQLiteDialect()


class TestTypeNameGrammar:
    """A type name is a name, so it is parsed as one."""

    @pytest.mark.parametrize("name", VALID_NAMES)
    def test_accepts_names_databases_accept(self, name):
        assert is_valid_type_name(name), f"{name!r} is a legitimate type name"

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_rejects_injection_payloads(self, payload):
        assert not is_valid_type_name(payload)

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_validate_raises_on_payload(self, payload):
        """validate_type_name reports a bad name by raising."""
        with pytest.raises(InvalidTypeNameError):
            validate_type_name(payload)

    def test_predicate_does_not_raise(self):
        """The predicate answers a question; it does not raise to report."""
        assert is_valid_type_name(None) is False
        assert is_valid_type_name(123) is False

    @pytest.mark.parametrize(
        "name",
        [
            "INTEGER",
            "bigint",
            "numeric(10,2)",
            "VARCHAR(10)",
            "boolean",
            "timestamp with time zone",
            "jsonb",
            "uuid",
            "xml",
            "blob",
        ],
    )
    def test_real_type_names_are_accepted_as_names(self, name):
        """Each of these is a type a database has.

        They used to be pinned to the value family a cast to them produces,
        which no longer exists: ``cast`` now answers with the class of the type
        it was handed, so there is no name-to-family table to be right about.
        What still matters is that the name is recognised as a name, whatever
        the type behind it means.
        """
        assert is_valid_type_name(name)

    def test_an_unknown_type_name_is_still_a_valid_name(self):
        """Grammar and meaning are separate questions.

        ``some_extension_type`` names nothing this package knows, but it is
        still shaped like a type name, so it passes the grammar and fails at
        the dialect that cannot render it -- not here.
        """
        assert is_valid_type_name("some_extension_type")


class TestCastRequiresADataType:
    def test_cast_accepts_a_type_instance(self, sqlite_dialect):
        sql, _ = Column(sqlite_dialect, "c", table="t").cast(
            IntegerType(sqlite_dialect)
        ).to_sql()
        assert "AS INTEGER" in sql

    def test_cast_renders_the_spelling_it_was_given(self, sqlite_dialect):
        """``INT`` and ``INTEGER`` are one type with two spellings, so the
        spelling reaches the statement instead of being normalised away."""
        sql, _ = Column(sqlite_dialect, "c", table="t").cast(
            IntegerType(sqlite_dialect, spelling="int")
        ).to_sql()
        assert "AS INT)" in sql

    def test_cast_chains(self, sqlite_dialect):
        column = Column(sqlite_dialect, "c", table="t")
        sql, _ = column.cast(IntegerType(sqlite_dialect)).cast(
            TextType(sqlite_dialect)
        ).to_sql()
        assert sql.count("CAST(") == 2

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_cast_rejects_a_string(self, sqlite_dialect, payload):
        column = Column(sqlite_dialect, "c", table="t")
        with pytest.raises(TypeError):
            column.cast(payload)

    def test_cast_rejects_a_non_type(self, sqlite_dialect):
        with pytest.raises(TypeError):
            Column(sqlite_dialect, "c", table="t").cast(object())


class TestCustomTypeValidatesItsName:
    """CustomType exists so unknown names stay reachable, not so they stay raw."""

    @pytest.mark.parametrize("name", ["mytype", "my_schema.my_type", "text[]"])
    def test_accepts_a_real_name(self, sqlite_dialect, name):
        assert CustomType(sqlite_dialect, raw=name).raw == name

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_rejects_an_injection(self, sqlite_dialect, payload):
        with pytest.raises(InvalidTypeNameError):
            CustomType(sqlite_dialect, raw=payload)


class TestCastRendersWhateverItWasGiven:
    def test_the_target_reaches_the_statement(self, sqlite_dialect):
        cast = Column(sqlite_dialect, "c", table="t").cast(
            DecimalType(sqlite_dialect)
        )
        sql, _ = cast.to_sql()
        assert "AS NUMERIC" in sql

    def test_an_unknown_type_is_still_rendered(self, sqlite_dialect):
        """A user-defined type has no value class, so nothing re-spells it.

        The cast can only say what it was told, which is what this checks: the
        name survives to the statement rather than being dropped or guessed at.
        """
        cast = Column(sqlite_dialect, "c", table="t").cast(
            CustomType(sqlite_dialect, raw="some_extension")
        )
        sql, _ = cast.to_sql()
        assert "some_extension" in sql