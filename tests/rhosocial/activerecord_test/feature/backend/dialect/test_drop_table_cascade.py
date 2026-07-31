# tests/rhosocial/activerecord_test/feature/backend/dialect/test_drop_table_cascade.py
"""
Tests for DROP TABLE ... CASCADE/RESTRICT capability switches in the generic
TableMixin helper.

Covers:
- TableMixin default capability switch values (True/True optimistic).
- Gating: cascade=True/False raising UnsupportedFeatureError when unsupported.
- Gating: cascade=None (omit) is always allowed, even on dialects that reject
  the keywords.
- Real SQLite dialect (False/False) confirms gating does not depend on subclass
  of DummyDialect.
- Serialization round-trip of a DropTableExpression with cascade=True.
"""

import pytest

from rhosocial.activerecord.backend.dialect import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import DropTableExpression
from rhosocial.activerecord.backend.expression.serialization import serialize, deserialize
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class NoCascadeDialect(DummyDialect):
    """Dialect that does NOT accept the CASCADE/RESTRICT keywords on DROP TABLE.

    Models SQLite/SQL Server/Firebird behavior: both switches False, and the
    generic TableMixin helper must raise rather than emit an invalid token.
    """

    def supports_drop_table_cascade(self) -> bool:
        return False

    def supports_drop_table_restrict(self) -> bool:
        return False


class TestDropTableCascadeCapabilitySwitches:
    """Capability switch defaults and gating."""

    def test_table_mixin_default_switches(self):
        """TableMixin defaults: both CASCADE and RESTRICT supported (optimistic)."""
        dialect = DummyDialect()
        assert dialect.supports_drop_table_cascade() is True
        assert dialect.supports_drop_table_restrict() is True

    def test_dummy_dialect_renders_cascade(self):
        """DummyDialect renders the standard CASCADE token when supported."""
        dialect = DummyDialect()
        expr = DropTableExpression(dialect, table="users", cascade=True)
        sql, params = expr.to_sql()
        assert sql.endswith(" CASCADE")
        assert "RESTRICT" not in sql
        assert params == ()

    def test_dummy_dialect_renders_restrict(self):
        """DummyDialect renders the standard RESTRICT token when supported."""
        dialect = DummyDialect()
        expr = DropTableExpression(dialect, table="users", cascade=False)
        sql, params = expr.to_sql()
        assert sql.endswith(" RESTRICT")
        assert "CASCADE" not in sql
        assert params == ()

    def test_no_cascade_dialect_rejects_cascade(self):
        """cascade=True raises UnsupportedFeatureError when unsupported."""
        dialect = NoCascadeDialect()
        expr = DropTableExpression(dialect, table="users", cascade=True)
        with pytest.raises(UnsupportedFeatureError, match="DROP TABLE ... CASCADE"):
            expr.to_sql()

    def test_no_cascade_dialect_rejects_restrict(self):
        """cascade=False raises UnsupportedFeatureError when unsupported."""
        dialect = NoCascadeDialect()
        expr = DropTableExpression(dialect, table="users", cascade=False)
        with pytest.raises(UnsupportedFeatureError, match="DROP TABLE ... RESTRICT"):
            expr.to_sql()

    def test_cascade_none_always_allowed(self):
        """cascade=None is always allowed, even on dialects that reject keywords."""
        dialect = NoCascadeDialect()
        expr = DropTableExpression(dialect, table="users", cascade=None)
        sql, params = expr.to_sql()
        assert "CASCADE" not in sql
        assert "RESTRICT" not in sql
        assert params == ()

    def test_real_sqlite_dialect_rejects_cascade(self):
        """The real SQLite dialect (False/False) confirms gating without subclassing.

        Regression for the pre-fix behavior where the generic helper would emit
        ``DROP TABLE t CASCADE`` which SQLite treats as a syntax error.
        """
        dialect = SQLiteDialect()
        assert dialect.supports_drop_table_cascade() is False
        assert dialect.supports_drop_table_restrict() is False
        expr = DropTableExpression(dialect, table="users", cascade=True)
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_real_sqlite_dialect_plain_drop_still_works(self):
        """A plain DROP TABLE on SQLite (cascade=None) renders normally."""
        dialect = SQLiteDialect()
        expr = DropTableExpression(dialect, table="users", if_exists=True)
        sql, params = expr.to_sql()
        assert sql.startswith("DROP TABLE IF EXISTS")
        assert params == ()


class TestDropTableCascadeSerialization:
    """Serialization round-trip for a DropTableExpression with cascade set."""

    def test_cascade_true_serialization_roundtrip(self):
        dialect = DummyDialect()
        expr = DropTableExpression(dialect, table="users", cascade=True)

        expected_sql, expected_params = expr.to_sql()

        spec = serialize(expr)
        assert spec["params"]["cascade"] is True

        restored = deserialize(spec, dialect)
        sql, params = restored.to_sql()

        assert sql == expected_sql
        assert params == expected_params

    def test_cascade_false_serialization_roundtrip(self):
        dialect = DummyDialect()
        expr = DropTableExpression(dialect, table="users", cascade=False)

        expected_sql, expected_params = expr.to_sql()

        spec = serialize(expr)
        assert spec["params"]["cascade"] is False

        restored = deserialize(spec, dialect)
        sql, params = restored.to_sql()

        assert sql == expected_sql
        assert params == expected_params
