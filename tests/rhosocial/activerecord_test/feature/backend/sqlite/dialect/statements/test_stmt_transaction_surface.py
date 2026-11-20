# tests/rhosocial/activerecord_test/feature/backend/sqlite/dialect/statements/test_stmt_transaction_surface.py
"""SQLite's BEGIN TRANSACTION surface: what it has and what it refuses.

SQLite has no transaction mode beyond BEGIN [DEFERRED|IMMEDIATE|EXCLUSIVE].
Everything the standard grammar offers on top of that -- DEFERRABLE, WAIT,
READ ONLY -- is refused by name rather than dropped, so a caller never believes
a mode took effect when it did not.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.errors import UnsupportedTransactionModeError
from rhosocial.activerecord.backend.expression.transaction import BeginTransactionStatement
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode

DIALECT = SQLiteDialect(version=(3, 53, 0))


def test_transaction_capability_matrix():
    assert DIALECT.supports_transaction_mode() is False
    assert DIALECT.supports_isolation_level_in_begin() is False
    assert DIALECT.supports_read_only_transaction() is False
    assert DIALECT.supports_deferrable_transaction() is False
    assert DIALECT.supports_transaction_wait() is False
    assert DIALECT.supports_savepoint() is True


@pytest.mark.parametrize("keyword", ["deferrable", "not_deferrable"])
def test_deferrable_is_refused_by_name(keyword):
    with pytest.raises(UnsupportedFeatureError, match="DEFERRABLE"):
        BeginTransactionStatement(DIALECT, **{keyword: True}).to_sql()


@pytest.mark.parametrize("keyword,feature", [("wait", "WAIT"), ("no_wait", "NO WAIT")])
def test_wait_clauses_are_refused_by_name(keyword, feature):
    with pytest.raises(UnsupportedFeatureError, match=feature):
        BeginTransactionStatement(DIALECT, **{keyword: True}).to_sql()


def test_read_only_has_its_own_refusal():
    with pytest.raises(UnsupportedTransactionModeError, match="READ ONLY"):
        BeginTransactionStatement(DIALECT, mode=TransactionMode.READ_ONLY).to_sql()


@pytest.mark.parametrize("begin_type", ["deferred", "immediate", "exclusive"])
def test_begin_type_is_spelled_verbatim(begin_type):
    sql, params = BeginTransactionStatement(DIALECT, begin_type=begin_type).to_sql()
    assert sql == f"BEGIN {begin_type.upper()} TRANSACTION"
    assert params == ()


def test_unknown_begin_type_is_refused():
    with pytest.raises(ValueError, match="Invalid SQLite begin type"):
        BeginTransactionStatement(DIALECT, begin_type="serializable").to_sql()


def test_isolation_level_selects_deferred_or_immediate():
    deferred = BeginTransactionStatement(DIALECT, isolation_level=IsolationLevel.READ_UNCOMMITTED)
    assert deferred.to_sql() == ("BEGIN DEFERRED TRANSACTION", ())

    immediate = BeginTransactionStatement(DIALECT, isolation_level=IsolationLevel.SERIALIZABLE)
    assert immediate.to_sql() == ("BEGIN IMMEDIATE TRANSACTION", ())
