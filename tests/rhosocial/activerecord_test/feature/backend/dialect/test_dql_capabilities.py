# tests/rhosocial/activerecord_test/feature/backend/dialect/test_dql_capabilities.py
"""Tests for DQL capability switches, silent-skip fixes and expression gaps.

Covers:
- FETCH FIRST ... WITH TIES (G01)
- ORDER BY ... NULLS FIRST/LAST (G02)
- typed ForUpdateClause LockStrength (G03-G06)
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    Column,
    ForUpdateClause,
    LimitOffsetClause,
    LockStrength,
    OrderByClause,
    OrderByItem,
)
from rhosocial.activerecord.backend.impl.dummy.backend import DummyDialect

pytestmark = [pytest.mark.feature, pytest.mark.backend]


class NoFetchWithTies(DummyDialect):
    def supports_fetch_with_ties(self) -> bool:
        return False


class NoNullsFirstLast(DummyDialect):
    def supports_nulls_first_last(self) -> bool:
        return False


class NoShare(DummyDialect):
    def supports_for_share(self) -> bool:
        return False


class TestFetchWithTies:
    """G01: FETCH FIRST ... WITH TIES."""

    def test_capability_defaults(self):
        assert DummyDialect().supports_fetch_with_ties() is True

    def test_renders_when_supported(self):
        dialect = DummyDialect()
        clause = LimitOffsetClause(dialect, limit=10, with_ties=True)
        sql, params = dialect.format_limit_offset_clause(clause)
        assert sql == "FETCH FIRST ? ROWS WITH TIES"
        assert params == (10,)

    def test_raises_when_unsupported(self):
        dialect = NoFetchWithTies()
        clause = LimitOffsetClause(dialect, limit=10, with_ties=True)
        with pytest.raises(UnsupportedFeatureError, match="WITH TIES"):
            dialect.format_limit_offset_clause(clause)

    def test_without_ties_uses_limit_syntax(self):
        dialect = DummyDialect()
        clause = LimitOffsetClause(dialect, limit=10)
        sql, _ = dialect.format_limit_offset_clause(clause)
        assert sql == "LIMIT ?"


class TestNullsFirstLast:
    """G02: ORDER BY ... NULLS FIRST/LAST."""

    def test_capability_defaults(self):
        assert DummyDialect().supports_nulls_first_last() is True

    def test_nulls_first_renders(self):
        dialect = DummyDialect()
        clause = OrderByClause(
            dialect,
            expressions=[OrderByItem(dialect, Column(dialect, "name"), nulls="first")],
        )
        sql, _ = dialect.format_order_by_clause(clause)
        assert sql == 'ORDER BY "name" NULLS FIRST'

    def test_direction_and_nulls_last_render(self):
        dialect = DummyDialect()
        clause = OrderByClause(
            dialect,
            expressions=[OrderByItem(dialect, Column(dialect, "name"), "DESC", nulls="last")],
        )
        sql, _ = dialect.format_order_by_clause(clause)
        assert sql == 'ORDER BY "name" DESC NULLS LAST'

    def test_raises_when_unsupported(self):
        dialect = NoNullsFirstLast()
        clause = OrderByClause(
            dialect,
            expressions=[OrderByItem(dialect, Column(dialect, "name"), nulls="first")],
        )
        with pytest.raises(UnsupportedFeatureError, match="NULLS FIRST/LAST"):
            dialect.format_order_by_clause(clause)

    def test_invalid_nulls_word(self):
        dialect = DummyDialect()
        with pytest.raises(ValueError):
            OrderByItem(dialect, Column(dialect, "x"), nulls="sideways")

    def test_invalid_direction(self):
        dialect = DummyDialect()
        with pytest.raises(ValueError):
            OrderByItem(dialect, Column(dialect, "x"), "SIDEWAYS")


class TestForUpdateStrength:
    """G03-G06: typed ForUpdateClause.strength with core LockStrength."""

    def test_default_strength_is_update(self):
        assert ForUpdateClause(DummyDialect()).strength == LockStrength.UPDATE

    @pytest.mark.parametrize(
        "strength,expected",
        [
            (LockStrength.UPDATE, "FOR UPDATE"),
            (LockStrength.NO_KEY_UPDATE, "FOR NO KEY UPDATE"),
            (LockStrength.SHARE, "FOR SHARE"),
            (LockStrength.KEY_SHARE, "FOR KEY SHARE"),
            (LockStrength.LOCK_IN_SHARE_MODE, "LOCK IN SHARE MODE"),
        ],
    )
    def test_renders_each_strength(self, strength, expected):
        dialect = DummyDialect()
        sql, _ = ForUpdateClause(dialect, strength=strength).to_sql()
        assert sql == expected

    def test_share_raises_when_unsupported(self):
        dialect = NoShare()
        with pytest.raises(UnsupportedFeatureError, match="FOR SHARE"):
            ForUpdateClause(dialect, strength=LockStrength.SHARE).to_sql()

    def test_skip_locked_raises_when_unsupported(self):
        class NoSkip(DummyDialect):
            def supports_for_update_skip_locked(self) -> bool:
                return False

        dialect = NoSkip()
        with pytest.raises(UnsupportedFeatureError, match="SKIP LOCKED"):
            ForUpdateClause(dialect, skip_locked=True).to_sql()
