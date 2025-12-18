import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, TableExpression,
    DeleteExpression, ComparisonPredicate
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

class TestDeleteStatements:
    """Tests for DELETE statements with various WHERE conditions."""
    
    @pytest.mark.parametrize("table, where_condition, expected_sql, expected_params", [
        ("orders", ComparisonPredicate(None, "<", Column(None, "order_date"), Literal(None, "2023-01-01")),  # Mock
         'DELETE FROM "orders" WHERE "order_date" < ?', ("2023-01-01",)),
        
        ("users", ComparisonPredicate(None, "!=", Column(None, "status"), Literal(None, "active")),  # Mock
         'DELETE FROM "users" WHERE "status" != ?', ("active",)),
        
        ("products", ComparisonPredicate(None, "=", Column(None, "category_id"), Literal(None, 5)),  # Mock
         'DELETE FROM "products" WHERE "category_id" = ?', (5,)),
    ])
    def test_basic_delete(self, dummy_dialect: DummyDialect, table, where_condition, expected_sql, expected_params):
        """Tests basic DELETE statements with a WHERE condition."""
        # Properly initialize with actual dialect
        if "2023-01-01" in expected_params:
            where_condition = ComparisonPredicate(dummy_dialect, "<", Column(dummy_dialect, "order_date"), Literal(dummy_dialect, "2023-01-01"))
        elif "active" in expected_params:
            where_condition = ComparisonPredicate(dummy_dialect, "!=", Column(dummy_dialect, "status"), Literal(dummy_dialect, "active"))
        elif 5 in expected_params:
            where_condition = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "category_id"), Literal(dummy_dialect, 5))
        
        delete_expr = DeleteExpression(
            dummy_dialect,
            table=table,
            where=where_condition
        )
        sql, params = delete_expr.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    @pytest.mark.parametrize("comparison_op,right_value", [
        (">", 100),
        ("<=", 50),
        (">=", 200),
        ("!=", "deleted"),
        ("IS", None),
        ("IS NOT", None),
    ])
    def test_delete_with_various_operators(self, dummy_dialect: DummyDialect, comparison_op, right_value):
        """Tests DELETE with different comparison operators."""
        from rhosocial.activerecord.backend.expression import IsNullPredicate
        
        # Handle special case for IS/IS NOT NULL
        if comparison_op in ["IS", "IS NOT"]:
            column_expr = Column(dummy_dialect, "deleted_at")
            where_condition = IsNullPredicate(dummy_dialect, column_expr, is_not=(comparison_op == "IS NOT"))
        else:
            column_expr = Column(dummy_dialect, "value")
            value_expr = Literal(dummy_dialect, right_value)
            where_condition = ComparisonPredicate(dummy_dialect, comparison_op, column_expr, value_expr)
        
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="temp_records",
            where=where_condition
        )
        sql, params = delete_expr.to_sql()
        assert 'DELETE FROM "temp_records" WHERE' in sql
        if comparison_op in ["IS", "IS NOT"]:
            assert comparison_op.replace(" ", " ") in sql  # "IS NULL" or "IS NOT NULL"
        else:
            assert comparison_op in sql
        if comparison_op not in ["IS", "IS NOT"]:
            assert params == (right_value,)

    def test_delete_with_complex_where(self, dummy_dialect: DummyDialect):
        """Tests DELETE statement with a complex WHERE condition."""
        from rhosocial.activerecord.backend.expression import (
            LogicalPredicate, InPredicate
        )
        condition1 = ComparisonPredicate(
            dummy_dialect, 
            "=", 
            Column(dummy_dialect, "status"), 
            Literal(dummy_dialect, "cancelled")
        )
        condition2 = InPredicate(
            dummy_dialect, 
            Column(dummy_dialect, "user_id"), 
            Literal(dummy_dialect, [101, 102, 103])
        )
        complex_condition = LogicalPredicate(dummy_dialect, "AND", condition1, condition2)
        
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="temp_records",
            where=complex_condition
        )
        sql, params = delete_expr.to_sql()
        assert sql == 'DELETE FROM "temp_records" WHERE "status" = ? AND "user_id" IN (?, ?, ?)'
        assert params == ("cancelled", 101, 102, 103)

    @pytest.mark.parametrize("values_list", [
        [101, 102, 103],
        ["user1", "user2"],
        [1, 2, 3, 4, 5],
        [],  # Empty list case
    ])
    def test_delete_with_in_condition(self, dummy_dialect: DummyDialect, values_list):
        """Tests DELETE with IN condition for different value lists."""
        from rhosocial.activerecord.backend.expression import InPredicate
        
        in_condition = InPredicate(
            dummy_dialect,
            Column(dummy_dialect, "user_id"),
            Literal(dummy_dialect, values_list)
        )
        
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="records",
            where=in_condition
        )
        sql, params = delete_expr.to_sql()
        if not values_list:  # Empty list case
            assert 'IN ()' in sql
        else:
            assert 'IN (' in sql
            expected_placeholders = len(values_list)
            actual_placeholders = sql.count('?')
            # Account for any additional parameters in the SQL
            assert len(params) >= expected_placeholders
            assert list(params[:len(values_list)]) == values_list

    def test_delete_with_range_condition(self, dummy_dialect: DummyDialect):
        """Tests DELETE with BETWEEN range condition."""
        from rhosocial.activerecord.backend.expression import BetweenPredicate, Literal
        
        # Use BETWEEN condition
        between_condition = BetweenPredicate(
            dummy_dialect,
            Column(dummy_dialect, "date_created"),
            Literal(dummy_dialect, "2023-01-01"),
            Literal(dummy_dialect, "2023-12-31")
        )
        
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="old_logs",
            where=between_condition
        )
        sql, params = delete_expr.to_sql()
        assert 'DELETE FROM "old_logs" WHERE "date_created" BETWEEN ? AND ?' == sql
        assert params == ("2023-01-01", "2023-12-31")

    @pytest.mark.parametrize("table_name, column_name, pattern", [
        ("users", "email", "%@example.com"),
        ("products", "name", "Discontinued%"),
        ("orders", "tracking_number", "OLD%"), 
    ])
    def test_delete_with_like_condition(self, dummy_dialect: DummyDialect, table_name, column_name, pattern):
        """Tests DELETE with LIKE condition."""
        from rhosocial.activerecord.backend.expression import LikePredicate
        
        like_condition = LikePredicate(
            dummy_dialect,
            "LIKE",
            Column(dummy_dialect, column_name),
            Literal(dummy_dialect, pattern)
        )
        
        delete_expr = DeleteExpression(
            dummy_dialect,
            table=table_name,
            where=like_condition
        )
        sql, params = delete_expr.to_sql()
        assert f'DELETE FROM "{table_name}" WHERE "{column_name}" LIKE ?' == sql
        assert params == (pattern,)

    def test_multiple_conditional_deletes_combined(self, dummy_dialect: DummyDialect):
        """Tests combining multiple conditional predicates using AND/OR."""
        from rhosocial.activerecord.backend.expression import LogicalPredicate
        
        # Create multiple conditions
        condition1 = ComparisonPredicate(dummy_dialect, ">", Column(dummy_dialect, "age"), Literal(dummy_dialect, 65))
        condition2 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "status"), Literal(dummy_dialect, "retired"))
        condition3 = ComparisonPredicate(dummy_dialect, "<", Column(dummy_dialect, "last_login"), Literal(dummy_dialect, "2023-01-01"))
        
        # Combine conditions: (age > 65 AND status = 'retired') OR last_login < '2023-01-01'
        and_condition = LogicalPredicate(dummy_dialect, "AND", condition1, condition2)
        final_condition = LogicalPredicate(dummy_dialect, "OR", and_condition, condition3)
        
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="users",
            where=final_condition
        )
        sql, params = delete_expr.to_sql()
        # Verify the structure contains the expected elements
        assert 'DELETE FROM "users" WHERE' in sql
        assert "OR" in sql  # Should have OR connecting the conditions
        assert params == (65, "retired", "2023-01-01")