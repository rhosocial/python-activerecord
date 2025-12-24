# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_update.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, QueryExpression, TableExpression,
    InsertExpression, UpdateExpression, ValuesSource, SelectSource,
    DefaultValuesSource, OnConflictClause, core,
    JoinExpression,
    LogicalPredicate, ReturningClause, ComparisonPredicate
)
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression import bases # For set_dialect_recursive


class TestUpdateStatements:
    """Tests for the refactored UPDATE statement expressions."""

    def test_update_empty_assignments_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that UpdateExpression raises ValueError for empty assignments."""
        with pytest.raises(ValueError, match="Assignments cannot be empty for an UPDATE statement."):
            UpdateExpression(
                dummy_dialect,
                table="users",
                assignments={}
            )

    @pytest.mark.parametrize(
        "table_param, assignments_param, where_param, returning_param, expected_sql, expected_params, test_id",
        [
            pytest.param(
                "users", {"name": Literal(None, "Jane Doe")}, None, None,
                'UPDATE "users" SET "name" = ?',
                ("Jane Doe",),
                "basic_update_str_table",
                id="basic_update_str_table"
            ),
            pytest.param(
                TableExpression(None, "products", alias="p"), {"price": Literal(None, 19.99)}, None, None,
                'UPDATE "products" AS "p" SET "price" = ?',
                (19.99,),
                "basic_update_table_expr",
                id="basic_update_table_expr"
            ),
            pytest.param(
                "orders",
                {"status": Literal(None, "shipped"), "updated_at": RawSQLExpression(None, "CURRENT_TIMESTAMP")},
                Column(None, "id") == Literal(None, 1), None,
                'UPDATE "orders" SET "status" = ?, "updated_at" = CURRENT_TIMESTAMP WHERE "id" = ?',
                ("shipped", 1),
                "update_with_where",
                id="update_with_where"
            ),
            pytest.param(
                "items",
                {"quantity": Column(None, "quantity") + Literal(None, 1)},
                None,
                [Column(None, "id"), Column(None, "quantity")],
                'UPDATE "items" SET "quantity" = "quantity" + ? RETURNING "id", "quantity"',
                (1,),
                "update_with_returning",
                id="update_with_returning"
            ),
            # pytest.param(  # Commented out because it uses old-style parameters in QueryExpression
            #     "accounts",
            #     {"balance": Column(None, "balance") + Literal(None, 100)},
            #     Column(None, "user_id") == QueryExpression(None, select=[Column(None, "id")], from_="users", where=Column(None, "name") == Literal(None, "Alice")),
            #     None,
            #     'UPDATE "accounts" SET "balance" = "balance" + ? WHERE "user_id" = (SELECT "id" FROM "users" WHERE "name" = ?)',
            #     (100, "Alice"),
            #     "update_with_subquery_assignment_and_where",
            #     id="update_with_subquery_assignment_and_where"
            # ),
        ]
    )
    def test_update_expression_combinations(self, dummy_dialect: DummyDialect,
                                             table_param, assignments_param, where_param, returning_param,
                                             expected_sql, expected_params, test_id):
        """Tests various combinations for the UPDATE statement."""
        # Helper function to recursively set dialect for BaseExpression objects.
        # This is needed because test parameters might initialize expressions with None dialect,
        # and we need to propagate the dummy_dialect before to_sql() is called.
        def set_dialect_recursive(expr, dialect):
            from rhosocial.activerecord.backend.expression import bases # Import needed classes
            
            # Only process BaseExpression instances
            if not isinstance(expr, bases.BaseExpression):
                return

            expr._dialect = dialect

            # Recursively set dialect for nested expressions.
            if hasattr(expr, 'args') and isinstance(expr.args, list):
                for arg in expr.args:
                    set_dialect_recursive(arg, dialect)
            if hasattr(expr, 'elements') and isinstance(expr.elements, list):
                for elem in expr.elements:
                    set_dialect_recursive(elem, dialect)
            if hasattr(expr, 'left'):
                set_dialect_recursive(expr.left, dialect)
            if hasattr(expr, 'right'):
                set_dialect_recursive(expr.right, dialect)
            if hasattr(expr, 'expr'): # For predicates
                set_dialect_recursive(expr.expr, dialect)
            if hasattr(expr, 'value') and isinstance(expr.value, bases.BaseExpression): # For Literal, if value is an expression
                set_dialect_recursive(expr.value, dialect)
            if hasattr(expr, 'subquery'): # For QueryExpression in from_ or assignments
                set_dialect_recursive(expr.subquery, dialect)
            if isinstance(expr, QueryExpression): # For QueryExpression itself
                for s_elem in expr.select:
                    set_dialect_recursive(s_elem, dialect)
                if expr.from_:
                    if isinstance(expr.from_, list):
                        for f_item in expr.from_:
                            if isinstance(f_item, bases.BaseExpression): # Only recurse if it's an expression
                                set_dialect_recursive(f_item, dialect)
                    elif isinstance(expr.from_, bases.BaseExpression): # Only recurse if it's an expression
                        set_dialect_recursive(expr.from_, dialect)
                set_dialect_recursive(expr.where, dialect)
            
            if isinstance(expr, LogicalPredicate) and (expr.op == "AND" or expr.op == "OR"):
                set_dialect_recursive(expr.left, dialect)
                set_dialect_recursive(expr.right, dialect)


        # Apply dialect recursively to all expressions in assignments
        dialect_assignments = {}
        for col, expr in assignments_param.items():
            set_dialect_recursive(expr, dummy_dialect)
            dialect_assignments[col] = expr
            
        # Apply dialect recursively to the table_param
        dialect_table_param = table_param
        if isinstance(dialect_table_param, TableExpression):
            set_dialect_recursive(dialect_table_param, dummy_dialect)

        # Apply dialect recursively to where_param
        dialect_where_param = where_param
        set_dialect_recursive(dialect_where_param, dummy_dialect)

        # Create where_clause if where_param is provided
        where_clause_param = None
        if dialect_where_param is not None:
            where_clause_param = WhereClause(dummy_dialect, condition=dialect_where_param)

        # Apply dialect recursively to returning_param
        dialect_returning_param = None
        if returning_param:
            for item in returning_param:
                set_dialect_recursive(item, dummy_dialect)
            dialect_returning_param = ReturningClause(dummy_dialect, expressions=returning_param)

        update_expr = UpdateExpression(
            dummy_dialect,
            table=dialect_table_param,
            assignments=dialect_assignments,
            where=where_clause_param,
            returning=dialect_returning_param
        )
        sql, params = update_expr.to_sql()
        assert sql == expected_sql
        assert params == expected_params


    # region FROM Clause Tests
    @pytest.mark.parametrize(
        "from_param, assignments_to_use, where_to_use, expected_from_sql, expected_sql_template, expected_params, test_id",
        [
            pytest.param(
                TableExpression(None, "logs", alias="l"),
                {"last_login": Column(None, "login_time", "l")},
                Column(None, "id", "users") == Column(None, "user_id", "l"),
                'FROM "logs" AS "l"',
                'UPDATE "users" SET "last_login" = "l"."login_time" %s WHERE "users"."id" = "l"."user_id"',
                (), # No extra params, all from expressions
                "from_table_expr",
                id="from_table_expr"
            ),
            pytest.param(
                QueryExpression(None, select=[Column(None, "id", "s"), Column(None, "status_val", "s")], from_=TableExpression(None, "sub_users", alias="s")),
                {"status": Column(None, "status_val", "s")},
                Column(None, "id", "users") == Column(None, "id", "s"),
                'FROM (SELECT "s"."id", "s"."status_val" FROM "sub_users" AS "s")',
                'UPDATE "users" SET "status" = "s"."status_val" %s WHERE "users"."id" = "s"."id"',
                (),
                "from_subquery",
                id="from_subquery"
            ),
            pytest.param(
                [TableExpression(None, "logs", alias="l"), TableExpression(None, "actions", alias="a")],
                {"activity_count": Column(None, "count", "a")},
                (Column(None, "id", "users") == Column(None, "user_id", "l")) & \
                (Column(None, "action_id", "l") == Column(None, "id", "a")),
                'FROM "logs" AS "l", "actions" AS "a"',
                'UPDATE "users" SET "activity_count" = "a"."count" %s WHERE "users"."id" = "l"."user_id" AND "l"."action_id" = "a"."id"',
                (),
                "from_list_of_tables",
                id="from_list_of_tables"
            ),
            pytest.param(
                JoinExpression(None, TableExpression(None, "user_data", alias="ud"), TableExpression(None, "users", alias="u"), condition=Column(None, "user_id", "ud") == Column(None, "id", "u")),
                {"value": Literal(None, 123)},
                Column(None, "id", "ud") == Column(None, "id", "u"), # Example WHERE, effectively part of JOIN
                'FROM "user_data" AS "ud" JOIN "users" AS "u" ON "ud"."user_id" = "u"."id"',
                'UPDATE "user_data" SET "value" = ? %s WHERE "ud"."id" = "u"."id"',
                (123,),
                "from_join_expr",
                id="from_join_expr"
            ),
            pytest.param(
                "logs_table", # Simple string for FROM source
                {"status": Literal(None, "active")},
                Column(None, "user_id") == Literal(None, 1),
                'FROM "logs_table"',
                'UPDATE "users" SET "status" = ? %s WHERE "user_id" = ?',
                ("active", 1),
                "from_string_table_name",
                id="from_string_table_name"
            )
        ]
    )
    def test_update_with_from_clause(self, dummy_dialect: DummyDialect,
                                      from_param, assignments_to_use, where_to_use, expected_from_sql, expected_sql_template, expected_params, test_id):
        """Tests UPDATE statement with a FROM clause."""
        # Helper function to recursively set dialect for BaseExpression objects.
        # This is needed because test parameters might initialize expressions with None dialect,
        # and we need to propagate the dummy_dialect before to_sql() is called.
        # This is a general recursive dialect setter, similar to the one in test_statements_insert.py
        def set_dialect_recursive(expr, dialect):
            from rhosocial.activerecord.backend.expression import bases # Import needed classes
            
            # Only process BaseExpression instances
            if not isinstance(expr, bases.BaseExpression):
                # If it's a list, recurse into elements
                if isinstance(expr, list):
                    for item in expr:
                        set_dialect_recursive(item, dialect)
                return

            expr._dialect = dialect

            # Recursively set dialect for nested expressions.
            if hasattr(expr, 'args') and isinstance(expr.args, list):
                for arg in expr.args:
                    set_dialect_recursive(arg, dialect)
            if hasattr(expr, 'elements') and isinstance(expr.elements, list):
                for elem in expr.elements:
                    set_dialect_recursive(elem, dialect)
            if hasattr(expr, 'left'):
                set_dialect_recursive(expr.left, dialect)
            if hasattr(expr, 'right'):
                set_dialect_recursive(expr.right, dialect)
            if hasattr(expr, 'expr'): # For predicates
                set_dialect_recursive(expr.expr, dialect)
            if hasattr(expr, 'value') and isinstance(expr.value, bases.BaseExpression): # For Literal, if value is an expression
                set_dialect_recursive(expr.value, dialect)
            if hasattr(expr, 'subquery'): # For QueryExpression in from_ or assignments
                set_dialect_recursive(expr.subquery, dialect)
            if isinstance(expr, QueryExpression): # For QueryExpression itself
                for s_elem in expr.select:
                    set_dialect_recursive(s_elem, dialect)
                if expr.from_:
                    if isinstance(expr.from_, list):
                        for f_item in expr.from_:
                            set_dialect_recursive(f_item, dialect)
                    else:
                        set_dialect_recursive(expr.from_, dialect)
                set_dialect_recursive(expr.where, dialect)
            
            # Specific for JoinExpression
            if isinstance(expr, JoinExpression):
                set_dialect_recursive(expr.left_table, dialect)
                set_dialect_recursive(expr.right_table, dialect)
                set_dialect_recursive(expr.condition, dialect)
            
            if isinstance(expr, LogicalPredicate): # LogicalPredicate has 'predicates'
                for pred in expr.predicates:
                    set_dialect_recursive(pred, dialect)


        # Apply dialect recursively to from_param
        dialect_from_param = from_param
        set_dialect_recursive(dialect_from_param, dummy_dialect)
        
        # Apply dialect recursively to assignments
        dialect_assignments = {}
        for col, expr in assignments_to_use.items():
            set_dialect_recursive(expr, dummy_dialect)
            dialect_assignments[col] = expr
            
        # Apply dialect recursively to where_to_use
        dialect_where_to_use = where_to_use
        set_dialect_recursive(dialect_where_to_use, dummy_dialect)

        # Create where_clause if we have a where condition
        where_clause_param = None
        if dialect_where_to_use is not None:
            from rhosocial.activerecord.backend.expression.query_parts import WhereClause
            where_clause_param = WhereClause(dummy_dialect, condition=dialect_where_to_use)

        update_expr = UpdateExpression(
            dummy_dialect,
            table="users" if test_id not in ["from_join_expr"] else "user_data", # Target table for the update
            assignments=dialect_assignments,
            from_=dialect_from_param,
            where=where_clause_param
        )
        sql, params = update_expr.to_sql()
        
        # Manually construct the expected SQL to include the FROM clause
        # The expected_sql_template includes a %s placeholder for the FROM clause
        assert sql == expected_sql_template % (expected_from_sql,)
        assert params == expected_params
    # endregion FROM Clause Tests

    def test_update_from_unsupported_source_type_raises_type_error(self, dummy_dialect: DummyDialect):
        """Tests that UpdateExpression raises TypeError for unsupported FROM source types."""
        unsupported_source = 123 # An integer, not a string or BaseExpression

        assignments = {"name": Literal(dummy_dialect, "New Name")}
        where = Column(dummy_dialect, "id") == Literal(dummy_dialect, 1)
        
        with pytest.raises(TypeError, match=r"Unsupported FROM source type: <class 'int'>"):
            update_expr = UpdateExpression(
                dummy_dialect,
                table="users",
                assignments=assignments,
                from_=unsupported_source,
                where=where
            )
            update_expr.to_sql()

    def test_update_expression_without_where_clause(self, dummy_dialect: DummyDialect):
        """Test UpdateExpression with no WHERE clause to cover the else branch where where=None."""
        from rhosocial.activerecord.backend.expression.core import TableExpression

        # Create an UpdateExpression without a WHERE clause
        update_expr = UpdateExpression(
            dummy_dialect,
            table=TableExpression(dummy_dialect, "users"),
            assignments={
                "status": Literal(dummy_dialect, "updated")
            }  # No where clause provided
        )
        sql, params = update_expr.to_sql()

        # Should generate a basic UPDATE statement without WHERE
        assert sql == 'UPDATE "users" SET "status" = ?'
        assert params == ("updated",)

    def test_update_expression_with_where_clause_object(self, dummy_dialect: DummyDialect):
        """Test UpdateExpression with a WhereClause object to cover the isinstance(where, WhereClause) branch."""
        from rhosocial.activerecord.backend.expression.core import TableExpression
        from rhosocial.activerecord.backend.expression.query_parts import WhereClause

        # Create a WhereClause object using comparison operator
        where_clause_obj = WhereClause(
            dummy_dialect,
            condition=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        )

        # Create an UpdateExpression with the WhereClause object
        update_expr = UpdateExpression(
            dummy_dialect,
            table=TableExpression(dummy_dialect, "users"),
            assignments={
                "last_updated": Literal(dummy_dialect, "2023-01-01")
            },
            where=where_clause_obj  # Pass WhereClause object directly
        )
        sql, params = update_expr.to_sql()

        # Should generate an UPDATE statement with WHERE clause
        assert 'UPDATE "users" SET "last_updated" = ? WHERE "status" = ?' == sql
        assert params == ("2023-01-01", "active")

    @pytest.mark.parametrize("op, pattern, expected_sql_part", [
        ("LIKE", "John%", '"name" LIKE ?'),
        ("ILIKE", "JOHN%", '"name" ILIKE ?'),  # Case-insensitive like
        ("LIKE", "%admin%", '"name" LIKE ?'),  # Contains pattern
    ])
    def test_update_with_like_condition(self, dummy_dialect: DummyDialect, op, pattern, expected_sql_part):
        """Tests UPDATE with LIKE/ILIKE conditions."""
        name_col = Column(dummy_dialect, "name")
        if op == "LIKE":
            like_condition = name_col.like(pattern)
        elif op == "ILIKE":
            like_condition = name_col.ilike(pattern)
        else:
            raise ValueError(f"Unsupported LIKE operation: {op}")

        update_expr = UpdateExpression(
            dummy_dialect,
            table="users",
            assignments={"status": Literal(dummy_dialect, "active")},
            where=WhereClause(dummy_dialect, condition=like_condition)
        )
        sql, params = update_expr.to_sql()

        expected_sql = f'UPDATE "users" SET "status" = ? WHERE {expected_sql_part}'
        assert sql == expected_sql
        assert params == ("active", pattern)

    def test_update_with_combined_like_and_other_conditions(self, dummy_dialect: DummyDialect):
        """Tests UPDATE with LIKE condition combined with other conditions."""
        name_col = Column(dummy_dialect, "name")
        age_col = Column(dummy_dialect, "age")

        # Combine LIKE with comparison condition
        like_condition = name_col.like("John%")
        age_condition = age_col > Literal(dummy_dialect, 18)
        combined_condition = like_condition & age_condition

        update_expr = UpdateExpression(
            dummy_dialect,
            table="users",
            assignments={"last_updated": Literal(dummy_dialect, "2023-01-01")},
            where=WhereClause(dummy_dialect, condition=combined_condition)
        )
        sql, params = update_expr.to_sql()

        assert 'UPDATE "users" SET "last_updated" = ? WHERE' in sql
        assert 'LIKE ?' in sql
        assert '> ?' in sql
        assert params == ("2023-01-01", "John%", 18)
