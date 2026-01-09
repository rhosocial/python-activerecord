# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_query_parts_join.py
import pytest
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    Column, ComparisonPredicate, TableExpression
)
from rhosocial.activerecord.backend.expression.query_parts import JoinExpression
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class TestSQLiteJoinExpression:
    """Tests for JoinExpression formatting in SQLite dialect."""

    def test_supported_inner_join(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that INNER JOIN is supported."""
        join_expr = JoinExpression(
            sqlite_dialect_3_8_0,
            left_table=TableExpression(sqlite_dialect_3_8_0, "users", alias="u"),
            right_table=TableExpression(sqlite_dialect_3_8_0, "orders", alias="o"),
            join_type="INNER JOIN",
            condition=Column(sqlite_dialect_3_8_0, "id", "u") == Column(sqlite_dialect_3_8_0, "user_id", "o")
        )
        sql, params = join_expr.to_sql()
        assert sql == '"users" AS "u" INNER JOIN "orders" AS "o" ON "u"."id" = "o"."user_id"'
        assert params == ()

    def test_supported_left_join(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that LEFT JOIN is supported."""
        join_expr = JoinExpression(
            sqlite_dialect_3_8_0,
            left_table=TableExpression(sqlite_dialect_3_8_0, "users", alias="u"),
            right_table=TableExpression(sqlite_dialect_3_8_0, "orders", alias="o"),
            join_type="LEFT JOIN",
            condition=Column(sqlite_dialect_3_8_0, "id", "u") == Column(sqlite_dialect_3_8_0, "user_id", "o")
        )
        sql, params = join_expr.to_sql()
        assert sql == '"users" AS "u" LEFT JOIN "orders" AS "o" ON "u"."id" = "o"."user_id"'
        assert params == ()

    def test_supported_left_outer_join(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that LEFT OUTER JOIN is supported."""
        join_expr = JoinExpression(
            sqlite_dialect_3_8_0,
            left_table=TableExpression(sqlite_dialect_3_8_0, "users", alias="u"),
            right_table=TableExpression(sqlite_dialect_3_8_0, "orders", alias="o"),
            join_type="LEFT OUTER JOIN",
            condition=Column(sqlite_dialect_3_8_0, "id", "u") == Column(sqlite_dialect_3_8_0, "user_id", "o")
        )
        sql, params = join_expr.to_sql()
        assert sql == '"users" AS "u" LEFT OUTER JOIN "orders" AS "o" ON "u"."id" = "o"."user_id"'
        assert params == ()

    def test_supported_cross_join(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that CROSS JOIN is supported."""
        join_expr = JoinExpression(
            sqlite_dialect_3_8_0,
            left_table=TableExpression(sqlite_dialect_3_8_0, "users"),
            right_table=TableExpression(sqlite_dialect_3_8_0, "departments"),
            join_type="CROSS JOIN"
        )
        sql, params = join_expr.to_sql()
        assert sql == '"users" CROSS JOIN "departments"'
        assert params == ()

    def test_supported_natural_inner_join(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test NATURAL INNER JOIN is supported in SQLite."""
        join_expr = JoinExpression(
            sqlite_dialect_3_8_0,
            left_table=TableExpression(sqlite_dialect_3_8_0, "table_a"),
            right_table=TableExpression(sqlite_dialect_3_8_0, "table_b"),
            join_type="INNER JOIN",
            natural=True
        )
        sql, params = join_expr.to_sql()
        assert sql == '"table_a" NATURAL INNER JOIN "table_b"'
        assert params == ()

    def test_supported_natural_left_join(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test NATURAL LEFT JOIN is supported in SQLite."""
        join_expr = JoinExpression(
            sqlite_dialect_3_8_0,
            left_table=TableExpression(sqlite_dialect_3_8_0, "table_a"),
            right_table=TableExpression(sqlite_dialect_3_8_0, "table_b"),
            join_type="LEFT JOIN",
            natural=True
        )
        sql, params = join_expr.to_sql()
        assert sql == '"table_a" NATURAL LEFT JOIN "table_b"'
        assert params == ()

    def test_unsupported_natural_right_join(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test NATURAL RIGHT JOIN raises UnsupportedFeatureError in SQLite."""
        join_expr = JoinExpression(
            sqlite_dialect_3_8_0,
            left_table=TableExpression(sqlite_dialect_3_8_0, "table_a"),
            right_table=TableExpression(sqlite_dialect_3_8_0, "table_b"),
            join_type="RIGHT JOIN",  # This should cause the error
            natural=True
        )
        with pytest.raises(UnsupportedFeatureError, match="does not support RIGHT JOIN"):
            join_expr.to_sql()

    def test_unsupported_natural_full_join(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test NATURAL FULL JOIN raises UnsupportedFeatureError in SQLite."""
        join_expr = JoinExpression(
            sqlite_dialect_3_8_0,
            left_table=TableExpression(sqlite_dialect_3_8_0, "table_a"),
            right_table=TableExpression(sqlite_dialect_3_8_0, "table_b"),
            join_type="FULL JOIN",  # This should cause the error
            natural=True
        )
        with pytest.raises(UnsupportedFeatureError, match="does not support FULL JOIN"):
            join_expr.to_sql()

    def test_unsupported_right_join(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that RIGHT JOIN raises UnsupportedFeatureError."""
        join_expr = JoinExpression(
            sqlite_dialect_3_8_0,
            left_table=TableExpression(sqlite_dialect_3_8_0, "users"),
            right_table=TableExpression(sqlite_dialect_3_8_0, "orders"),
            join_type="RIGHT JOIN",
            condition=Column(sqlite_dialect_3_8_0, "id", "users") == Column(sqlite_dialect_3_8_0, "user_id", "orders")
        )
        with pytest.raises(UnsupportedFeatureError, match="does not support RIGHT JOIN"):
            join_expr.to_sql()

    def test_unsupported_full_outer_join(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that FULL OUTER JOIN raises UnsupportedFeatureError."""
        join_expr = JoinExpression(
            sqlite_dialect_3_8_0,
            left_table=TableExpression(sqlite_dialect_3_8_0, "users"),
            right_table=TableExpression(sqlite_dialect_3_8_0, "orders"),
            join_type="FULL OUTER JOIN",
            condition=Column(sqlite_dialect_3_8_0, "id", "users") == Column(sqlite_dialect_3_8_0, "user_id", "orders")
        )
        with pytest.raises(UnsupportedFeatureError, match="does not support FULL JOIN"):
            join_expr.to_sql()

    def test_chained_join_with_unsupported_type(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that a chained join with an unsupported type fails."""
        base_join = JoinExpression(
            sqlite_dialect_3_8_0,
            left_table=TableExpression(sqlite_dialect_3_8_0, "users", alias="u"),
            right_table=TableExpression(sqlite_dialect_3_8_0, "orders", alias="o"),
            join_type="LEFT JOIN",
            condition=Column(sqlite_dialect_3_8_0, "id", "u") == Column(sqlite_dialect_3_8_0, "user_id", "o")
        )

        # Chain with an unsupported RIGHT JOIN
        chained_join_with_unsupported = base_join.right_join(
            right_table=TableExpression(sqlite_dialect_3_8_0, "products", alias="p"),
            condition=Column(sqlite_dialect_3_8_0, "product_id", "o") == Column(sqlite_dialect_3_8_0, "id", "p")
        )

        with pytest.raises(UnsupportedFeatureError, match="does not support RIGHT JOIN"):
            chained_join_with_unsupported.to_sql()
