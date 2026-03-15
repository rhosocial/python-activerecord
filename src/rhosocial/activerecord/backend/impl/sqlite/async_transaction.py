# src/rhosocial/activerecord/backend/impl/sqlite/async_transaction.py
"""Asynchronous SQLite transaction manager.

This module provides async transaction management for SQLite using aiosqlite.
It is kept separate from the sync transaction module to avoid forcing
aiosqlite as a dependency for users who only need synchronous operations.
"""
import logging
from typing import Optional, TYPE_CHECKING

import aiosqlite

from ...transaction import AsyncTransactionManager, IsolationLevel
from ...errors import TransactionError

if TYPE_CHECKING:
    pass

_ISOLATION_LEVELS = {
    IsolationLevel.SERIALIZABLE: "IMMEDIATE",
    IsolationLevel.READ_UNCOMMITTED: "DEFERRED",
}


class AsyncSQLiteTransactionManager(AsyncTransactionManager):
    """Async transaction manager for SQLite using aiosqlite."""

    def __init__(
        self,
        connection: aiosqlite.Connection,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize async SQLite transaction manager.

        Args:
            connection: aiosqlite database connection
            logger: Optional logger instance
        """
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

    def _validate_isolation_level(self, level: IsolationLevel) -> None:
        """Validate that the isolation level is supported by SQLite."""
        if level not in _ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _check_no_active_transaction(self) -> None:
        """Check that no transaction is active before changing isolation level."""
        if self.is_active:
            error_msg = "Cannot change isolation level during active transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

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
