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
from rhosocial.activerecord.backend.expression.type_name import (
    InvalidTypeNameError,
    family_for_sql_type_name,
    is_valid_type_name,
    validate_type_name,
)
from rhosocial.activerecord.backend.expression.types import (
    CustomType,
    DecimalType,
    IntType,
    TextType,
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


FAMILIES = [
    ("INTEGER", "integer"),
    ("bigint", "integer"),
    ("numeric(10,2)", "numeric"),
    ("VARCHAR(10)", "string"),
    ("boolean", "boolean"),
    ("timestamp with time zone", "datetime"),
    ("jsonb", "json"),
    ("uuid", "uuid"),
    ("xml", "xml"),
    ("blob", "binary"),
]


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

    @pytest.mark.parametrize("name,family", FAMILIES)
    def test_family_matches_the_type(self, name, family):
        assert family_for_sql_type_name(name) == family

    def test_unknown_name_has_no_family(self):
        """An unrecognised type is unknown rather than guessed."""
        assert family_for_sql_type_name("some_extension_type") is None


class TestCastRequiresADataType:
    def test_cast_accepts_a_type_instance(self, sqlite_dialect):
        sql, _ = Column(sqlite_dialect, "c", table="t").cast(
            IntType(sqlite_dialect)
        ).to_sql()
        assert "AS INTEGER" in sql

    def test_cast_chains(self, sqlite_dialect):
        column = Column(sqlite_dialect, "c", table="t")
        sql, _ = column.cast(IntType(sqlite_dialect)).cast(
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


class TestFamilyTravelsWithTheType:
    def test_cast_to_a_known_type_knows_its_family(self, sqlite_dialect):
        cast = Column(sqlite_dialect, "c", table="t").cast(
            DecimalType(sqlite_dialect)
        )
        assert cast.VALUE_FAMILY == "numeric"

    def test_cast_to_an_unknown_type_stays_unknown(self, sqlite_dialect):
        """A type nothing recognises should not claim a family."""
        cast = Column(sqlite_dialect, "c", table="t").cast(
            CustomType(sqlite_dialect, raw="some_extension")
        )
        assert getattr(cast, "VALUE_FAMILY", None) is None