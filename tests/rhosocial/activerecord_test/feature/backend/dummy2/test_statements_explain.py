# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_explain.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, TableExpression,
    QueryExpression, InsertExpression, UpdateExpression, DeleteExpression,
    ExplainExpression, FunctionCall
)
from rhosocial.activerecord.backend.expression.statements import (
    ExplainOptions, ExplainType, ExplainFormat
)
from rhosocial.activerecord.backend.expression.statements import ValuesSource
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.query_parts import WhereClause


class TestExplainStatements:
    """Tests for EXPLAIN statements with various options."""

    def test_basic_explain_query(self, dummy_dialect: DummyDialect):
        """Tests basic EXPLAIN statement with a SELECT query."""
        # Create a base query to EXPLAIN
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

    @pytest.mark.parametrize(
        "explain_type,expected_prefix", 
        [
            pytest.param(ExplainType.BASIC, "EXPLAIN", id="basic_explain"),
            pytest.param(ExplainType.ANALYZE, "EXPLAIN ANALYZE", id="analyze_explain"),
        ]
    )
    def test_explain_with_types(self, dummy_dialect: DummyDialect, explain_type, expected_prefix):
        """Tests EXPLAIN with different types (BASIC, ANALYZE)."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "products"),
            where=WhereClause(dummy_dialect, condition=Column(dummy_dialect, "price") > Literal(dummy_dialect, 100))
        )

        # Create EXPLAIN options
        options = ExplainOptions(type=explain_type)

        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=options
        )
        sql, params = explain_expr.to_sql()
        assert sql.startswith(expected_prefix)
        assert 'SELECT "id" FROM "products" WHERE "price" > ?' in sql
        assert params == (100,)

    @pytest.mark.parametrize(
        "format_type,expected_format_clause", 
        [
            pytest.param(ExplainFormat.TEXT, "FORMAT TEXT", id="text_format"),
            pytest.param(ExplainFormat.JSON, "FORMAT JSON", id="json_format"),
            pytest.param(ExplainFormat.TREE, "FORMAT TREE", id="tree_format"),
        ]
    )
    def test_explain_with_formats(self, dummy_dialect: DummyDialect, format_type, expected_format_clause):
        """Tests EXPLAIN with different output formats."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "employees")
        )

        # Create EXPLAIN options with specific format
        options = ExplainOptions(type=ExplainType.BASIC, format=format_type)

        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=options
        )
        sql, params = explain_expr.to_sql()
        assert 'EXPLAIN' in sql
        assert expected_format_clause in sql
        assert params == ()

    def test_explain_with_analyze_and_format(self, dummy_dialect: DummyDialect):
        """Tests EXPLAIN with both ANALYZE and FORMAT options."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "total")],
            from_=TableExpression(dummy_dialect, "orders"),
            where=WhereClause(dummy_dialect, condition=Column(dummy_dialect, "order_date") > Literal(dummy_dialect, "2024-01-01"))
        )

        # Create EXPLAIN options with ANALYZE and JSON format
        options = ExplainOptions(type=ExplainType.ANALYZE, format=ExplainFormat.JSON)

        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=options
        )
        sql, params = explain_expr.to_sql()
        assert sql.startswith('EXPLAIN ANALYZE')
        assert 'FORMAT JSON' in sql
        assert params == ("2024-01-01",)

    @pytest.mark.parametrize(
        "statement_type", 
        [
            pytest.param("SELECT", id="explain_select"),
            pytest.param("INSERT", id="explain_insert"),
            pytest.param("UPDATE", id="explain_update"),
            pytest.param("DELETE", id="explain_delete"),
        ]
    )
    def test_explain_with_different_statements(self, dummy_dialect: DummyDialect, statement_type):
        """Tests EXPLAIN with different types of SQL statements."""
        if statement_type == "SELECT":
            stmt = QueryExpression(
                dummy_dialect,
                select=[Column(dummy_dialect, "id")],
                from_=TableExpression(dummy_dialect, "test_table")
            )
        elif statement_type == "INSERT":
            stmt = InsertExpression(
                dummy_dialect,
                into=TableExpression(dummy_dialect, "test_table"),
                source=ValuesSource(dummy_dialect, values_list=[[Literal(dummy_dialect, "test")]])
            )
        elif statement_type == "UPDATE":
            stmt = UpdateExpression(
                dummy_dialect,
                table=TableExpression(dummy_dialect, "test_table"),
                assignments={"name": Literal(dummy_dialect, "updated")},
                where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
            )
        elif statement_type == "DELETE":
            stmt = DeleteExpression(
                dummy_dialect,
                table=TableExpression(dummy_dialect, "test_table"),
                where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
            )

        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=stmt
        )
        sql, params = explain_expr.to_sql()
        assert sql.startswith('EXPLAIN ')
        # Should contain the appropriate statement type
        assert statement_type in sql

    @pytest.mark.parametrize(
        "buffers,costs,timing,verbose",
        [
            pytest.param(True, True, True, True, id="all_options_enabled"),
            pytest.param(True, False, False, False, id="buffers_only"),
            pytest.param(False, True, False, False, id="costs_only"),
            pytest.param(False, False, True, False, id="timing_only"),
            pytest.param(False, False, False, True, id="verbose_only"),
            pytest.param(False, False, False, False, id="no_extended_options"),
        ]
    )
    def test_explain_with_extended_options(self, dummy_dialect: DummyDialect, buffers, costs, timing, verbose):
        """Tests EXPLAIN with extended options like BUFFERS, COSTS, TIMING, VERBOSE."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "perf_test")
        )

        # Create EXPLAIN options with extended settings
        options = ExplainOptions(
            buffers=buffers,
            costs=costs,
            timing=timing,
            verbose=verbose,
            analyze=timing  # Timing requires ANALYZE according to SQL standard
        )

        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=options
        )
        sql, params = explain_expr.to_sql()
        assert sql.startswith('EXPLAIN ')
        
        # Check that specified options appear in the SQL if enabled
        if buffers:
            assert "BUFFERS" in sql
        if not costs:
            assert "COSTS OFF" in sql or "COSTS" not in sql  # Either explicitly turned off or not mentioned
        if timing:
            assert "TIMING" in sql
        if verbose:
            assert "VERBOSE" in sql
        assert params == ()

    def test_explain_expression_initialization(self, dummy_dialect: DummyDialect):
        """Tests ExplainExpression initialization with various parameters."""
        from rhosocial.activerecord.backend.expression.statements import ExplainOptions

        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "users")
        )

        # Test initialization with no options (None)
        explain_expr_none = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=None
        )
        assert explain_expr_none.statement == query
        assert explain_expr_none.options is None

        # Test initialization with basic options
        basic_options = ExplainOptions()
        explain_expr_basic = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=basic_options
        )
        assert explain_expr_basic.statement == query
        assert explain_expr_basic.options == basic_options

        # Test initialization with specific options
        detailed_options = ExplainOptions(
            analyze=True,
            verbose=True,
            buffers=True,
            costs=False,
            format=ExplainFormat.JSON
        )
        explain_expr_detailed = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=detailed_options
        )
        assert explain_expr_detailed.statement == query
        assert explain_expr_detailed.options == detailed_options
        assert explain_expr_detailed.options.analyze is True
        assert explain_expr_detailed.options.verbose is True
        assert explain_expr_detailed.options.buffers is True
        assert explain_expr_detailed.options.costs is False
        assert explain_expr_detailed.options.format == ExplainFormat.JSON

    def test_explain_expression_to_sql_delegation(self, dummy_dialect: DummyDialect):
        """Tests that ExplainExpression.to_sql properly delegates to dialect."""
        from rhosocial.activerecord.backend.expression.statements import ExplainOptions

        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "products")
        )

        options = ExplainOptions(
            analyze=True,
            format=ExplainFormat.TEXT
        )

        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=options
        )

        # Check that to_sql properly delegates to dialect
        sql, params = explain_expr.to_sql()

        # Verify the SQL contains explain, analyze and format parts
        assert sql.startswith('EXPLAIN ANALYZE')
        assert 'FORMAT TEXT' in sql
        assert 'SELECT "name" FROM "products"' in sql
        assert params == ()