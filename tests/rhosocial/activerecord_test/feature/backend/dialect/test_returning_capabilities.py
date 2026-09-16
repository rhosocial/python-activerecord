# tests/rhosocial/activerecord_test/feature/backend/dialect/test_returning_capabilities.py
"""Tests for the RETURNING capability switches, validation, and merge.

Covers:
- ``ReturningMixin`` merged into ``DMLMixin`` (and ``returning.py`` removed)
- ``supports_returning_clause()`` removed
- New generic capability switches and their defaults
- Expression-type coverage in ``format_returning_clause``
- ``UnsupportedFeatureError`` exposure when a requested feature is unsupported
- ``RETURNING ... INTO`` / ``OUTPUT ... INTO`` handling
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.aggregates import AggregateFunctionCall
from rhosocial.activerecord.backend.expression.core import (
    Column,
    FunctionCall,
    WildcardExpression,
)
from rhosocial.activerecord.backend.expression.statements import ReturningClause
from rhosocial.activerecord.backend.impl.dummy import DummyDialect

pytestmark = [pytest.mark.feature, pytest.mark.backend]


class NoExprDialect(DummyDialect):
    def supports_returning_expressions(self) -> bool:
        return False


class NoAliasDialect(DummyDialect):
    def supports_returning_alias(self) -> bool:
        return False


class NoWildcardDialect(DummyDialect):
    def supports_returning_wildcard(self) -> bool:
        return False


class NoOldNewDialect(DummyDialect):
    def supports_returning_old_new(self) -> bool:
        return False


class IntoDialect(DummyDialect):
    def supports_returning_into(self) -> bool:
        return True


class TestReturningMerge:
    """The former ReturningMixin methods now live on DMLMixin."""

    def test_dml_mixin_has_returning_methods(self):
        dialect = DummyDialect()
        for name in (
            "supports_returning_insert",
            "supports_returning_update",
            "supports_returning_delete",
            "format_returning_clause",
        ):
            assert hasattr(dialect, name), name

    def test_returning_mixin_module_removed(self):
        with pytest.raises(ModuleNotFoundError):
            from rhosocial.activerecord.backend.dialect.mixins.returning import (  # noqa: F401
                ReturningMixin,
            )

    def test_supports_returning_clause_removed(self):
        assert not hasattr(DummyDialect(), "supports_returning_clause")


class TestReturningSwitchDefaults:
    """New switch defaults on the optimistic DummyDialect."""

    def test_expressions_default_true(self):
        assert DummyDialect().supports_returning_expressions() is True

    def test_alias_default_true(self):
        assert DummyDialect().supports_returning_alias() is True

    def test_wildcard_default_true(self):
        assert DummyDialect().supports_returning_wildcard() is True

    def test_single_row_default_false(self):
        assert DummyDialect().supports_returning_single_row() is False

    def test_old_new_default_false(self):
        assert DummyDialect().supports_returning_old_new() is False

    def test_into_default_false(self):
        assert DummyDialect().supports_returning_into() is False


class TestReturningExpressionTypes:
    """Expressions render through the generic formatter."""

    def test_column_renders(self):
        dialect = DummyDialect()
        clause = ReturningClause(dialect, expressions=[Column(dialect, "id")])
        sql, params = dialect.format_returning_clause(clause)
        assert sql == 'RETURNING "id"'
        assert params == ()

    def test_wildcard_renders(self):
        dialect = DummyDialect()
        clause = ReturningClause(dialect, expressions=[WildcardExpression(dialect)])
        sql, params = dialect.format_returning_clause(clause)
        assert sql == "RETURNING *"

    def test_function_call_renders(self):
        dialect = DummyDialect()
        clause = ReturningClause(
            dialect, expressions=[FunctionCall(dialect, "UPPER", Column(dialect, "name"))]
        )
        sql, _ = dialect.format_returning_clause(clause)
        assert "UPPER" in sql

    def test_clause_alias_renders(self):
        dialect = DummyDialect()
        clause = ReturningClause(dialect, expressions=[Column(dialect, "id")], alias="result")
        sql, _ = dialect.format_returning_clause(clause)
        assert sql.endswith('AS "result"')

    def test_multiple_expressions_render(self):
        dialect = DummyDialect()
        clause = ReturningClause(
            dialect,
            expressions=[Column(dialect, "id"), Column(dialect, "name"), FunctionCall(dialect, "NOW")],
        )
        sql, _ = dialect.format_returning_clause(clause)
        assert sql.count(",") == 2


class TestReturningUnsupportedFeatures:
    """Requesting an unsupported feature raises UnsupportedFeatureError."""

    def test_expressions_raise_when_unsupported(self):
        dialect = NoExprDialect()
        dialect.strict_validation = False
        clause = ReturningClause(
            dialect,
            expressions=[FunctionCall(dialect, "UPPER", Column(dialect, "name"))],
        )
        with pytest.raises(UnsupportedFeatureError, match="expressions in RETURNING"):
            dialect.format_returning_clause(clause)

    def test_column_allowed_when_expressions_unsupported(self):
        dialect = NoExprDialect()
        clause = ReturningClause(dialect, expressions=[Column(dialect, "id")])
        sql, _ = dialect.format_returning_clause(clause)
        assert sql == 'RETURNING "id"'

    def test_alias_raises_when_unsupported(self):
        dialect = NoAliasDialect()
        clause = ReturningClause(dialect, expressions=[Column(dialect, "id")], alias="r")
        with pytest.raises(UnsupportedFeatureError, match="alias in RETURNING"):
            dialect.format_returning_clause(clause)

    def test_wildcard_raises_when_unsupported(self):
        dialect = NoWildcardDialect()
        clause = ReturningClause(dialect, expressions=[WildcardExpression(dialect)])
        with pytest.raises(UnsupportedFeatureError, match="wildcard in RETURNING"):
            dialect.format_returning_clause(clause)

    def test_old_new_raises_when_unsupported(self):
        dialect = NoOldNewDialect()
        clause = ReturningClause(dialect, expressions=[Column(dialect, "name", table="OLD")])
        with pytest.raises(UnsupportedFeatureError, match="OLD/NEW in RETURNING"):
            dialect.format_returning_clause(clause)

    def test_aggregate_rejected(self):
        dialect = DummyDialect()
        clause = ReturningClause(
            dialect, expressions=[AggregateFunctionCall(dialect, "COUNT", Column(dialect, "id"))]
        )
        with pytest.raises(UnsupportedFeatureError, match="aggregate/subquery in RETURNING"):
            dialect.format_returning_clause(clause)


class TestReturningInto:
    """RETURNING ... INTO handling."""

    def test_into_raises_when_unsupported(self):
        dialect = DummyDialect()
        clause = ReturningClause(dialect, expressions=[Column(dialect, "id")], output_into=":1")
        with pytest.raises(UnsupportedFeatureError, match=r"RETURNING \.\.\. INTO"):
            dialect.format_returning_clause(clause)

    def test_into_renders_when_supported(self):
        dialect = IntoDialect()
        clause = ReturningClause(
            dialect, expressions=[Column(dialect, "id")], output_into=":1"
        )
        sql, _ = dialect.format_returning_clause(clause)
        assert sql == 'RETURNING "id" INTO :1'
