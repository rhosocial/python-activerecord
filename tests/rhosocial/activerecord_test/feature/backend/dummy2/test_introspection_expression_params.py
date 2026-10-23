# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_introspection_expression_params.py
"""
Tests for introspection expression instantiation parameters.

This module tests that all introspection expression classes properly
accept parameters at construction time and generate correct SQL.
"""


from rhosocial.activerecord.backend.expression.introspection import (
    IntrospectionExpression,
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


class TestIntrospectionExpressionParams:
    """Tests for introspection expression construction parameters."""

    def test_introspection_expression_with_schema(self, dummy_dialect):
        """Test IntrospectionExpression accepts schema parameter."""
        expr = IntrospectionExpression(dummy_dialect, schema="public")
        params = expr.get_params()
        assert params.get("schema") == "public"

    def test_introspection_expression_fluent_schema(self, dummy_dialect):
        """Test schema can be set via fluent API."""
        expr = IntrospectionExpression(dummy_dialect).with_schema("public")
        params = expr.get_params()
        assert params.get("schema") == "public"


class TestTableListExpressionParams:
    """Tests for TableListQueryStatement construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test TableListQueryStatement accepts all parameters at construction."""
        expr = TableListQueryStatement(
            dialect=dummy_dialect, schema="main", include_views=False, include_system=True, table_type="TABLE"
        )
        params = expr.get_params()
        assert params.get("schema") == "main"
        assert params.get("include_views") is False
        assert params.get("include_system") is True
        assert params.get("table_type") == "TABLE"

    def test_constructor_defaults(self, dummy_dialect):
        """Test TableListQueryStatement default values."""
        expr = TableListQueryStatement(dialect=dummy_dialect)
        params = expr.get_params()
        assert params.get("schema") is None
        assert params.get("include_views") is True
        assert params.get("include_system") is False
        assert params.get("table_type") is None

    def test_fluent_api_override(self, dummy_dialect):
        """Test fluent API can override constructor values."""
        expr = TableListQueryStatement(dialect=dummy_dialect, include_views=False).with_include_views(True)
        params = expr.get_params()
        assert params.get("include_views") is True


class TestTableInfoExpressionParams:
    """Tests for TableInfoQueryStatement construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test TableInfoQueryStatement accepts all parameters at construction."""
        expr = TableInfoQueryStatement(
            dialect=dummy_dialect,
            table_name="users",
            schema="public",
            include_columns=False,
            include_indexes=False,
            include_foreign_keys=False,
        )
        params = expr.get_params()
        assert params.get("table_name") == "users"
        assert params.get("schema") == "public"
        assert params.get("include_columns") is False
        assert params.get("include_indexes") is False
        assert params.get("include_foreign_keys") is False

    def test_constructor_defaults(self, dummy_dialect):
        """Test TableInfoQueryStatement default values."""
        expr = TableInfoQueryStatement(dialect=dummy_dialect, table_name="users")
        params = expr.get_params()
        assert params.get("table_name") == "users"
        assert params.get("schema") is None
        assert params.get("include_columns") is True
        assert params.get("include_indexes") is True
        assert params.get("include_foreign_keys") is True

    def test_fluent_api_override(self, dummy_dialect):
        """Test fluent API can override constructor values."""
        expr = (
            TableInfoQueryStatement(dialect=dummy_dialect, table_name="users", include_columns=False)
            .with_include_columns(True)
            .with_table_name("posts")
        )
        params = expr.get_params()
        assert params.get("table_name") == "posts"
        assert params.get("include_columns") is True


class TestColumnInfoExpressionParams:
    """Tests for ColumnInfoQueryStatement construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test ColumnInfoQueryStatement accepts all parameters at construction."""
        expr = ColumnInfoQueryStatement(dialect=dummy_dialect, table_name="users", schema="public", include_hidden=True)
        params = expr.get_params()
        assert params.get("table_name") == "users"
        assert params.get("schema") == "public"
        assert params.get("include_hidden") is True

    def test_constructor_defaults(self, dummy_dialect):
        """Test ColumnInfoQueryStatement default values."""
        expr = ColumnInfoQueryStatement(dialect=dummy_dialect, table_name="users")
        params = expr.get_params()
        assert params.get("table_name") == "users"
        assert params.get("schema") is None
        assert params.get("include_hidden") is False


class TestIndexInfoExpressionParams:
    """Tests for IndexInfoQueryStatement construction parameters."""

    def test_constructor_with_schema(self, dummy_dialect):
        """Test IndexInfoQueryStatement accepts schema parameter."""
        expr = IndexInfoQueryStatement(dialect=dummy_dialect, table_name="users", schema="main")
        params = expr.get_params()
        assert params.get("table_name") == "users"
        assert params.get("schema") == "main"

    def test_constructor_defaults(self, dummy_dialect):
        """Test IndexInfoQueryStatement default values."""
        expr = IndexInfoQueryStatement(dialect=dummy_dialect, table_name="users")
        params = expr.get_params()
        assert params.get("table_name") == "users"
        assert params.get("schema") is None


class TestForeignKeyExpressionParams:
    """Tests for ForeignKeyQueryStatement construction parameters."""

    def test_constructor_with_schema(self, dummy_dialect):
        """Test ForeignKeyQueryStatement accepts schema parameter."""
        expr = ForeignKeyQueryStatement(dialect=dummy_dialect, table_name="posts", schema="public")
        params = expr.get_params()
        assert params.get("table_name") == "posts"
        assert params.get("schema") == "public"

    def test_constructor_defaults(self, dummy_dialect):
        """Test ForeignKeyQueryStatement default values."""
        expr = ForeignKeyQueryStatement(dialect=dummy_dialect, table_name="posts")
        params = expr.get_params()
        assert params.get("table_name") == "posts"
        assert params.get("schema") is None


class TestViewListExpressionParams:
    """Tests for ViewListQueryStatement construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test ViewListQueryStatement accepts all parameters at construction."""
        expr = ViewListQueryStatement(dialect=dummy_dialect, schema="main", include_system=True)
        params = expr.get_params()
        assert params.get("schema") == "main"
        assert params.get("include_system") is True

    def test_constructor_defaults(self, dummy_dialect):
        """Test ViewListQueryStatement default values."""
        expr = ViewListQueryStatement(dialect=dummy_dialect)
        params = expr.get_params()
        assert params.get("schema") is None
        assert params.get("include_system") is False

    def test_fluent_api_override(self, dummy_dialect):
        """Test fluent API can override constructor values."""
        expr = ViewListQueryStatement(dialect=dummy_dialect, include_system=False).with_include_system(True)
        params = expr.get_params()
        assert params.get("include_system") is True


class TestViewInfoExpressionParams:
    """Tests for ViewInfoQueryStatement construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test ViewInfoQueryStatement accepts all parameters at construction."""
        expr = ViewInfoQueryStatement(
            dialect=dummy_dialect, view_name="user_view", schema="public", include_columns=False
        )
        params = expr.get_params()
        assert params.get("view_name") == "user_view"
        assert params.get("schema") == "public"
        assert params.get("include_columns") is False

    def test_constructor_defaults(self, dummy_dialect):
        """Test ViewInfoQueryStatement default values."""
        expr = ViewInfoQueryStatement(dialect=dummy_dialect, view_name="user_view")
        params = expr.get_params()
        assert params.get("view_name") == "user_view"
        assert params.get("schema") is None
        assert params.get("include_columns") is True


class TestTriggerListExpressionParams:
    """Tests for TriggerListQueryStatement construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test TriggerListQueryStatement accepts all parameters at construction."""
        expr = TriggerListQueryStatement(dialect=dummy_dialect, schema="main", table_name="users")
        params = expr.get_params()
        assert params.get("schema") == "main"
        assert params.get("table_name") == "users"

    def test_constructor_defaults(self, dummy_dialect):
        """Test TriggerListQueryStatement default values."""
        expr = TriggerListQueryStatement(dialect=dummy_dialect)
        params = expr.get_params()
        assert params.get("schema") is None
        assert params.get("table_name") is None

    def test_fluent_api_for_table(self, dummy_dialect):
        """Test for_table fluent API."""
        expr = TriggerListQueryStatement(dialect=dummy_dialect, table_name="users").for_table("posts")
        params = expr.get_params()
        assert params.get("table_name") == "posts"


class TestTriggerInfoExpressionParams:
    """Tests for TriggerInfoQueryStatement construction parameters."""

    def test_constructor_with_all_params(self, dummy_dialect):
        """Test TriggerInfoQueryStatement accepts all parameters at construction."""
        expr = TriggerInfoQueryStatement(
            dialect=dummy_dialect, trigger_name="my_trigger", schema="main", table_name="users"
        )
        params = expr.get_params()
        assert params.get("trigger_name") == "my_trigger"
        assert params.get("schema") == "main"
        assert params.get("table_name") == "users"

    def test_constructor_defaults(self, dummy_dialect):
        """Test TriggerInfoQueryStatement default values."""
        expr = TriggerInfoQueryStatement(dialect=dummy_dialect, trigger_name="my_trigger")
        params = expr.get_params()
        assert params.get("trigger_name") == "my_trigger"
        assert params.get("schema") is None
        assert params.get("table_name") is None
