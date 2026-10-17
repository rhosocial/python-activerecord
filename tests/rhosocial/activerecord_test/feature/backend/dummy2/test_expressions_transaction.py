# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expressions_transaction.py
"""Tests for transaction expression classes."""

import pytest
from rhosocial.activerecord.backend.expression.transaction import (
    BeginTransactionStatement,
    CommitStatement,
    RollbackStatement,
    SavepointStatement,
    ReleaseSavepointStatement,
    SetTransactionExpression,
)
from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.errors import UnsupportedTransactionModeError
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class TestBeginTransactionExpression:
    """Tests for BeginTransactionStatement."""

    def test_basic_begin(self, dummy_dialect: DummyDialect):
        """Test basic BEGIN statement."""
        expr = BeginTransactionStatement(dummy_dialect)
        sql, params = expr.to_sql()
        assert sql == "BEGIN"
        assert params == ()

    def test_begin_with_isolation_level(self, dummy_dialect: DummyDialect):
        """Test BEGIN with isolation level."""
        expr = BeginTransactionStatement(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE)
        sql, params = expr.to_sql()
        assert "ISOLATION LEVEL SERIALIZABLE" in sql
        assert params == ()

    def test_begin_read_only(self, dummy_dialect: DummyDialect):
        """Test BEGIN READ ONLY."""
        expr = BeginTransactionStatement(dummy_dialect)
        expr.read_only()
        sql, params = expr.to_sql()
        assert "READ ONLY" in sql
        assert params == ()

    def test_begin_read_write(self, dummy_dialect: DummyDialect):
        """Test BEGIN READ WRITE."""
        expr = BeginTransactionStatement(dummy_dialect)
        expr.read_write()
        sql, params = expr.to_sql()
        assert "READ WRITE" in sql
        assert params == ()

    def test_begin_with_isolation_and_mode(self, dummy_dialect: DummyDialect):
        """Test BEGIN with isolation level and mode."""
        expr = BeginTransactionStatement(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.REPEATABLE_READ).read_only()
        sql, params = expr.to_sql()
        assert "ISOLATION LEVEL REPEATABLE READ" in sql
        assert "READ ONLY" in sql
        assert params == ()

    def test_begin_deferrable(self, dummy_dialect: DummyDialect):
        """Test BEGIN with DEFERRABLE."""
        expr = BeginTransactionStatement(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE).with_deferrable()
        sql, params = expr.to_sql()
        assert "ISOLATION LEVEL SERIALIZABLE" in sql
        assert "DEFERRABLE" in sql
        assert params == ()

    def test_begin_not_deferrable(self, dummy_dialect: DummyDialect):
        """Test BEGIN with NOT DEFERRABLE."""
        expr = BeginTransactionStatement(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE).with_not_deferrable()
        sql, params = expr.to_sql()
        assert "NOT DEFERRABLE" in sql
        assert params == ()

    def test_begin_wait(self, dummy_dialect: DummyDialect):
        """Test BEGIN with the WAIT lock-wait spelling."""
        expr = BeginTransactionStatement(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE).with_wait()
        sql, params = expr.to_sql()
        assert "ISOLATION LEVEL SERIALIZABLE" in sql
        assert sql.endswith("WAIT")
        assert "NO WAIT" not in sql
        assert params == ()

    def test_begin_no_wait(self, dummy_dialect: DummyDialect):
        """Test BEGIN with the NO WAIT lock-wait spelling."""
        expr = BeginTransactionStatement(dummy_dialect)
        expr.with_no_wait()
        sql, params = expr.to_sql()
        assert sql == "BEGIN NO WAIT"
        assert params == ()

    def test_begin_wait_constructor_kwarg(self, dummy_dialect: DummyDialect):
        """The pair is also settable at construction."""
        assert BeginTransactionStatement(dummy_dialect, wait=True).to_sql()[0] == "BEGIN WAIT"

    def test_begin_wait_pair_is_mutually_exclusive(self, dummy_dialect: DummyDialect):
        with pytest.raises(ValueError, match="wait and no_wait are mutually exclusive"):
            BeginTransactionStatement(dummy_dialect, wait=True, no_wait=True)

    def test_begin_deferrable_without_serializable_is_rendered(self, dummy_dialect: DummyDialect):
        """[NOT] DEFERRABLE is an independent transaction mode, not dropped.

        It is only *effective* for SERIALIZABLE transactions, but the grammar
        accepts it alone, so the request must be carried through rather than
        silently ignored.
        """
        expr = BeginTransactionStatement(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.READ_COMMITTED).with_deferrable()
        sql, params = expr.to_sql()
        assert "DEFERRABLE" in sql
        assert "READ COMMITTED" in sql

    def test_method_chaining(self, dummy_dialect: DummyDialect):
        """Test method chaining returns self."""
        expr = BeginTransactionStatement(dummy_dialect)
        result = expr.with_isolation_level(IsolationLevel.SERIALIZABLE)
        assert result is expr
        result = expr.read_only()
        assert result is expr
        result = expr.with_deferrable()
        assert result is expr

    def test_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns correct dictionary."""
        expr = BeginTransactionStatement(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE).read_only().with_deferrable()
        params = expr.get_params()
        assert params["isolation_level"] == IsolationLevel.SERIALIZABLE
        assert params["mode"] == TransactionMode.READ_ONLY
        assert params["deferrable"]

    def test_sqlite_read_only_raises_error(self):
        """Test SQLite READ ONLY raises UnsupportedTransactionModeError."""
        sqlite_dialect = SQLiteDialect()
        expr = BeginTransactionStatement(sqlite_dialect)
        expr.read_only()
        with pytest.raises(UnsupportedTransactionModeError) as exc_info:
            expr.to_sql()
        assert "READ ONLY" in str(exc_info.value)

    def test_sqlite_begin_serializable(self):
        """Test SQLite BEGIN with SERIALIZABLE isolation."""
        sqlite_dialect = SQLiteDialect()
        expr = BeginTransactionStatement(sqlite_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE)
        sql, params = expr.to_sql()
        assert sql == "BEGIN IMMEDIATE TRANSACTION"
        assert params == ()

    def test_sqlite_begin_read_uncommitted(self):
        """Test SQLite BEGIN with READ UNCOMMITTED isolation."""
        sqlite_dialect = SQLiteDialect()
        expr = BeginTransactionStatement(sqlite_dialect)
        expr.with_isolation_level(IsolationLevel.READ_UNCOMMITTED)
        sql, params = expr.to_sql()
        assert sql == "BEGIN DEFERRED TRANSACTION"
        assert params == ()


class TestCommitTransactionExpression:
    """Tests for CommitStatement."""

    def test_commit(self, dummy_dialect: DummyDialect):
        """Test COMMIT statement."""
        expr = CommitStatement(dummy_dialect)
        sql, params = expr.to_sql()
        assert sql == "COMMIT"
        assert params == ()

    def test_commit_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns empty dict."""
        expr = CommitStatement(dummy_dialect)
        params = expr.get_params()
        assert params == {}


class TestRollbackTransactionExpression:
    """Tests for RollbackStatement."""

    def test_rollback(self, dummy_dialect: DummyDialect):
        """Test ROLLBACK statement."""
        expr = RollbackStatement(dummy_dialect)
        sql, params = expr.to_sql()
        assert sql == "ROLLBACK"
        assert params == ()

    def test_rollback_to_savepoint(self, dummy_dialect: DummyDialect):
        """Test ROLLBACK TO SAVEPOINT statement."""
        expr = RollbackStatement(dummy_dialect)
        expr.to_savepoint("my_savepoint")
        sql, params = expr.to_sql()
        assert "ROLLBACK" in sql
        assert "SAVEPOINT" in sql
        assert params == ()

    def test_rollback_get_params_with_savepoint(self, dummy_dialect: DummyDialect):
        """Test get_params returns savepoint name."""
        expr = RollbackStatement(dummy_dialect)
        expr.to_savepoint("test_sp")
        params = expr.get_params()
        assert params == {"savepoint": "test_sp"}

    def test_rollback_get_params_empty(self, dummy_dialect: DummyDialect):
        """Test get_params returns savepoint=None when none set."""
        expr = RollbackStatement(dummy_dialect)
        params = expr.get_params()
        assert params == {"savepoint": None}

    def test_rollback_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns savepoint=None when none set."""
        expr = RollbackStatement(dummy_dialect)
        params = expr.get_params()
        assert params == {"savepoint": None}


class TestSavepointExpression:
    """Tests for SavepointStatement."""

    def test_savepoint(self, dummy_dialect: DummyDialect):
        """Test SAVEPOINT statement."""
        expr = SavepointStatement(dummy_dialect, "my_savepoint")
        sql, params = expr.to_sql()
        assert "SAVEPOINT" in sql
        assert "my_savepoint" in sql
        assert params == ()

    def test_savepoint_name_property(self, dummy_dialect: DummyDialect):
        """Test name property."""
        expr = SavepointStatement(dummy_dialect, "test_sp")
        assert expr.name == "test_sp"

    def test_savepoint_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns name."""
        expr = SavepointStatement(dummy_dialect, "my_sp")
        params = expr.get_params()
        assert params == {"name": "my_sp"}


class TestReleaseSavepointExpression:
    """Tests for ReleaseSavepointStatement."""

    def test_release_savepoint(self, dummy_dialect: DummyDialect):
        """Test RELEASE SAVEPOINT statement."""
        expr = ReleaseSavepointStatement(dummy_dialect, "my_savepoint")
        sql, params = expr.to_sql()
        assert "RELEASE SAVEPOINT" in sql
        assert "my_savepoint" in sql
        assert params == ()

    def test_release_savepoint_name_property(self, dummy_dialect: DummyDialect):
        """Test name property."""
        expr = ReleaseSavepointStatement(dummy_dialect, "test_sp")
        assert expr.name == "test_sp"

    def test_release_savepoint_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns name."""
        expr = ReleaseSavepointStatement(dummy_dialect, "my_sp")
        params = expr.get_params()
        assert params == {"name": "my_sp"}


class TestSetTransactionExpression:
    """Tests for SetTransactionExpression."""

    def test_set_transaction_isolation_level(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION with isolation level."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE)
        sql, params = expr.to_sql()
        assert "SET TRANSACTION" in sql
        assert "ISOLATION LEVEL SERIALIZABLE" in sql
        assert params == ()

    def test_set_transaction_read_only(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION READ ONLY."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.read_only()
        sql, params = expr.to_sql()
        assert "SET TRANSACTION" in sql
        assert "READ ONLY" in sql
        assert params == ()

    def test_set_transaction_read_write(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION READ WRITE."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.read_write()
        sql, params = expr.to_sql()
        assert "SET TRANSACTION" in sql
        assert "READ WRITE" in sql
        assert params == ()

    def test_set_transaction_session(self, dummy_dialect: DummyDialect):
        """Test SET SESSION CHARACTERISTICS AS TRANSACTION."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.with_session(True)
        sql, params = expr.to_sql()
        assert "SET SESSION CHARACTERISTICS AS TRANSACTION" in sql
        assert params == ()

    def test_set_transaction_deferrable(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION DEFERRABLE."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE).with_deferrable()
        sql, params = expr.to_sql()
        assert "ISOLATION LEVEL SERIALIZABLE" in sql
        assert "DEFERRABLE" in sql
        assert params == ()

    def test_set_transaction_not_deferrable(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION NOT DEFERRABLE."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE).with_not_deferrable()
        sql, params = expr.to_sql()
        assert "NOT DEFERRABLE" in sql
        assert params == ()

    def test_set_transaction_wait(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION with the WAIT lock-wait spelling."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE).with_wait()
        sql, params = expr.to_sql()
        assert sql == "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE WAIT"
        assert params == ()

    def test_set_transaction_no_wait(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION with the NO WAIT lock-wait spelling."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.with_no_wait()
        sql, params = expr.to_sql()
        assert sql == "SET TRANSACTION NO WAIT"
        assert params == ()

    def test_set_transaction_wait_pair_is_mutually_exclusive(self, dummy_dialect: DummyDialect):
        with pytest.raises(ValueError, match="wait and no_wait are mutually exclusive"):
            SetTransactionExpression(dummy_dialect, wait=True, no_wait=True)

    def test_set_transaction_all_options(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION with all options."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.with_session(True).with_isolation_level(IsolationLevel.SERIALIZABLE).read_only().with_deferrable()
        sql, params = expr.to_sql()
        assert "SET SESSION CHARACTERISTICS AS TRANSACTION" in sql
        assert "ISOLATION LEVEL SERIALIZABLE" in sql
        assert "READ ONLY" in sql
        assert "DEFERRABLE" in sql
        assert params == ()

    def test_method_chaining(self, dummy_dialect: DummyDialect):
        """Test method chaining returns self."""
        expr = SetTransactionExpression(dummy_dialect)
        result = expr.with_isolation_level(IsolationLevel.SERIALIZABLE)
        assert result is expr
        result = expr.read_only()
        assert result is expr
        result = expr.with_session(True)
        assert result is expr
        result = expr.with_deferrable()
        assert result is expr

    def test_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns correct dictionary."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE).read_only().with_session(True).with_deferrable()
        params = expr.get_params()
        assert params["isolation_level"] == IsolationLevel.SERIALIZABLE
        assert params["mode"] == TransactionMode.READ_ONLY
        assert params["session"]
        assert params["deferrable"]

    def test_get_params_empty(self, dummy_dialect: DummyDialect):
        """Test get_params returns defaults when nothing set."""
        expr = SetTransactionExpression(dummy_dialect)
        params = expr.get_params()
        assert params == {
            "isolation_level": None,
            "mode": None,
            "session": False,
            "deferrable": False,
            "not_deferrable": False,
            "wait": False,
            "no_wait": False,
        }


class TestAllIsolationLevels:
    """Tests for all isolation levels."""

    @pytest.mark.parametrize(
        "level,expected_name",
        [
            (IsolationLevel.READ_UNCOMMITTED, "READ UNCOMMITTED"),
            (IsolationLevel.READ_COMMITTED, "READ COMMITTED"),
            (IsolationLevel.REPEATABLE_READ, "REPEATABLE READ"),
            (IsolationLevel.SERIALIZABLE, "SERIALIZABLE"),
        ],
    )
    def test_isolation_level_names(self, dummy_dialect: DummyDialect, level, expected_name):
        """Test all isolation level names are correctly formatted."""
        expr = BeginTransactionStatement(dummy_dialect)
        expr.with_isolation_level(level)
        sql, params = expr.to_sql()
        assert expected_name in sql


class TestDummyDialectTransactionCapabilities:
    """Tests for Dummy dialect transaction capability methods."""

    def test_supports_transaction_mode(self, dummy_dialect: DummyDialect):
        """Test supports_transaction_mode returns True."""
        assert dummy_dialect.supports_transaction_mode() is True

    def test_supports_isolation_level_in_begin(self, dummy_dialect: DummyDialect):
        """Test supports_isolation_level_in_begin returns True."""
        assert dummy_dialect.supports_isolation_level_in_begin() is True

    def test_supports_read_only_transaction(self, dummy_dialect: DummyDialect):
        """Test supports_read_only_transaction returns True."""
        assert dummy_dialect.supports_read_only_transaction() is True

    def test_supports_deferrable_transaction(self, dummy_dialect: DummyDialect):
        """Test supports_deferrable_transaction returns True."""
        assert dummy_dialect.supports_deferrable_transaction() is True

    def test_supports_transaction_wait(self, dummy_dialect: DummyDialect):
        """Test supports_transaction_wait returns True."""
        assert dummy_dialect.supports_transaction_wait() is True

    def test_supports_savepoint(self, dummy_dialect: DummyDialect):
        """Test supports_savepoint returns True."""
        assert dummy_dialect.supports_savepoint() is True


class TestReleaseSavepointSQL:
    """Tests for ReleaseSavepointStatement SQL output."""

    def test_release_savepoint_sql(self, dummy_dialect: DummyDialect):
        """Test RELEASE SAVEPOINT SQL output."""
        expr = ReleaseSavepointStatement(dummy_dialect, "my_savepoint")
        sql, params = expr.to_sql()
        assert "RELEASE SAVEPOINT" in sql
        assert "my_savepoint" in sql
        assert params == ()

    def test_release_savepoint_with_special_chars(self, dummy_dialect: DummyDialect):
        """Test RELEASE SAVEPOINT with special characters in name."""
        expr = ReleaseSavepointStatement(dummy_dialect, "sp_with_underscore")
        sql, params = expr.to_sql()
        assert "RELEASE SAVEPOINT" in sql
        assert "sp_with_underscore" in sql
        assert params == ()


class TestSQLiteDialectTransactionCapabilities:
    """Tests for SQLite dialect transaction capability methods."""

    @pytest.fixture
    def sqlite_dialect(self):
        """Provides a SQLiteDialect instance."""
        return SQLiteDialect()

    def test_not_supports_transaction_mode(self, sqlite_dialect: SQLiteDialect):
        """Test supports_transaction_mode returns False for SQLite."""
        assert sqlite_dialect.supports_transaction_mode() is False

    def test_not_supports_isolation_level_in_begin(self, sqlite_dialect: SQLiteDialect):
        """Test supports_isolation_level_in_begin returns False for SQLite."""
        assert sqlite_dialect.supports_isolation_level_in_begin() is False

    def test_not_supports_read_only_transaction(self, sqlite_dialect: SQLiteDialect):
        """Test supports_read_only_transaction returns False for SQLite."""
        assert sqlite_dialect.supports_read_only_transaction() is False

    def test_not_supports_deferrable_transaction(self, sqlite_dialect: SQLiteDialect):
        """Test supports_deferrable_transaction returns False for SQLite."""
        assert sqlite_dialect.supports_deferrable_transaction() is False

    def test_not_supports_transaction_wait(self, sqlite_dialect: SQLiteDialect):
        """Test supports_transaction_wait returns False for SQLite."""
        assert sqlite_dialect.supports_transaction_wait() is False

    def test_begin_refuses_wait(self, sqlite_dialect: SQLiteDialect):
        """SQLite has no WAIT / NO WAIT clause; the request is refused by name."""
        with pytest.raises(UnsupportedFeatureError, match="WAIT"):
            BeginTransactionStatement(sqlite_dialect, wait=True).to_sql()
        with pytest.raises(UnsupportedFeatureError, match="NO WAIT"):
            BeginTransactionStatement(sqlite_dialect, no_wait=True).to_sql()

    def test_supports_savepoint(self, sqlite_dialect: SQLiteDialect):
        """Test supports_savepoint returns True for SQLite."""
        assert sqlite_dialect.supports_savepoint() is True

    def test_begin_raises_error_for_read_only(self, sqlite_dialect: SQLiteDialect):
        """Test BEGIN with READ ONLY raises UnsupportedTransactionModeError."""
        expr = BeginTransactionStatement(sqlite_dialect)
        expr.read_only()
        with pytest.raises(UnsupportedTransactionModeError) as exc_info:
            expr.to_sql()
        assert "READ ONLY" in str(exc_info.value)

    def test_begin_serializable_uses_immediate(self, sqlite_dialect: SQLiteDialect):
        """Test BEGIN with SERIALIZABLE uses IMMEDIATE keyword."""
        expr = BeginTransactionStatement(sqlite_dialect)
        expr.with_isolation_level(IsolationLevel.SERIALIZABLE)
        sql, params = expr.to_sql()
        assert sql == "BEGIN IMMEDIATE TRANSACTION"
        assert params == ()

    def test_begin_read_uncommitted_uses_deferred(self, sqlite_dialect: SQLiteDialect):
        """Test BEGIN with READ_UNCOMMITTED uses DEFERRED keyword."""
        expr = BeginTransactionStatement(sqlite_dialect)
        expr.with_isolation_level(IsolationLevel.READ_UNCOMMITTED)
        sql, params = expr.to_sql()
        assert sql == "BEGIN DEFERRED TRANSACTION"
        assert params == ()

    def test_begin_default_uses_immediate(self, sqlite_dialect: SQLiteDialect):
        """Test default BEGIN uses IMMEDIATE for better concurrency."""
        expr = BeginTransactionStatement(sqlite_dialect)
        sql, params = expr.to_sql()
        assert sql == "BEGIN IMMEDIATE TRANSACTION"
        assert params == ()
