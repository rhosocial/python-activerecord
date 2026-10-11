# tests/rhosocial/activerecord_test/feature/backend/ddl/test_foreign_key_match.py
"""MATCH is a typed field on every constraint that can carry it.

It used to be three different shapes: a bare ``str`` on ``ReferencesClause``,
a bare ``str`` reachable only through the ``ForeignKeyConstraint`` subclass,
and nothing at all on ``ColumnConstraint``. So a column-level
``REFERENCES ... MATCH FULL`` could not be written, and the value was
re-validated by hand inside the formatter on every render.
"""
import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.mixins.ddl_table import (
    normalize_foreign_key_match_type,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
    ForeignKeyConstraint,
    ForeignKeyMatchType,
    ReferentialAction,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def probed(**answers):
    namespace = {
        name: (lambda self, answer=answer: answer)
        for name, answer in answers.items()
    }
    return type("ProbedDialect", (SQLiteDialect,), namespace)


def column_fk(dialect, **kwargs):
    return ColumnConstraint(
        dialect,
        ColumnConstraintType.FOREIGN_KEY,
        foreign_key_reference=(Table(dialect, "parent"), ["id"]),
        **kwargs,
    )


class TestNormalizer:
    """The normalizer accepts a member, its value, or its name, in any case."""

    @pytest.mark.parametrize(
        "given, expected",
        (
            (ForeignKeyMatchType.FULL, ForeignKeyMatchType.FULL),
            ("FULL", ForeignKeyMatchType.FULL),
            ("full", ForeignKeyMatchType.FULL),
            ("  Partial  ", ForeignKeyMatchType.PARTIAL),
            ("SIMPLE", ForeignKeyMatchType.SIMPLE),
        ),
    )
    def test_accepted_spellings(self, given, expected):
        assert normalize_foreign_key_match_type(given) is expected

    def test_none_means_not_specified(self):
        """None is not SIMPLE: a dialect may treat the default differently."""
        assert normalize_foreign_key_match_type(None) is None

    @pytest.mark.parametrize("bad", ("MATCH", "FULL PARTIAL", "", 3))
    def test_a_bad_value_is_refused_by_name(self, bad):
        with pytest.raises(ValueError, match="MATCH type"):
            normalize_foreign_key_match_type(bad)


class TestEnumRendersItsSqlSpelling:
    """A dialect may interpolate the member directly."""

    def test_str_is_the_sql_word(self):
        assert str(ForeignKeyMatchType.PARTIAL) == "PARTIAL"
        assert f"{ForeignKeyMatchType.FULL}" == "FULL"


class TestColumnLevelMatch:
    """The point of the change: a column-level MATCH is expressible."""

    def test_renders(self):
        dialect = probed(supports_fk_match=True)()

        assert column_fk(dialect, match_type="FULL").to_sql() == (
            ' REFERENCES "parent"("id") MATCH FULL',
            (),
        )

    def test_accepts_the_member_too(self):
        dialect = probed(supports_fk_match=True)()
        constraint = column_fk(dialect, match_type=ForeignKeyMatchType.PARTIAL)

        assert "MATCH PARTIAL" in constraint.to_sql()[0]

    def test_refused_where_unsupported(self):
        dialect = probed(supports_fk_match=False)()

        with pytest.raises(UnsupportedFeatureError, match="MATCH"):
            column_fk(dialect, match_type="FULL").to_sql()

    def test_no_match_type_renders_nothing_extra(self):
        dialect = probed(supports_fk_match=True)()

        assert "MATCH" not in column_fk(dialect).to_sql()[0]

    def test_a_bad_value_is_refused(self):
        dialect = probed(supports_fk_match=True)()

        with pytest.raises(ValueError, match="MATCH type"):
            column_fk(dialect, match_type="HALF").to_sql()


class TestTableLevelMatchNeedsNoSubclass:
    """The fields are on the base, so no formatter has to ask which class it got."""

    def test_a_plain_table_constraint_carries_the_actions(self):
        dialect = probed(supports_fk_match=True)()
        constraint = TableConstraint(
            dialect,
            TableConstraintType.FOREIGN_KEY,
            columns=["a"],
            foreign_key_table=Table(dialect, "parent"),
            foreign_key_columns=["id"],
            match_type="FULL",
        )

        assert constraint.match_type == "FULL"
        assert "MATCH FULL" in constraint.to_sql()[0]

    def test_the_subclass_still_works_and_still_defaults_the_actions(self):
        dialect = probed(supports_fk_match=True)()
        constraint = ForeignKeyConstraint(
            dialect,
            columns=["a"],
            foreign_key_table=Table(dialect, "parent"),
            foreign_key_columns=["id"],
            match_type="FULL",
        )

        assert isinstance(constraint, TableConstraint)
        assert constraint.on_delete is ReferentialAction.NO_ACTION
        assert "MATCH FULL" in constraint.to_sql()[0]

    def test_the_base_leaves_the_actions_unspecified(self):
        dialect = probed(supports_fk_match=True)()
        constraint = TableConstraint(
            dialect,
            TableConstraintType.FOREIGN_KEY,
            columns=["a"],
            foreign_key_table=Table(dialect, "parent"),
            foreign_key_columns=["id"],
        )

        assert constraint.on_delete is None
        assert "ON DELETE" not in constraint.to_sql()[0]


class TestActionsOnANonForeignKey:
    """The fields mean nothing on a PRIMARY KEY, and are never rendered."""

    def test_a_primary_key_keeps_but_ignores_them(self):
        dialect = probed(supports_fk_match=True)()
        constraint = TableConstraint(
            dialect,
            TableConstraintType.PRIMARY_KEY,
            columns=["a"],
            match_type="FULL",
        )

        assert constraint.match_type == "FULL"
        assert constraint.to_sql()[0] == 'PRIMARY KEY ("a")'
