# src/rhosocial/activerecord/backend/impl/sqlite/transaction.py
import logging
from typing import Dict, Optional

from rhosocial.activerecord.backend.transaction import TransactionManager, IsolationLevel
from rhosocial.activerecord.backend.errors import TransactionError


_ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
    IsolationLevel.SERIALIZABLE: "IMMEDIATE",
    IsolationLevel.READ_UNCOMMITTED: "DEFERRED",
}


class SQLiteTransactionMixin:
    """Mixin providing common SQLite transaction functionality.

    This mixin provides non-I/O methods that can be shared between
    sync and async transaction managers. All methods in this mixin
    are pure Python operations that don't involve database I/O.
    """

    _ISOLATION_LEVELS = _ISOLATION_LEVELS
    _isolation_level: IsolationLevel
    _logger: logging.Logger

    def _get_isolation_pragma(self) -> Optional[str]:
        """Get PRAGMA setting for corresponding isolation level.

        Returns:
            PRAGMA statement string or None if not applicable.
        """
        if self._isolation_level == IsolationLevel.READ_UNCOMMITTED:
            return "PRAGMA read_uncommitted = 1"
        return "PRAGMA read_uncommitted = 0"

    def _get_savepoint_name(self, level: int) -> str:
        """Generate savepoint name for nested transactions.

        Args:
            level: The nesting level of the transaction.

        Returns:
            A savepoint name string.
        """
        return f"LEVEL{level}"

    def _validate_isolation_level(self, level: IsolationLevel) -> None:
        """Validate that the isolation level is supported by SQLite.

        Args:
            level: The isolation level to validate.

        Raises:
            TransactionError: If the isolation level is not supported.
        """
        if level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            if hasattr(self, "log"):
                self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _check_no_active_transaction(self) -> None:
        """Check that no transaction is active before changing isolation level.

        Raises:
            TransactionError: If a transaction is currently active.
        """
        if self.is_active:
            error_msg = "Cannot change isolation level during active transaction"
            if hasattr(self, "log"):
                self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _build_begin_sql(self) -> str:
        """Build the BEGIN TRANSACTION SQL statement.

        Returns:
            The SQL statement for beginning a transaction.

        Raises:
            TransactionError: If the isolation level is not supported.
        """
        level = self._ISOLATION_LEVELS.get(self._isolation_level)
        if level:
            return f"BEGIN {level} TRANSACTION"
        raise TransactionError(f"Unsupported isolation level: {self._isolation_level}")

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported by SQLite.

        This is a non-I/O operation that returns a constant value.

        Returns:
            True, as SQLite always supports savepoints.
        """
        return True


class SQLiteTransactionManager(SQLiteTransactionMixin, TransactionManager):
    """SQLite transaction manager implementation."""

    def __init__(self, connection, logger=None):
        """Initialize SQLite transaction manager.

        Args:
            connection: SQLite database connection
            logger: Optional logger instance
        """
        super().__init__(connection, logger)
        self.connection.isolation_level = None
        self._isolation_level = IsolationLevel.SERIALIZABLE

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get the current transaction isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set the transaction isolation level."""
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        self._check_no_active_transaction()
        self._validate_isolation_level(level)
        self._isolation_level = level

    def _do_begin(self) -> None:
        """Begin SQLite transaction."""
        sql = self._build_begin_sql()
        self.log(logging.DEBUG, f"Executing: {sql}")
        self.connection.execute(sql)

        pragma = self._get_isolation_pragma()
        if pragma:
            self.log(logging.DEBUG, f"Executing: {pragma}")
            self.connection.execute(pragma)

    def _do_commit(self) -> None:
        """Commit SQLite transaction."""
        sql = "COMMIT"
        self.log(logging.DEBUG, f"Executing: {sql}")
        self.connection.execute(sql)

    def _do_rollback(self) -> None:
        """Rollback SQLite transaction."""
        sql = "ROLLBACK"
        self.log(logging.DEBUG, f"Executing: {sql}")
        self.connection.execute(sql)

    def _do_create_savepoint(self, name: str) -> None:
        """Create SQLite savepoint."""
        try:
            sql = f"SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            self.connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to create savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def _do_release_savepoint(self, name: str) -> None:
        """Release SQLite savepoint."""
        try:
            sql = f"RELEASE SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            self.connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to SQLite savepoint."""
        try:
            sql = f"ROLLBACK TO SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            self.connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e
