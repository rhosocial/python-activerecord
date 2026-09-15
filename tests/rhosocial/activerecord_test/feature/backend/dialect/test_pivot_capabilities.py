# tests/rhosocial/activerecord_test/feature/backend/dialect/test_pivot_capabilities.py
"""Tests for the core PIVOT / UNPIVOT expressions and capability switches."""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import PivotExpression, UnpivotExpression
from rhosocial.activerecord.backend.impl.dummy import DummyDialect

pytestmark = [pytest.mark.feature, pytest.mark.backend]


class NoPivotDialect(DummyDialect):
    def supports_pivot(self) -> bool:
        return False

    def supports_unpivot(self) -> bool:
        return False


class TestPivot:
    def test_switch_defaults(self):
        assert DummyDialect().supports_pivot() is True
        assert DummyDialect().supports_unpivot() is True

    def test_renders(self):
        dialect = DummyDialect()
        expr = PivotExpression(dialect, "SUM", "amount", "month", ["Jan", "Feb"], alias="p")
        sql, _ = expr.to_sql()
        assert sql == "PIVOT (SUM(\"amount\") FOR \"month\" IN ('Jan', 'Feb')) \"p\""

    def test_default_renders(self):
        dialect = DummyDialect()
        expr = PivotExpression(dialect, "SUM", "amount", "month", ["Jan"], default=0)
        sql, _ = expr.to_sql()
        assert sql.endswith("DEFAULT 0)")

    def test_raises_when_unsupported(self):
        dialect = NoPivotDialect()
        expr = PivotExpression(dialect, "SUM", "amount", "month", ["Jan"])
        with pytest.raises(UnsupportedFeatureError, match="PIVOT"):
            expr.to_sql()


class TestUnpivot:
    def test_renders_exclude_nulls(self):
        dialect = DummyDialect()
        expr = UnpivotExpression(dialect, "val", "col", ["a", "b"])
        sql, _ = expr.to_sql()
        assert sql == 'UNPIVOT EXCLUDE NULLS ("val" FOR "col" IN ("a", "b"))'

    def test_renders_include_nulls_with_alias(self):
        dialect = DummyDialect()
        expr = UnpivotExpression(dialect, "val", "col", ["a", "b"], include_nulls=True, alias="u")
        sql, _ = expr.to_sql()
        assert sql == 'UNPIVOT INCLUDE NULLS ("val" FOR "col" IN ("a", "b")) "u"'

    def test_raises_when_unsupported(self):
        dialect = NoPivotDialect()
        expr = UnpivotExpression(dialect, "val", "col", ["a"])
        with pytest.raises(UnsupportedFeatureError, match="UNPIVOT"):
            expr.to_sql()
