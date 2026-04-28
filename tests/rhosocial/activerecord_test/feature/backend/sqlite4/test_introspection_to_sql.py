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
    DatabaseInfoExpression,
    TableListExpression,
    TableInfoExpression,
    ColumnInfoExpression,
    IndexInfoExpression,
    ForeignKeyExpression,
    ViewListExpression,
    ViewInfoExpression,
    TriggerListExpression,
    TriggerInfoExpression,
)


@pytest.fixture
def sqlite_dialect():
    return SQLiteDialect()


class TestIntrospectionExpressionBase:
    """Cover IntrospectionExpression.to_sql() raising NotImplementedError."""

    def test_base_to_sql_raises_not_implemented(self, sqlite_dialect):
        expr = IntrospectionExpression(sqlite_dialect)
        with pytest.raises(NotImplementedError):
            expr.to_sql()


class TestDatabaseInfoToSql:
    """Cover DatabaseInfoExpression.to_sql() delegation."""

    def test_database_info_to_sql(self, sqlite_dialect):
        expr = DatabaseInfoExpression(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert len(sql) > 0


class TestTableListToSql:
    """Cover TableListExpression.to_sql() delegation and setters."""

    def test_table_list_to_sql(self, sqlite_dialect):
        expr = TableListExpression(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_include_system_setter(self, sqlite_dialect):
        expr = TableListExpression(sqlite_dialect)
        result = expr.include_system(True)
        assert result is expr
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_table_type_setter(self, sqlite_dialect):
        expr = TableListExpression(sqlite_dialect)
        result = expr.table_type("TABLE")
        assert result is expr
        sql, params = expr.to_sql()
        assert isinstance(sql, str)


class TestTableInfoToSql:
    """Cover TableInfoExpression.to_sql() delegation and setters."""

    def test_table_info_to_sql(self, sqlite_dialect):
        expr = TableInfoExpression(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)
        assert len(sql) > 0

    def test_include_indexes_setter(self, sqlite_dialect):
        """Cover introspection.py:346-347 — include_indexes setter."""
        expr = TableInfoExpression(sqlite_dialect, table_name="users")
        result = expr.include_indexes(False)
        assert result is expr

    def test_include_foreign_keys_setter(self, sqlite_dialect):
        """Cover introspection.py:365-366 — include_foreign_keys setter."""
        expr = TableInfoExpression(sqlite_dialect, table_name="users")
        result = expr.include_foreign_keys(False)
        assert result is expr


class TestColumnInfoToSql:
    """Cover ColumnInfoExpression.to_sql() delegation and setters."""

    def test_column_info_to_sql(self, sqlite_dialect):
        expr = ColumnInfoExpression(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_table_name_setter(self, sqlite_dialect):
        """Cover introspection.py:438-439 — table_name setter."""
        expr = ColumnInfoExpression(sqlite_dialect, table_name="old")
        result = expr.table_name("new")
        assert result is expr

    def test_include_hidden_setter(self, sqlite_dialect):
        """Cover introspection.py:457-458 — include_hidden setter."""
        expr = ColumnInfoExpression(sqlite_dialect, table_name="users")
        result = expr.include_hidden(True)
        assert result is expr


class TestIndexInfoToSql:
    """Cover IndexInfoExpression.to_sql() delegation and setters."""

    def test_index_info_to_sql(self, sqlite_dialect):
        expr = IndexInfoExpression(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_table_name_setter(self, sqlite_dialect):
        """Cover introspection.py:524-525 — table_name setter."""
        expr = IndexInfoExpression(sqlite_dialect, table_name="old")
        result = expr.table_name("new")
        assert result is expr


class TestForeignKeyToSql:
    """Cover ForeignKeyExpression.to_sql() delegation and setters."""

    def test_foreign_key_to_sql(self, sqlite_dialect):
        expr = ForeignKeyExpression(sqlite_dialect, table_name="users")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_table_name_setter(self, sqlite_dialect):
        """Cover introspection.py:589-590 — table_name setter."""
        expr = ForeignKeyExpression(sqlite_dialect, table_name="old")
        result = expr.table_name("new")
        assert result is expr


class TestViewListToSql:
    """Cover ViewListExpression.to_sql() delegation."""

    def test_view_list_to_sql(self, sqlite_dialect):
        expr = ViewListExpression(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)


class TestViewInfoToSql:
    """Cover ViewInfoExpression.to_sql() delegation and setters."""

    def test_view_info_to_sql(self, sqlite_dialect):
        expr = ViewInfoExpression(sqlite_dialect, view_name="user_summary")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_view_name_setter(self, sqlite_dialect):
        """Cover introspection.py:728-729 — view_name setter."""
        expr = ViewInfoExpression(sqlite_dialect, view_name="old_view")
        result = expr.view_name("new_view")
        assert result is expr

    def test_include_columns_setter(self, sqlite_dialect):
        """Cover introspection.py:747-748 — include_columns setter."""
        expr = ViewInfoExpression(sqlite_dialect, view_name="user_summary")
        result = expr.include_columns(False)
        assert result is expr


class TestTriggerListToSql:
    """Cover TriggerListExpression.to_sql() delegation."""

    def test_trigger_list_to_sql(self, sqlite_dialect):
        expr = TriggerListExpression(sqlite_dialect)
        sql, params = expr.to_sql()
        assert isinstance(sql, str)


class TestTriggerInfoToSql:
    """Cover TriggerInfoExpression.to_sql() delegation and setters."""

    def test_trigger_info_to_sql(self, sqlite_dialect):
        expr = TriggerInfoExpression(sqlite_dialect, trigger_name="update_ts")
        sql, params = expr.to_sql()
        assert isinstance(sql, str)

    def test_trigger_name_setter(self, sqlite_dialect):
        """Cover introspection.py:888-889 — trigger_name setter."""
        expr = TriggerInfoExpression(sqlite_dialect, trigger_name="old")
        result = expr.trigger_name("new")
        assert result is expr

    def test_for_table_setter(self, sqlite_dialect):
        """Cover introspection.py:906-907 — for_table setter."""
        expr = TriggerInfoExpression(sqlite_dialect, trigger_name="update_ts")
        result = expr.for_table("users")
        assert result is expr
