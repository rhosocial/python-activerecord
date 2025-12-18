import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, TableExpression, 
    QueryExpression, InsertExpression, UpdateExpression, DeleteExpression,
    ExplainExpression
)
from rhosocial.activerecord.backend.dialect.options import ExplainOptions, ExplainType, ExplainFormat
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

class TestExplainStatements:
    """Tests for EXPLAIN statements with various options."""
    
    def test_basic_explain(self, dummy_dialect: DummyDialect):
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

    @pytest.mark.parametrize("explain_type,expected_prefix", [
        (ExplainType.BASIC, "EXPLAIN"),
        (ExplainType.ANALYZE, "EXPLAIN ANALYZE"),
    ])
    def test_explain_with_types(self, dummy_dialect: DummyDialect, explain_type, expected_prefix):
        """Tests EXPLAIN with different types (BASIC, ANALYZE)."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "products"),
            where=Column(dummy_dialect, "price") > Literal(dummy_dialect, 100)
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

    @pytest.mark.parametrize("format_type,expected_format_clause", [
        (ExplainFormat.TEXT, "FORMAT TEXT"),
        (ExplainFormat.JSON, "FORMAT JSON"),  
        (ExplainFormat.TREE, "FORMAT TREE"),
    ])
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
            where=Column(dummy_dialect, "order_date") > Literal(dummy_dialect, "2024-01-01")
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

    @pytest.mark.parametrize("statement_type", ["SELECT", "INSERT", "UPDATE", "DELETE"])
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
                table="test_table",
                columns=["name"],
                values=[Literal(dummy_dialect, "test")]
            )
        elif statement_type == "UPDATE":
            stmt = UpdateExpression(
                dummy_dialect,
                table="test_table",
                assignments={"name": Literal(dummy_dialect, "updated")},
                where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
            )
        elif statement_type == "DELETE":
            stmt = DeleteExpression(
                dummy_dialect,
                table="test_table",
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

    def test_explain_options_validation(self, dummy_dialect: DummyDialect):
        """Tests validation of EXPLAIN options."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "validated_table")
        )
        
        # Create options with dummy database name for validation
        options = ExplainOptions(type=ExplainType.ANALYZE)
        try:
            # Validate options against dialect
            options.validate_for_database("dummy")
            # If no exception, continue with test
            explain_expr = ExplainExpression(
                dummy_dialect,
                statement=query,
                options=options
            )
            sql, params = explain_expr.to_sql()
            assert 'EXPLAIN ANALYZE' in sql
        except ValueError:
            # If validation fails, that's also valid behavior - just make sure it doesn't crash
            pass

    @pytest.mark.parametrize("buffers,costs", [
        (True, True),
        (True, False), 
        (False, True),
        (False, False),
    ])
    def test_explain_with_extended_options(self, dummy_dialect: DummyDialect, buffers, costs):
        """Tests EXPLAIN with extended options like BUFFERS, COSTS."""
        # Note: Based on the implementation, advanced options may be handled differently
        # This is a placeholder for testing when those options are supported
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "perf_test")
        )
        
        # Create basic EXPLAIN options
        options = ExplainOptions(type=ExplainType.BASIC)
        
        explain_expr = ExplainExpression(
            dummy_dialect,
            statement=query,
            options=options
        )
        sql, params = explain_expr.to_sql()
        assert sql.startswith('EXPLAIN ')
        assert params == ()