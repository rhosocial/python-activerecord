# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_to_sql.py
"""
Tests to cover missing lines in expression/introspection.py.
Uses SQLiteDialect which supports introspection format methods.

Targets all to_sql() delegation methods and IntrospectionExpression base.
"""

import pytest
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.introspection import (
    IntrospectionExpression,
    DatabaseInfoQueryStatement,
    TableListQueryStatement,
    TableInfoQueryStatement,
    ColumnInfoQueryStatement,
    IndexInfoQueryStatement,
    ForeignKeyQueryStatement,
    ViewListQueryStatement,
    ViewInfoQueryStatement,
    TriggerListQueryStatement,
    TriggerInfoQueryStatement,
)


@pytest.fixture
def sqlite_dialect():
    return SQLiteDialect(version=(3, 35, 0))


class TestIntrospectionExpressionBase:
    """Cover IntrospectionExpression.to_sql() raising NotImplementedError."""

    def test_base_to_sql_raises_not_implemented(self, sqlite_dialect):
        expr = IntrospectionExpression(sqlite_dialect)
        with pytest.raises(NotImplementedError):
            expr.to_sql()


class TestDatabaseInfoToSql:
    """Cover DatabaseInfoQueryStatement.to_sql() delegation."""

    def test_database_info_to_sql(self, sqlite_dialect):
        expr = DatabaseInfoQueryStatement(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert len(sql) > 0


class TestTableListToSql:
    """Cover TableListQueryStatement.to_sql() delegation and setters."""

    def test_table_list_to_sql(self, sqlite_dialect):
        expr = TableListQueryStatement(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_include_system_setter(self, sqlite_dialect):
        expr = TableListQueryStatement(sqlite_dialect)
        result = expr.with_include_system(True)
        assert result is expr
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_table_type_setter(self, sqlite_dialect):
        expr = TableListQueryStatement(sqlite_dialect)
        result = expr.with_table_type("TABLE")
        assert result is expr
        sql, params = expr.to_sql()
        assert isinstance(sql, str)


class TestTableInfoToSql:
    """Cover TableInfoQueryStatement.to_sql() delegation and setters."""

    def test_table_info_to_sql(self, sqlite_dialect):
        expr = TableInfoQueryStatement(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert len(sql) > 0

    def test_include_indexes_setter(self, sqlite_dialect):
        """Cover introspection.py:346-347 — include_indexes setter."""
        expr = TableInfoQueryStatement(sqlite_dialect, table_name="users")
        result = expr.with_include_indexes(False)
        assert result is expr

    def test_include_foreign_keys_setter(self, sqlite_dialect):
        """Cover introspection.py:365-366 — include_foreign_keys setter."""
        expr = TableInfoQueryStatement(sqlite_dialect, table_name="users")
        result = expr.with_include_foreign_keys(False)
        assert result is expr


class TestColumnInfoToSql:
    """Cover ColumnInfoQueryStatement.to_sql() delegation and setters."""

    def test_column_info_to_sql(self, sqlite_dialect):
        expr = ColumnInfoQueryStatement(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_table_name_setter(self, sqlite_dialect):
        """Cover introspection.py:438-439 — table_name setter."""
        expr = ColumnInfoQueryStatement(sqlite_dialect, table_name="old")
        result = expr.with_table_name("new")
        assert result is expr

    def test_include_hidden_setter(self, sqlite_dialect):
        """Cover introspection.py:457-458 — include_hidden setter."""
        expr = ColumnInfoQueryStatement(sqlite_dialect, table_name="users")
        result = expr.with_include_hidden(True)
        assert result is expr


class TestIndexInfoToSql:
    """Cover IndexInfoQueryStatement.to_sql() delegation and setters."""

    def test_index_info_to_sql(self, sqlite_dialect):
        expr = IndexInfoQueryStatement(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_table_name_setter(self, sqlite_dialect):
        """Cover introspection.py:524-525 — table_name setter."""
        expr = IndexInfoQueryStatement(sqlite_dialect, table_name="old")
        result = expr.with_table_name("new")
        assert result is expr


class TestForeignKeyToSql:
    """Cover ForeignKeyQueryStatement.to_sql() delegation and setters."""

    def test_foreign_key_to_sql(self, sqlite_dialect):
        expr = ForeignKeyQueryStatement(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_table_name_setter(self, sqlite_dialect):
        """Cover introspection.py:589-590 — table_name setter."""
        expr = ForeignKeyQueryStatement(sqlite_dialect, table_name="old")
        result = expr.with_table_name("new")
        assert result is expr


class TestViewListToSql:
    """Cover ViewListQueryStatement.to_sql() delegation."""

    def test_view_list_to_sql(self, sqlite_dialect):
        expr = ViewListQueryStatement(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)


class TestViewInfoToSql:
    """Cover ViewInfoQueryStatement.to_sql() delegation and setters."""

    def test_view_info_to_sql(self, sqlite_dialect):
        expr = ViewInfoQueryStatement(sqlite_dialect, view_name="user_summary")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_view_name_setter(self, sqlite_dialect):
        """Cover introspection.py:728-729 — view_name setter."""
        expr = ViewInfoQueryStatement(sqlite_dialect, view_name="old_view")
        result = expr.with_view_name("new_view")
        assert result is expr

    def test_include_columns_setter(self, sqlite_dialect):
        """Cover introspection.py:747-748 — include_columns setter."""
        expr = ViewInfoQueryStatement(sqlite_dialect, view_name="user_summary")
        result = expr.with_include_columns(False)
        assert result is expr


class TestTriggerListToSql:
    """Cover TriggerListQueryStatement.to_sql() delegation."""

    def test_trigger_list_to_sql(self, sqlite_dialect):
        expr = TriggerListQueryStatement(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)


class TestTriggerInfoToSql:
    """Cover TriggerInfoQueryStatement.to_sql() delegation and setters."""

    def test_trigger_info_to_sql(self, sqlite_dialect):
        expr = TriggerInfoQueryStatement(sqlite_dialect, trigger_name="update_ts")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_trigger_name_setter(self, sqlite_dialect):
        """Cover introspection.py:888-889 — trigger_name setter."""
        expr = TriggerInfoQueryStatement(sqlite_dialect, trigger_name="old")
        result = expr.with_trigger_name("new")
        assert result is expr

    def test_for_table_setter(self, sqlite_dialect):
        """Cover introspection.py:906-907 — for_table setter."""
        expr = TriggerInfoQueryStatement(sqlite_dialect, trigger_name="update_ts")
        result = expr.for_table("users")
        assert result is expr
