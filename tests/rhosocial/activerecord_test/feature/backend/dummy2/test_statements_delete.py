# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_delete.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, QueryExpression, TableExpression,
    DeleteExpression,
    JoinExpression,
    LogicalPredicate, ReturningClause
)
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
            pytest.param(
                "products",
                QueryExpression(None, select=[Column(None, "id")], from_="archived_products", where=Column(None, "deleted_at") < RawSQLExpression(None, "NOW()")),
                Column(None, "id", "products") == Column(None, "id"),
                None,
                'DELETE FROM "products" FROM (SELECT "id" FROM "archived_products" WHERE "deleted_at" < NOW()) WHERE "products"."id" = "id"',
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
                'DELETE FROM "main_table" FROM "join_table" AS "jt" INNER JOIN "lookup_table" AS "lt" ON "jt"."key" = "lt"."id" WHERE "main_table"."id" = "jt"."main_id"',
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
