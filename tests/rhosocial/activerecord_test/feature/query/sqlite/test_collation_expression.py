# tests/rhosocial/activerecord_test/feature/query/sqlite/test_collation_expression.py
"""
Tests for expression-level COLLATE support on SQLite.
"""

from enum import Enum

import pytest

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins import CollationMixin
from rhosocial.activerecord.backend.expression import Column, Literal, collate
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class StandardCollationDialect(SQLDialectBase, CollationMixin):
    def supports_collate_expression(self) -> bool:
        return True


class SQLiteCollation(Enum):
    NOCASE = "NOCASE"


@pytest.fixture
def dialect():
    return SQLiteDialect()


class TestSQLiteCollationExpression:
    def test_column_collate_generates_sql(self, dialect):
        expr = Column(dialect, "name", table="users").collate("NOCASE")

        sql, params = expr.to_sql()

        assert sql == '"users"."name" COLLATE NOCASE'
        assert params == ()

    def test_function_collate_generates_sql(self, dialect):
        expr = collate(Column(dialect, "name"), "BINARY")

        sql, params = expr.to_sql()

        assert sql == '"name" COLLATE BINARY'
        assert params == ()

    def test_enum_collate_generates_sql(self, dialect):
        expr = Column(dialect, "name").collate(SQLiteCollation.NOCASE)

        sql, params = expr.to_sql()

        assert sql == '"name" COLLATE NOCASE'
        assert params == ()

    def test_literal_collate_preserves_parameter_binding(self, dialect):
        expr = Literal(dialect, "Alice").collate("NOCASE")

        sql, params = expr.to_sql()

        assert sql == "? COLLATE NOCASE"
        assert params == ("Alice",)

    def test_collate_participates_in_comparison(self, dialect):
        predicate = Column(dialect, "name").collate("NOCASE") == "alice"

        sql, params = predicate.to_sql()

        assert sql == '"name" COLLATE NOCASE = ?'
        assert params == ("alice",)

    def test_collate_supports_alias_and_cast(self, dialect):
        expr = Column(dialect, "name").collate("NOCASE").cast("TEXT").as_("normalized_name")

        sql, params = expr.to_sql()

        assert sql == 'CAST("name" COLLATE NOCASE AS TEXT) AS "normalized_name"'
        assert params == ()

    def test_default_collation_validation_requires_dialect_override(self):
        dialect = StandardCollationDialect()
        expr = Column(dialect, "name").collate("NOCASE")

        with pytest.raises(Exception, match="COLLATE collation validation"):
            expr.to_sql()

    def test_collate_expression_stores_backend_options(self, dialect):
        expr = Column(dialect, "name").collate("case_insensitive", schema="public")

        assert expr.collation_name == "case_insensitive"
        assert expr.collation_options == {"schema": "public"}

    def test_sqlite_rejects_schema_qualified_collation(self, dialect):
        expr = Column(dialect, "name").collate("case_insensitive", schema="public")

        with pytest.raises(Exception, match="schema-qualified COLLATE"):
            expr.to_sql()

    @pytest.mark.parametrize(
        "collation",
        [
            "NOCASE; DROP TABLE users",
            "NOCASE -- comment",
            "NOCASE/*comment*/",
            "# comment",
            "",
            "has space",
            "has\tcontrol",
            'quoted"name',
            "quoted'name",
            "quoted`name",
            "[bracketed]",
        ],
    )
    def test_rejects_unsafe_collation_names(self, dialect, collation):
        expr = Column(dialect, "name").collate(collation)

        with pytest.raises(ValueError):
            expr.to_sql()

    def test_collate_executes_case_insensitive_match(self, order_fixtures):
        User, _, _ = order_fixtures
        User(username="Alice", email="alice@example.com", age=30).save()
        User(username="bob", email="bob@example.com", age=25).save()

        results = User.query().where(User.c.username.collate("NOCASE") == "alice").all()

        assert [user.username for user in results] == ["Alice"]

    def test_collate_executes_case_insensitive_order(self, order_fixtures):
        User, _, _ = order_fixtures
        User(username="bob", email="bob@example.com", age=20).save()
        User(username="Alice", email="alice@example.com", age=20).save()
        User(username="charlie", email="charlie@example.com", age=20).save()

        results = User.query().order_by(User.c.username.collate("NOCASE")).all()

        assert [user.username for user in results] == ["Alice", "bob", "charlie"]
