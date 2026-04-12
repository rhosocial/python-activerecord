# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_introspection_expression_params.py
"""
Tests for introspection expression instantiation parameters.

This module tests that all introspection expression classes properly
accept parameters at construction time and generate correct SQL.
"""

import pytest

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
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestIntrospectionExpressionParams:
    """Tests for introspection expression construction parameters."""

    def test_introspection_expression_with_schema(self, dummy_dialect):
        """Test IntrospectionExpression accepts schema parameter."""
        expr = IntrospectionExpression(dummy_dialect, schema='public')
        params = expr.get_params()
        assert params.get('schema') == 'public'

    def test_introspection_expression_fluent_schema(self, dummy_dialect):
        """Test schema can be set via fluent API."""
        expr = IntrospectionExpression(dummy_dialect).schema('public')
        params = expr.get_params()
        assert params.get('schema') == 'public'


class TestTableListExpressionParams:
    """Tests for TableListExpression construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test TableListExpression accepts all parameters at construction."""
        expr = TableListExpression(
            dialect=dummy_dialect,
            schema='main',
            include_views=False,
            include_system=True,
            table_type='TABLE'
        )
        params = expr.get_params()
        assert params.get('schema') == 'main'
        assert params.get('include_views') is False
        assert params.get('include_system') is True
        assert params.get('table_type') == 'TABLE'

    def test_constructor_defaults(self, dummy_dialect):
        """Test TableListExpression default values."""
        expr = TableListExpression(dialect=dummy_dialect)
        params = expr.get_params()
        assert 'schema' not in params
        assert params.get('include_views') is True
        assert params.get('include_system') is False
        assert 'table_type' not in params

    def test_fluent_api_override(self, dummy_dialect):
        """Test fluent API can override constructor values."""
        expr = TableListExpression(
            dialect=dummy_dialect,
            include_views=False
        ).include_views(True)
        params = expr.get_params()
        assert params.get('include_views') is True


class TestTableInfoExpressionParams:
    """Tests for TableInfoExpression construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test TableInfoExpression accepts all parameters at construction."""
        expr = TableInfoExpression(
            dialect=dummy_dialect,
            table_name='users',
            schema='public',
            include_columns=False,
            include_indexes=False,
            include_foreign_keys=False
        )
        params = expr.get_params()
        assert params.get('table_name') == 'users'
        assert params.get('schema') == 'public'
        assert params.get('include_columns') is False
        assert params.get('include_indexes') is False
        assert params.get('include_foreign_keys') is False

    def test_constructor_defaults(self, dummy_dialect):
        """Test TableInfoExpression default values."""
        expr = TableInfoExpression(dialect=dummy_dialect, table_name='users')
        params = expr.get_params()
        assert params.get('table_name') == 'users'
        assert 'schema' not in params
        assert params.get('include_columns') is True
        assert params.get('include_indexes') is True
        assert params.get('include_foreign_keys') is True

    def test_fluent_api_override(self, dummy_dialect):
        """Test fluent API can override constructor values."""
        expr = TableInfoExpression(
            dialect=dummy_dialect,
            table_name='users',
            include_columns=False
        ).include_columns(True).table_name('posts')
        params = expr.get_params()
        assert params.get('table_name') == 'posts'
        assert params.get('include_columns') is True


class TestColumnInfoExpressionParams:
    """Tests for ColumnInfoExpression construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test ColumnInfoExpression accepts all parameters at construction."""
        expr = ColumnInfoExpression(
            dialect=dummy_dialect,
            table_name='users',
            schema='public',
            include_hidden=True
        )
        params = expr.get_params()
        assert params.get('table_name') == 'users'
        assert params.get('schema') == 'public'
        assert params.get('include_hidden') is True

    def test_constructor_defaults(self, dummy_dialect):
        """Test ColumnInfoExpression default values."""
        expr = ColumnInfoExpression(dialect=dummy_dialect, table_name='users')
        params = expr.get_params()
        assert params.get('table_name') == 'users'
        assert 'schema' not in params
        assert params.get('include_hidden') is False


class TestIndexInfoExpressionParams:
    """Tests for IndexInfoExpression construction parameters."""

    def test_constructor_with_schema(self, dummy_dialect):
        """Test IndexInfoExpression accepts schema parameter."""
        expr = IndexInfoExpression(
            dialect=dummy_dialect,
            table_name='users',
            schema='main'
        )
        params = expr.get_params()
        assert params.get('table_name') == 'users'
        assert params.get('schema') == 'main'

    def test_constructor_defaults(self, dummy_dialect):
        """Test IndexInfoExpression default values."""
        expr = IndexInfoExpression(dialect=dummy_dialect, table_name='users')
        params = expr.get_params()
        assert params.get('table_name') == 'users'
        assert 'schema' not in params


class TestForeignKeyExpressionParams:
    """Tests for ForeignKeyExpression construction parameters."""

    def test_constructor_with_schema(self, dummy_dialect):
        """Test ForeignKeyExpression accepts schema parameter."""
        expr = ForeignKeyExpression(
            dialect=dummy_dialect,
            table_name='posts',
            schema='public'
        )
        params = expr.get_params()
        assert params.get('table_name') == 'posts'
        assert params.get('schema') == 'public'

    def test_constructor_defaults(self, dummy_dialect):
        """Test ForeignKeyExpression default values."""
        expr = ForeignKeyExpression(dialect=dummy_dialect, table_name='posts')
        params = expr.get_params()
        assert params.get('table_name') == 'posts'
        assert 'schema' not in params


class TestViewListExpressionParams:
    """Tests for ViewListExpression construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test ViewListExpression accepts all parameters at construction."""
        expr = ViewListExpression(
            dialect=dummy_dialect,
            schema='main',
            include_system=True
        )
        params = expr.get_params()
        assert params.get('schema') == 'main'
        assert params.get('include_system') is True

    def test_constructor_defaults(self, dummy_dialect):
        """Test ViewListExpression default values."""
        expr = ViewListExpression(dialect=dummy_dialect)
        params = expr.get_params()
        assert 'schema' not in params
        assert params.get('include_system') is False

    def test_fluent_api_override(self, dummy_dialect):
        """Test fluent API can override constructor values."""
        expr = ViewListExpression(
            dialect=dummy_dialect,
            include_system=False
        ).include_system(True)
        params = expr.get_params()
        assert params.get('include_system') is True


class TestViewInfoExpressionParams:
    """Tests for ViewInfoExpression construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test ViewInfoExpression accepts all parameters at construction."""
        expr = ViewInfoExpression(
            dialect=dummy_dialect,
            view_name='user_view',
            schema='public',
            include_columns=False
        )
        params = expr.get_params()
        assert params.get('view_name') == 'user_view'
        assert params.get('schema') == 'public'
        assert params.get('include_columns') is False

    def test_constructor_defaults(self, dummy_dialect):
        """Test ViewInfoExpression default values."""
        expr = ViewInfoExpression(dialect=dummy_dialect, view_name='user_view')
        params = expr.get_params()
        assert params.get('view_name') == 'user_view'
        assert 'schema' not in params
        assert params.get('include_columns') is True


class TestTriggerListExpressionParams:
    """Tests for TriggerListExpression construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test TriggerListExpression accepts all parameters at construction."""
        expr = TriggerListExpression(
            dialect=dummy_dialect,
            schema='main',
            table_name='users'
        )
        params = expr.get_params()
        assert params.get('schema') == 'main'
        assert params.get('table_name') == 'users'

    def test_constructor_defaults(self, dummy_dialect):
        """Test TriggerListExpression default values."""
        expr = TriggerListExpression(dialect=dummy_dialect)
        params = expr.get_params()
        assert 'schema' not in params
        assert 'table_name' not in params

    def test_fluent_api_for_table(self, dummy_dialect):
        """Test for_table fluent API."""
        expr = TriggerListExpression(
            dialect=dummy_dialect,
            table_name='users'
        ).for_table('posts')
        params = expr.get_params()
        assert params.get('table_name') == 'posts'


class TestTriggerInfoExpressionParams:
    """Tests for TriggerInfoExpression construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test TriggerInfoExpression accepts all parameters at construction."""
        expr = TriggerInfoExpression(
            dialect=dummy_dialect,
            trigger_name='my_trigger',
            schema='main',
            table_name='users'
        )
        params = expr.get_params()
        assert params.get('trigger_name') == 'my_trigger'
        assert params.get('schema') == 'main'
        assert params.get('table_name') == 'users'

    def test_constructor_defaults(self, dummy_dialect):
        """Test TriggerInfoExpression default values."""
        expr = TriggerInfoExpression(dialect=dummy_dialect, trigger_name='my_trigger')
        params = expr.get_params()
        assert params.get('trigger_name') == 'my_trigger'
        assert 'schema' not in params
        assert 'table_name' not in params
