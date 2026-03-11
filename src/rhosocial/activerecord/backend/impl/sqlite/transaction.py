# src/rhosocial/activerecord/backend/impl/sqlite/transaction.py
import logging
from typing import Dict, List, Optional

import aiosqlite

from ...transaction import TransactionManager, AsyncTransactionManager, IsolationLevel
from ...errors import TransactionError


_ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
    IsolationLevel.SERIALIZABLE: "IMMEDIATE",
    IsolationLevel.READ_UNCOMMITTED: "DEFERRED",
}


class SQLiteTransactionMixin:
    """Mixin providing common SQLite transaction functionality."""

    _ISOLATION_LEVELS = _ISOLATION_LEVELS
    _isolation_level: IsolationLevel
    _logger: logging.Logger

    def _get_isolation_pragma(self) -> Optional[str]:
        """Get PRAGMA setting for corresponding isolation level."""
        if self._isolation_level == IsolationLevel.READ_UNCOMMITTED:
            return "PRAGMA read_uncommitted = 1"
        return "PRAGMA read_uncommitted = 0"

    def _get_savepoint_name(self, level: int) -> str:
        """Generate savepoint name for nested transactions."""
        return f"LEVEL{level}"

    def _validate_isolation_level(self, level: IsolationLevel) -> None:
        """Validate that the isolation level is supported by SQLite."""
        if level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            if hasattr(self, 'log'):
                self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _check_no_active_transaction(self) -> None:
        """Check that no transaction is active before changing isolation level."""
        if self.is_active:
            error_msg = "Cannot change isolation level during active transaction"
            if hasattr(self, 'log'):
                self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _build_begin_sql(self) -> str:
        """Build the BEGIN TRANSACTION SQL statement."""
        level = self._ISOLATION_LEVELS.get(self._isolation_level)
        if level:
            return f"BEGIN {level} TRANSACTION"
        raise TransactionError(f"Unsupported isolation level: {self._isolation_level}")


class SQLiteTransactionManager(SQLiteTransactionMixin, TransactionManager):
    """SQLite transaction manager implementation."""

    def __init__(self, connection, logger=None):
        """Initialize SQLite transaction manager

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

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported by SQLite."""
        return True


class AsyncSQLiteTransactionManager(SQLiteTransactionMixin, AsyncTransactionManager):
    """Async transaction manager for SQLite using aiosqlite."""

    def __init__(
        self,
        connection: aiosqlite.Connection,
        logger: Optional[logging.Logger] = None
    ):
        super().__init__(connection, logger)
        self._isolation_level = IsolationLevel.SERIALIZABLE

    @property
    def isolation_level(self) -> IsolationLevel:
        """Get isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: IsolationLevel):
        """Set isolation level."""
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        self._check_no_active_transaction()
        self._validate_isolation_level(level)
        self._isolation_level = level

    async def _do_begin(self) -> None:
        """Begin SQLite transaction."""
        if self._isolation_level == IsolationLevel.SERIALIZABLE:
            await self.connection.execute("BEGIN IMMEDIATE")
            await self.connection.execute("PRAGMA read_uncommitted = 0")
        else:
            await self.connection.execute("BEGIN DEFERRED")
            await self.connection.execute("PRAGMA read_uncommitted = 1")

    async def _do_commit(self) -> None:
        """Commit SQLite transaction."""
        await self.connection.commit()

    async def _do_rollback(self) -> None:
        """Rollback SQLite transaction."""
        await self.connection.rollback()

    async def _do_create_savepoint(self, name: str) -> None:
        """Create SQLite savepoint."""
        try:
            await self.connection.execute(f"SAVEPOINT {name}")
        except Exception as e:
            error_msg = f"Failed to create savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def _do_release_savepoint(self, name: str) -> None:
        """Release SQLite savepoint."""
        try:
            await self.connection.execute(f"RELEASE SAVEPOINT {name}")
        except Exception as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to SQLite savepoint."""
        try:
            await self.connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def supports_savepoint(self) -> bool:
        """Check if savepoints are supported by SQLite."""
        return True
