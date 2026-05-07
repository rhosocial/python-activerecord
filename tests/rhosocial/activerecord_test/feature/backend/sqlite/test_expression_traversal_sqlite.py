# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_expression_traversal.py
"""

TEST PURPOSE:
    This test file verifies two categories of expressions:
    1. Expressions with dialect_options - verify that dialect-specific options are preserved
       through serialization/deserialization roundtrips
    2. SQLite-specific expressions - verify SQLite-only expressions like ReindexExpression
    
    This complements test_expression_traversal.py (dummy2) which tests generic
    expressions using discovery. This file tests specific scenarios that require
    a real dialect (SQLite) to verify proper handling.
    
    COVERAGE:
    - INSERT/UPDATE/DELETE with dialect_options (e.g., INSERT ... ON CONFLICT IGNORE)
    - DDL statements with dialect_options (CREATE INDEX, DROP TABLE with IF EXISTS)
    - SQLite-specific expressions (SQLiteReindexExpression, SQLiteMatchPredicate,
      SQLiteTableListExpression, SQLiteColumnInfoExpression)
    
    See also: dummy2/test_expression_traversal.py for generic expression discovery tests.
"""

import pytest

from rhosocial.activerecord.backend.expression import serialization
from rhosocial.activerecord.backend.expression import TableExpression, Literal
from rhosocial.activerecord.backend.expression.statements.dml import InsertExpression, DeleteExpression, ValuesSource
from rhosocial.activerecord.backend.expression.statements.ddl_table import DropTableExpression
from rhosocial.activerecord.backend.expression.statements.ddl_index import CreateIndexExpression, DropIndexExpression
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.reindex import SQLiteReindexExpression
from rhosocial.activerecord.backend.impl.sqlite.expression.predicates import SQLiteMatchPredicate
from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import SQLiteColumnInfoExpression
from rhosocial.activerecord.backend.impl.sqlite.expression.table_list import SQLiteTableListExpression


@pytest.fixture
def sqlite_dialect():
    """Provides a SQLiteDialect instance."""
    return SQLiteDialect(version=(3, 53, 0))


class TestDialectOptionsExpressionTraversal:
    """Test expressions with dialect_options."""

    def test_insert_with_dialect_options(self, sqlite_dialect):
        table = TableExpression(sqlite_dialect, "users")
        source = ValuesSource(sqlite_dialect, values_list=[[Literal(sqlite_dialect, "John"), Literal(sqlite_dialect, 30)]])
        expr = InsertExpression(sqlite_dialect, into=table, source=source, dialect_options={"ignore": True})
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()
        assert restored.dialect_options == expr.dialect_options

    def test_delete_with_dialect_options(self, sqlite_dialect):
        table = TableExpression(sqlite_dialect, "users")
        expr = DeleteExpression(sqlite_dialect, tables=table, dialect_options={"temp_option": "value"})
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()
        assert restored.dialect_options == expr.dialect_options

    def test_drop_table_with_dialect_options(self, sqlite_dialect):
        expr = DropTableExpression(sqlite_dialect, table="users", dialect_options={"if_exists": True})
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()
        assert restored.dialect_options == expr.dialect_options

    def test_create_index_with_dialect_options(self, sqlite_dialect):
        expr = CreateIndexExpression(sqlite_dialect, "idx_users", "users", ["name"], dialect_options={"unique": True})
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()
        assert restored.dialect_options == expr.dialect_options

    def test_drop_index_with_dialect_options(self, sqlite_dialect):
        expr = DropIndexExpression(sqlite_dialect, "idx_users", dialect_options={"if_exists": True})
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()
        assert restored.dialect_options == expr.dialect_options


class TestSQLiteSpecificExpressionTraversal:
    """Test SQLite-specific expressions."""

    def test_reindex_table_name(self, sqlite_dialect):
        expr = SQLiteReindexExpression(sqlite_dialect, table_name="users")
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_reindex_index_name(self, sqlite_dialect):
        expr = SQLiteReindexExpression(sqlite_dialect, index_name="idx_users")
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_reindex_expressions(self, sqlite_dialect):
        expr = SQLiteReindexExpression(sqlite_dialect, expressions=True)
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_match_predicate(self, sqlite_dialect):
        expr = SQLiteMatchPredicate(sqlite_dialect, table="docs", query="Python")
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_match_predicate_with_columns(self, sqlite_dialect):
        expr = SQLiteMatchPredicate(sqlite_dialect, table="docs", query="prog*", columns=["title"])
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_match_predicate_negated(self, sqlite_dialect):
        expr = SQLiteMatchPredicate(sqlite_dialect, table="docs", query="python", negate=True)
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_column_info_expression(self, sqlite_dialect):
        expr = SQLiteColumnInfoExpression(sqlite_dialect, table_name="users")
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_column_info_expression_xinfo(self, sqlite_dialect):
        expr = SQLiteColumnInfoExpression(sqlite_dialect, table_name="users", use_xinfo_pragma=True)
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_table_list_expression(self, sqlite_dialect):
        expr = SQLiteTableListExpression(sqlite_dialect)
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_table_list_expression_with_pragma(self, sqlite_dialect):
        expr = SQLiteTableListExpression(sqlite_dialect, use_table_list_pragma=True)
        spec = serialization.serialize(expr)
        restored = serialization.deserialize(spec, sqlite_dialect)
        assert restored.to_sql() == expr.to_sql()