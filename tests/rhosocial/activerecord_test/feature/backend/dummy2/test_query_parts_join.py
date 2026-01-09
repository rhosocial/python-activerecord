# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_query_parts_join.py
"""
Tests for JoinExpression and its chaining capabilities for multiple joins.
"""
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, TableExpression, ComparisonPredicate, QueryExpression, FunctionCall
)
from rhosocial.activerecord.backend.expression.query_parts import JoinExpression, JoinType, GroupByHavingClause
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestJoinExpressionChaining:
    """Tests for JoinExpression chaining and multiple join capabilities."""

    def test_basic_join_expression_creation(self, dummy_dialect: DummyDialect):
        """Test basic JoinExpression creation."""
        left_table = TableExpression(dummy_dialect, "users", alias="u")
        right_table = TableExpression(dummy_dialect, "orders", alias="o")
        
        join_expr = JoinExpression(
            dummy_dialect,
            left_table=left_table,
            right_table=right_table,
            join_type="INNER JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id", "u"),
                Column(dummy_dialect, "user_id", "o")
            )
        )
        
        sql, params = join_expr.to_sql()
        
        assert '"users" AS "u" INNER JOIN "orders" AS "o" ON "u"."id" = "o"."user_id"' == sql
        assert params == ()

    def test_join_expression_chaining(self, dummy_dialect: DummyDialect):
        """Test chaining multiple joins using the join() method."""
        # Create initial join: users JOIN orders
        users_orders_join = JoinExpression(
            dummy_dialect,
            left_table=TableExpression(dummy_dialect, "users", alias="u"),
            right_table=TableExpression(dummy_dialect, "orders", alias="o"),
            join_type="INNER JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id", "u"),
                Column(dummy_dialect, "user_id", "o")
            )
        )
        
        # Chain with products: (users JOIN orders) JOIN products
        chained_join = users_orders_join.join(
            right_table=TableExpression(dummy_dialect, "products", alias="p"),
            join_type="LEFT JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "product_id", "o"),
                Column(dummy_dialect, "id", "p")
            )
        )
        
        sql, params = chained_join.to_sql()
        
        # Verify the chained join structure
        assert '"users" AS "u" INNER JOIN "orders" AS "o" ON "u"."id" = "o"."user_id"' in sql
        assert 'LEFT JOIN "products" AS "p" ON "o"."product_id" = "p"."id"' in sql
        assert params == ()

    def test_multiple_join_chaining(self, dummy_dialect: DummyDialect):
        """Test chaining multiple joins consecutively."""
        # Start with users and orders
        base_join = JoinExpression(
            dummy_dialect,
            left_table=TableExpression(dummy_dialect, "users", alias="u"),
            right_table=TableExpression(dummy_dialect, "orders", alias="o"),
            join_type="INNER JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id", "u"),
                Column(dummy_dialect, "user_id", "o")
            )
        )
        
        # Add products
        second_join = base_join.join(
            right_table=TableExpression(dummy_dialect, "products", alias="p"),
            join_type="LEFT JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "product_id", "o"),
                Column(dummy_dialect, "id", "p")
            )
        )
        
        # Add categories
        third_join = second_join.join(
            right_table=TableExpression(dummy_dialect, "categories", alias="c"),
            join_type="INNER JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "category_id", "p"),
                Column(dummy_dialect, "id", "c")
            )
        )
        
        sql, params = third_join.to_sql()
        
        # Verify all three joins are present
        assert '"users" AS "u" INNER JOIN "orders" AS "o" ON "u"."id" = "o"."user_id"' in sql
        assert 'LEFT JOIN "products" AS "p" ON "o"."product_id" = "p"."id"' in sql
        assert 'INNER JOIN "categories" AS "c" ON "p"."category_id" = "c"."id"' in sql
        assert params == ()

    def test_convenience_methods_chaining(self, dummy_dialect: DummyDialect):
        """Test chaining using convenience methods like inner_join, left_join, etc."""
        # Start with a basic join
        base_join = JoinExpression(
            dummy_dialect,
            left_table=TableExpression(dummy_dialect, "users", alias="u"),
            right_table=TableExpression(dummy_dialect, "orders", alias="o"),
            join_type="INNER JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id", "u"),
                Column(dummy_dialect, "user_id", "o")
            )
        )
        
        # Use convenience method to add products
        chained_join = base_join.left_join(
            right_table=TableExpression(dummy_dialect, "products", alias="p"),
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "product_id", "o"),
                Column(dummy_dialect, "id", "p")
            )
        )
        
        # Use another convenience method to add categories
        final_join = chained_join.inner_join(
            right_table=TableExpression(dummy_dialect, "categories", alias="c"),
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "category_id", "p"),
                Column(dummy_dialect, "id", "c")
            )
        )
        
        sql, params = final_join.to_sql()
        
        # Verify the joins with correct types
        assert '"users" AS "u" INNER JOIN "orders" AS "o" ON "u"."id" = "o"."user_id"' in sql
        assert 'LEFT JOIN "products" AS "p" ON "o"."product_id" = "p"."id"' in sql
        assert 'INNER JOIN "categories" AS "c" ON "p"."category_id" = "c"."id"' in sql
        assert params == ()

    def test_different_join_types_chaining(self, dummy_dialect: DummyDialect):
        """Test chaining with different join types."""
        base_join = JoinExpression(
            dummy_dialect,
            left_table=TableExpression(dummy_dialect, "customers", alias="c"),
            right_table=TableExpression(dummy_dialect, "orders", alias="o"),
            join_type="LEFT JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id", "c"),
                Column(dummy_dialect, "customer_id", "o")
            )
        )
        
        # Add order_items with INNER JOIN
        second_join = base_join.inner_join(
            right_table=TableExpression(dummy_dialect, "order_items", alias="oi"),
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id", "o"),
                Column(dummy_dialect, "order_id", "oi")
            )
        )
        
        # Add products with RIGHT JOIN
        third_join = second_join.right_join(
            right_table=TableExpression(dummy_dialect, "products", alias="p"),
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "product_id", "oi"),
                Column(dummy_dialect, "id", "p")
            )
        )
        
        # Add suppliers with CROSS JOIN (no condition)
        fourth_join = third_join.cross_join(
            right_table=TableExpression(dummy_dialect, "suppliers", alias="s")
        )
        
        sql, params = fourth_join.to_sql()
        
        # Verify all join types are present
        assert 'LEFT JOIN' in sql
        assert 'INNER JOIN' in sql
        assert 'RIGHT JOIN' in sql
        assert 'CROSS JOIN' in sql
        assert params == ()

    def test_join_with_using_clause_chaining(self, dummy_dialect: DummyDialect):
        """Test chaining joins that use USING clause instead of ON."""
        base_join = JoinExpression(
            dummy_dialect,
            left_table=TableExpression(dummy_dialect, "table_a", alias="a"),
            right_table=TableExpression(dummy_dialect, "table_b", alias="b"),
            join_type="INNER JOIN",
            using=["common_id"]
        )
        
        # Chain with another join using USING
        chained_join = base_join.join(
            right_table=TableExpression(dummy_dialect, "table_c", alias="c"),
            join_type="LEFT JOIN",
            using=["another_common_id"]
        )
        
        sql, params = chained_join.to_sql()
        
        assert 'USING ("common_id")' in sql
        assert 'LEFT JOIN "table_c" AS "c" USING ("another_common_id")' in sql
        assert params == ()

    def test_join_with_alias_chaining(self, dummy_dialect: DummyDialect):
        """Test chaining joins with aliases."""
        base_join = JoinExpression(
            dummy_dialect,
            left_table=TableExpression(dummy_dialect, "users", alias="u"),
            right_table=TableExpression(dummy_dialect, "orders", alias="o"),
            join_type="INNER JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id", "u"),
                Column(dummy_dialect, "user_id", "o")
            ),
            alias="user_orders"
        )
        
        # Chain with products, also with alias
        chained_join = base_join.left_join(
            right_table=TableExpression(dummy_dialect, "products", alias="p"),
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "product_id", "o"),
                Column(dummy_dialect, "id", "p")
            ),
            alias="full_join"
        )
        
        sql, params = chained_join.to_sql()
        
        # Verify the alias is applied to the whole join expression
        assert 'AS "user_orders"' in sql or 'AS "full_join"' in sql
        assert params == ()

    def test_complex_conditions_in_chained_joins(self, dummy_dialect: DummyDialect):
        """Test chained joins with complex conditions."""
        base_join = JoinExpression(
            dummy_dialect,
            left_table=TableExpression(dummy_dialect, "users", alias="u"),
            right_table=TableExpression(dummy_dialect, "orders", alias="o"),
            join_type="INNER JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "AND",
                ComparisonPredicate(
                    dummy_dialect,
                    "=",
                    Column(dummy_dialect, "id", "u"),
                    Column(dummy_dialect, "user_id", "o")
                ),
                ComparisonPredicate(
                    dummy_dialect,
                    ">",
                    Column(dummy_dialect, "total_amount", "o"),
                    Literal(dummy_dialect, 100)
                )
            )
        )
        
        # Chain with products with another complex condition
        chained_join = base_join.left_join(
            right_table=TableExpression(dummy_dialect, "products", alias="p"),
            condition=ComparisonPredicate(
                dummy_dialect,
                "AND",
                ComparisonPredicate(
                    dummy_dialect,
                    "=",
                    Column(dummy_dialect, "product_id", "o"),
                    Column(dummy_dialect, "id", "p")
                ),
                ComparisonPredicate(
                    dummy_dialect,
                    "=",
                    Column(dummy_dialect, "status", "p"),
                    Literal(dummy_dialect, "active")
                )
            )
        )
        
        sql, params = chained_join.to_sql()
        
        assert '"users" AS "u" INNER JOIN "orders" AS "o"' in sql
        assert 'LEFT JOIN "products" AS "p"' in sql
        assert '"total_amount" > ?' in sql
        assert '"status" = ?' in sql
        assert params == (100, "active")

    def test_join_expression_with_query_expression_as_table(self, dummy_dialect: DummyDialect):
        """Test JoinExpression with QueryExpression as one of the tables."""
        # Create a subquery
        subquery = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "inactive_users")
        )
        
        # Join regular table with subquery
        join_expr = JoinExpression(
            dummy_dialect,
            left_table=TableExpression(dummy_dialect, "orders", alias="o"),
            right_table=subquery,
            join_type="INNER JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "user_id", "o"),
                Column(dummy_dialect, "id", "")  # No table alias for subquery result
            )
        )
        
        sql, params = join_expr.to_sql()
        
        assert '"orders" AS "o" INNER JOIN (SELECT "id", "name" FROM "inactive_users")' in sql
        assert params == ()

    def test_chaining_with_subquery_joins(self, dummy_dialect: DummyDialect):
        """Test chaining joins where one of the 'tables' is a subquery."""
        # Create a subquery
        user_summary = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "user_id"),
                FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id"))
            ],
            from_=TableExpression(dummy_dialect, "orders"),
            group_by_having=GroupByHavingClause(
                dialect=dummy_dialect,
                group_by=[Column(dummy_dialect, "user_id")]
            )
        )
        
        # Join users with the subquery
        base_join = JoinExpression(
            dummy_dialect,
            left_table=TableExpression(dummy_dialect, "users", alias="u"),
            right_table=user_summary,
            join_type="LEFT JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id", "u"),
                Column(dummy_dialect, "user_id", "")
            )
        )
        
        # Chain with another table
        chained_join = base_join.inner_join(
            right_table=TableExpression(dummy_dialect, "profiles", alias="p"),
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id", "u"),
                Column(dummy_dialect, "user_id", "p")
            )
        )
        
        sql, params = chained_join.to_sql()
        
        assert '"users" AS "u" LEFT JOIN (SELECT' in sql
        assert 'INNER JOIN "profiles" AS "p"' in sql
        assert params == ()

    def test_nested_join_expressions(self, dummy_dialect: DummyDialect):
        """Test creating a join where one side is already a JoinExpression."""
        # Create first join
        first_join = JoinExpression(
            dummy_dialect,
            left_table=TableExpression(dummy_dialect, "users", alias="u"),
            right_table=TableExpression(dummy_dialect, "user_profiles", alias="up"),
            join_type="LEFT JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id", "u"),
                Column(dummy_dialect, "user_id", "up")
            )
        )
        
        # Create second join
        second_join = JoinExpression(
            dummy_dialect,
            left_table=TableExpression(dummy_dialect, "orders", alias="o"),
            right_table=TableExpression(dummy_dialect, "products", alias="p"),
            join_type="INNER JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "product_id", "o"),
                Column(dummy_dialect, "id", "p")
            )
        )
        
        # Join the two join expressions together
        final_join = JoinExpression(
            dummy_dialect,
            left_table=first_join,
            right_table=second_join,
            join_type="LEFT JOIN",
            condition=ComparisonPredicate(
                dummy_dialect,
                "=",
                Column(dummy_dialect, "id", "u"),
                Column(dummy_dialect, "user_id", "o")
            )
        )
        
        sql, params = final_join.to_sql()
        
        # Verify both sides contain their respective joins
        assert '"users" AS "u" LEFT JOIN "user_profiles" AS "up"' in sql
        assert 'INNER JOIN "products" AS "p"' in sql
        assert 'LEFT JOIN' in sql  # The final join type
        assert params == ()