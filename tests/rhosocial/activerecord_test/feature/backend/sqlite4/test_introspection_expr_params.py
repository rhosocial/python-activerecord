# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_expression_params.py
"""
Tests for introspection expression instantiation parameters with SQLite backend.

This module tests that all introspection expression classes properly
accept parameters at construction time and generate valid SQL that
can be executed by SQLite.
"""

import pytest

from rhosocial.activerecord.backend.expression.introspection import (
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
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


class TestTableListExpressionExecution:
    """Tests for TableListExpression execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_tables):
        """Test TableListExpression with constructor params can execute."""
        expr = TableListExpression(
            dialect=backend_with_tables.dialect,
            schema='main',
            include_views=True,
            include_system=False
        )
        sql, params = expr.to_sql()
        assert sql is not None
        assert len(sql) > 0
        result = backend_with_tables.execute(sql, params)
        assert result is not None

    def test_constructor_table_type_filter(self, backend_with_view):
        """Test TableListExpression with table_type filter."""
        expr = TableListExpression(
            dialect=backend_with_view.dialect,
            schema='main',
            table_type='table'
        )
        sql, params = expr.to_sql()
        result = backend_with_view.execute(sql, params)
        assert result is not None

    def test_fluent_vs_constructor_equivalence(self, backend_with_tables):
        """Test fluent API and constructor params produce same SQL."""
        expr1 = TableListExpression(
            dialect=backend_with_tables.dialect,
            schema='main',
            include_views=False
        )
        expr2 = TableListExpression(
            dialect=backend_with_tables.dialect
        ).schema('main').include_views(False)

        sql1, params1 = expr1.to_sql()
        sql2, params2 = expr2.to_sql()
        assert sql1 == sql2
        assert params1 == params2


class TestTableInfoExpressionExecution:
    """Tests for TableInfoExpression execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_tables):
        """Test TableInfoExpression with constructor params can execute."""
        expr = TableInfoExpression(
            dialect=backend_with_tables.dialect,
            table_name='users',
            schema='main'
        )
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_tables.execute(sql, params)
        assert result is not None

    def test_fluent_vs_constructor_equivalence(self, backend_with_tables):
        """Test fluent API and constructor params produce same SQL."""
        expr1 = TableInfoExpression(
            dialect=backend_with_tables.dialect,
            table_name='users',
            schema='main'
        )
        expr2 = TableInfoExpression(
            dialect=backend_with_tables.dialect,
            table_name='users'
        ).schema('main')

        sql1, params1 = expr1.to_sql()
        sql2, params2 = expr2.to_sql()
        assert sql1 == sql2
        assert params1 == params2


class TestColumnInfoExpressionExecution:
    """Tests for ColumnInfoExpression execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_tables):
        """Test ColumnInfoExpression with constructor params can execute."""
        expr = ColumnInfoExpression(
            dialect=backend_with_tables.dialect,
            table_name='users',
            schema='main'
        )
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_tables.execute(sql, params)
        assert result is not None

    def test_include_hidden_param(self, backend_with_tables):
        """Test ColumnInfoExpression with include_hidden parameter."""
        expr = ColumnInfoExpression(
            dialect=backend_with_tables.dialect,
            table_name='users',
            schema='main',
            include_hidden=True
        )
        sql, params = expr.to_sql()
        result = backend_with_tables.execute(sql, params)
        assert result is not None


class TestIndexInfoExpressionExecution:
    """Tests for IndexInfoExpression execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_tables):
        """Test IndexInfoExpression with constructor params can execute."""
        expr = IndexInfoExpression(
            dialect=backend_with_tables.dialect,
            table_name='users',
            schema='main'
        )
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_tables.execute(sql, params)
        assert result is not None


class TestForeignKeyExpressionExecution:
    """Tests for ForeignKeyExpression execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_tables):
        """Test ForeignKeyExpression with constructor params can execute."""
        expr = ForeignKeyExpression(
            dialect=backend_with_tables.dialect,
            table_name='posts',
            schema='main'
        )
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_tables.execute(sql, params)
        assert result is not None


class TestViewListExpressionExecution:
    """Tests for ViewListExpression execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_view):
        """Test ViewListExpression with constructor params can execute."""
        expr = ViewListExpression(
            dialect=backend_with_view.dialect,
            schema='main',
            include_system=False
        )
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_view.execute(sql, params)
        assert result is not None

    def test_include_system_param(self, sqlite_backend):
        """Test ViewListExpression with include_system parameter."""
        expr = ViewListExpression(
            dialect=sqlite_backend.dialect,
            schema='main',
            include_system=True
        )
        sql, params = expr.to_sql()
        result = sqlite_backend.execute(sql, params)
        assert result is not None


class TestViewInfoExpressionExecution:
    """Tests for ViewInfoExpression execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_view):
        """Test ViewInfoExpression with constructor params can execute."""
        expr = ViewInfoExpression(
            dialect=backend_with_view.dialect,
            view_name='user_posts_summary',
            schema='main'
        )
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_view.execute(sql, params)
        assert result is not None

    def test_include_columns_param(self, backend_with_view):
        """Test ViewInfoExpression with include_columns parameter."""
        expr = ViewInfoExpression(
            dialect=backend_with_view.dialect,
            view_name='user_posts_summary',
            schema='main',
            include_columns=True
        )
        sql, params = expr.to_sql()
        result = backend_with_view.execute(sql, params)
        assert result is not None


class TestTriggerListExpressionExecution:
    """Tests for TriggerListExpression execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_trigger):
        """Test TriggerListExpression with constructor params can execute."""
        expr = TriggerListExpression(
            dialect=backend_with_trigger.dialect,
            schema='main'
        )
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_trigger.execute(sql, params)
        assert result is not None

    def test_table_name_filter(self, backend_with_trigger):
        """Test TriggerListExpression with table_name filter."""
        expr = TriggerListExpression(
            dialect=backend_with_trigger.dialect,
            schema='main',
            table_name='users'
        )
        sql, params = expr.to_sql()
        result = backend_with_trigger.execute(sql, params)
        assert result is not None


class TestTriggerInfoExpressionExecution:
    """Tests for TriggerInfoExpression execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_trigger):
        """Test TriggerInfoExpression with constructor params can execute."""
        expr = TriggerInfoExpression(
            dialect=backend_with_trigger.dialect,
            trigger_name='update_user_timestamp',
            schema='main'
        )
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_trigger.execute(sql, params)
        assert result is not None

    def test_with_table_name(self, backend_with_trigger):
        """Test TriggerInfoExpression with table_name parameter."""
        expr = TriggerInfoExpression(
            dialect=backend_with_trigger.dialect,
            trigger_name='update_user_timestamp',
            schema='main',
            table_name='users'
        )
        sql, params = expr.to_sql()
        result = backend_with_trigger.execute(sql, params)
        assert result is not None
