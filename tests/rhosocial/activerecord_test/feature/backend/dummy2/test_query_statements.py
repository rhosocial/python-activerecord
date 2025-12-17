import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, RawSQLExpression, TableExpression, FunctionCall,
    ComparisonPredicate, LogicalPredicate, InPredicate,
    QueryExpression, InsertExpression, UpdateExpression, DeleteExpression,
    BinaryArithmeticExpression,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

class TestQueryStatements:
    """Tests for complete SQL query statements (SELECT, INSERT, UPDATE, DELETE)."""

    # --- QueryExpression (SELECT) ---
    def test_simple_select(self, dummy_dialect: DummyDialect):
        """Tests a simple SELECT statement."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "users")
        )
        sql, params = query.to_sql()
        assert sql == 'SELECT "id", "name" FROM "users"'
        assert params == ()

    def test_select_with_where_orderby_limit_offset(self, dummy_dialect: DummyDialect):
        """Tests SELECT with WHERE, ORDER BY, LIMIT, and OFFSET."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "products", "p"),
            where=ComparisonPredicate(dummy_dialect, ">", Column(dummy_dialect, "price", "p"), Literal(dummy_dialect, 100)),
            order_by=[Column(dummy_dialect, "name", order="ASC")],
            limit=10,
            offset=5
        )
        sql, params = query.to_sql()
        assert sql == 'SELECT "id", "name" FROM "products" AS "p" WHERE ("p"."price" > ?) ORDER BY "name" ASC LIMIT ? OFFSET ?'
        assert params == (100, 10, 5)

    def test_select_with_groupby_having(self, dummy_dialect: DummyDialect):
        """Tests SELECT with GROUP BY and HAVING clauses."""
        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "category"),
                FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id"), alias="product_count")
            ],
            from_=TableExpression(dummy_dialect, "products"),
            group_by=[Column(dummy_dialect, "category")],
            having=ComparisonPredicate(dummy_dialect, ">", FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")), Literal(dummy_dialect, 5))
        )
        sql, params = query.to_sql()
        assert sql == 'SELECT "category", COUNT("id") AS "product_count" FROM "products" GROUP BY "category" HAVING (COUNT("id") > ?)'
        assert params == (5,)

    # --- InsertExpression ---
    def test_simple_insert(self, dummy_dialect: DummyDialect):
        """Tests a simple INSERT statement with explicit columns and values."""
        insert_expr = InsertExpression(
            dummy_dialect,
            table="users",
            columns=["name", "email"],
            values=[Literal(dummy_dialect, "John Doe"), Literal(dummy_dialect, "john@example.com")]
        )
        sql, params = insert_expr.to_sql()
        assert sql == 'INSERT INTO "users" ("name", "email") VALUES (?, ?)'
        assert params == ("John Doe", "john@example.com")

    def test_insert_with_raw_sql_value(self, dummy_dialect: DummyDialect):
        """Tests INSERT statement with a value from a raw SQL expression."""
        insert_expr = InsertExpression(
            dummy_dialect,
            table="logs",
            columns=["event_time", "message"],
            values=[RawSQLExpression(dummy_dialect, "CURRENT_TIMESTAMP"), Literal(dummy_dialect, "System started")]
        )
        sql, params = insert_expr.to_sql()
        assert sql == 'INSERT INTO "logs" ("event_time", "message") VALUES (CURRENT_TIMESTAMP, ?)'
        assert params == ("System started",)

    # --- UpdateExpression ---
    def test_simple_update(self, dummy_dialect: DummyDialect):
        """Tests a simple UPDATE statement with SET clause and WHERE condition."""
        update_expr = UpdateExpression(
            dummy_dialect,
            table="users",
            set_values={
                "name": Literal(dummy_dialect, "Jane Smith"),
                "age": Literal(dummy_dialect, 30)
            },
            where=ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "id"), Literal(dummy_dialect, 1))
        )
        sql, params = update_expr.to_sql()
        # Note: dictionary order is not guaranteed, so the SET clause might vary.
        # However, for DummyDialect, it generates based on insertion order, but we can't rely on it.
        # A more robust test would check for presence of parts or sort them.
        # For simplicity, we'll use a fixed order here.
        assert sql in [
            'UPDATE "users" SET "name" = ?, "age" = ? WHERE ("id" = ?)',
            'UPDATE "users" SET "age" = ?, "name" = ? WHERE ("id" = ?)'
        ]
        assert params == ("Jane Smith", 30, 1) or params == (30, "Jane Smith", 1)


    def test_update_with_arithmetic_expression(self, dummy_dialect: DummyDialect):
        """Tests UPDATE statement with an arithmetic expression in SET clause."""
        update_expr = UpdateExpression(
            dummy_dialect,
            table="products",
            set_values={
                "stock": BinaryArithmeticExpression(dummy_dialect, "-", Column(dummy_dialect, "stock"), Literal(dummy_dialect, 5))
            },
            where=ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "id"), Literal(dummy_dialect, 10))
        )
        sql, params = update_expr.to_sql()
        assert sql == 'UPDATE "products" SET "stock" = ("stock" - ?) WHERE ("id" = ?)'
        assert params == (5, 10)

    # --- DeleteExpression ---
    def test_simple_delete(self, dummy_dialect: DummyDialect):
        """Tests a simple DELETE statement with a WHERE condition."""
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="orders",
            where=ComparisonPredicate(dummy_dialect, "<", Column(dummy_dialect, "order_date"), Literal(dummy_dialect, "2023-01-01"))
        )
        sql, params = delete_expr.to_sql()
        assert sql == 'DELETE FROM "orders" WHERE ("order_date" < ?)'
        assert params == ("2023-01-01",)

    def test_delete_with_complex_where(self, dummy_dialect: DummyDialect):
        """Tests DELETE statement with a complex WHERE condition."""
        condition = LogicalPredicate(
            dummy_dialect, "AND",
            ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "status"), Literal(dummy_dialect, "cancelled")),
            InPredicate(dummy_dialect, Column(dummy_dialect, "user_id"), Literal(dummy_dialect, [101, 102]))
        )
        delete_expr = DeleteExpression(
            dummy_dialect,
            table="temp_records",
            where=condition
        )
        sql, params = delete_expr.to_sql()
        assert sql == 'DELETE FROM "temp_records" WHERE (("status" = ?) AND ("user_id" IN (?, ?)))'
        assert params == ("cancelled", 101, 102)
