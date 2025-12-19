import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, TableExpression, FunctionCall, RawSQLExpression,
    QueryExpression, InsertExpression, UpdateExpression, DeleteExpression,
    # Import new EXPLAIN-related classes
    ExplainExpression, ExplainOptions, ExplainType, ExplainFormat,
    # Import other classes as needed
    ComparisonPredicate,
    # Import aggregate functions
    count
)
from rhosocial.activerecord.backend.expression.statements import (
    ValuesSource
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestExplainStatementsExtended:
    """Extended tests for EXPLAIN statements with various configurations and options."""

    def test_basic_explain_query(self, dummy_dialect: DummyDialect):
        """Tests basic EXPLAIN statement with a SELECT query."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "users")
        )

        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query
        )
        sql, params = explain_expr.to_sql()
        # Basic EXPLAIN should exist
        assert sql.startswith('EXPLAIN ')
        assert 'SELECT "id", "name" FROM "users"' in sql
        assert params == ()

    def test_basic_explain_insert(self, dummy_dialect: DummyDialect):
        """Tests basic EXPLAIN statement with an INSERT query."""
        insert_query = InsertExpression(
            dummy_dialect,
            into=TableExpression(dummy_dialect, "users"),
            source=ValuesSource(
                dummy_dialect,
                values_list=[[Literal(dummy_dialect, "John Doe"), Literal(dummy_dialect, "john@example.com")]]
            )
        )

        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=insert_query
        )
        sql, params = explain_expr.to_sql()
        assert sql.startswith('EXPLAIN ')
        assert 'INSERT INTO "users"' in sql
        assert params == ("John Doe", "john@example.com")

    def test_basic_explain_update(self, dummy_dialect: DummyDialect):
        """Tests basic EXPLAIN statement with an UPDATE query."""
        update_query = UpdateExpression(
            dummy_dialect,
            table=TableExpression(dummy_dialect, "users"),
            assignments={
                "name": Literal(dummy_dialect, "Jane Smith")
            },
            where=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id"),
                Literal(dummy_dialect, 1)
            )
        )

        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=update_query
        )
        sql, params = explain_expr.to_sql()
        assert sql.startswith('EXPLAIN ')
        assert 'UPDATE "users" SET' in sql
        assert params == ("Jane Smith", 1)

    def test_basic_explain_delete(self, dummy_dialect: DummyDialect):
        """Tests basic EXPLAIN statement with a DELETE query."""
        delete_query = DeleteExpression(
            dummy_dialect,
            table=TableExpression(dummy_dialect, "users"),
            where=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "status"),
                Literal(dummy_dialect, "inactive")
            )
        )

        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=delete_query
        )
        sql, params = explain_expr.to_sql()
        assert sql.startswith('EXPLAIN ')
        assert 'DELETE FROM "users" WHERE "status" = ?' in sql
        assert params == ("inactive",)

    # --- Test EXPLAIN with ANALYZE option ---
    def test_explain_with_analyze_option(self, dummy_dialect: DummyDialect):
        """Tests EXPLAIN statement with ANALYZE option."""
        query = QueryExpression(
            dummy_dialect,
            select=[FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id"))],
            from_=TableExpression(dummy_dialect, "orders"),
            where=ComparisonPredicate(
                dummy_dialect,
                ">",
                Column(dummy_dialect, "order_date"),
                Literal(dummy_dialect, "2023-01-01")
            )
        )

        explain_options = ExplainOptions(analyze=True)
        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=explain_options
        )
        sql, params = explain_expr.to_sql()
        assert 'EXPLAIN ANALYZE' in sql
        assert 'COUNT("id") FROM "orders" WHERE "order_date" > ?' in sql
        assert params == ("2023-01-01",)

    # --- Test EXPLAIN with different output formats ---
    @pytest.mark.parametrize("format_type,expected_format_clause", [
        (ExplainFormat.TEXT, "FORMAT TEXT"),
        (ExplainFormat.JSON, "FORMAT JSON"),
        (ExplainFormat.XML, "FORMAT XML"),
        (ExplainFormat.YAML, "FORMAT YAML"),
        (ExplainFormat.TRADITIONAL, "FORMAT TRADITIONAL"),
    ])
    def test_explain_with_different_formats(self, dummy_dialect: DummyDialect, format_type, expected_format_clause):
        """Tests EXPLAIN with different output formats."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "name"), Column(dummy_dialect, "email")],
            from_=TableExpression(dummy_dialect, "users"),
            order_by=[Column(dummy_dialect, "name")]
        )

        explain_options = ExplainOptions(format=format_type)
        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=explain_options
        )
        sql, params = explain_expr.to_sql()
        assert f'EXPLAIN {expected_format_clause}' in sql
        assert '"name", "email" FROM "users" ORDER BY "name"' in sql
        assert params == ()

    # --- Test EXPLAIN with various option combinations ---
    def test_explain_with_costs_disabled(self, dummy_dialect: DummyDialect):
        """Tests EXPLAIN with costs disabled."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "large_table")
        )

        explain_options = ExplainOptions(costs=False)  # Disable costs display
        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=explain_options
        )
        sql, params = explain_expr.to_sql()
        assert 'EXPLAIN COSTS OFF' in sql  # Check that costs off is included
        assert 'SELECT "id" FROM "large_table"' in sql
        assert params == ()

    def test_explain_with_buffers_enabled(self, dummy_dialect: DummyDialect):
        """Tests EXPLAIN with buffers enabled."""
        query = QueryExpression(
            dummy_dialect,
            select=[FunctionCall(dummy_dialect, "SUM", Column(dummy_dialect, "amount"))],
            from_=TableExpression(dummy_dialect, "transactions")
        )

        explain_options = ExplainOptions(buffers=True, analyze=True)  # Enable buffers and analyze
        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=explain_options
        )
        sql, params = explain_expr.to_sql()
        assert 'EXPLAIN ANALYZE' in sql
        assert 'BUFFERS' in sql  # Check that buffers option is included
        assert 'SUM("amount") FROM "transactions"' in sql
        assert params == ()

    def test_explain_with_timing_enabled(self, dummy_dialect: DummyDialect):
        """Tests EXPLAIN with timing enabled (requires ANALYZE)."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "product_name"), Column(dummy_dialect, "price")],
            from_=TableExpression(dummy_dialect, "products"),
            where=ComparisonPredicate(
                dummy_dialect,
                ">",
                Column(dummy_dialect, "price"),
                Literal(dummy_dialect, 100)
            ),
            order_by=[(Column(dummy_dialect, "price"), "DESC")]
        )

        explain_options = ExplainOptions(timing=True, analyze=True)  # Timing requires ANALYZE
        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=explain_options
        )
        sql, params = explain_expr.to_sql()
        assert 'EXPLAIN ANALYZE' in sql
        assert 'TIMING ON' in sql  # Check that timing option is included
        assert '"product_name", "price" FROM "products" WHERE "price" > ? ORDER BY "price" DESC' in sql
        assert params == (100,)

    def test_explain_with_verbose_enabled(self, dummy_dialect: DummyDialect):
        """Tests EXPLAIN with verbose output enabled."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "category"), count(dummy_dialect, "*")],
            from_=TableExpression(dummy_dialect, "products"),
            group_by=[Column(dummy_dialect, "category")]
        )

        explain_options = ExplainOptions(verbose=True)
        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=explain_options
        )
        sql, params = explain_expr.to_sql()
        assert 'EXPLAIN VERBOSE' in sql  # Check that verbose option is included
        assert 'COUNT(*) FROM "products" GROUP BY "category"' in sql
        assert params == ()

    def test_explain_with_multiple_options(self, dummy_dialect: DummyDialect):
        """Tests EXPLAIN with multiple options enabled."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "created_at")],
            from_=TableExpression(dummy_dialect, "logs"),
            where=ComparisonPredicate(
                dummy_dialect,
                ">",
                Column(dummy_dialect, "created_at"),
                Literal(dummy_dialect, "2024-01-01")
            ),
            order_by=[Column(dummy_dialect, "created_at")],
            limit=100
        )

        # Combine multiple options
        explain_options = ExplainOptions(
            analyze=True,
            buffers=True,
            timing=True,
            verbose=True,
            format=ExplainFormat.JSON
        )
        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=explain_options
        )
        sql, params = explain_expr.to_sql()
        # Check that multiple options are present
        assert 'EXPLAIN ANALYZE' in sql
        assert 'BUFFERS' in sql
        assert 'TIMING ON' in sql
        assert 'VERBOSE' in sql
        assert 'FORMAT JSON' in sql
        assert 'SELECT "id", "created_at" FROM "logs" WHERE "created_at" > ? ORDER BY "created_at" LIMIT ?' in sql
        assert params == ("2024-01-01", 100)

    def test_explain_with_enable_settings_option(self, dummy_dialect: DummyDialect):
        """Tests EXPLAIN with settings impact display enabled."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "title")],
            from_=TableExpression(dummy_dialect, "articles"),
            where=ComparisonPredicate(
                dummy_dialect,
                "LIKE",
                Column(dummy_dialect, "title"),
                Literal(dummy_dialect, "%python%")
            )
        )

        explain_options = ExplainOptions(enable_settings=True)
        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=explain_options
        )
        sql, params = explain_expr.to_sql()
        assert 'EXPLAIN SETTINGS' in sql  # Check that settings option is included
        assert 'SELECT "title" FROM "articles" WHERE "title" LIKE ?' in sql
        assert params == ("%python%",)

    def test_explain_with_wal_option(self, dummy_dialect: DummyDialect):
        """Tests EXPLAIN with WAL statistics enabled (PostgreSQL-specific feature)."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "transaction_id")],
            from_=TableExpression(dummy_dialect, "financial_transactions"),
            where=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "status"),
                Literal(dummy_dialect, "failed")
            )
        )

        explain_options = ExplainOptions(wal=True)
        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=explain_options
        )
        sql, params = explain_expr.to_sql()
        assert 'EXPLAIN WAL' in sql  # Check that WAL option is included
        assert 'SELECT "transaction_id" FROM "financial_transactions" WHERE "status" = ?' in sql
        assert params == ("failed",)

    # --- Test edge cases and error conditions ---
    def test_explain_with_none_options(self, dummy_dialect: DummyDialect):
        """Tests EXPLAIN with None options (should work like basic EXPLAIN)."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "simple_table")
        )

        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=None  # Explicitly pass None
        )
        sql, params = explain_expr.to_sql()
        assert sql == 'EXPLAIN SELECT "id" FROM "simple_table"'
        assert params == ()