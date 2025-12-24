# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_truncate.py
import pytest
from rhosocial.activerecord.backend.expression import (
    TruncateExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestTruncateStatements:
    """Tests for TRUNCATE TABLE statements with various configurations."""

    def test_basic_truncate(self, dummy_dialect: DummyDialect):
        """Tests basic TRUNCATE TABLE statement."""
        truncate_expr = TruncateExpression(
            dummy_dialect,
            table_name="users"
        )
        sql, params = truncate_expr.to_sql()

        assert 'TRUNCATE TABLE "users"' in sql
        assert params == ()

    def test_truncate_with_restart_identity(self, dummy_dialect: DummyDialect):
        """Tests TRUNCATE TABLE with RESTART IDENTITY option."""
        truncate_expr = TruncateExpression(
            dummy_dialect,
            table_name="orders",
            restart_identity=True
        )
        sql, params = truncate_expr.to_sql()

        assert 'TRUNCATE TABLE "orders"' in sql
        assert 'RESTART IDENTITY' in sql
        assert params == ()

    def test_truncate_with_cascade(self, dummy_dialect: DummyDialect):
        """Tests TRUNCATE TABLE with CASCADE option."""
        truncate_expr = TruncateExpression(
            dummy_dialect,
            table_name="products",
            cascade=True
        )
        sql, params = truncate_expr.to_sql()

        assert 'TRUNCATE TABLE "products"' in sql
        assert 'CASCADE' in sql
        assert params == ()

    def test_truncate_with_all_options(self, dummy_dialect: DummyDialect):
        """Tests TRUNCATE TABLE with both RESTART IDENTITY and CASCADE options."""
        truncate_expr = TruncateExpression(
            dummy_dialect,
            table_name="inventory",
            restart_identity=True,
            cascade=True
        )
        sql, params = truncate_expr.to_sql()

        assert 'TRUNCATE TABLE "inventory"' in sql
        assert 'RESTART IDENTITY' in sql
        assert 'CASCADE' in sql
        assert params == ()

    def test_truncate_with_dialect_options(self, dummy_dialect: DummyDialect):
        """Tests TRUNCATE TABLE with dialect-specific options."""
        truncate_expr = TruncateExpression(
            dummy_dialect,
            table_name="logs",
            dialect_options={"custom_option": "value"}
        )
        sql, params = truncate_expr.to_sql()

        assert 'TRUNCATE TABLE "logs"' in sql
        assert params == ()