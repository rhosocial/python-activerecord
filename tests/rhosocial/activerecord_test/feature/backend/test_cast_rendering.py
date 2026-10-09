# tests/rhosocial/activerecord_test/feature/backend/test_cast_rendering.py
"""A cast renders its target and concatenates; it never interpolates it.

The target of a cast is a DataType, which is an expression, so it renders
itself through ``to_sql()`` and the cast wraps that. Interpolating the object
instead of rendering it is a mistake that type-checks and looks right in the
source: it produced ``col::IntegerType()`` on PostgreSQL, where ``col::INTEGER``
was meant. Nothing rejected it, because a Python object always has a ``str``.

So the assertions below are about the SQL that comes out, per family and per
parameter shape, and one of them exists only to fail if an object repr ever
reaches the statement again.
"""

import pytest

from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.types import (
    BooleanType,
    CustomType,
    DateType,
    DecimalType,
    FloatType,
    IntegerType,
    InvalidTypeNameError,
    JsonType,
    RealType,
    TextType,
    UUIDType,
    VarCharType,
)

#: A type, and the token the SQL has to contain. One per family, so a family
#: that stopped rendering would fail here rather than in someone's query.
TYPES = [
    (IntegerType, "INTEGER"),
    (IntegerType(spelling="int"), "INT"),
    (DecimalType, "DECIMAL"),
    (TextType, "TEXT"),
    (RealType, "REAL"),
    (FloatType, "FLOAT"),
    (DateType, "DATE"),
    (BooleanType, "BOOLEAN"),
    (JsonType, "JSON"),
]

#: What an object repr, a str() of an object, or a missed format_method would
#: leave in the statement. "Type" catches the class name; "None" catches an
#: unset parameter; the quotes catch a repr of a string field.
#: What an object repr, a str() of an object, or an unset parameter would leave
#: behind. Deliberately not substring checks on quotes: a correctly rendered
#: statement is full of them, and a leak check that fires on correct SQL is
#: worse than none.
LEAKS = ("Type(", "Type()", "(None", "(Decimal(", "object at 0x")


@pytest.fixture
def dialect():
    """A dialect of whichever backend is running this file.

    Constructed here rather than taken from a fixture so the file collects
    under any backend's test directory without depending on its fixtures.
    """
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

    return DummyDialect()


def column(dialect, name="price"):
    return Column(dialect, name, table="t")


class TestCastRendersItsTarget:
    @pytest.mark.parametrize("cls,token", TYPES)
    def test_each_family_reaches_the_sql(self, dialect, cls, token):
        sql, _ = column(dialect).cast(cls(dialect)).to_sql()
        assert token in sql

    @pytest.mark.parametrize("cls,token", TYPES)
    def test_no_object_repr_reaches_the_sql(self, dialect, cls, token):
        """The ``col::IntegerType()`` failure, as a standing check."""
        sql, _ = column(dialect).cast(cls(dialect)).to_sql()
        for leak in LEAKS:
            assert leak not in sql, f"{leak!r} leaked into {sql!r}"

    def test_a_backend_type_renders_its_own_sql_name(self):
        """``name`` is the dispatch key; the SQL spelling drops the prefix.

        Run against PostgreSQL rather than the shared fixture, because a
        backend type is rendered by that backend -- asking another one to render
        CITEXT tests nothing but the wrong thing.
        """
        types = pytest.importorskip(
            "rhosocial.activerecord.backend.impl.postgres.expression.types"
        )
        pytest.importorskip(
            "rhosocial.activerecord.backend.impl.postgres.dialect"
        )
        from rhosocial.activerecord.backend.impl.postgres.dialect import (
            PostgresDialect,
        )

        pg = PostgresDialect()
        pg._version = (16, 2, 0)
        citext = types.PostgresCitextType(pg)
        assert citext.name == "postgres_citext"
        assert "CITEXT" in Column(pg, "c", table="t").cast(citext).to_sql()[0]

    def test_a_custom_type_renders_its_name(self, dialect):
        sql, _ = column(dialect).cast(
            CustomType(dialect, raw="FLOAT8")
        ).to_sql()
        assert "FLOAT8" in sql


class TestParametersReachTheSql:
    @pytest.mark.parametrize(
        "make,expected",
        [
            # Built here rather than in parametrize: the type binds its dialect
            # at construction, and parametrize runs at collection time.
            (lambda d: VarCharType(d, length=100), "VARCHAR(100)"),
            (lambda d: VarCharType(d), "VARCHAR"),
            (lambda d: DecimalType(d, precision=10, scale=2), "DECIMAL(10,2)"),
            (lambda d: DecimalType(d, precision=10), "DECIMAL(10)"),
            (lambda d: DecimalType(d), "DECIMAL"),
        ],
    )
    def test_parameters_are_rendered(self, dialect, make, expected):
        """A precision is part of the type; dropping it changes the column."""
        sql, _ = column(dialect).cast(make(dialect)).to_sql()
        assert expected in sql


class TestChainedCasts:
    def test_every_layer_is_rendered(self, dialect):
        sql, _ = (
            column(dialect)
            .cast(IntegerType(dialect))
            .cast(DecimalType(dialect))
            .cast(TextType(dialect))
            .to_sql()
        )
        assert "INTEGER" in sql and "DECIMAL" in sql and "TEXT" in sql
        assert sql.count("::") + sql.count("CAST(") >= 3

    def test_chaining_is_associative_in_structure(self, dialect):
        one_shot, _ = column(dialect).cast(TextType(dialect)).to_sql()
        in_two, _ = (
            column(dialect)
            .cast(IntegerType(dialect))
            .cast(TextType(dialect))
            .to_sql()
        )
        # Two casts nest; the second type is what each expression yields.
        assert in_two.count("CAST(") == 2 or in_two.count("::") == 2
        assert one_shot != in_two


class TestCastIsNotLimitedToColumns:
    def test_a_literal(self, dialect):
        sql, params = Literal(dialect, 42).cast(IntegerType(dialect)).to_sql()
        assert "INTEGER" in sql
        assert params == (42,)

    def test_the_alias_lands_outside_the_cast(self, dialect):
        sql, _ = column(dialect).as_("p").cast(DecimalType(dialect)).to_sql()
        assert sql.endswith('AS "p"')
        assert 'AS "p"' in sql

    def test_aliasing_after_the_cast_is_the_same_statement(self, dialect):
        before, _ = column(dialect).as_("p").cast(DecimalType(dialect)).to_sql()
        after, _ = column(dialect).cast(DecimalType(dialect)).as_("p").to_sql()
        assert before == after


class TestCastRendersItsTarget:
    """A cast renders the type it was handed, whatever that type is.

    What the cast *is* afterwards is a separate question, and this pins only
    what the SQL says: the target renders itself and the cast wraps it. There
    used to be a family tag read back out of the type's name here as well, which
    said what the result would be rather than checking that it renders.
    """

    @pytest.mark.parametrize(
        "cls,token",
        [
            (IntegerType, "INTEGER"),
            (DecimalType, "DECIMAL"),
            (TextType, "TEXT"),
            (DateType, "DATE"),
            (JsonType, "JSON"),
            (BooleanType, "BOOLEAN"),
        ],
    )
    def test_the_target_reaches_the_statement(self, dialect, cls, token):
        sql, _ = column(dialect).cast(cls(dialect)).to_sql()
        assert f"AS {token}" in sql

    def test_a_user_defined_type_renders_verbatim(self, dialect):
        """Nothing here knows what a GEOMETRY is, so nothing rewrites it.

        The cast cannot offer the operations of a type it has no class for,
        which is why it says nothing rather than guessing; rendering the name
        the caller gave is all it can honestly do.
        """
        sql, _ = column(dialect).cast(
            CustomType(dialect, raw="some_extension")
        ).to_sql()
        assert "AS some_extension" in sql


class TestCastTakesOnlyAType:
    """The type position cannot be bound, so free text there is SQL code."""

    @pytest.mark.parametrize(
        "value", ["INTEGER", "DECIMAL(10,2)", 123, None, object(), 42]
    )
    def test_refused(self, dialect, value):
        with pytest.raises(TypeError):
            column(dialect).cast(value)

    def test_a_string_carrying_an_injection_is_refused(self, dialect):
        with pytest.raises(TypeError):
            column(dialect).cast("INTEGER); DROP TABLE users; --")

    @pytest.mark.parametrize(
        "raw",
        [
            "INTEGER); DROP TABLE users; --",
            "INTEGER, (SELECT password FROM users)",
            "INTEGER'",
            "INTEGER --x",
            "",
            ",,,",
        ],
    )
    def test_a_custom_type_validates_its_name(self, dialect, raw):
        with pytest.raises(InvalidTypeNameError):
            CustomType(dialect, raw=raw)

    @pytest.mark.parametrize(
        "raw", ["mytype", "my_schema.my_type", "text[]", "double precision"]
    )
    def test_a_custom_type_keeps_a_real_name(self, dialect, raw):
        assert CustomType(dialect, raw=raw).raw == raw
