import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, UpdateExpression, ComparisonPredicate, BinaryArithmeticExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

class TestUpdateStatements:
    """Tests for UPDATE statements with various configurations."""

    def test_basic_update_users(self, dummy_dialect: DummyDialect):
        """Tests basic UPDATE statement for users table."""
        assignments = {"name": Literal(dummy_dialect, "Jane Smith"), "age": Literal(dummy_dialect, 30)}
        where_condition = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "id"), Literal(dummy_dialect, 1))
        
        update_expr = UpdateExpression(
            dummy_dialect,
            table="users",
            assignments=assignments,
            where=where_condition
        )
        sql, params = update_expr.to_sql()
        # Note: dictionary order is not guaranteed, so the SET clause might vary.
        # Check for presence of elements rather than exact order
        assert 'UPDATE "users" SET' in sql
        assert "WHERE" in sql
        # Check that there are 3 parameters (name, age, id)
        assert len(params) == 3
        assert params[0] == "Jane Smith"  # First assignment value
        assert params[1] == 30            # Second assignment value  
        assert params[2] == 1             # Where condition value

    def test_basic_update_products(self, dummy_dialect: DummyDialect):
        """Tests basic UPDATE statement for products table."""
        assignments = {"price": Literal(dummy_dialect, 29.99), "updated_at": RawSQLExpression(dummy_dialect, "CURRENT_TIMESTAMP")}
        where_condition = ComparisonPredicate(dummy_dialect, ">", Column(dummy_dialect, "price"), Literal(dummy_dialect, 50))

        update_expr = UpdateExpression(
            dummy_dialect,
            table="products",
            assignments=assignments,
            where=where_condition
        )
        sql, params = update_expr.to_sql()
        # Note: dictionary order is not guaranteed, so the SET clause might vary.
        # Check for presence of elements rather than exact order
        assert 'UPDATE "products" SET' in sql
        assert "WHERE" in sql
        assert "CURRENT_TIMESTAMP" in sql  # Check raw SQL expression appears literally
        # Check that there are 2 parameters (price assignment value and where condition value)
        assert len(params) == 2
        assert params[0] == 29.99  # Assignment value
        assert params[1] == 50     # Where condition value

    def test_update_with_arithmetic_expression(self, dummy_dialect: DummyDialect):
        """Tests UPDATE statement with an arithmetic expression in SET clause."""
        from rhosocial.activerecord.backend.expression import BinaryArithmeticExpression
        
        update_expr = UpdateExpression(
            dummy_dialect,
            table="products",
            assignments={
                "stock": BinaryArithmeticExpression(dummy_dialect, "-", Column(dummy_dialect, "stock"), Literal(dummy_dialect, 5))
            },
            where=ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "id"), Literal(dummy_dialect, 10))
        )
        sql, params = update_expr.to_sql()
        assert sql == 'UPDATE "products" SET "stock" = "stock" - ? WHERE "id" = ?'
        assert params == (5, 10)

    @pytest.mark.parametrize("table, assignments_data, expected_partial_set_clause", [
        ("inventory", {"qty": (Literal, 100)}, 'SET "qty" = ?'),
        ("employees", {"salary": (Literal, 65000), "title": (Literal, "Manager")}, 'SET'),
        ("orders", {"status": (Literal, "shipped"), "ship_date": ("RawSQLExpression", "CURRENT_DATE")}, 'SET'),
    ])
    def test_update_set_clauses(self, dummy_dialect: DummyDialect, table, assignments_data, expected_partial_set_clause):
        """Tests various UPDATE SET clause configurations."""
        # Properly initialize assignments with dialect
        assignments = {}
        for col_name, (type_name, value) in assignments_data.items():
            if type_name == "Literal":
                assignments[col_name] = Literal(dummy_dialect, value)
            elif type_name == "RawSQLExpression":
                assignments[col_name] = RawSQLExpression(dummy_dialect, value)

        update_expr = UpdateExpression(
            dummy_dialect,
            table=table,
            assignments=assignments,
            where=ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "id"), Literal(dummy_dialect, 1))
        )
        sql, params = update_expr.to_sql()
        assert f'UPDATE "{table}"' in sql
        assert "SET" in sql
        # Count the actual number of parameters, considering that RawSQLExpression doesn't add parameters
        expected_param_count = 1  # +1 for WHERE clause
        for col_name, (type_name, value) in assignments_data.items():
            if type_name == "Literal":
                expected_param_count += 1  # Each literal adds one parameter
            # RawSQLExpression doesn't add parameters
        assert len(params) == expected_param_count

    def test_update_with_multiple_conditions(self, dummy_dialect: DummyDialect):
        """Tests UPDATE with complex WHERE conditions."""
        from rhosocial.activerecord.backend.expression import LogicalPredicate
        
        condition1 = ComparisonPredicate(dummy_dialect, ">", Column(dummy_dialect, "age"), Literal(dummy_dialect, 18))
        condition2 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "status"), Literal(dummy_dialect, "active"))
        complex_condition = LogicalPredicate(dummy_dialect, "AND", condition1, condition2)
        
        update_expr = UpdateExpression(
            dummy_dialect,
            table="users",
            assignments={"discount": Literal(dummy_dialect, 0.1)},
            where=complex_condition
        )
        sql, params = update_expr.to_sql()
        assert sql == 'UPDATE "users" SET "discount" = ? WHERE "age" > ? AND "status" = ?'
        assert params == (0.1, 18, "active")

    @pytest.mark.parametrize("operation, operand, expected_sql_pattern", [
        ("+", 10, 'SET "value" = "value" + ?'),
        ("-", 5, 'SET "value" = "value" - ?'),
        ("*", 3, 'SET "value" = "value" * ?'),
        ("/", 4, 'SET "value" = "value" / ?'),
    ])
    def test_update_with_arithmetic_operations(self, dummy_dialect: DummyDialect, operation, operand, expected_sql_pattern):
        """Tests UPDATE with various arithmetic operations."""
        from rhosocial.activerecord.backend.expression import BinaryArithmeticExpression

        new_value = BinaryArithmeticExpression(
            dummy_dialect,
            operation,
            Column(dummy_dialect, "value"),
            Literal(dummy_dialect, operand)
        )

        update_expr = UpdateExpression(
            dummy_dialect,
            table="items",
            assignments={"value": new_value},
            where=ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "id"), Literal(dummy_dialect, 1))
        )
        sql, params = update_expr.to_sql()
        assert expected_sql_pattern in sql
        assert params == (operand, 1)  # operand + where clause parameter

    def test_update_where_with_subquery_condition(self, dummy_dialect: DummyDialect):
        """Tests UPDATE with a WHERE condition that includes a subquery."""
        from rhosocial.activerecord.backend.expression import Subquery, ExistsExpression

        # First test: Using EXISTS in WHERE
        subquery = Subquery(dummy_dialect, "SELECT 1 FROM orders WHERE orders.user_id = users.id AND orders.status = ?", ("pending",))
        exists_condition = ExistsExpression(dummy_dialect, subquery)

        update_expr = UpdateExpression(
            dummy_dialect,
            table="users",
            assignments={"flag": Literal(dummy_dialect, 1)},
            where=exists_condition
        )
        sql, params = update_expr.to_sql()
        assert 'UPDATE "users" SET "flag" = ? WHERE EXISTS' in sql
        assert params == (1, "pending")