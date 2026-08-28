# tests/rhosocial/activerecord_test/feature/query/joins/test_join_right_table_resolution.py
"""
Unit tests for JoinQueryMixin._resolve_right_table / AsyncJoinQueryMixin._resolve_right_table.

These tests lock in the alias non-contamination contract for join targets:
passing a TableExpression or JoinExpression with an alias must return a NEW
aliased copy and never mutate the caller's expression (regression tests for
the ``as_()`` copy semantics and the ``issubclass`` model-class guard).
"""

from types import SimpleNamespace

import pytest

from rhosocial.activerecord.backend.expression import TableExpression
from rhosocial.activerecord.backend.expression.query_parts import JoinExpression
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.query.join import JoinQueryMixin
from rhosocial.activerecord.query.async_join import AsyncJoinQueryMixin


@pytest.fixture
def dummy_dialect():
    """Provides a DummyDialect instance that supports all features."""
    return DummyDialect()


def _make_join_expression(dialect: DummyDialect) -> JoinExpression:
    """Build a minimal valid JoinExpression for alias tests."""
    return JoinExpression(
        dialect,
        left_table=TableExpression(dialect, "users"),
        right_table=TableExpression(dialect, "items"),
        join_type="INNER JOIN",
        using=["id"],
    )


class _SyncJoinQueryStub(JoinQueryMixin):
    """Minimal query double exposing only what JoinQueryMixin needs."""

    def __init__(self, dialect: DummyDialect):
        self._dialect = dialect
        self.join_clause = None

    def backend(self):
        return SimpleNamespace(dialect=self._dialect)


class _AsyncJoinQueryStub(AsyncJoinQueryMixin):
    """Minimal async query double exposing only what AsyncJoinQueryMixin needs."""

    def __init__(self, dialect: DummyDialect):
        self._dialect = dialect
        self.join_clause = None

    def backend(self):
        return SimpleNamespace(dialect=self._dialect)


class TestSyncResolveRightTable:
    """Sync _resolve_right_table alias resolution tests."""

    def test_table_expression_with_alias_not_mutated(self, dummy_dialect: DummyDialect):
        table = TableExpression(dummy_dialect, "orders")
        query = _SyncJoinQueryStub(dummy_dialect)

        resolved = query._resolve_right_table(table, alias="o")

        assert resolved is not table
        assert isinstance(resolved, TableExpression)
        assert resolved.alias == "o"
        assert table.alias is None
        assert resolved.to_sql()[0] == '"orders" AS "o"'
        assert table.to_sql()[0] == '"orders"'

    def test_same_table_reused_with_two_aliases(self, dummy_dialect: DummyDialect):
        """Self-join style reuse: one TableExpression, two independent aliases."""
        table = TableExpression(dummy_dialect, "orders")
        query = _SyncJoinQueryStub(dummy_dialect)

        first = query._resolve_right_table(table, alias="o1")
        second = query._resolve_right_table(table, alias="o2")

        assert first is not second
        assert first.alias == "o1"
        assert second.alias == "o2"
        assert table.alias is None

    def test_table_expression_without_alias_is_passthrough(self, dummy_dialect: DummyDialect):
        table = TableExpression(dummy_dialect, "orders")
        query = _SyncJoinQueryStub(dummy_dialect)

        resolved = query._resolve_right_table(table, alias=None)

        assert resolved is table

    def test_join_expression_with_alias_not_mutated(self, dummy_dialect: DummyDialect):
        join_expr = _make_join_expression(dummy_dialect)
        query = _SyncJoinQueryStub(dummy_dialect)

        resolved = query._resolve_right_table(join_expr, alias="jx")

        assert resolved is not join_expr
        assert isinstance(resolved, JoinExpression)
        assert resolved.alias == "jx"
        assert join_expr.alias is None
        assert resolved.to_sql()[0].endswith('AS "jx"')

    def test_string_target_with_alias(self, dummy_dialect: DummyDialect):
        query = _SyncJoinQueryStub(dummy_dialect)

        resolved = query._resolve_right_table("orders", alias="o")

        assert isinstance(resolved, TableExpression)
        assert resolved.alias == "o"

    def test_unsupported_type_raises_type_error(self, dummy_dialect: DummyDialect):
        query = _SyncJoinQueryStub(dummy_dialect)

        with pytest.raises(TypeError):
            query._resolve_right_table(42, alias="o")  # type: ignore[arg-type]


class TestAsyncResolveRightTable:
    """Async _resolve_right_table alias resolution tests."""

    def test_table_expression_with_alias_not_mutated(self, dummy_dialect: DummyDialect):
        table = TableExpression(dummy_dialect, "orders")
        query = _AsyncJoinQueryStub(dummy_dialect)

        resolved = query._resolve_right_table(table, alias="o")

        assert resolved is not table
        assert isinstance(resolved, TableExpression)
        assert resolved.alias == "o"
        assert table.alias is None
        assert resolved.to_sql()[0] == '"orders" AS "o"'
        assert table.to_sql()[0] == '"orders"'

    def test_same_table_reused_with_two_aliases(self, dummy_dialect: DummyDialect):
        table = TableExpression(dummy_dialect, "orders")
        query = _AsyncJoinQueryStub(dummy_dialect)

        first = query._resolve_right_table(table, alias="o1")
        second = query._resolve_right_table(table, alias="o2")

        assert first is not second
        assert first.alias == "o1"
        assert second.alias == "o2"
        assert table.alias is None

    def test_join_expression_with_alias_not_mutated(self, dummy_dialect: DummyDialect):
        join_expr = _make_join_expression(dummy_dialect)
        query = _AsyncJoinQueryStub(dummy_dialect)

        resolved = query._resolve_right_table(join_expr, alias="jx")

        assert resolved is not join_expr
        assert isinstance(resolved, JoinExpression)
        assert resolved.alias == "jx"
        assert join_expr.alias is None

    def test_string_target_with_alias(self, dummy_dialect: DummyDialect):
        query = _AsyncJoinQueryStub(dummy_dialect)

        resolved = query._resolve_right_table("orders", alias="o")

        assert isinstance(resolved, TableExpression)
        assert resolved.alias == "o"

    def test_unsupported_type_raises_type_error(self, dummy_dialect: DummyDialect):
        query = _AsyncJoinQueryStub(dummy_dialect)

        with pytest.raises(TypeError):
            query._resolve_right_table(42, alias="o")  # type: ignore[arg-type]
