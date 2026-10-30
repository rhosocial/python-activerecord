# tests/rhosocial/activerecord_test/feature/backend/ddl/test_sqlite_auto_increment.py
"""SQLite spells AUTOINCREMENT as part of INTEGER PRIMARY KEY, and nowhere else.

It used to be a flag on any column constraint, read only by a private SQLite
handler, and dropped without a word anywhere else. Twenty-three examples in
the tree were relying on that silence: they put the flag on a NOT NULL
constraint next to a PRIMARY KEY and got a table whose key did not
autoincrement.
"""
import pytest
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefaultConstraint,
    ColumnNotNullConstraint,
    ColumnNullableConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnUniqueConstraint,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.types import SQLiteIntegerType
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnDefinition,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError



def definition(dialect, data_type, *constraints):
    return ColumnDefinition(dialect, "id", data_type, constraints=list(constraints))


def primary_key(dialect, **kwargs):
    return ColumnConstraint(
        dialect, branch=ColumnPrimaryKeyConstraint(dialect, **kwargs)
    )


class TestAutoIncrementRenders:
    def test_integer_primary_key(self):
        dialect = SQLiteDialect()
        column = definition(dialect, IntegerType(dialect), primary_key(dialect, is_auto_increment=True))

        assert column.to_sql()[0] == '"id" INTEGER PRIMARY KEY AUTOINCREMENT'

    def test_the_sqlite_integer_spelling_too(self):
        dialect = SQLiteDialect()
        column = definition(
            dialect,
            SQLiteIntegerType(dialect),
            primary_key(dialect, is_auto_increment=True),
        )

        assert "AUTOINCREMENT" in column.to_sql()[0]

    def test_without_the_flag_there_is_no_marker(self):
        dialect = SQLiteDialect()
        column = definition(dialect, IntegerType(dialect), primary_key(dialect))

        assert column.to_sql()[0] == '"id" INTEGER PRIMARY KEY'


class TestAutoIncrementRefusedElsewhere:
    """SQLite would reject the SQL, so the request is refused by name."""

    def test_the_flag_belongs_to_the_primary_key_branch_alone(self):
        """The refusal is structural now: no other branch has the field.

        What SQLite used to refuse at render time -- a flag on a constraint
        kind that has nowhere to spell it -- is no longer expressible: the flag
        is a field of the primary-key branch, and the other branches do not
        declare it, so ``is_auto_increment=True`` cannot reach them at all.
        """

        assert "is_auto_increment" in ColumnPrimaryKeyConstraint.__init__.__code__.co_varnames
        for branch_cls in (
            ColumnNotNullConstraint,
            ColumnNullableConstraint,
            ColumnUniqueConstraint,
        ):
            assert "is_auto_increment" not in branch_cls.__init__.__code__.co_varnames

    def test_on_a_non_integer_column(self):
        dialect = SQLiteDialect()
        column = definition(
            dialect, TextType(dialect), primary_key(dialect, is_auto_increment=True)
        )

        with pytest.raises(UnsupportedFeatureError, match="non-INTEGER"):
            column.to_sql()


class TestPrivateHandlersAreGone:
    """The SQLite-specific copies of the shared renderers are deleted.

    Every column constraint now goes through one public entry point, so a
    constraint cannot render one way inside CREATE TABLE and another way on its
    own.
    """

    @pytest.mark.parametrize(
        "branch_cls, expected",
        (
            (ColumnPrimaryKeyConstraint, " PRIMARY KEY"),
            (ColumnNotNullConstraint, " NOT NULL"),
            (ColumnNullableConstraint, " NULL"),
            (ColumnUniqueConstraint, " UNIQUE"),
        ),
    )
    def test_each_kind_renders_through_the_one_entry_point(self, branch_cls, expected):
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, branch=branch_cls(dialect))

        assert constraint.to_sql() == (expected, ())

    @pytest.mark.parametrize(
        "deleted",
        (
            "format_not_null_constraint",
            "format_null_constraint",
            "format_unique_constraint",
            "format_check_constraint",
        ),
    )
    def test_the_duplicates_no_longer_exist(self, deleted):
        """Names only SQLite ever defined; core's own methods are untouched."""
        assert not hasattr(SQLiteDialect, deleted)

    def test_two_paths_agree_for_every_kind(self):
        dialect = SQLiteDialect()
        for branch in (
            ColumnNotNullConstraint(dialect),
            ColumnNullableConstraint(dialect),
            ColumnUniqueConstraint(dialect),
            ColumnDefaultConstraint(dialect, 0),
        ):
            constraint = ColumnConstraint(dialect, branch=branch)
            column_sql, _ = definition(dialect, IntegerType(dialect), constraint).to_sql()
            constraint_sql, _ = constraint.to_sql()
            assert column_sql == f'"id" INTEGER{constraint_sql}'
