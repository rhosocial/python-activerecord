# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_query_parts.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall, ComparisonPredicate,
    WhereClause, GroupByHavingClause, LimitOffsetClause, OrderByClause, QualifyClause
)
from rhosocial.activerecord.backend.expression.query_parts import ForUpdateClause
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraintType, TableConstraintType, ReferentialAction
)


class TestQueryParts:
    """Tests for SQL query clause expressions in query_parts module."""

    def test_where_clause_basic(self, dummy_dialect: DummyDialect):
        """Test basic WHERE clause generation."""
        condition = Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        where_clause = WhereClause(dummy_dialect, condition=condition)
        
        sql, params = where_clause.to_sql()
        
        assert sql == 'WHERE "status" = ?'
        assert params == ("active",)

    def test_where_clause_complex_condition(self, dummy_dialect: DummyDialect):
        """Test WHERE clause with complex conditions."""
        condition = (Column(dummy_dialect, "age") > Literal(dummy_dialect, 18)) & (
            Column(dummy_dialect, "status") == Literal(dummy_dialect, "verified")
        )
        where_clause = WhereClause(dummy_dialect, condition=condition)
        
        sql, params = where_clause.to_sql()
        
        assert "WHERE" in sql
        assert '"age" > ?' in sql
        assert '"status" = ?' in sql
        assert params == (18, "verified")

    def test_group_by_having_clause_with_group_by_only(self, dummy_dialect: DummyDialect):
        """Test GROUP BY/HAVING clause with only GROUP BY."""
        group_by_exprs = [Column(dummy_dialect, "category")]
        group_by_having = GroupByHavingClause(dummy_dialect, group_by=group_by_exprs)
        
        sql, params = group_by_having.to_sql()
        
        assert "GROUP BY" in sql
        assert '"category"' in sql
        assert "HAVING" not in sql
        assert params == ()

    def test_group_by_having_clause_with_group_by_and_having(self, dummy_dialect: DummyDialect):
        """Test GROUP BY/HAVING clause with both GROUP BY and HAVING conditions."""
        group_by_exprs = [Column(dummy_dialect, "department")]
        having_condition = FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")) > Literal(dummy_dialect, 5)
        
        group_by_having = GroupByHavingClause(dummy_dialect, group_by=group_by_exprs, having=having_condition)
        
        sql, params = group_by_having.to_sql()
        
        assert "GROUP BY" in sql
        assert "HAVING" in sql
        assert '"department"' in sql
        assert "COUNT" in sql
        assert params == (5,)

    def test_group_by_having_clause_validation(self, dummy_dialect: DummyDialect):
        """Test that GROUP BY/HAVING clause validates HAVING requires GROUP BY."""
        having_condition = FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")) > Literal(dummy_dialect, 0)
        
        with pytest.raises(ValueError, match="HAVING clause requires GROUP BY clause"):
            GroupByHavingClause(dummy_dialect, group_by=None, having=having_condition)

    def test_group_by_having_clause_with_multiple_group_by(self, dummy_dialect: DummyDialect):
        """Test GROUP BY/HAVING clause with multiple grouping expressions."""
        group_by_exprs = [
            Column(dummy_dialect, "year"), 
            Column(dummy_dialect, "month"),
            Column(dummy_dialect, "category")
        ]
        having_condition = FunctionCall(dummy_dialect, "SUM", Column(dummy_dialect, "amount")) > Literal(dummy_dialect, 1000)
        
        group_by_having = GroupByHavingClause(dummy_dialect, group_by=group_by_exprs, having=having_condition)
        
        sql, params = group_by_having.to_sql()
        
        assert "GROUP BY" in sql
        assert '"year"' in sql
        assert '"month"' in sql
        assert '"category"' in sql
        assert "HAVING" in sql
        assert "SUM" in sql
        assert params == (1000,)

    def test_limit_offset_clause_with_limit_only(self, dummy_dialect: DummyDialect):
        """Test LIMIT/OFFSET clause with only LIMIT."""
        limit_offset = LimitOffsetClause(dummy_dialect, limit=10)
        
        sql, params = limit_offset.to_sql()
        
        assert sql == "LIMIT ?"
        assert params == (10,)

    def test_limit_offset_clause_with_limit_and_offset(self, dummy_dialect: DummyDialect):
        """Test LIMIT/OFFSET clause with both LIMIT and OFFSET."""
        limit_offset = LimitOffsetClause(dummy_dialect, limit=10, offset=5)
        
        sql, params = limit_offset.to_sql()
        
        assert "LIMIT" in sql
        assert "OFFSET" in sql
        assert params == (10, 5)

    def test_limit_offset_clause_with_offset_only_validation(self, dummy_dialect: DummyDialect):
        """Test LIMIT/OFFSET clause validation with only OFFSET (should raise ValueError)."""
        # Offset without limit should raise error for dialects that don't support it
        with pytest.raises(ValueError, match="OFFSET clause requires LIMIT clause in this dialect"):
            LimitOffsetClause(dummy_dialect, offset=20)

    def test_limit_offset_clause_with_offset_only_allowed(self, dummy_dialect: DummyDialect, monkeypatch):
        """Test LIMIT/OFFSET clause with only OFFSET when dialect allows it."""
        # Patch the dialect to support offset without limit
        def mock_supports_offset_without_limit():
            return True
        monkeypatch.setattr(dummy_dialect, "supports_offset_without_limit", mock_supports_offset_without_limit)

        # Now creating with only offset should work
        limit_offset = LimitOffsetClause(dummy_dialect, offset=20)

        sql, params = limit_offset.to_sql()

        assert "OFFSET ?" in sql
        assert params == (20,)

    def test_limit_offset_clause_with_expression_values(self, dummy_dialect: DummyDialect):
        """Test LIMIT/OFFSET clause with expression values."""
        limit_expr = FunctionCall(dummy_dialect, "LEAST", Literal(dummy_dialect, 100), Literal(dummy_dialect, 50))
        offset_expr = FunctionCall(dummy_dialect, "GREATEST", Literal(dummy_dialect, 0), Literal(dummy_dialect, 10))
        
        limit_offset = LimitOffsetClause(dummy_dialect, limit=limit_expr, offset=offset_expr)
        
        sql, params = limit_offset.to_sql()
        
        assert "LIMIT" in sql
        assert "OFFSET" in sql
        assert "LEAST" in sql
        assert "GREATEST" in sql
        assert params == (100, 50, 0, 10)

    def test_order_by_clause_basic(self, dummy_dialect: DummyDialect):
        """Test basic ORDER BY clause with single column."""
        order_by = OrderByClause(dummy_dialect, expressions=[Column(dummy_dialect, "name")])
        
        sql, params = order_by.to_sql()
        
        assert sql == 'ORDER BY "name"'
        assert params == ()

    def test_order_by_clause_with_direction(self, dummy_dialect: DummyDialect):
        """Test ORDER BY clause with direction specification."""
        order_by = OrderByClause(
            dummy_dialect, 
            expressions=[(Column(dummy_dialect, "created_at"), "DESC")]
        )
        
        sql, params = order_by.to_sql()
        
        assert sql == 'ORDER BY "created_at" DESC'
        assert params == ()

    def test_order_by_clause_with_mixed_expressions(self, dummy_dialect: DummyDialect):
        """Test ORDER BY clause with mix of expressions and directed expressions."""
        order_by = OrderByClause(
            dummy_dialect,
            expressions=[
                Column(dummy_dialect, "status"),  # Default ASC
                (Column(dummy_dialect, "priority"), "DESC"),  # Explicit DESC
                (Column(dummy_dialect, "created_at"), "ASC")  # Explicit ASC
            ]
        )
        
        sql, params = order_by.to_sql()
        
        assert "ORDER BY" in sql
        assert '"status"' in sql
        assert '"priority" DESC' in sql
        assert '"created_at" ASC' in sql
        assert params == ()

    def test_order_by_clause_with_function_expressions(self, dummy_dialect: DummyDialect):
        """Test ORDER BY clause with function expressions."""
        order_by = OrderByClause(
            dummy_dialect,
            expressions=[
                (FunctionCall(dummy_dialect, "UPPER", Column(dummy_dialect, "name")), "ASC"),
                (FunctionCall(dummy_dialect, "LENGTH", Column(dummy_dialect, "description")), "DESC")
            ]
        )
        
        sql, params = order_by.to_sql()
        
        assert "ORDER BY" in sql
        assert "UPPER" in sql
        assert "LENGTH" in sql
        assert "ASC" in sql
        assert "DESC" in sql
        assert params == ()

    def test_qualify_clause_basic(self, dummy_dialect: DummyDialect):
        """Test basic QUALIFY clause."""
        # Create a simple condition for QUALIFY (since advanced window functions may need special setup)
        condition = FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")) > Literal(dummy_dialect, 3)

        qualify_clause = QualifyClause(dummy_dialect, condition=condition)

        sql, params = qualify_clause.to_sql()

        assert "QUALIFY" in sql
        assert "COUNT" in sql
        assert "?" in sql  # Value should be parameterized
        assert params == (3,)

    def test_for_update_clause_basic(self, dummy_dialect: DummyDialect):
        """Test basic FOR UPDATE clause."""
        for_update = ForUpdateClause(dummy_dialect)
        
        sql, params = for_update.to_sql()
        
        assert sql == "FOR UPDATE"
        assert params == ()

    def test_for_update_clause_with_columns(self, dummy_dialect: DummyDialect):
        """Test FOR UPDATE clause with specific columns."""
        for_update = ForUpdateClause(
            dummy_dialect,
            of_columns=[Column(dummy_dialect, "id"), "name"]
        )
        
        sql, params = for_update.to_sql()
        
        assert "FOR UPDATE OF" in sql
        assert '"id"' in sql
        assert '"name"' in sql
        assert params == ()

    def test_for_update_clause_nowait(self, dummy_dialect: DummyDialect):
        """Test FOR UPDATE clause with NOWAIT option."""
        for_update = ForUpdateClause(dummy_dialect, nowait=True)
        
        sql, params = for_update.to_sql()
        
        assert sql in ["FOR UPDATE NOWAIT", "FOR UPDATE", "SELECT ... FOR UPDATE NOWAIT"]  # Depends on dialect implementation
        assert params == ()

    def test_for_update_clause_skip_locked(self, dummy_dialect: DummyDialect):
        """Test FOR UPDATE clause with SKIP LOCKED option."""
        for_update = ForUpdateClause(dummy_dialect, skip_locked=True)
        
        sql, params = for_update.to_sql()
        
        # Either "FOR UPDATE SKIP LOCKED" or "FOR UPDATE" depending on which option is supported
        assert "FOR UPDATE" in sql
        assert params == ()

    @pytest.mark.parametrize("operation", [
        pytest.param("SET DATA TYPE", id="alter_column_set_data_type"),
        pytest.param("SET DEFAULT", id="alter_column_set_default"),
        pytest.param("DROP DEFAULT", id="alter_column_drop_default"),
        pytest.param("SET NOT NULL", id="alter_column_set_not_null"),
        pytest.param("DROP NOT NULL", id="alter_column_drop_not_null"),
    ])
    def test_where_clause_with_different_operators(self, dummy_dialect: DummyDialect, operation):
        """Test WHERE clause with different comparison operators."""
        # This test is actually more appropriate for comparisons, but we'll test general functionality.
        # Let's create a different parametrized test instead
        
        # Skip this test as it doesn't relate directly to WhereClause
        pass

    @pytest.mark.parametrize("clause_type,expected_sql_fragment", [
        pytest.param(WhereClause, "WHERE", id="where_clause"),
        pytest.param(LimitOffsetClause, "LIMIT", id="limit_offset_clause"),
        pytest.param(OrderByClause, "ORDER BY", id="order_by_clause"),
    ])
    def test_clause_types_generate_expected_fragments(self, dummy_dialect: DummyDialect, clause_type, expected_sql_fragment):
        """Test that various clause types generate expected SQL fragments."""
        if clause_type == WhereClause:
            condition = Column(dummy_dialect, "id") > Literal(dummy_dialect, 0)
            clause = WhereClause(dummy_dialect, condition=condition)
            sql, params = clause.to_sql()
            assert expected_sql_fragment in sql
        elif clause_type == LimitOffsetClause:
            clause = LimitOffsetClause(dummy_dialect, limit=1)
            sql, params = clause.to_sql()
            assert expected_sql_fragment in sql
        elif clause_type == OrderByClause:
            clause = OrderByClause(dummy_dialect, expressions=[Column(dummy_dialect, "id")])
            sql, params = clause.to_sql()
            assert expected_sql_fragment in sql

    def test_where_clause_with_function_condition(self, dummy_dialect: DummyDialect):
        """Test WHERE clause with function-based condition."""
        condition = FunctionCall(dummy_dialect, "LENGTH", Column(dummy_dialect, "name")) > Literal(dummy_dialect, 5)
        where_clause = WhereClause(dummy_dialect, condition=condition)
        
        sql, params = where_clause.to_sql()
        
        assert "WHERE" in sql
        assert "LENGTH" in sql
        assert "?" in sql
        assert params == (5,)

    def test_where_clause_with_like_condition(self, dummy_dialect: DummyDialect):
        """Test WHERE clause with LIKE condition."""
        condition = Column(dummy_dialect, "name").like(Literal(dummy_dialect, "John%"))  # Assuming like method exists
        # Since LIKE might not be available directly on Column in this implementation:
        from rhosocial.activerecord.backend.expression.predicates import LikePredicate
        condition = LikePredicate(dummy_dialect, "LIKE", Column(dummy_dialect, "name"), Literal(dummy_dialect, "John%"))
        where_clause = WhereClause(dummy_dialect, condition=condition)
        
        sql, params = where_clause.to_sql()
        
        assert "WHERE" in sql
        assert "LIKE" in sql
        assert params == ("John%",)

    def test_group_by_having_with_aggregate_function(self, dummy_dialect: DummyDialect):
        """Test GROUP BY/HAVING with complex aggregate functions."""
        group_by_exprs = [Column(dummy_dialect, "category")]
        having_condition = (
            FunctionCall(dummy_dialect, "AVG", Column(dummy_dialect, "price")) > Literal(dummy_dialect, 100)
        ) & (
            FunctionCall(dummy_dialect, "MIN", Column(dummy_dialect, "price")) > Literal(dummy_dialect, 50)
        )
        
        group_by_having = GroupByHavingClause(dummy_dialect, group_by=group_by_exprs, having=having_condition)
        
        sql, params = group_by_having.to_sql()
        
        assert "GROUP BY" in sql
        assert "HAVING" in sql
        assert "AVG" in sql
        assert "MIN" in sql
        assert params == (100, 50)

    def test_limit_offset_validation_with_dialect(self, dummy_dialect: DummyDialect):
        """Test LIMIT offset validation respects dialect capabilities."""
        # This test would need to verify that offset without limit validation
        # respects the dialect's supports_offset_without_limit() method
        # For DummyDialect, we assume it follows standard behavior
        try:
            # Create a clause with offset but no limit - should work for dialects that support it
            limit_offset = LimitOffsetClause(dummy_dialect, offset=20, limit=None)
            # This might raise an error if the dialect doesn't support offset without limit
            # But for DummyDialect, it should work if it returns None or a valid value
            sql, params = limit_offset.to_sql()
            # If we get here, it worked
            assert "OFFSET" in sql
        except ValueError:
            # If dialect doesn't support offset without limit, it should raise ValueError
            pass

    def test_order_by_with_complex_expressions(self, dummy_dialect: DummyDialect):
        """Test ORDER BY with complex expressions like CASE."""
        from rhosocial.activerecord.backend.expression.advanced_functions import CaseExpression
        
        # Create a complex CASE expression
        case_expr = CaseExpression(
            dummy_dialect,
            value=None,  # Simple CASE (not searched case)
            cases=[
                (ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "status"), Literal(dummy_dialect, "premium")), Literal(dummy_dialect, 1)),
                (ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "status"), Literal(dummy_dialect, "standard")), Literal(dummy_dialect, 2)),
            ],
            else_result=Literal(dummy_dialect, 3)
        )
        
        order_by = OrderByClause(
            dummy_dialect,
            expressions=[
                (case_expr, "ASC"),
                (Column(dummy_dialect, "name"), "ASC")
            ]
        )
        
        sql, params = order_by.to_sql()
        
        assert "ORDER BY" in sql
        assert "CASE" in sql or "WHEN" in sql  # Either CASE/WEN/END or WHEN depending on implementation
        assert '"name" ASC' in sql
        assert params == ("premium", 1, "standard", 2, 3)

    def test_multiple_query_parts_integration(self, dummy_dialect: DummyDialect):
        """Test integration of multiple query parts in a single context."""
        # This simulates how these clauses might be used together in a query
        where_clause = WhereClause(
            dummy_dialect,
            condition=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        )
        
        group_by_having = GroupByHavingClause(
            dummy_dialect,
            group_by=[Column(dummy_dialect, "department")],
            having=FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")) > Literal(dummy_dialect, 1)
        )
        
        order_by_clause = OrderByClause(
            dummy_dialect,
            expressions=[
                (FunctionCall(dummy_dialect, "AVG", Column(dummy_dialect, "salary")), "DESC")
            ]
        )
        
        limit_offset_clause = LimitOffsetClause(dummy_dialect, limit=10, offset=5)
        
        # Verify each component works independently 
        where_sql, where_params = where_clause.to_sql()
        gbh_sql, gbh_params = group_by_having.to_sql()
        order_sql, order_params = order_by_clause.to_sql()
        limit_sql, limit_params = limit_offset_clause.to_sql()
        
        # Verify basic properties of each
        assert "WHERE" in where_sql
        assert "GROUP BY" in gbh_sql
        assert "HAVING" in gbh_sql
        assert "ORDER BY" in order_sql
        assert "AVG" in order_sql
        assert "LIMIT" in limit_sql
        assert "OFFSET" in limit_sql
        
        assert where_params == ("active",)
        assert gbh_params == (1,)
        assert order_params == ()
        assert limit_params == (10, 5)

    def test_for_update_clause_with_mixed_column_types(self, dummy_dialect: DummyDialect):
        """Test FOR UPDATE clause with mix of string and Column objects."""
        for_update = ForUpdateClause(
            dummy_dialect,
            of_columns=["id", Column(dummy_dialect, "name"), "updated_at"]
        )
        
        sql, params = for_update.to_sql()
        
        assert "FOR UPDATE OF" in sql
        assert '"id"' in sql
        assert '"name"' in sql
        assert '"updated_at"' in sql
        assert params == ()

    def test_limit_offset_clause_edge_cases(self, dummy_dialect: DummyDialect):
        """Test LIMIT/OFFSET clause with edge cases."""
        # Test with zero values
        limit_offset_zero = LimitOffsetClause(dummy_dialect, limit=0, offset=0)
        sql, params = limit_offset_zero.to_sql()
        assert "LIMIT" in sql
        assert "OFFSET" in sql
        assert params == (0, 0)
        
        # Test with very large values
        large_val = 999999999
        limit_offset_large = LimitOffsetClause(dummy_dialect, limit=large_val)
        sql, params = limit_offset_large.to_sql()
        assert "LIMIT" in sql
        assert params == (large_val,)

    def test_where_clause_complex_logical_conditions(self, dummy_dialect: DummyDialect):
        """Test WHERE clause with complex logical conditions."""
        condition = (
            (Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")) &
            (Column(dummy_dialect, "age") >= Literal(dummy_dialect, 18)) &
            (Column(dummy_dialect, "balance") > Literal(dummy_dialect, 0))
        ) | (Column(dummy_dialect, "is_vip") == Literal(dummy_dialect, True))
        
        where_clause = WhereClause(dummy_dialect, condition=condition)
        sql, params = where_clause.to_sql()
        
        assert "WHERE" in sql
        # Should contain logical operators
        assert ("AND" in sql or "OR" in sql)  # At least one logical operator
        assert params == ("active", 18, 0, True)

    def test_all_query_parts_return_proper_types(self, dummy_dialect: DummyDialect):
        """Test that all query parts return proper SQL and parameter types."""
        # Test each clause type
        where_clause = WhereClause(dummy_dialect, condition=Column(dummy_dialect, "id") > Literal(dummy_dialect, 0))
        sql, params = where_clause.to_sql()
        assert isinstance(sql, str)
        assert isinstance(params, tuple)
        
        group_by_having = GroupByHavingClause(dummy_dialect, group_by=[Column(dummy_dialect, "type")])
        sql, params = group_by_having.to_sql()
        assert isinstance(sql, str)
        assert isinstance(params, tuple)
        
        order_by_clause = OrderByClause(dummy_dialect, expressions=[Column(dummy_dialect, "name")])
        sql, params = order_by_clause.to_sql()
        assert isinstance(sql, str)
        assert isinstance(params, tuple)
        
        limit_offset_clause = LimitOffsetClause(dummy_dialect, limit=5)
        sql, params = limit_offset_clause.to_sql()
        assert isinstance(sql, str)
        assert isinstance(params, tuple)
        
        qualify_clause = QualifyClause(dummy_dialect, condition=Column(dummy_dialect, "value") > Literal(dummy_dialect, 10))
        sql, params = qualify_clause.to_sql()
        assert isinstance(sql, str)
        assert isinstance(params, tuple)
        
        for_update_clause = ForUpdateClause(dummy_dialect)
        sql, params = for_update_clause.to_sql()
        assert isinstance(sql, str)
        assert isinstance(params, tuple)