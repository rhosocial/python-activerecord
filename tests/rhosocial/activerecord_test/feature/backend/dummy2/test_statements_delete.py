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

        # Handle specific expression types that have left/right attributes
        if hasattr(expr, 'left') and hasattr(expr, 'right'):
            # This handles ComparisonPredicate and other binary operations
            self.set_dialect_recursive(expr.left, dialect)
            self.set_dialect_recursive(expr.right, dialect)

        # Handle specific types that may not have been covered by the generic logic
        if hasattr(expr, 'condition'):  # For WhereClause, etc.
            self.set_dialect_recursive(expr.condition, dialect)


    @pytest.mark.parametrize(
        "table_param, using_param, where_param, returning_param, expected_sql, expected_params, test_id",
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
                'DELETE FROM "users" USING "old_users_table" WHERE "users"."id" = "old_users_table"."old_id"',
                (),
                "delete_using_str_table",
                id="delete_using_str_table"
            ),
            pytest.param(
                "users", TableExpression(None, "old_users", alias="o"),
                Column(None, "id", "users") == Column(None, "old_id", "o"), None,
                'DELETE FROM "users" USING "old_users" AS "o" WHERE "users"."id" = "o"."old_id"',
                (),
                "delete_using_table_expr",
                id="delete_using_table_expr"
            ),
            pytest.param(
                "products",
                QueryExpression(None, select=[Column(None, "id")], from_="archived_products", where=Column(None, "deleted_at") < RawSQLExpression(None, "NOW()")),
                Column(None, "id", "products") == Column(None, "id"),
                None,
                'DELETE FROM "products" USING (SELECT "id" FROM "archived_products" WHERE "deleted_at" < NOW()) WHERE "products"."id" = "id"',
                (),
                "delete_from_subquery",
                id="delete_from_subquery"
            ),
            pytest.param(
                "orders",
                [TableExpression(None, "order_items", alias="oi"), TableExpression(None, "customers", alias="c")],
                (Column(None, "id", "orders") == Column(None, "order_id", "oi")) &
                (Column(None, "customer_id", "orders") == Column(None, "id", "c")),
                None,
                'DELETE FROM "orders" USING "order_items" AS "oi", "customers" AS "c" WHERE "orders"."id" = "oi"."order_id" AND "orders"."customer_id" = "c"."id"',
                (),
                "delete_using_list_of_tables",
                id="delete_using_list_of_tables"
            ),
            pytest.param(
                "main_table",
                JoinExpression(None, TableExpression(None, "join_table", alias="jt"), TableExpression(None, "lookup_table", alias="lt"), condition=Column(None, "key", "jt") == Column(None, "id", "lt")),
                Column(None, "id", "main_table") == Column(None, "main_id", "jt") ,
                None,
                'DELETE FROM "main_table" USING "join_table" AS "jt" JOIN "lookup_table" AS "lt" ON "jt"."key" = "lt"."id" WHERE "main_table"."id" = "jt"."main_id"',
                (),
                "delete_using_join_expr",
                id="delete_using_join_expr"
            ),
            pytest.param(
                "employees",
                "salaries",
                Column(None, "employee_id", "employees") == Column(None, "emp_id", "salaries") ,
                [Column(None, "employee_id"), Column(None, "first_name")],
                'DELETE FROM "employees" USING "salaries" WHERE "employees"."employee_id" = "salaries"."emp_id" RETURNING "employee_id", "first_name"',
                (),
                "delete_using_and_returning",
                id="delete_using_and_returning"
            ),
        ]
    )
    def test_delete_expression_combinations(self, dummy_dialect: DummyDialect,
                                             table_param, using_param, where_param, returning_param,
                                             expected_sql, expected_params, test_id):
        """Tests various combinations for the DELETE statement."""
        # Apply dialect recursively to the table_param
        dialect_table_param = table_param
        if isinstance(dialect_table_param, TableExpression):
            self.set_dialect_recursive(dialect_table_param, dummy_dialect)

        # Apply dialect recursively to using_param
        dialect_using_param = using_param
        self.set_dialect_recursive(dialect_using_param, dummy_dialect)

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
            using=dialect_using_param,
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

        with pytest.raises(TypeError, match=r"using must be one of: str, TableExpression, Subquery, SetOperationExpression, JoinExpression, list, ValuesExpression, TableFunctionExpression, LateralExpression, QueryExpression, got <class 'int'>"):
            delete_expr = DeleteExpression(
                dummy_dialect,
                table="users",
                using=unsupported_source,
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

    # --- Validation failure tests ---
    # Note: table parameter is automatically converted in the constructor,
    # so we don't validate its type in the expression validation.
    # from_ parameter is also converted but we can still test the converted value

    def test_delete_expression_invalid_where_type_after_construction(self, dummy_dialect: DummyDialect):
        """Tests that DeleteExpression raises TypeError for invalid where parameter type after construction."""
        # Manually set an invalid type after construction to test validation
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="users",
            where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
        )
        # Manually assign invalid type to trigger validation error
        delete_expr.where = 123  # Invalid type - should be WhereClause or SQLPredicate

        with pytest.raises(TypeError, match=r"where must be WhereClause or SQLPredicate, got <class 'int'>"):
            delete_expr.validate(strict=True)

    def test_delete_expression_invalid_using_type_after_construction(self, dummy_dialect: DummyDialect):
        """Tests that DeleteExpression raises TypeError for invalid using parameter type."""
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="users",
            where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
        )
        # Manually assign invalid type to trigger validation error
        delete_expr.using = 456  # Invalid type

        with pytest.raises(TypeError, match=r"using must be one of: str, TableExpression, Subquery, SetOperationExpression, JoinExpression, list, ValuesExpression, TableFunctionExpression, LateralExpression, QueryExpression, got <class 'int'>"):
            delete_expr.validate(strict=True)

    def test_delete_expression_invalid_where_type_initial(self, dummy_dialect: DummyDialect):
        """Tests that DeleteExpression raises TypeError for invalid where parameter type (initial case)."""
        # This tests the case where an invalid type is passed initially
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="users",
            where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
        )
        # Manually assign invalid type to trigger validation error
        delete_expr.where = 789  # Invalid type - should be WhereClause or SQLPredicate

        with pytest.raises(TypeError, match=r"where must be WhereClause or SQLPredicate, got <class 'int'>"):
            delete_expr.validate(strict=True)

    def test_delete_expression_invalid_returning_type(self, dummy_dialect: DummyDialect):
        """Tests that DeleteExpression raises TypeError for invalid returning parameter type."""
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="users",
            where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
        )
        # Manually assign invalid type to trigger validation error
        delete_expr.returning = 999  # Invalid type - should be ReturningClause

        with pytest.raises(TypeError, match=r"returning must be ReturningClause, got <class 'int'>"):
            delete_expr.validate(strict=True)

    def test_delete_expression_invalid_tables_type(self, dummy_dialect: DummyDialect):
        """Tests that DeleteExpression raises TypeError for invalid tables parameter type."""
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="users",
            where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
        )
        # Manually assign invalid type to trigger validation error
        delete_expr.tables = "invalid_type"  # Invalid type - should be list

        with pytest.raises(TypeError, match=r"tables must be a list of tables, got <class 'str'>"):
            delete_expr.validate(strict=True)

    def test_delete_expression_empty_tables_value_error(self, dummy_dialect: DummyDialect):
        """Tests that DeleteExpression raises ValueError for empty tables parameter."""
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="users",
            where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
        )
        # Manually assign empty list to trigger validation error
        delete_expr.tables = []  # Invalid value - should not be empty

        with pytest.raises(ValueError, match=r"Tables cannot be empty for a DELETE statement."):
            delete_expr.validate(strict=True)

    def test_delete_expression_invalid_table_element_type(self, dummy_dialect: DummyDialect):
        """Tests that DeleteExpression raises TypeError for invalid table element type in tables list."""
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="users",
            where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
        )
        # Manually assign invalid element type in the list to trigger validation error
        delete_expr.tables = [Column(dummy_dialect, "invalid_table")]  # Invalid element type - should be TableExpression

        with pytest.raises(TypeError, match=r"tables\[0\] must be TableExpression, got <class 'rhosocial.activerecord.backend.expression.core.Column'>"):
            delete_expr.validate(strict=True)

    def test_delete_expression_empty_table_list_value_error(self, dummy_dialect: DummyDialect):
        """Tests that DeleteExpression raises ValueError for empty table list."""
        with pytest.raises(ValueError, match=r"Table list cannot be empty for a DELETE statement."):
            DeleteExpression(
                dummy_dialect,
                table=[]
            )

    def test_delete_expression_single_table_in_list(self, dummy_dialect: DummyDialect):
        """Tests DeleteExpression with single table in list."""
        delete_expr = DeleteExpression(
            dummy_dialect,
            table=["users"],
            where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
        )
        # Check that the table was properly converted to TableExpression
        assert len(delete_expr.tables) == 1
        from rhosocial.activerecord.backend.expression.core import TableExpression
        assert isinstance(delete_expr.tables[0], TableExpression)
        assert delete_expr.tables[0].name == "users"

        sql, params = delete_expr.to_sql()
        assert sql == 'DELETE FROM "users" WHERE "id" = ?'
        assert params == (1,)

    def test_delete_expression_multiple_tables_in_list(self, dummy_dialect: DummyDialect):
        """Tests DeleteExpression with multiple tables in list."""
        delete_expr = DeleteExpression(
            dummy_dialect,
            table=["users", "profiles"],
            where=Column(dummy_dialect, "user_id") == Literal(dummy_dialect, 123)
        )
        # Check that the tables were properly converted to TableExpression
        assert len(delete_expr.tables) == 2
        from rhosocial.activerecord.backend.expression.core import TableExpression
        assert all(isinstance(table, TableExpression) for table in delete_expr.tables)
        assert delete_expr.tables[0].name == "users"
        assert delete_expr.tables[1].name == "profiles"

        sql, params = delete_expr.to_sql()
        assert sql == 'DELETE FROM "users", "profiles" WHERE "user_id" = ?'
        assert params == (123,)

    def test_delete_expression_table_list_with_table_expressions(self, dummy_dialect: DummyDialect):
        """Tests DeleteExpression with TableExpression objects in the table list (testing the self.tables.append(t) branch)."""
        from rhosocial.activerecord.backend.expression.core import TableExpression

        # Create TableExpression objects directly
        table_expr1 = TableExpression(dummy_dialect, "users", alias="u")
        table_expr2 = TableExpression(dummy_dialect, "orders", alias="o")

        delete_expr = DeleteExpression(
            dummy_dialect,
            table=[table_expr1, table_expr2],  # Pass TableExpression objects directly
            where=Column(dummy_dialect, "user_id") == Literal(dummy_dialect, 123)
        )

        # Check that the table expressions were directly appended (not recreated)
        assert len(delete_expr.tables) == 2
        assert delete_expr.tables[0] is table_expr1  # Should be the same object (testing self.tables.append(t))
        assert delete_expr.tables[1] is table_expr2  # Should be the same object (testing self.tables.append(t))
        assert delete_expr.tables[0].alias == "u"
        assert delete_expr.tables[1].alias == "o"

        sql, params = delete_expr.to_sql()
        assert sql == 'DELETE FROM "users" AS "u", "orders" AS "o" WHERE "user_id" = ?'
        assert params == (123,)

    def test_delete_expression_validate_with_strict_false(self, dummy_dialect: DummyDialect):
        """Tests that DeleteExpression.validate with strict=False skips validation."""
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="users",
            where=Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
        )
        # Manually assign invalid type that would normally cause an error
        delete_expr.where = 999  # Invalid type - should be WhereClause or SQLPredicate

        # With strict=False, validation should pass without raising an error
        delete_expr.validate(strict=False)  # Should not raise any exception

        # Also test with valid parameters and strict=False
        delete_expr_valid = DeleteExpression(
            dummy_dialect,
            table="products",
            where=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        )
        delete_expr_valid.validate(strict=False)  # Should not raise any exception
        assert True  # Just to ensure the test passes

    @pytest.mark.parametrize("op, pattern, expected_sql_part", [
        ("LIKE", "John%", '"name" LIKE ?'),
        ("ILIKE", "JOHN%", '"name" ILIKE ?'),  # Case-insensitive like
        ("LIKE", "%admin%", '"name" LIKE ?'),  # Contains pattern
    ])
    def test_delete_with_like_condition(self, dummy_dialect: DummyDialect, op, pattern, expected_sql_part):
        """Tests DELETE with LIKE/ILIKE conditions."""
        name_col = Column(dummy_dialect, "name")
        if op == "LIKE":
            like_condition = name_col.like(pattern)
        elif op == "ILIKE":
            like_condition = name_col.ilike(pattern)
        else:
            raise ValueError(f"Unsupported LIKE operation: {op}")

        delete_expr = DeleteExpression(
            dummy_dialect,
            table="users",
            where=like_condition
        )
        sql, params = delete_expr.to_sql()

        expected_sql = f'DELETE FROM "users" WHERE {expected_sql_part}'
        assert sql == expected_sql
        assert params == (pattern,)

    def test_delete_with_combined_like_and_other_conditions(self, dummy_dialect: DummyDialect):
        """Tests DELETE with LIKE condition combined with other conditions."""
        name_col = Column(dummy_dialect, "name")
        age_col = Column(dummy_dialect, "age")

        # Combine LIKE with comparison condition
        like_condition = name_col.like("John%")
        age_condition = age_col > Literal(dummy_dialect, 18)
        combined_condition = like_condition & age_condition

        delete_expr = DeleteExpression(
            dummy_dialect,
            table="users",
            where=combined_condition
        )
        sql, params = delete_expr.to_sql()

        assert 'DELETE FROM "users" WHERE' in sql
        assert 'LIKE ?' in sql
        assert '> ?' in sql
        assert params == ("John%", 18)

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

    def test_format_case_expression_with_empty_conditions_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that format_case_expression raises ValueError when called with empty conditions_results."""
        with pytest.raises(ValueError, match=r"CASE expression must have at least one WHEN/THEN condition-result pair."):
            dummy_dialect.format_case_expression(
                value_sql=None,
                value_params=None,
                conditions_results=[],  # Empty list should raise error
                else_result_sql=None,
                else_result_params=None
            )

    def test_format_window_specification_with_no_components_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that format_window_specification raises ValueError when called with no components."""
        from rhosocial.activerecord.backend.expression.advanced_functions import WindowSpecification

        # Create a WindowSpecification with no components (empty)
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[],  # Empty partition
            order_by=[],      # Empty order by
            frame=None        # No frame
        )

        with pytest.raises(ValueError, match=r"Window specification must have at least one component: PARTITION BY, ORDER BY, or FRAME."):
            dummy_dialect.format_window_specification(window_spec)

    def test_format_column_definition_with_default_constraint_but_no_value_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that format_column_definition raises ValueError when DEFAULT constraint has no value."""
        from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint, ColumnConstraintType

        # Create a ColumnDefinition with DEFAULT constraint but no value
        col_def = ColumnDefinition(
            name="test_col",
            data_type="VARCHAR(255)",
            constraints=[
                ColumnConstraint(
                    constraint_type=ColumnConstraintType.DEFAULT,
                    default_value=None  # No default value provided but constraint type is DEFAULT
                )
            ]
        )

        with pytest.raises(ValueError, match=r"DEFAULT constraint must have a default value specified."):
            dummy_dialect.format_column_definition(col_def)