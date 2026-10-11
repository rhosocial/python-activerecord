# tests/rhosocial/activerecord_test/feature/backend/ddl/test_sqlite_auto_increment.py
"""SQLite spells AUTOINCREMENT as part of INTEGER PRIMARY KEY, and nowhere else.

It used to be a flag on any column constraint, read only by a private SQLite
handler, and dropped without a word anywhere else. Twenty-three examples in
the tree were relying on that silence: they put the flag on a NOT NULL
constraint next to a PRIMARY KEY and got a table whose key did not
autoincrement.
"""
import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.types import SQLiteIntegerType


def definition(dialect, data_type, *constraints):
    return ColumnDefinition(dialect, "id", data_type, constraints=list(constraints))


def primary_key(dialect, **kwargs):
    return ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY, **kwargs)


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

    def test_on_another_constraint_kind(self):
        dialect = SQLiteDialect()
        column = definition(
            dialect,
            IntegerType(dialect),
            primary_key(dialect),
            ColumnConstraint(
                dialect, ColumnConstraintType.NOT_NULL, is_auto_increment=True
            ),
        )

        with pytest.raises(UnsupportedFeatureError, match="non-primary-key"):
            column.to_sql()

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
        "constraint_type, expected",
        (
            (ColumnConstraintType.PRIMARY_KEY, " PRIMARY KEY"),
            (ColumnConstraintType.NOT_NULL, " NOT NULL"),
            (ColumnConstraintType.NULL, " NULL"),
            (ColumnConstraintType.UNIQUE, " UNIQUE"),
        ),
    )
    def test_each_kind_renders_through_the_one_entry_point(self, constraint_type, expected):
        dialect = SQLiteDialect()
        constraint = ColumnConstraint(dialect, constraint_type)

        assert constraint.to_sql() == (expected, ())

    @pytest.mark.parametrize(
        "deleted",
        (
            "format_not_null_constraint",
            "format_null_constraint",
            "format_column_unique_constraint",
            "format_check_constraint",
        ),
    )
    def test_the_duplicates_no_longer_exist(self, deleted):
        """Names only SQLite ever defined; core's own methods are untouched."""
        assert not hasattr(SQLiteDialect, deleted)

    def test_two_paths_agree_for_every_kind(self):
        dialect = SQLiteDialect()
        for constraint_type in ColumnConstraintType:
            if constraint_type is ColumnConstraintType.PRIMARY_KEY:
                # SQLite's own handler appends AUTOINCREMENT, so it is covered
                # by the tests above rather than by this equality.
                continue
            kwargs = {}
            if constraint_type is ColumnConstraintType.DEFAULT:
                kwargs["default_value"] = 0
            constraint = ColumnConstraint(dialect, constraint_type, **kwargs)
            if constraint_type in (ColumnConstraintType.CHECK, ColumnConstraintType.FOREIGN_KEY):
                continue  # both need a payload this loop does not build
            column_sql, _ = definition(dialect, IntegerType(dialect), constraint).to_sql()
            constraint_sql, _ = constraint.to_sql()
            assert column_sql == f'"id" INTEGER{constraint_sql}'
