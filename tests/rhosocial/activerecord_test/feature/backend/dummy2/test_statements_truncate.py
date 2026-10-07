# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_truncate.py
from rhosocial.activerecord.backend.expression import TruncateExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.objects import Table


class TestTruncateStatements:
    """Tests for TRUNCATE TABLE statements with various configurations."""

    def test_basic_truncate(self, dummy_dialect: DummyDialect):
        """Tests basic TRUNCATE TABLE statement."""
        truncate_expr = TruncateExpression(dummy_dialect, table=Table(dummy_dialect, "users"))
        sql, params = truncate_expr.to_sql()

        assert 'TRUNCATE TABLE "users"' in sql
        assert params == ()

    def test_truncate_with_restart_identity(self, dummy_dialect: DummyDialect):
        """Tests TRUNCATE TABLE with RESTART IDENTITY option."""
        truncate_expr = TruncateExpression(dummy_dialect, table=Table(dummy_dialect, "orders"), restart_identity=True)
        sql, params = truncate_expr.to_sql()

        assert 'TRUNCATE TABLE "orders"' in sql
        assert "RESTART IDENTITY" in sql
        assert params == ()

    def test_truncate_with_cascade(self, dummy_dialect: DummyDialect):
        """Tests TRUNCATE TABLE with CASCADE option."""
        truncate_expr = TruncateExpression(dummy_dialect, table=Table(dummy_dialect, "products"), cascade=True)
        sql, params = truncate_expr.to_sql()

        assert 'TRUNCATE TABLE "products"' in sql
        assert "CASCADE" in sql
        assert params == ()

    def test_truncate_with_all_options(self, dummy_dialect: DummyDialect):
        """Tests TRUNCATE TABLE with both RESTART IDENTITY and CASCADE options."""
        truncate_expr = TruncateExpression(dummy_dialect, table=Table(dummy_dialect, "inventory"), restart_identity=True, cascade=True)
        sql, params = truncate_expr.to_sql()

        assert 'TRUNCATE TABLE "inventory"' in sql
        assert "RESTART IDENTITY" in sql
        assert "CASCADE" in sql
        assert params == ()

    def test_truncate_has_no_dialect_options(self, dummy_dialect: DummyDialect):
        """The generic TRUNCATE expression carries no dialect_options bag."""
        truncate_expr = TruncateExpression(dummy_dialect, table=Table(dummy_dialect, "logs"))
        assert not hasattr(truncate_expr, "dialect_options")
        sql, params = truncate_expr.to_sql()

        assert 'TRUNCATE TABLE "logs"' in sql
        assert params == ()
