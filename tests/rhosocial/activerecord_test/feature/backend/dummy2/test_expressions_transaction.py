# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expressions_transaction.py
"""Tests for transaction expression classes."""
import pytest
from rhosocial.activerecord.backend.expression.transaction import (
    BeginTransactionExpression,
    CommitTransactionExpression,
    RollbackTransactionExpression,
    SavepointExpression,
    ReleaseSavepointExpression,
    SetTransactionExpression,
)
from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.errors import UnsupportedTransactionModeError


class TestBeginTransactionExpression:
    """Tests for BeginTransactionExpression."""

    def test_basic_begin(self, dummy_dialect: DummyDialect):
        """Test basic BEGIN statement."""
        expr = BeginTransactionExpression(dummy_dialect)
        sql, params = expr.to_sql()
        assert sql == "BEGIN"
        assert params == ()

    def test_begin_with_isolation_level(self, dummy_dialect: DummyDialect):
        """Test BEGIN with isolation level."""
        expr = BeginTransactionExpression(dummy_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE)
        sql, params = expr.to_sql()
        assert "ISOLATION LEVEL SERIALIZABLE" in sql
        assert params == ()

    def test_begin_read_only(self, dummy_dialect: DummyDialect):
        """Test BEGIN READ ONLY."""
        expr = BeginTransactionExpression(dummy_dialect)
        expr.read_only()
        sql, params = expr.to_sql()
        assert "READ ONLY" in sql
        assert params == ()

    def test_begin_read_write(self, dummy_dialect: DummyDialect):
        """Test BEGIN READ WRITE."""
        expr = BeginTransactionExpression(dummy_dialect)
        expr.read_write()
        sql, params = expr.to_sql()
        assert "READ WRITE" in sql
        assert params == ()

    def test_begin_with_isolation_and_mode(self, dummy_dialect: DummyDialect):
        """Test BEGIN with isolation level and mode."""
        expr = BeginTransactionExpression(dummy_dialect)
        expr.isolation_level(IsolationLevel.REPEATABLE_READ).read_only()
        sql, params = expr.to_sql()
        assert "ISOLATION LEVEL REPEATABLE READ" in sql
        assert "READ ONLY" in sql
        assert params == ()

    def test_begin_deferrable(self, dummy_dialect: DummyDialect):
        """Test BEGIN with DEFERRABLE."""
        expr = BeginTransactionExpression(dummy_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE).deferrable()
        sql, params = expr.to_sql()
        assert "ISOLATION LEVEL SERIALIZABLE" in sql
        assert "DEFERRABLE" in sql
        assert params == ()

    def test_begin_not_deferrable(self, dummy_dialect: DummyDialect):
        """Test BEGIN with NOT DEFERRABLE."""
        expr = BeginTransactionExpression(dummy_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE).deferrable(False)
        sql, params = expr.to_sql()
        assert "NOT DEFERRABLE" in sql
        assert params == ()

    def test_begin_deferrable_without_serializable(self, dummy_dialect: DummyDialect):
        """Test DEFERRABLE without SERIALIZABLE is ignored."""
        expr = BeginTransactionExpression(dummy_dialect)
        expr.isolation_level(IsolationLevel.READ_COMMITTED).deferrable()
        sql, params = expr.to_sql()
        assert "DEFERRABLE" not in sql
        assert "READ COMMITTED" in sql

    def test_method_chaining(self, dummy_dialect: DummyDialect):
        """Test method chaining returns self."""
        expr = BeginTransactionExpression(dummy_dialect)
        result = expr.isolation_level(IsolationLevel.SERIALIZABLE)
        assert result is expr
        result = expr.read_only()
        assert result is expr
        result = expr.deferrable()
        assert result is expr

    def test_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns correct dictionary."""
        expr = BeginTransactionExpression(dummy_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE).read_only().deferrable()
        params = expr.get_params()
        assert params["isolation_level"] == IsolationLevel.SERIALIZABLE
        assert params["mode"] == TransactionMode.READ_ONLY
        assert params["deferrable"] == True

    def test_sqlite_read_only_raises_error(self):
        """Test SQLite READ ONLY raises UnsupportedTransactionModeError."""
        sqlite_dialect = SQLiteDialect()
        expr = BeginTransactionExpression(sqlite_dialect)
        expr.read_only()
        with pytest.raises(UnsupportedTransactionModeError) as exc_info:
            expr.to_sql()
        assert "READ ONLY" in str(exc_info.value)

    def test_sqlite_begin_serializable(self):
        """Test SQLite BEGIN with SERIALIZABLE isolation."""
        sqlite_dialect = SQLiteDialect()
        expr = BeginTransactionExpression(sqlite_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE)
        sql, params = expr.to_sql()
        assert sql == "BEGIN IMMEDIATE TRANSACTION"
        assert params == ()

    def test_sqlite_begin_read_uncommitted(self):
        """Test SQLite BEGIN with READ UNCOMMITTED isolation."""
        sqlite_dialect = SQLiteDialect()
        expr = BeginTransactionExpression(sqlite_dialect)
        expr.isolation_level(IsolationLevel.READ_UNCOMMITTED)
        sql, params = expr.to_sql()
        assert sql == "BEGIN DEFERRED TRANSACTION"
        assert params == ()


class TestCommitTransactionExpression:
    """Tests for CommitTransactionExpression."""

    def test_commit(self, dummy_dialect: DummyDialect):
        """Test COMMIT statement."""
        expr = CommitTransactionExpression(dummy_dialect)
        sql, params = expr.to_sql()
        assert sql == "COMMIT"
        assert params == ()

    def test_commit_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns empty dict."""
        expr = CommitTransactionExpression(dummy_dialect)
        params = expr.get_params()
        assert params == {}


class TestRollbackTransactionExpression:
    """Tests for RollbackTransactionExpression."""

    def test_rollback(self, dummy_dialect: DummyDialect):
        """Test ROLLBACK statement."""
        expr = RollbackTransactionExpression(dummy_dialect)
        sql, params = expr.to_sql()
        assert sql == "ROLLBACK"
        assert params == ()

    def test_rollback_to_savepoint(self, dummy_dialect: DummyDialect):
        """Test ROLLBACK TO SAVEPOINT statement."""
        expr = RollbackTransactionExpression(dummy_dialect)
        expr.to_savepoint("my_savepoint")
        sql, params = expr.to_sql()
        assert "ROLLBACK" in sql
        assert "SAVEPOINT" in sql
        assert params == ()

    def test_rollback_get_params_with_savepoint(self, dummy_dialect: DummyDialect):
        """Test get_params returns savepoint name."""
        expr = RollbackTransactionExpression(dummy_dialect)
        expr.to_savepoint("test_sp")
        params = expr.get_params()
        assert params == {"savepoint": "test_sp"}

    def test_rollback_get_params_empty(self, dummy_dialect: DummyDialect):
        """Test get_params returns empty dict when no savepoint."""
        expr = RollbackTransactionExpression(dummy_dialect)
        params = expr.get_params()
        assert params == {}

    def test_rollback_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns empty dict."""
        expr = RollbackTransactionExpression(dummy_dialect)
        params = expr.get_params()
        assert params == {}


class TestSavepointExpression:
    """Tests for SavepointExpression."""

    def test_savepoint(self, dummy_dialect: DummyDialect):
        """Test SAVEPOINT statement."""
        expr = SavepointExpression(dummy_dialect, "my_savepoint")
        sql, params = expr.to_sql()
        assert "SAVEPOINT" in sql
        assert "my_savepoint" in sql
        assert params == ()

    def test_savepoint_name_property(self, dummy_dialect: DummyDialect):
        """Test name property."""
        expr = SavepointExpression(dummy_dialect, "test_sp")
        assert expr.name == "test_sp"

    def test_savepoint_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns name."""
        expr = SavepointExpression(dummy_dialect, "my_sp")
        params = expr.get_params()
        assert params == {"name": "my_sp"}


class TestReleaseSavepointExpression:
    """Tests for ReleaseSavepointExpression."""

    def test_release_savepoint(self, dummy_dialect: DummyDialect):
        """Test RELEASE SAVEPOINT statement."""
        expr = ReleaseSavepointExpression(dummy_dialect, "my_savepoint")
        sql, params = expr.to_sql()
        assert "RELEASE SAVEPOINT" in sql
        assert "my_savepoint" in sql
        assert params == ()

    def test_release_savepoint_name_property(self, dummy_dialect: DummyDialect):
        """Test name property."""
        expr = ReleaseSavepointExpression(dummy_dialect, "test_sp")
        assert expr.name == "test_sp"

    def test_release_savepoint_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns name."""
        expr = ReleaseSavepointExpression(dummy_dialect, "my_sp")
        params = expr.get_params()
        assert params == {"name": "my_sp"}


class TestSetTransactionExpression:
    """Tests for SetTransactionExpression."""

    def test_set_transaction_isolation_level(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION with isolation level."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE)
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
        expr.session(True)
        sql, params = expr.to_sql()
        assert "SET SESSION CHARACTERISTICS AS TRANSACTION" in sql
        assert params == ()

    def test_set_transaction_deferrable(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION DEFERRABLE."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE).deferrable()
        sql, params = expr.to_sql()
        assert "ISOLATION LEVEL SERIALIZABLE" in sql
        assert "DEFERRABLE" in sql
        assert params == ()

    def test_set_transaction_not_deferrable(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION NOT DEFERRABLE."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE).deferrable(False)
        sql, params = expr.to_sql()
        assert "NOT DEFERRABLE" in sql
        assert params == ()

    def test_set_transaction_all_options(self, dummy_dialect: DummyDialect):
        """Test SET TRANSACTION with all options."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.session(True).isolation_level(IsolationLevel.SERIALIZABLE).read_only().deferrable()
        sql, params = expr.to_sql()
        assert "SET SESSION CHARACTERISTICS AS TRANSACTION" in sql
        assert "ISOLATION LEVEL SERIALIZABLE" in sql
        assert "READ ONLY" in sql
        assert "DEFERRABLE" in sql
        assert params == ()

    def test_method_chaining(self, dummy_dialect: DummyDialect):
        """Test method chaining returns self."""
        expr = SetTransactionExpression(dummy_dialect)
        result = expr.isolation_level(IsolationLevel.SERIALIZABLE)
        assert result is expr
        result = expr.read_only()
        assert result is expr
        result = expr.session(True)
        assert result is expr
        result = expr.deferrable()
        assert result is expr

    def test_get_params(self, dummy_dialect: DummyDialect):
        """Test get_params returns correct dictionary."""
        expr = SetTransactionExpression(dummy_dialect)
        expr.isolation_level(IsolationLevel.SERIALIZABLE).read_only().session(True).deferrable()
        params = expr.get_params()
        assert params["isolation_level"] == IsolationLevel.SERIALIZABLE
        assert params["mode"] == TransactionMode.READ_ONLY
        assert params["session"] == True
        assert params["deferrable"] == True

    def test_get_params_empty(self, dummy_dialect: DummyDialect):
        """Test get_params returns empty dict when nothing set."""
        expr = SetTransactionExpression(dummy_dialect)
        params = expr.get_params()
        assert params == {}


class TestAllIsolationLevels:
    """Tests for all isolation levels."""

    @pytest.mark.parametrize("level,expected_name", [
        (IsolationLevel.READ_UNCOMMITTED, "READ UNCOMMITTED"),
        (IsolationLevel.READ_COMMITTED, "READ COMMITTED"),
        (IsolationLevel.REPEATABLE_READ, "REPEATABLE READ"),
        (IsolationLevel.SERIALIZABLE, "SERIALIZABLE"),
    ])
    def test_isolation_level_names(self, dummy_dialect: DummyDialect, level, expected_name):
        """Test all isolation level names are correctly formatted."""
        expr = BeginTransactionExpression(dummy_dialect)
        expr.isolation_level(level)
        sql, params = expr.to_sql()
        assert expected_name in sql
