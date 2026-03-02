# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_materialized_view.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall, TableExpression, QueryExpression,
    CreateMaterializedViewExpression, DropMaterializedViewExpression,
    RefreshMaterializedViewExpression
)
from rhosocial.activerecord.backend.expression.query_parts import GroupByHavingClause, OrderByClause
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCreateMaterializedViewStatements:
    """Tests for CREATE MATERIALIZED VIEW statement expressions."""

    def test_basic_create_materialized_view(self, dummy_dialect: DummyDialect):
        """Tests basic CREATE MATERIALIZED VIEW statement."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "users")
        )

        create_mv = CreateMaterializedViewExpression(
            dummy_dialect,
            view_name="user_summary",
            query=query
        )
        sql, params = create_mv.to_sql()

        assert 'CREATE MATERIALIZED VIEW "user_summary"' in sql
        assert 'SELECT "id", "name" FROM "users"' in sql
        assert 'WITH DATA' in sql
        assert params == ()

    def test_create_materialized_view_with_aggregates(self, dummy_dialect: DummyDialect):
        """Tests CREATE MATERIALIZED VIEW with aggregate query."""
        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "user_id"),
                FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id"), alias="order_count")
            ],
            from_=TableExpression(dummy_dialect, "orders"),
            group_by_having=GroupByHavingClause(
                dummy_dialect,
                group_by=[Column(dummy_dialect, "user_id")]
            )
        )

        create_mv = CreateMaterializedViewExpression(
            dummy_dialect,
            view_name="order_summary",
            query=query
        )
        sql, params = create_mv.to_sql()

        assert 'CREATE MATERIALIZED VIEW "order_summary"' in sql
        assert 'COUNT("id")' in sql
        assert 'GROUP BY "user_id"' in sql
        assert 'WITH DATA' in sql
        assert params == ()

    def test_create_materialized_view_with_column_aliases(self, dummy_dialect: DummyDialect):
        """Tests CREATE MATERIALIZED VIEW with column aliases."""
        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "user_id"),
                FunctionCall(dummy_dialect, "SUM", Column(dummy_dialect, "amount"))
            ],
            from_=TableExpression(dummy_dialect, "transactions"),
            group_by_having=GroupByHavingClause(
                dummy_dialect,
                group_by=[Column(dummy_dialect, "user_id")]
            )
        )

        create_mv = CreateMaterializedViewExpression(
            dummy_dialect,
            view_name="user_totals",
            query=query,
            column_aliases=["user_id", "total_amount"]
        )
        sql, params = create_mv.to_sql()

        assert 'CREATE MATERIALIZED VIEW "user_totals"' in sql
        assert '("user_id", "total_amount")' in sql
        assert 'WITH DATA' in sql

    def test_create_materialized_view_with_tablespace(self, dummy_dialect: DummyDialect):
        """Tests CREATE MATERIALIZED VIEW with tablespace."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "products")
        )

        create_mv = CreateMaterializedViewExpression(
            dummy_dialect,
            view_name="product_cache",
            query=query,
            tablespace="fast_storage"
        )
        sql, params = create_mv.to_sql()

        assert 'CREATE MATERIALIZED VIEW "product_cache"' in sql
        assert 'TABLESPACE "fast_storage"' in sql

    def test_create_materialized_view_with_no_data(self, dummy_dialect: DummyDialect):
        """Tests CREATE MATERIALIZED VIEW WITH NO DATA."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "categories")
        )

        create_mv = CreateMaterializedViewExpression(
            dummy_dialect,
            view_name="category_mv",
            query=query,
            with_data=False
        )
        sql, params = create_mv.to_sql()

        assert 'CREATE MATERIALIZED VIEW "category_mv"' in sql
        assert 'WITH NO DATA' in sql
        assert 'WITH DATA' not in sql


class TestDropMaterializedViewStatements:
    """Tests for DROP MATERIALIZED VIEW statement expressions."""

    def test_basic_drop_materialized_view(self, dummy_dialect: DummyDialect):
        """Tests basic DROP MATERIALIZED VIEW statement."""
        drop_mv = DropMaterializedViewExpression(
            dummy_dialect,
            view_name="old_summary"
        )
        sql, params = drop_mv.to_sql()

        assert sql == 'DROP MATERIALIZED VIEW "old_summary"'
        assert params == ()

    def test_drop_materialized_view_with_if_exists(self, dummy_dialect: DummyDialect):
        """Tests DROP MATERIALIZED VIEW IF EXISTS statement."""
        drop_mv = DropMaterializedViewExpression(
            dummy_dialect,
            view_name="possibly_missing_mv",
            if_exists=True
        )
        sql, params = drop_mv.to_sql()

        assert sql == 'DROP MATERIALIZED VIEW IF EXISTS "possibly_missing_mv"'
        assert params == ()

    def test_drop_materialized_view_with_cascade(self, dummy_dialect: DummyDialect):
        """Tests DROP MATERIALIZED VIEW ... CASCADE statement."""
        drop_mv = DropMaterializedViewExpression(
            dummy_dialect,
            view_name="parent_mv",
            cascade=True
        )
        sql, params = drop_mv.to_sql()

        assert sql == 'DROP MATERIALIZED VIEW "parent_mv" CASCADE'
        assert params == ()

    def test_drop_materialized_view_if_exists_cascade(self, dummy_dialect: DummyDialect):
        """Tests DROP MATERIALIZED VIEW IF EXISTS ... CASCADE statement."""
        drop_mv = DropMaterializedViewExpression(
            dummy_dialect,
            view_name="dependent_mv",
            if_exists=True,
            cascade=True
        )
        sql, params = drop_mv.to_sql()

        assert sql == 'DROP MATERIALIZED VIEW IF EXISTS "dependent_mv" CASCADE'
        assert params == ()


class TestRefreshMaterializedViewStatements:
    """Tests for REFRESH MATERIALIZED VIEW statement expressions."""

    def test_basic_refresh_materialized_view(self, dummy_dialect: DummyDialect):
        """Tests basic REFRESH MATERIALIZED VIEW statement."""
        refresh_mv = RefreshMaterializedViewExpression(
            dummy_dialect,
            view_name="user_summary"
        )
        sql, params = refresh_mv.to_sql()

        assert sql == 'REFRESH MATERIALIZED VIEW "user_summary"'
        assert params == ()

    def test_refresh_materialized_view_concurrent(self, dummy_dialect: DummyDialect):
        """Tests REFRESH MATERIALIZED VIEW CONCURRENTLY statement."""
        refresh_mv = RefreshMaterializedViewExpression(
            dummy_dialect,
            view_name="product_stats",
            concurrent=True
        )
        sql, params = refresh_mv.to_sql()

        assert 'REFRESH MATERIALIZED VIEW CONCURRENTLY "product_stats"' == sql
        assert params == ()

    def test_refresh_materialized_view_with_data(self, dummy_dialect: DummyDialect):
        """Tests REFRESH MATERIALIZED VIEW WITH DATA statement."""
        refresh_mv = RefreshMaterializedViewExpression(
            dummy_dialect,
            view_name="sales_summary",
            with_data=True
        )
        sql, params = refresh_mv.to_sql()

        assert sql == 'REFRESH MATERIALIZED VIEW "sales_summary" WITH DATA'
        assert params == ()

    def test_refresh_materialized_view_with_no_data(self, dummy_dialect: DummyDialect):
        """Tests REFRESH MATERIALIZED VIEW WITH NO DATA statement."""
        refresh_mv = RefreshMaterializedViewExpression(
            dummy_dialect,
            view_name="empty_view",
            with_data=False
        )
        sql, params = refresh_mv.to_sql()

        assert sql == 'REFRESH MATERIALIZED VIEW "empty_view" WITH NO DATA'
        assert params == ()

    def test_refresh_materialized_view_concurrent_with_data(self, dummy_dialect: DummyDialect):
        """Tests REFRESH MATERIALIZED VIEW CONCURRENTLY WITH DATA statement."""
        refresh_mv = RefreshMaterializedViewExpression(
            dummy_dialect,
            view_name="complex_stats",
            concurrent=True,
            with_data=True
        )
        sql, params = refresh_mv.to_sql()

        assert 'REFRESH MATERIALIZED VIEW CONCURRENTLY "complex_stats" WITH DATA' == sql
        assert params == ()


class TestMaterializedViewRoundtrip:
    """Tests for complete materialized view lifecycle."""

    def test_materialized_view_create_drop_refresh_cycle(self, dummy_dialect: DummyDialect):
        """Tests creating, refreshing, and dropping a materialized view."""
        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "department"),
                FunctionCall(dummy_dialect, "AVG", Column(dummy_dialect, "salary"))
            ],
            from_=TableExpression(dummy_dialect, "employees"),
            group_by_having=GroupByHavingClause(
                dummy_dialect,
                group_by=[Column(dummy_dialect, "department")]
            )
        )

        # Create
        create_mv = CreateMaterializedViewExpression(
            dummy_dialect,
            view_name="dept_avg_salary",
            query=query
        )
        create_sql, create_params = create_mv.to_sql()

        # Refresh
        refresh_mv = RefreshMaterializedViewExpression(
            dummy_dialect,
            view_name="dept_avg_salary"
        )
        refresh_sql, refresh_params = refresh_mv.to_sql()

        # Drop
        drop_mv = DropMaterializedViewExpression(
            dummy_dialect,
            view_name="dept_avg_salary"
        )
        drop_sql, drop_params = drop_mv.to_sql()

        assert 'CREATE MATERIALIZED VIEW "dept_avg_salary"' in create_sql
        assert 'WITH DATA' in create_sql
        assert 'REFRESH MATERIALIZED VIEW "dept_avg_salary"' == refresh_sql
        assert 'DROP MATERIALIZED VIEW "dept_avg_salary"' == drop_sql
        assert create_params == ()
        assert refresh_params == ()
        assert drop_params == ()

    @pytest.mark.parametrize("view_name", [
        pytest.param("simple_mv", id="simple_name"),
        pytest.param("mv_with_underscores", id="underscore_name"),
        pytest.param("MVWithCamelCase", id="camelcase_name"),
    ])
    def test_materialized_view_various_names(self, dummy_dialect: DummyDialect, view_name: str):
        """Tests materialized view statements with various name formats."""
        query = QueryExpression(
            dummy_dialect,
            select=[Literal(dummy_dialect, 1)]
        )

        create_mv = CreateMaterializedViewExpression(
            dummy_dialect,
            view_name=view_name,
            query=query
        )
        sql, params = create_mv.to_sql()

        assert f'CREATE MATERIALIZED VIEW "{view_name}"' in sql
