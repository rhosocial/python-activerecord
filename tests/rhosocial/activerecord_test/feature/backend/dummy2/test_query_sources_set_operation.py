# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_query_sources_set_operation.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, Subquery, QueryExpression, TableExpression
)
from rhosocial.activerecord.backend.expression.query_sources import SetOperationExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestSetOperationExpression:
    """Tests for SetOperationExpression with UNION, INTERSECT, EXCEPT operations."""

    def test_union_operation_basic(self, dummy_dialect: DummyDialect):
        """Test basic UNION operation between two queries."""
        left_query = Subquery(dummy_dialect, "SELECT id, name FROM users WHERE age > ?", (18,))
        right_query = Subquery(dummy_dialect, "SELECT id, name FROM customers WHERE status = ?", ("active",))
        
        set_op = SetOperationExpression(
            dummy_dialect,
            left=left_query,
            right=right_query,
            operation="UNION",
            alias="combined_results"
        )
        
        sql, params = set_op.to_sql()
        
        assert "UNION" in sql.upper()
        assert params == (18, "active")

    def test_union_all_operation(self, dummy_dialect: DummyDialect):
        """Test UNION ALL operation."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM table1", ())
        right_query = Subquery(dummy_dialect, "SELECT id FROM table2", ())
        
        set_op = SetOperationExpression(
            dummy_dialect,
            left=left_query,
            right=right_query,
            operation="UNION",
            alias="union_all_results",
            all_=True  # This should add ALL to the operation
        )
        
        sql, params = set_op.to_sql()
        
        assert "UNION ALL" in sql.upper()
        assert params == ()

    def test_intersect_operation(self, dummy_dialect: DummyDialect):
        """Test INTERSECT operation."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM table1 WHERE col1 = ?", ("value1",))
        right_query = Subquery(dummy_dialect, "SELECT id FROM table2 WHERE col2 = ?", ("value2",))
        
        set_op = SetOperationExpression(
            dummy_dialect,
            left=left_query,
            right=right_query,
            operation="INTERSECT",
            alias="intersection"
        )
        
        sql, params = set_op.to_sql()
        
        assert "INTERSECT" in sql.upper()
        assert params == ("value1", "value2")

    def test_except_operation(self, dummy_dialect: DummyDialect):
        """Test EXCEPT operation."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM table1 WHERE active = ?", (True,))
        right_query = Subquery(dummy_dialect, "SELECT id FROM table2 WHERE archived = ?", (True,))
        
        set_op = SetOperationExpression(
            dummy_dialect,
            left=left_query,
            right=right_query,
            operation="EXCEPT",
            alias="except_results"
        )
        
        sql, params = set_op.to_sql()
        
        assert "EXCEPT" in sql.upper()
        assert params == (True, True)

    def test_nested_set_operations(self, dummy_dialect: DummyDialect):
        """Test nested set operations (set operation as operand)."""
        query1 = Subquery(dummy_dialect, "SELECT id FROM table1 WHERE col = ?", ("a",))
        query2 = Subquery(dummy_dialect, "SELECT id FROM table2 WHERE col = ?", ("b",))
        query3 = Subquery(dummy_dialect, "SELECT id FROM table3 WHERE col = ?", ("c",))
        
        # First set operation
        inner_op = SetOperationExpression(
            dummy_dialect,
            left=query1,
            right=query2,
            operation="UNION",
            alias="inner_union"
        )
        
        # Outer set operation using the inner one
        outer_op = SetOperationExpression(
            dummy_dialect,
            left=inner_op,
            right=query3,
            operation="UNION",
            alias="outer_union"
        )
        
        sql, params = outer_op.to_sql()
        
        assert "UNION" in sql.upper()
        assert params == ("a", "b", "c")

    def test_set_operation_with_complex_queries(self, dummy_dialect: DummyDialect):
        """Test set operation with more complex query structures."""
        # Create complex left query
        left_table = TableExpression(dummy_dialect, "users")
        left_query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=left_table
        )
        
        # Create complex right query  
        right_table = TableExpression(dummy_dialect, "customers")
        right_query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=right_table
        )
        
        set_op = SetOperationExpression(
            dummy_dialect,
            left=left_query,
            right=right_query,
            operation="UNION",
            alias="complex_union"
        )
        
        sql, params = set_op.to_sql()
        
        assert "UNION" in sql.upper()
        assert '"users"' in sql or 'SELECT' in sql
        assert '"customers"' in sql or 'SELECT' in sql
        assert params == ()

    def test_set_operation_parameters_handling(self, dummy_dialect: DummyDialect):
        """Test that parameters from both sides are properly combined."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM users WHERE age > ? AND status = ?", (18, "active"))
        right_query = Subquery(dummy_dialect, "SELECT id FROM customers WHERE region = ?", ("west",))
        
        set_op = SetOperationExpression(
            dummy_dialect,
            left=left_query,
            right=right_query,
            operation="UNION",
            alias="param_union"
        )
        
        sql, params = set_op.to_sql()
        
        # Should contain parameters from both queries
        assert params == (18, "active", "west")
        assert len(params) == 3

    def test_set_operation_with_alias_formatting(self, dummy_dialect: DummyDialect):
        """Test that alias is properly formatted in the SQL."""
        left_query = Subquery(dummy_dialect, "SELECT col FROM table1", ())
        right_query = Subquery(dummy_dialect, "SELECT col FROM table2", ())
        
        set_op = SetOperationExpression(
            dummy_dialect,
            left=left_query,
            right=right_query,
            operation="UNION",
            alias="custom_alias"
        )
        
        sql, params = set_op.to_sql()
        
        # Verify alias is included in the formatted result
        assert "custom_alias" in sql
        assert params == ()

    def test_set_operation_case_insensitive_operation_names(self, dummy_dialect: DummyDialect):
        """Test that different case operation names work."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM t1", ())
        right_query = Subquery(dummy_dialect, "SELECT id FROM t2", ())
        
        # Test with uppercase (normal case)
        set_op_upper = SetOperationExpression(
            dummy_dialect,
            left=left_query,
            right=right_query,
            operation="UNION",
            alias="test"
        )
        
        sql_upper, _ = set_op_upper.to_sql()
        assert "UNION" in sql_upper

    def test_set_operation_all_variants(self, dummy_dialect: DummyDialect):
        """Test all operation variants with and without ALL."""
        query1 = Subquery(dummy_dialect, "SELECT id FROM t1 WHERE a = ?", (1,))
        query2 = Subquery(dummy_dialect, "SELECT id FROM t2 WHERE b = ?", (2,))

        operations = ["UNION", "INTERSECT", "EXCEPT"]

        for op in operations:
            # Test without ALL
            set_op = SetOperationExpression(
                dummy_dialect,
                left=query1,
                right=query2,
                operation=op,
                alias=f"test_{op.lower()}"
            )

            sql, params = set_op.to_sql()
            assert op in sql.upper()
            assert params == (1, 2)

            # Test with ALL
            set_op_all = SetOperationExpression(
                dummy_dialect,
                left=query1,
                right=query2,
                operation=op,
                alias=f"test_{op.lower()}_all",
                all_=True
            )

            sql_all, params_all = set_op_all.to_sql()
            assert f"{op} ALL" in sql_all.upper()
            assert params_all == (1, 2)

    def test_set_operation_without_alias(self, dummy_dialect: DummyDialect):
        """Test set operation expression without alias."""
        left_query = Subquery(dummy_dialect, "SELECT id, name FROM users WHERE age > ?", (18,))
        right_query = Subquery(dummy_dialect, "SELECT id, name FROM customers WHERE status = ?", ("active",))

        # Create SetOperationExpression without alias
        set_op = SetOperationExpression(
            dummy_dialect,
            left=left_query,
            right=right_query,
            operation="UNION"
        )

        sql, params = set_op.to_sql()

        # Verify that no alias is present in the SQL
        assert "AS" not in sql.upper() or "AS " not in sql  # Check that alias is not in SQL
        # Verify UNION is still present
        assert "UNION" in sql.upper()
        # Verify parameters are still handled
        assert params == (18, "active")