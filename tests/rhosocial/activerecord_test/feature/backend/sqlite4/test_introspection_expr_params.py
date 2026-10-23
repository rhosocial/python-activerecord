# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_expression_params.py
"""
Tests for introspection expression instantiation parameters with SQLite backend.

This module tests that all introspection expression classes properly
accept parameters at construction time and generate valid SQL that
can be executed by SQLite.
"""


from rhosocial.activerecord.backend.expression.introspection import (
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


class TestTableListExpressionExecution:
    """Tests for TableListQueryStatement execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_tables):
        """Test TableListQueryStatement with constructor params can execute."""
        expr = TableListQueryStatement(
            dialect=backend_with_tables.dialect, schema="main", include_views=True, include_system=False
        )
        sql, params = expr.to_sql()
        assert sql is not None
        assert len(sql) > 0
        result = backend_with_tables.execute(sql, params)
        assert result is not None

    def test_constructor_table_type_filter(self, backend_with_view):
        """Test TableListQueryStatement with table_type filter."""
        expr = TableListQueryStatement(dialect=backend_with_view.dialect, schema="main", table_type="table")
        sql, params = expr.to_sql()
        result = backend_with_view.execute(sql, params)
        assert result is not None

    def test_fluent_vs_constructor_equivalence(self, backend_with_tables):
        """Test fluent API and constructor params produce same SQL."""
        expr1 = TableListQueryStatement(dialect=backend_with_tables.dialect, schema="main", include_views=False)
        expr2 = (
            TableListQueryStatement(dialect=backend_with_tables.dialect)
            .with_schema("main")
            .with_include_views(False)
        )

        sql1, params1 = expr1.to_sql()
        sql2, params2 = expr2.to_sql()
        assert sql1 == sql2
        assert params1 == params2


class TestTableInfoExpressionExecution:
    """Tests for TableInfoQueryStatement execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_tables):
        """Test TableInfoQueryStatement with constructor params can execute."""
        expr = TableInfoQueryStatement(dialect=backend_with_tables.dialect, table_name="users", schema="main")
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_tables.execute(sql, params)
        assert result is not None

    def test_fluent_vs_constructor_equivalence(self, backend_with_tables):
        """Test fluent API and constructor params produce same SQL."""
        expr1 = TableInfoQueryStatement(dialect=backend_with_tables.dialect, table_name="users", schema="main")
        expr2 = TableInfoQueryStatement(dialect=backend_with_tables.dialect, table_name="users").with_schema("main")

        sql1, params1 = expr1.to_sql()
        sql2, params2 = expr2.to_sql()
        assert sql1 == sql2
        assert params1 == params2


class TestColumnInfoExpressionExecution:
    """Tests for ColumnInfoQueryStatement execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_tables):
        """Test ColumnInfoQueryStatement with constructor params can execute."""
        expr = ColumnInfoQueryStatement(dialect=backend_with_tables.dialect, table_name="users", schema="main")
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_tables.execute(sql, params)
        assert result is not None

    def test_include_hidden_param(self, backend_with_tables):
        """Test ColumnInfoQueryStatement with include_hidden parameter."""
        expr = ColumnInfoQueryStatement(
            dialect=backend_with_tables.dialect, table_name="users", schema="main", include_hidden=True
        )
        sql, params = expr.to_sql()
        result = backend_with_tables.execute(sql, params)
        assert result is not None


class TestIndexInfoExpressionExecution:
    """Tests for IndexInfoQueryStatement execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_tables):
        """Test IndexInfoQueryStatement with constructor params can execute."""
        expr = IndexInfoQueryStatement(dialect=backend_with_tables.dialect, table_name="users", schema="main")
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_tables.execute(sql, params)
        assert result is not None


class TestForeignKeyExpressionExecution:
    """Tests for ForeignKeyQueryStatement execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_tables):
        """Test ForeignKeyQueryStatement with constructor params can execute."""
        expr = ForeignKeyQueryStatement(dialect=backend_with_tables.dialect, table_name="posts", schema="main")
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_tables.execute(sql, params)
        assert result is not None


class TestViewListExpressionExecution:
    """Tests for ViewListQueryStatement execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_view):
        """Test ViewListQueryStatement with constructor params can execute."""
        expr = ViewListQueryStatement(dialect=backend_with_view.dialect, schema="main", include_system=False)
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_view.execute(sql, params)
        assert result is not None

    def test_include_system_param(self, sqlite_backend):
        """Test ViewListQueryStatement with include_system parameter."""
        expr = ViewListQueryStatement(dialect=sqlite_backend.dialect, schema="main", include_system=True)
        sql, params = expr.to_sql()
        result = sqlite_backend.execute(sql, params)
        assert result is not None


class TestViewInfoExpressionExecution:
    """Tests for ViewInfoQueryStatement execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_view):
        """Test ViewInfoQueryStatement with constructor params can execute."""
        expr = ViewInfoQueryStatement(dialect=backend_with_view.dialect, view_name="user_posts_summary", schema="main")
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_view.execute(sql, params)
        assert result is not None

    def test_include_columns_param(self, backend_with_view):
        """Test ViewInfoQueryStatement with include_columns parameter."""
        expr = ViewInfoQueryStatement(
            dialect=backend_with_view.dialect, view_name="user_posts_summary", schema="main", include_columns=True
        )
        sql, params = expr.to_sql()
        result = backend_with_view.execute(sql, params)
        assert result is not None


class TestTriggerListExpressionExecution:
    """Tests for TriggerListQueryStatement execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_trigger):
        """Test TriggerListQueryStatement with constructor params can execute."""
        expr = TriggerListQueryStatement(dialect=backend_with_trigger.dialect, schema="main")
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_trigger.execute(sql, params)
        assert result is not None

    def test_table_name_filter(self, backend_with_trigger):
        """Test TriggerListQueryStatement with table_name filter."""
        expr = TriggerListQueryStatement(dialect=backend_with_trigger.dialect, schema="main", table_name="users")
        sql, params = expr.to_sql()
        result = backend_with_trigger.execute(sql, params)
        assert result is not None


class TestTriggerInfoExpressionExecution:
    """Tests for TriggerInfoQueryStatement execution with SQLite."""

    def test_constructor_params_execution(self, backend_with_trigger):
        """Test TriggerInfoQueryStatement with constructor params can execute."""
        expr = TriggerInfoQueryStatement(
            dialect=backend_with_trigger.dialect, trigger_name="update_user_timestamp", schema="main"
        )
        sql, params = expr.to_sql()
        assert sql is not None
        result = backend_with_trigger.execute(sql, params)
        assert result is not None

    def test_with_table_name(self, backend_with_trigger):
        """Test TriggerInfoQueryStatement with table_name parameter."""
        expr = TriggerInfoQueryStatement(
            dialect=backend_with_trigger.dialect,
            trigger_name="update_user_timestamp",
            schema="main",
            table_name="users",
        )
        sql, params = expr.to_sql()
        result = backend_with_trigger.execute(sql, params)
        assert result is not None
