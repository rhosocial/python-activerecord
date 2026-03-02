# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_materialized_view.py
"""
Tests for SQLite materialized view support.

SQLite does not support materialized views, so these tests verify that:
1. The dialect correctly reports that materialized views are not supported
2. Attempting to use materialized view operations raises UnsupportedFeatureError
3. Regular view operations still work correctly
"""
import pytest
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall, TableExpression, QueryExpression,
    CreateMaterializedViewExpression, DropMaterializedViewExpression,
    RefreshMaterializedViewExpression, CreateViewExpression, DropViewExpression
)
from rhosocial.activerecord.backend.expression.query_parts import GroupByHavingClause
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class TestSQLiteMaterializedViewSupport:
    """Test SQLite materialized view feature detection."""

    def test_supports_materialized_view_false(self, sqlite_dialect: SQLiteDialect):
        """SQLite does not support materialized views regardless of version."""
        assert sqlite_dialect.supports_materialized_view() == False

    def test_supports_refresh_materialized_view_false(self, sqlite_dialect: SQLiteDialect):
        """SQLite does not support REFRESH MATERIALIZED VIEW."""
        assert sqlite_dialect.supports_refresh_materialized_view() == False

    def test_supports_materialized_view_concurrent_refresh_false(self, sqlite_dialect: SQLiteDialect):
        """SQLite does not support concurrent refresh."""
        assert sqlite_dialect.supports_materialized_view_concurrent_refresh() == False

    def test_supports_materialized_view_tablespace_false(self, sqlite_dialect: SQLiteDialect):
        """SQLite does not support tablespace for materialized views."""
        assert sqlite_dialect.supports_materialized_view_tablespace() == False

    def test_supports_materialized_view_storage_options_false(self, sqlite_dialect: SQLiteDialect):
        """SQLite does not support storage options for materialized views."""
        assert sqlite_dialect.supports_materialized_view_storage_options() == False


class TestSQLiteMaterializedViewErrors:
    """Test that materialized view operations raise appropriate errors."""

    def test_create_materialized_view_raises_error(self, sqlite_dialect: SQLiteDialect):
        """Test that CREATE MATERIALIZED VIEW raises UnsupportedFeatureError."""
        query = QueryExpression(
            sqlite_dialect,
            select=[Column(sqlite_dialect, "id"), Column(sqlite_dialect, "name")],
            from_=TableExpression(sqlite_dialect, "users")
        )
        create_mv = CreateMaterializedViewExpression(
            sqlite_dialect,
            view_name="user_summary",
            query=query
        )
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            create_mv.to_sql()
        
        assert "CREATE MATERIALIZED VIEW" in str(exc_info.value)
        assert "SQLite" in str(exc_info.value)
        assert "does not support materialized views" in str(exc_info.value)

    def test_create_materialized_view_with_aggregates_raises_error(self, sqlite_dialect: SQLiteDialect):
        """Test that CREATE MATERIALIZED VIEW with aggregates raises error."""
        query = QueryExpression(
            sqlite_dialect,
            select=[
                Column(sqlite_dialect, "user_id"),
                FunctionCall(sqlite_dialect, "COUNT", Column(sqlite_dialect, "id"))
            ],
            from_=TableExpression(sqlite_dialect, "orders"),
            group_by_having=GroupByHavingClause(
                sqlite_dialect,
                group_by=[Column(sqlite_dialect, "user_id")]
            )
        )
        create_mv = CreateMaterializedViewExpression(
            sqlite_dialect,
            view_name="order_counts",
            query=query
        )
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            create_mv.to_sql()
        
        assert "CREATE MATERIALIZED VIEW" in str(exc_info.value)

    def test_drop_materialized_view_raises_error(self, sqlite_dialect: SQLiteDialect):
        """Test that DROP MATERIALIZED VIEW raises UnsupportedFeatureError."""
        drop_mv = DropMaterializedViewExpression(
            sqlite_dialect,
            view_name="old_summary"
        )
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            drop_mv.to_sql()
        
        assert "DROP MATERIALIZED VIEW" in str(exc_info.value)
        assert "SQLite" in str(exc_info.value)

    def test_drop_materialized_view_if_exists_raises_error(self, sqlite_dialect: SQLiteDialect):
        """Test that DROP MATERIALIZED VIEW IF EXISTS raises error."""
        drop_mv = DropMaterializedViewExpression(
            sqlite_dialect,
            view_name="possibly_missing",
            if_exists=True
        )
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            drop_mv.to_sql()
        
        assert "DROP MATERIALIZED VIEW" in str(exc_info.value)

    def test_refresh_materialized_view_raises_error(self, sqlite_dialect: SQLiteDialect):
        """Test that REFRESH MATERIALIZED VIEW raises UnsupportedFeatureError."""
        refresh_mv = RefreshMaterializedViewExpression(
            sqlite_dialect,
            view_name="user_summary"
        )
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            refresh_mv.to_sql()
        
        assert "REFRESH MATERIALIZED VIEW" in str(exc_info.value)
        assert "SQLite" in str(exc_info.value)

    def test_refresh_materialized_view_concurrent_raises_error(self, sqlite_dialect: SQLiteDialect):
        """Test that REFRESH MATERIALIZED VIEW CONCURRENTLY raises error."""
        refresh_mv = RefreshMaterializedViewExpression(
            sqlite_dialect,
            view_name="stats",
            concurrent=True
        )
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            refresh_mv.to_sql()
        
        assert "REFRESH MATERIALIZED VIEW" in str(exc_info.value)


class TestSQLiteRegularViewSupport:
    """Test that SQLite regular view operations work correctly."""

    def test_supports_create_view_true(self, sqlite_dialect: SQLiteDialect):
        """SQLite supports CREATE VIEW."""
        assert sqlite_dialect.supports_create_view() == True

    def test_supports_drop_view_true(self, sqlite_dialect: SQLiteDialect):
        """SQLite supports DROP VIEW."""
        assert sqlite_dialect.supports_drop_view() == True

    def test_supports_or_replace_view_true(self, sqlite_dialect: SQLiteDialect):
        """SQLite supports CREATE VIEW IF NOT EXISTS (similar to OR REPLACE)."""
        assert sqlite_dialect.supports_or_replace_view() == True

    def test_supports_temporary_view_true(self, sqlite_dialect: SQLiteDialect):
        """SQLite supports TEMPORARY views."""
        assert sqlite_dialect.supports_temporary_view() == True

    def test_supports_if_exists_view_true(self, sqlite_dialect: SQLiteDialect):
        """SQLite supports DROP VIEW IF EXISTS."""
        assert sqlite_dialect.supports_if_exists_view() == True

    def test_supports_view_check_option_false(self, sqlite_dialect: SQLiteDialect):
        """SQLite does not support WITH CHECK OPTION."""
        assert sqlite_dialect.supports_view_check_option() == False

    def test_supports_cascade_view_false(self, sqlite_dialect: SQLiteDialect):
        """SQLite does not support CASCADE for DROP VIEW."""
        assert sqlite_dialect.supports_cascade_view() == False

    def test_basic_create_view(self, sqlite_dialect: SQLiteDialect):
        """Test basic CREATE VIEW works."""
        query = QueryExpression(
            sqlite_dialect,
            select=[Column(sqlite_dialect, "id"), Column(sqlite_dialect, "name")],
            from_=TableExpression(sqlite_dialect, "users")
        )
        create_view = CreateViewExpression(
            sqlite_dialect,
            view_name="user_view",
            query=query
        )
        sql, params = create_view.to_sql()
        
        assert 'CREATE VIEW "user_view"' in sql
        assert 'SELECT "id", "name" FROM "users"' in sql

    def test_create_temporary_view(self, sqlite_dialect: SQLiteDialect):
        """Test CREATE TEMPORARY VIEW works."""
        query = QueryExpression(
            sqlite_dialect,
            select=[Column(sqlite_dialect, "id")],
            from_=TableExpression(sqlite_dialect, "sessions")
        )
        create_view = CreateViewExpression(
            sqlite_dialect,
            view_name="temp_session_view",
            query=query,
            temporary=True
        )
        sql, params = create_view.to_sql()
        
        assert 'CREATE TEMPORARY VIEW "temp_session_view"' in sql

    def test_create_view_if_not_exists(self, sqlite_dialect: SQLiteDialect):
        """Test CREATE VIEW IF NOT EXISTS works (SQLite style)."""
        query = QueryExpression(
            sqlite_dialect,
            select=[Column(sqlite_dialect, "id")],
            from_=TableExpression(sqlite_dialect, "products")
        )
        create_view = CreateViewExpression(
            sqlite_dialect,
            view_name="product_view",
            query=query,
            replace=True
        )
        sql, params = create_view.to_sql()
        
        assert 'CREATE VIEW IF NOT EXISTS "product_view"' in sql

    def test_drop_view(self, sqlite_dialect: SQLiteDialect):
        """Test DROP VIEW works."""
        drop_view = DropViewExpression(
            sqlite_dialect,
            view_name="old_view"
        )
        sql, params = drop_view.to_sql()
        
        assert sql == 'DROP VIEW "old_view"'

    def test_drop_view_if_exists(self, sqlite_dialect: SQLiteDialect):
        """Test DROP VIEW IF EXISTS works."""
        drop_view = DropViewExpression(
            sqlite_dialect,
            view_name="possibly_missing",
            if_exists=True
        )
        sql, params = drop_view.to_sql()
        
        assert sql == 'DROP VIEW IF EXISTS "possibly_missing"'

    def test_create_view_with_column_aliases(self, sqlite_dialect: SQLiteDialect):
        """Test CREATE VIEW with column aliases."""
        query = QueryExpression(
            sqlite_dialect,
            select=[Column(sqlite_dialect, "id"), Column(sqlite_dialect, "name")],
            from_=TableExpression(sqlite_dialect, "users")
        )
        create_view = CreateViewExpression(
            sqlite_dialect,
            view_name="aliased_view",
            query=query,
            column_aliases=["user_id", "user_name"]
        )
        sql, params = create_view.to_sql()
        
        assert 'CREATE VIEW "aliased_view" ("user_id", "user_name")' in sql


class TestSQLiteMaterializedViewAlternatives:
    """Test suggestions for materialized view alternatives."""

    def test_error_message_suggests_alternatives(self, sqlite_dialect: SQLiteDialect):
        """Test that error message suggests alternatives."""
        query = QueryExpression(
            sqlite_dialect,
            select=[Column(sqlite_dialect, "id")],
            from_=TableExpression(sqlite_dialect, "users")
        )
        create_mv = CreateMaterializedViewExpression(
            sqlite_dialect,
            view_name="test_mv",
            query=query
        )
        
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            create_mv.to_sql()
        
        error_msg = str(exc_info.value)
        assert "regular views" in error_msg.lower() or "tables" in error_msg.lower()
