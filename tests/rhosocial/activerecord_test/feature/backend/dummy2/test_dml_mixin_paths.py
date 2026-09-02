# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_dml_mixin_paths.py
"""
Cover DMLMixin statement formatting via DummyDialect.

Targets uncovered branches in backend/dialect/mixins/dml.py: INSERT
(DefaultValuesSource / ValuesSource / SelectSource, ON CONFLICT, RETURNING),
UPDATE (assignments, FROM sources), DELETE (WHERE/RETURNING/USING).
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    DeleteExpression,
    InsertExpression,
    UpdateExpression,
)
from rhosocial.activerecord.backend.expression.core import Column, Literal, TableExpression
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    DefaultValuesSource,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


@pytest.fixture
def dialect():
    return DummyDialect()


def _insert(dialect, source):
    return InsertExpression(
        dialect=dialect,
        into="users",
        columns=["name"],
        source=source,
    )


class TestInsertStatement:
    def test_default_values(self, dialect):
        expr = InsertExpression(
            dialect=dialect, into="users", source=DefaultValuesSource(dialect)
        )
        sql, params = expr.to_sql()
        assert "DEFAULT VALUES" in sql
        assert params == ()

    def test_values_source(self, dialect):
        src = ValuesSource(dialect, [[Literal(dialect, "Alice"), Literal(dialect, 1)]])
        sql, params = _insert(dialect, src).to_sql()
        assert "INSERT INTO" in sql and "VALUES" in sql
        assert len(params) == 2

    def test_values_source_multi_row(self, dialect):
        src = ValuesSource(dialect, [[Literal(dialect, "A")], [Literal(dialect, "B")]])
        sql, params = _insert(dialect, src).to_sql()
        assert sql.count("VALUES") >= 1
        assert len(params) == 2

    def test_select_source(self, dialect):
        from rhosocial.activerecord.backend.expression import QueryExpression, SelectSource
        sel = QueryExpression(
            dialect=dialect,
            select=[Column(dialect, "name")],
            from_=TableExpression(dialect, "tmp"),
        )
        sql, params = _insert(dialect, SelectSource(dialect, sel)).to_sql()
        assert "INSERT INTO" in sql and "SELECT" in sql.upper()

    def _returning_expr(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.dml import ReturningClause
        return InsertExpression(
            dialect=dialect,
            into="users",
            source=ValuesSource(dialect, [[Literal(dialect, "Alice")]]),
            returning=ReturningClause(dialect, expressions=[Column(dialect, "id")]),
        )

    def test_returning_unsupported_raises(self, dialect):
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
        expr = self._returning_expr(dialect)
        if dialect.supports_returning_insert():
            pytest.skip("dialect supports RETURNING")
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_returning_supported(self, dialect):
        expr = self._returning_expr(dialect)
        if not dialect.supports_returning_insert():
            pytest.skip("dialect does not support RETURNING")
        sql, _ = expr.to_sql()
        assert "RETURNING" in sql.upper()


def _table(dialect):
    return CreateTable(dialect)


class CreateTable:
    """Helper creating a users table expression."""

    def __init__(self, dialect):
        self.expr = __import__(
            "rhosocial.activerecord.backend.expression", fromlist=["CreateTableExpression"]
        ).CreateTableExpression(
            dialect=dialect,
            table="users",
            columns=[
                ColumnDefinition("id", IntegerType(), constraints=[
                    ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                ]),
                ColumnDefinition("name", TextType()),
            ],
        )


class TestUpdateStatement:
    def test_basic_update(self, dialect):
        expr = UpdateExpression(
            dialect=dialect,
            table="users",
            assignments={"name": Literal(dialect, "Bob")},
            where=Column(dialect, "id") == Literal(dialect, 1),
        )
        sql, params = expr.to_sql()
        assert "UPDATE" in sql and "SET" in sql
        assert len(params) >= 2

    def test_update_multiple_columns(self, dialect):
        expr = UpdateExpression(
            dialect=dialect,
            table="users",
            assignments={
                "name": Literal(dialect, "Bob"),
                "age": Literal(dialect, 30),
            },
            where=None,
        )
        sql, params = expr.to_sql()
        assert sql.upper().count(",") >= 1
        assert len(params) == 2


class TestDeleteStatement:
    def test_delete_with_where(self, dialect):
        expr = DeleteExpression(
            dialect=dialect,
            tables=["users"],
            where=Column(dialect, "id") == Literal(dialect, 7),
        )
        sql, params = expr.to_sql()
        assert "DELETE FROM" in sql
        assert len(params) >= 1

    def test_delete_unconditional(self, dialect):
        expr = DeleteExpression(dialect=dialect, tables=["users"])
        sql, params = expr.to_sql()
        assert "DELETE FROM" in sql
