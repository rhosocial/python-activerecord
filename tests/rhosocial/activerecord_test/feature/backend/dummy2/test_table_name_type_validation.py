# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_table_name_type_validation.py
"""Tests for relation-object type validation in CreateTableExpression and DropTableExpression.

Both statements name the relation they act on, so both take a
:class:`~rhosocial.activerecord.backend.expression.objects.Table` rather than a
string. A string says how to spell a name; it does not say *which kind of object*
is named, and that is exactly the distinction these classes exist to draw.

An alias is not part of this contract at all: ``FROM users AS u`` renames a row
for one statement and renames nothing in the catalogue, so an alias lives on
:class:`~...expression.sources.NamedRelationRef`, never on the object.
"""

import pytest

from typing import List

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    DropTableExpression,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


def primary_key_columns(dialect: DummyDialect) -> List[ColumnDefinition]:
    """One primary-key column: the minimum a CREATE TABLE needs to be a test."""
    return [
        ColumnDefinition(
            dialect,
            name="id",
            data_type=IntegerType(dialect),
            constraints=[ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY)],
        )
    ]


class TestCreateTableExpressionTypeValidation:
    """Tests for CreateTableExpression relation type validation."""

    def test_create_table_keeps_the_object_it_was_given(self, dummy_dialect: DummyDialect):
        """The statement holds the caller's object rather than rebuilding one."""
        table = Table(dummy_dialect, "users")
        expr = CreateTableExpression(dummy_dialect, table, primary_key_columns(dummy_dialect))

        assert expr.table is table
        assert expr.table.name == "users"
        assert expr.table.schema_name is None

    def test_create_table_renders_the_object_name(self, dummy_dialect: DummyDialect):
        """Naming the table is the object's job, reached through to_sql()."""
        expr = CreateTableExpression(
            dummy_dialect, Table(dummy_dialect, "users"), primary_key_columns(dummy_dialect)
        )

        sql, params = expr.to_sql()

        assert sql == 'CREATE TABLE "users" ("id" INTEGER PRIMARY KEY)'
        assert params == ()

    def test_create_table_reports_the_table_name(self, dummy_dialect: DummyDialect):
        """``table_name`` reads through to the object it names."""
        expr = CreateTableExpression(
            dummy_dialect, Table(dummy_dialect, "users"), primary_key_columns(dummy_dialect)
        )

        assert expr.table_name == "users"

    def test_create_table_refuses_an_unqualified_namespace(self, dummy_dialect: DummyDialect):
        """A qualified name is the object's to carry; rendering is the dialect's."""
        table = Table(dummy_dialect, "users", schema_name="public")
        expr = CreateTableExpression(dummy_dialect, table, primary_key_columns(dummy_dialect))

        assert expr.table is table
        assert expr.table.schema_name == "public"
        # Dummy declares no namespace, so the qualification is refused rather
        # than silently dropped.
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            expr.to_sql()
        assert "schema-qualified" in str(exc_info.value)

    @pytest.mark.parametrize(
        "value,expected",
        [
            (123, "table must be a Table, got int"),
            (None, "table must be a Table, got NoneType"),
            ([], "table must be a Table, got list"),
            ({"name": "users"}, "table must be a Table, got dict"),
        ],
    )
    def test_create_table_rejects_a_non_table(self, dummy_dialect: DummyDialect, value, expected):
        """Anything that is not a relation object is refused, by name.

        The statement collects the value it was given; the dialect that would
        render it as the table's name is the one that refuses, so the error
        arrives from ``to_sql()``.
        """
        expr = CreateTableExpression(dummy_dialect, value, primary_key_columns(dummy_dialect))
        with pytest.raises(TypeError) as exc_info:
            expr.to_sql()
        assert expected in str(exc_info.value)


class TestDropTableExpressionTypeValidation:
    """Tests for DropTableExpression relation type validation."""

    def test_drop_table_keeps_the_object_it_was_given(self, dummy_dialect: DummyDialect):
        """The statement holds the caller's object rather than rebuilding one."""
        table = Table(dummy_dialect, "users")
        expr = DropTableExpression(dummy_dialect, table)

        assert expr.table is table
        assert expr.table.name == "users"
        assert expr.table.schema_name is None

        sql, params = expr.to_sql()
        assert sql == 'DROP TABLE "users"'
        assert params == ()

    def test_drop_table_honours_its_own_flags(self, dummy_dialect: DummyDialect):
        """IF EXISTS belongs to the statement, not to the object."""
        expr = DropTableExpression(dummy_dialect, Table(dummy_dialect, "users"), if_exists=True)

        sql, params = expr.to_sql()
        assert sql == 'DROP TABLE IF EXISTS "users"'
        assert params == ()

    def test_drop_table_refuses_an_unqualified_namespace(self, dummy_dialect: DummyDialect):
        """A qualified object renders only where the dialect has a namespace."""
        expr = DropTableExpression(
            dummy_dialect, Table(dummy_dialect, "users", schema_name="public"), cascade=True
        )

        assert expr.table.schema_name == "public"
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            expr.to_sql()
        assert "schema-qualified" in str(exc_info.value)

    @pytest.mark.parametrize(
        "value,expected",
        [
            (123, "table must be a Table, got int"),
            (None, "table must be a Table, got NoneType"),
            ([], "table must be a Table, got list"),
            ({"name": "users"}, "table must be a Table, got dict"),
        ],
    )
    def test_drop_table_rejects_a_non_table(self, dummy_dialect: DummyDialect, value, expected):
        """Anything that is not a relation object is refused, by name.

        The statement collects the value it was given; the dialect that would
        render it after DROP TABLE is the one that refuses.
        """
        expr = DropTableExpression(dummy_dialect, value)
        with pytest.raises(TypeError) as exc_info:
            expr.to_sql()
        assert expected in str(exc_info.value)

    def test_a_relation_object_carries_no_alias(self, dummy_dialect: DummyDialect):
        """An alias renames a row, not a catalogue entry, so it is not here."""
        table = Table(dummy_dialect, "users")

        assert not hasattr(table, "alias")
        assert not hasattr(table, "temporal_options")
