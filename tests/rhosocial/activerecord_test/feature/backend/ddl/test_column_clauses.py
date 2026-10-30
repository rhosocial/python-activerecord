# tests/rhosocial/activerecord_test/feature/backend/ddl/test_column_clauses.py
"""Column-definition clauses are expression nodes, not AR-layer objects.

``COLLATE`` and ``CHARACTER SET`` used to be reachable only by putting an
AR-layer ``ColumnAttribute`` into ``ColumnDefinition.attributes``, which put a
reverse dependency in the dialect: the formatter's subject was not an
expression. These tests pin the new shape (an expression node is the subject),
the capability gates, and the transitional AR route that still has to work
until a deriver exists.
"""
import pytest
from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
)
from rhosocial.activerecord.base.ddl import (
    CharacterSetAttribute,
    CollationAttribute,
    IdentityAttribute,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
from rhosocial.activerecord.backend.expression.statements import (
    CharacterSetClause,
    CollationClause,
    ColumnConstraint,
    ColumnDefinition,
    IdentityClause,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError



def probed(**answers):
    """Return a dialect class whose capability probes answer as ``answers``."""
    namespace = {
        name: (lambda self, answer=answer: answer)
        for name, answer in answers.items()
    }
    return type("ProbedDialect", (SQLiteDialect,), namespace)


def column_with(dialect, *clauses):
    return ColumnDefinition(dialect, "c", TextType(dialect), attributes=list(clauses))


class TestClauseNodes:
    """The nodes exist, name their formatter, and validate their one field."""

    def test_each_names_its_formatter(self):
        dialect = SQLiteDialect()

        assert CollationClause(dialect, "NOCASE").format_method == "format_collation_clause"
        assert (
            CharacterSetClause(dialect, "utf8mb4").format_method
            == "format_character_set_clause"
        )

    @pytest.mark.parametrize(
        "factory", (CollationClause, CharacterSetClause)
    )
    @pytest.mark.parametrize("bad", ("", "   ", None, 7))
    def test_a_name_is_required(self, factory, bad):
        dialect = SQLiteDialect()

        with pytest.raises((ValueError, TypeError)):
            factory(dialect, bad)

    def test_a_clause_with_no_formatter_says_so(self):
        """The base class refuses to pretend a formatter exists."""
        from rhosocial.activerecord.backend.expression.statements import ColumnClause

        dialect = SQLiteDialect()
        clause = ColumnClause(dialect)

        with pytest.raises(NotImplementedError, match="ColumnClause"):
            _ = clause.format_method


class TestCollationClause:
    """COLLATE renders as a clause, and only where the dialect has one."""

    def test_renders(self):
        dialect = SQLiteDialect()

        assert dialect.format_column_attribute(
            CollationClause(dialect, "NOCASE")
        ) == (" COLLATE NOCASE", ())

    def test_inside_a_column_definition(self):
        dialect = SQLiteDialect()

        sql, params = column_with(dialect, CollationClause(dialect, "NOCASE")).to_sql()

        assert params == ()
        assert sql.endswith("COLLATE NOCASE")

    def test_refused_where_unsupported(self):
        dialect = probed(supports_column_collation=False)()

        with pytest.raises(UnsupportedFeatureError, match="COLLATE"):
            dialect.format_column_attribute(CollationClause(dialect, "NOCASE"))

    def test_a_dialect_may_quote_the_specification_instead(self):
        """Snowflake and BigQuery spell COLLATE as a quoted string literal."""
        dialect = probed()()

        def quoted(clause):
            return f" COLLATE '{clause.name}'", ()

        dialect.format_collation_clause = quoted

        assert dialect.format_column_attribute(
            CollationClause(dialect, "und:ci")
        ) == (" COLLATE 'und:ci'", ())


class TestCharacterSetClause:
    """CHARACTER SET renders as a clause, gated because it is a MySQL-family
    construct rather than part of the standard column grammar."""

    def test_renders_where_supported(self):
        dialect = probed(supports_column_character_set=True)()

        assert dialect.format_column_attribute(
            CharacterSetClause(dialect, "utf8mb4")
        ) == (" CHARACTER SET utf8mb4", ())

    def test_refused_where_unsupported(self):
        dialect = SQLiteDialect()  # declares character sets unsupported

        with pytest.raises(UnsupportedFeatureError, match="CHARACTER SET"):
            dialect.format_column_attribute(CharacterSetClause(dialect, "utf8mb4"))


class TestArLayerRouteStillWorks:
    """The AR layer has no deriver yet, so its attributes still have to render.

    These are the tests that say when the transitional route may be deleted:
    once a deriver turns ``UseColumnAttributes`` into clauses, this whole class
    goes with it.
    """

    def test_collation_attribute_still_renders(self):
        dialect = SQLiteDialect()

        sql, _ = column_with(dialect, CollationAttribute(name="NOCASE")).to_sql()

        assert sql.endswith("COLLATE NOCASE")

    def test_character_set_attribute_still_renders_where_supported(self):
        dialect = probed(supports_column_character_set=True)()

        sql, _ = column_with(dialect, CharacterSetAttribute(name="utf8")).to_sql()

        assert sql.endswith("CHARACTER SET utf8")

    def test_identity_attribute_still_renders(self):
        dialect = probed(
            supports_identity_column=True,
            supports_identity_generation_always=True,
            supports_identity_start=True,
            supports_identity_increment=True,
        )()

        sql, _ = column_with(
            dialect, IdentityAttribute(generation="ALWAYS", start=1, increment=2)
        ).to_sql()

        assert "GENERATED ALWAYS AS IDENTITY" in sql

    def test_an_unknown_clause_is_refused_by_name(self):
        dialect = SQLiteDialect()

        with pytest.raises(UnsupportedFeatureError, match="object"):
            dialect.format_column_attribute(object())


class TestClauseOrderIsTheCallersOrder:
    """The sequence is spelled in the order it was built."""

    def test_two_clauses_keep_their_order(self):
        dialect = probed(
            supports_column_collation=True, supports_column_character_set=True
        )()
        clauses = [
            CollationClause(dialect, "NOCASE"),
            CharacterSetClause(dialect, "utf8mb4"),
        ]

        sql, _ = column_with(dialect, *clauses).to_sql()

        assert sql.index("COLLATE") < sql.index("CHARACTER SET")

    def test_reversing_the_sequence_reverses_the_sql(self):
        dialect = probed(
            supports_column_collation=True, supports_column_character_set=True
        )()

        forward, _ = column_with(
            dialect,
            CollationClause(dialect, "NOCASE"),
            CharacterSetClause(dialect, "utf8mb4"),
        ).to_sql()
        backward, _ = column_with(
            dialect,
            CharacterSetClause(dialect, "utf8mb4"),
            CollationClause(dialect, "NOCASE"),
        ).to_sql()

        assert forward != backward


class TestUnrelatedClausesUnaffected:
    """A column definition's other channels still render as before."""

    def test_constraints_and_clauses_coexist(self):
        dialect = probed(supports_column_collation=True)()
        definition = ColumnDefinition(
            dialect,
            "c",
            IntegerType(dialect),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))],
            attributes=[CollationClause(dialect, "NOCASE")],
        )

        sql, params = definition.to_sql()

        assert params == ()
        assert "NOT NULL" in sql and "COLLATE NOCASE" in sql

    def test_identity_clause_is_still_dispatched_by_format_method(self):
        dialect = probed(supports_identity_column=True)()
        clause = IdentityClause(dialect, "BY DEFAULT")

        assert dialect.format_column_attribute(clause) == (
            dialect.format_identity_clause(clause)
        )
