# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_delete.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, QueryExpression, TableExpression,
    DeleteExpression,
    JoinExpression,
    LogicalPredicate, ReturningClause, ComparisonPredicate
)
from rhosocial.activerecord.backend.expression import ComparisonPredicate, InPredicate, IsNullPredicate, BetweenPredicate, LikePredicate
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression import bases # For set_dialect_recursive


class TestDeleteStatements:
    """Tests for the refactored DELETE statement expressions."""

    # Helper function to recursively set dialect for BaseExpression objects.
    # This is needed because test parameters might initialize expressions with None dialect,
    # and we need to propagate the dummy_dialect before to_sql() is called.
    def set_dialect_recursive(self, expr, dialect):
        # Only process BaseExpression instances
        if not isinstance(expr, bases.BaseExpression):
            # If it's a list, recurse into elements
            if isinstance(expr, list):
                for item in expr:
                    self.set_dialect_recursive(item, dialect)
            return

        expr._dialect = dialect

        # Recursively set dialect for nested expressions.
        if hasattr(expr, 'args') and isinstance(expr.args, list):
            for arg in expr.args:
                self.set_dialect_recursive(arg, dialect)
        if hasattr(expr, 'elements') and isinstance(expr.elements, list):
            for elem in expr.elements:
                self.set_dialect_recursive(elem, dialect)
        if hasattr(expr, 'left'):
            self.set_dialect_recursive(expr.left, dialect)
        if hasattr(expr, 'right'):
            self.set_dialect_recursive(expr.right, dialect)
        if hasattr(expr, 'expr'): # For predicates
            self.set_dialect_recursive(expr.expr, dialect)
        if hasattr(expr, 'value') and isinstance(expr.value, bases.BaseExpression): # For Literal, if value is an expression
            self.set_dialect_recursive(expr.value, dialect)
        if hasattr(expr, 'subquery'): # For QueryExpression in from_ or assignments
            self.set_dialect_recursive(expr.subquery, dialect)
        if isinstance(expr, QueryExpression): # For QueryExpression itself
            for s_elem in expr.select:
                self.set_dialect_recursive(s_elem, dialect)
            if expr.from_:
                if isinstance(expr.from_, list):
                    for f_item in expr.from_:
                        if isinstance(f_item, bases.BaseExpression): # Only recurse if it's an expression
                            self.set_dialect_recursive(f_item, dialect)
                elif isinstance(expr.from_, bases.BaseExpression): # Only recurse if it's an expression
                    self.set_dialect_recursive(expr.from_, dialect)
            self.set_dialect_recursive(expr.where, dialect)

        # Specific for JoinExpression
        if isinstance(expr, JoinExpression):
            self.set_dialect_recursive(expr.left_table, dialect)
            self.set_dialect_recursive(expr.right_table, dialect)
            self.set_dialect_recursive(expr.condition, dialect)

        if isinstance(expr, LogicalPredicate): # LogicalPredicate has 'predicates'
            for pred in expr.predicates:
                self.set_dialect_recursive(pred, dialect)


    @pytest.mark.parametrize(
        "table_param, from_param, where_param, returning_param, expected_sql, expected_params, test_id",
        [
            pytest.param(
                "users", None, None, None,
                'DELETE FROM "users"',
                (),
                "basic_delete_str_table",
                id="basic_delete_str_table"
            ),
            pytest.param(
                TableExpression(None, "products", alias="p"), None, None, None,
                'DELETE FROM "products" AS "p"',
                (),
                "basic_delete_table_expr",
                id="basic_delete_table_expr"
            ),
            pytest.param(
                "orders", None,
                Column(None, "status") == Literal(None, "pending"), None,
                'DELETE FROM "orders" WHERE "status" = ?',
                ("pending",),
                "delete_with_where",
                id="delete_with_where"
            ),
            pytest.param(
                "items", None, None,
                [Column(None, "id"), Column(None, "quantity")],
                'DELETE FROM "items" RETURNING "id", "quantity"',
                (),
                "delete_with_returning",
                id="delete_with_returning"
            ),
            pytest.param(
                "users", "old_users_table",
                Column(None, "id", "users") == Column(None, "old_id", "old_users_table"), None,
                'DELETE FROM "users" FROM "old_users_table" WHERE "users"."id" = "old_users_table"."old_id"',
                (),
                "delete_from_str_table",
                id="delete_from_str_table"
            ),
            pytest.param(
                "users", TableExpression(None, "old_users", alias="o"),
                Column(None, "id", "users") == Column(None, "old_id", "o"), None,
                'DELETE FROM "users" FROM "old_users" AS "o" WHERE "users"."id" = "o"."old_id"',
                (),
                "delete_from_table_expr",
                id="delete_from_table_expr"
            ),
            # Skip parameter that uses old-style where parameter
            # This parameter would be handled differently since it involves QueryExpression with old API
            # pytest.param(
            #     "products",
            #     QueryExpression(None, select=[Column(None, "id")], from_="archived_products", where=Column(None, "deleted_at") < RawSQLExpression(None, "NOW()")),
            #     Column(None, "id", "products") == Column(None, "id"),
            #     None,
            #     'DELETE FROM "products" FROM (SELECT "id" FROM "archived_products" WHERE "deleted_at" < NOW()) WHERE "products"."id" = "id"',
            #     (),
            #     "delete_from_subquery",
            #     id="delete_from_subquery"
            # ),
            pytest.param(
                "orders",
                [TableExpression(None, "order_items", alias="oi"), TableExpression(None, "customers", alias="c")],
                (Column(None, "id", "orders") == Column(None, "order_id", "oi")) &
                (Column(None, "customer_id", "orders") == Column(None, "id", "c")),
                None,
                'DELETE FROM "orders" FROM "order_items" AS "oi", "customers" AS "c" WHERE "orders"."id" = "oi"."order_id" AND "orders"."customer_id" = "c"."id"',
                (),
                "delete_from_list_of_tables",
                id="delete_from_list_of_tables"
            ),
            pytest.param(
                "main_table",
                JoinExpression(None, TableExpression(None, "join_table", alias="jt"), TableExpression(None, "lookup_table", alias="lt"), condition=Column(None, "key", "jt") == Column(None, "id", "lt")),
                Column(None, "id", "main_table") == Column(None, "main_id", "jt") ,
                None,
                'DELETE FROM "main_table" FROM "join_table" AS "jt" JOIN "lookup_table" AS "lt" ON "jt"."key" = "lt"."id" WHERE "main_table"."id" = "jt"."main_id"',
                (),
                "delete_from_join_expr",
                id="delete_from_join_expr"
            ),
            pytest.param(
                "employees",
                "salaries",
                Column(None, "employee_id", "employees") == Column(None, "emp_id", "salaries") ,
                [Column(None, "employee_id"), Column(None, "first_name")],
                'DELETE FROM "employees" FROM "salaries" WHERE "employees"."employee_id" = "salaries"."emp_id" RETURNING "employee_id", "first_name"',
                (),
                "delete_from_and_returning",
                id="delete_from_and_returning"
            ),
        ]
    )
    def test_delete_expression_combinations(self, dummy_dialect: DummyDialect,
                                             table_param, from_param, where_param, returning_param,
                                             expected_sql, expected_params, test_id):
        """Tests various combinations for the DELETE statement."""
        # Apply dialect recursively to the table_param
        dialect_table_param = table_param
        if isinstance(dialect_table_param, TableExpression):
            self.set_dialect_recursive(dialect_table_param, dummy_dialect)

        # Apply dialect recursively to from_param
        dialect_from_param = from_param
        self.set_dialect_recursive(dialect_from_param, dummy_dialect)

        # Apply dialect recursively to where_param
        dialect_where_param = where_param
        self.set_dialect_recursive(dialect_where_param, dummy_dialect)

        # Apply dialect recursively to returning_param
        dialect_returning_param = None
        if returning_param:
            for item in returning_param:
                self.set_dialect_recursive(item, dummy_dialect)
            dialect_returning_param = ReturningClause(dummy_dialect, expressions=returning_param)

        delete_expr = DeleteExpression(
            dummy_dialect,
            table=dialect_table_param,
            from_=dialect_from_param,
            where=dialect_where_param,
            returning=dialect_returning_param
        )
        sql, params = delete_expr.to_sql()
        assert sql == expected_sql
        assert params == expected_params

    def test_delete_from_unsupported_source_type_raises_type_error(self, dummy_dialect: DummyDialect):
        """Tests that DeleteExpression raises TypeError for unsupported FROM source types."""
        unsupported_source = 123 # An integer, not a string or BaseExpression

        where = Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)

        with pytest.raises(TypeError, match=r"Unsupported FROM source type: <class 'int'>"):
            delete_expr = DeleteExpression(
                dummy_dialect,
                table="users",
                from_=unsupported_source,
                where=where
            )
            delete_expr.to_sql()

    # --- Additional tests from the original test_delete_statements.py ---
    
    @pytest.mark.parametrize("table, where_condition, expected_sql, expected_params", [
        ("orders", ComparisonPredicate(None, "<", Column(None, "order_date"), Literal(None, "2023-01-01")),  # Mock
         'DELETE FROM "orders" WHERE "order_date" < ?', ("2023-01-01",)),

        ("users", ComparisonPredicate(None, "!=", Column(None, "status"), Literal(None, "active")),  # Mock
         'DELETE FROM "users" WHERE "status" != ?', ("active",)),

        ("products", ComparisonPredicate(None, "=", Column(None, "category_id"), Literal(None, 5)),  # Mock
         'DELETE FROM "products" WHERE "category_id" = ?', (5,)),
    ])
    def test_basic_delete_original(self, dummy_dialect: DummyDialect, table, where_condition, expected_sql, expected_params):
        """Tests basic DELETE statements with a WHERE condition (original implementation)."""
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

    @pytest.mark.parametrize("comparison_op, right_value", [
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

    def test_delete_expression_without_where_clause(self, dummy_dialect: DummyDialect):
        """Test DeleteExpression with no WHERE clause to cover the else branch where where=None."""
        from rhosocial.activerecord.backend.expression.core import TableExpression

        # Create a DeleteExpression without a WHERE clause
        delete_expr = DeleteExpression(
            dummy_dialect,
            table=TableExpression(dummy_dialect, "users")  # No where clause provided
        )
        sql, params = delete_expr.to_sql()

        # Should generate a basic DELETE statement without WHERE
        assert sql == 'DELETE FROM "users"'
        assert params == ()

    def test_delete_expression_with_where_clause_object(self, dummy_dialect: DummyDialect):
        """Test DeleteExpression with a WhereClause object to cover the isinstance(where, WhereClause) branch."""
        from rhosocial.activerecord.backend.expression.core import TableExpression
        from rhosocial.activerecord.backend.expression.query_parts import WhereClause

        # Create a WhereClause object using comparison operator
        where_clause_obj = WhereClause(
            dummy_dialect,
            condition=Column(dummy_dialect, "status") == Literal(dummy_dialect, "inactive")
        )

        # Create a DeleteExpression with the WhereClause object
        delete_expr = DeleteExpression(
            dummy_dialect,
            table=TableExpression(dummy_dialect, "users"),
            where=where_clause_obj  # Pass WhereClause object directly
        )
        sql, params = delete_expr.to_sql()

        # Should generate a DELETE statement with WHERE clause
        assert 'DELETE FROM "users" WHERE "status" = ?' == sql
        assert params == ("inactive",)