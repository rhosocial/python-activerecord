# tests/rhosocial/activerecord_test/feature/backend/introspection/test_introspection_expr_params_async.py
"""Async twin of test_introspection_expr_params.py for introspection expression instantiation parameters."""

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


class TestAsyncTableListExpressionExecution:
    """Tests for TableListExpression execution with SQLite."""

    @pytest.mark.asyncio
    async def test_constructor_params_execution(self, async_backend_with_tables):
        """Test TableListExpression with constructor params can execute."""
        expr = TableListExpression(
            dialect=async_backend_with_tables.dialect, schema="main", include_views=True, include_system=False
        )
        sql, params = expr.to_sql()
        assert sql is not None
        assert len(sql) > 0
        result = await async_backend_with_tables.execute(sql, params)
        assert result is not None

    @pytest.mark.asyncio
    async def test_constructor_table_type_filter(self, async_backend_with_view):
        """Test TableListExpression with table_type filter."""
        expr = TableListExpression(dialect=async_backend_with_view.dialect, schema="main", table_type="table")
        sql, params = expr.to_sql()
        result = await async_backend_with_view.execute(sql, params)
        assert result is not None

    @pytest.mark.asyncio
    async def test_fluent_vs_constructor_equivalence(self, async_backend_with_tables):
        """Test fluent API and constructor params produce same SQL."""
        expr1 = TableListExpression(dialect=async_backend_with_tables.dialect, schema="main", include_views=False)
        expr2 = TableListExpression(dialect=async_backend_with_tables.dialect).schema("main").include_views(False)

        sql1, params1 = expr1.to_sql()
        sql2, params2 = expr2.to_sql()
        assert sql1 == sql2
        assert params1 == params2


class TestAsyncTableInfoExpressionExecution:
    """Tests for TableInfoExpression execution with SQLite."""

    @pytest.mark.asyncio
    async def test_constructor_params_execution(self, async_backend_with_tables):
        """Test TableInfoExpression with constructor params can execute."""
        expr = TableInfoExpression(dialect=async_backend_with_tables.dialect, table="users", schema="main")
        sql, params = expr.to_sql()
        assert sql is not None
        result = await async_backend_with_tables.execute(sql, params)
        assert result is not None

    @pytest.mark.asyncio
    async def test_fluent_vs_constructor_equivalence(self, async_backend_with_tables):
        """Test fluent API and constructor params produce same SQL."""
        expr1 = TableInfoExpression(dialect=async_backend_with_tables.dialect, table="users", schema="main")
        expr2 = TableInfoExpression(dialect=async_backend_with_tables.dialect, table="users").schema("main")

        sql1, params1 = expr1.to_sql()
        sql2, params2 = expr2.to_sql()
        assert sql1 == sql2
        assert params1 == params2


class TestAsyncColumnInfoExpressionExecution:
    """Tests for ColumnInfoExpression execution with SQLite."""

    @pytest.mark.asyncio
    async def test_constructor_params_execution(self, async_backend_with_tables):
        """Test ColumnInfoExpression with constructor params can execute."""
        expr = ColumnInfoExpression(dialect=async_backend_with_tables.dialect, table="users", schema="main")
        sql, params = expr.to_sql()
        assert sql is not None
        result = await async_backend_with_tables.execute(sql, params)
        assert result is not None

    @pytest.mark.asyncio
    async def test_include_hidden_param(self, async_backend_with_tables):
        """Test ColumnInfoExpression with include_hidden parameter."""
        expr = ColumnInfoExpression(
            dialect=async_backend_with_tables.dialect, table="users", schema="main", include_hidden=True
        )
        sql, params = expr.to_sql()
        result = await async_backend_with_tables.execute(sql, params)
        assert result is not None


class TestAsyncIndexInfoExpressionExecution:
    """Tests for IndexInfoExpression execution with SQLite."""

    @pytest.mark.asyncio
    async def test_constructor_params_execution(self, async_backend_with_tables):
        """Test IndexInfoExpression with constructor params can execute."""
        expr = IndexInfoExpression(dialect=async_backend_with_tables.dialect, table="users", schema="main")
        sql, params = expr.to_sql()
        assert sql is not None
        result = await async_backend_with_tables.execute(sql, params)
        assert result is not None


class TestAsyncForeignKeyExpressionExecution:
    """Tests for ForeignKeyExpression execution with SQLite."""

    @pytest.mark.asyncio
    async def test_constructor_params_execution(self, async_backend_with_tables):
        """Test ForeignKeyExpression with constructor params can execute."""
        expr = ForeignKeyExpression(dialect=async_backend_with_tables.dialect, table="posts", schema="main")
        sql, params = expr.to_sql()
        assert sql is not None
        result = await async_backend_with_tables.execute(sql, params)
        assert result is not None


class TestAsyncViewListExpressionExecution:
    """Tests for ViewListExpression execution with SQLite."""

    @pytest.mark.asyncio
    async def test_constructor_params_execution(self, async_backend_with_view):
        """Test ViewListExpression with constructor params can execute."""
        expr = ViewListExpression(dialect=async_backend_with_view.dialect, schema="main", include_system=False)
        sql, params = expr.to_sql()
        assert sql is not None
        result = await async_backend_with_view.execute(sql, params)
        assert result is not None

    @pytest.mark.asyncio
    async def test_include_system_param(self, async_sqlite_memory_backend):
        """Test ViewListExpression with include_system parameter."""
        expr = ViewListExpression(dialect=async_sqlite_memory_backend.dialect, schema="main", include_system=True)
        sql, params = expr.to_sql()
        result = await async_sqlite_memory_backend.execute(sql, params)
        assert result is not None


class TestAsyncViewInfoExpressionExecution:
    """Tests for ViewInfoExpression execution with SQLite."""

    @pytest.mark.asyncio
    async def test_constructor_params_execution(self, async_backend_with_view):
        """Test ViewInfoExpression with constructor params can execute."""
        expr = ViewInfoExpression(
            dialect=async_backend_with_view.dialect, view_name="user_posts_summary", schema="main"
        )
        sql, params = expr.to_sql()
        assert sql is not None
        result = await async_backend_with_view.execute(sql, params)
        assert result is not None

    @pytest.mark.asyncio
    async def test_include_columns_param(self, async_backend_with_view):
        """Test ViewInfoExpression with include_columns parameter."""
        expr = ViewInfoExpression(
            dialect=async_backend_with_view.dialect, view_name="user_posts_summary", schema="main", include_columns=True
        )
        sql, params = expr.to_sql()
        result = await async_backend_with_view.execute(sql, params)
        assert result is not None


class TestAsyncTriggerListExpressionExecution:
    """Tests for TriggerListExpression execution with SQLite."""

    @pytest.mark.asyncio
    async def test_constructor_params_execution(self, async_backend_with_trigger):
        """Test TriggerListExpression with constructor params can execute."""
        expr = TriggerListExpression(dialect=async_backend_with_trigger.dialect, schema="main")
        sql, params = expr.to_sql()
        assert sql is not None
        result = await async_backend_with_trigger.execute(sql, params)
        assert result is not None

    @pytest.mark.asyncio
    async def test_table_name_filter(self, async_backend_with_trigger):
        """Test TriggerListExpression with table_name filter."""
        expr = TriggerListExpression(dialect=async_backend_with_trigger.dialect, schema="main", table="users")
        sql, params = expr.to_sql()
        result = await async_backend_with_trigger.execute(sql, params)
        assert result is not None


class TestAsyncTriggerInfoExpressionExecution:
    """Tests for TriggerInfoExpression execution with SQLite."""

    @pytest.mark.asyncio
    async def test_constructor_params_execution(self, async_backend_with_trigger):
        """Test TriggerInfoExpression with constructor params can execute."""
        expr = TriggerInfoExpression(
            dialect=async_backend_with_trigger.dialect, trigger="update_user_timestamp", schema="main"
        )
        sql, params = expr.to_sql()
        assert sql is not None
        result = await async_backend_with_trigger.execute(sql, params)
        assert result is not None

    @pytest.mark.asyncio
    async def test_with_table_name(self, async_backend_with_trigger):
        """Test TriggerInfoExpression with table_name parameter."""
        expr = TriggerInfoExpression(
            dialect=async_backend_with_trigger.dialect,
            trigger="update_user_timestamp",
            schema="main",
            table="users",
        )
        sql, params = expr.to_sql()
        result = await async_backend_with_trigger.execute(sql, params)
        assert result is not None
