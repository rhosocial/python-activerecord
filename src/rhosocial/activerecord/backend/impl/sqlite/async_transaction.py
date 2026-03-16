# src/rhosocial/activerecord/backend/impl/sqlite/async_transaction.py
"""Asynchronous SQLite transaction manager.

This module provides async transaction management for SQLite using aiosqlite.
It is kept separate from the sync transaction module to avoid forcing
aiosqlite as a dependency for users who only need synchronous operations.
"""
import logging
from typing import Optional

import aiosqlite

from .transaction import SQLiteTransactionMixin
from rhosocial.activerecord.backend.transaction import AsyncTransactionManager, IsolationLevel
from rhosocial.activerecord.backend.errors import TransactionError


class AsyncSQLiteTransactionManager(SQLiteTransactionMixin, AsyncTransactionManager):
    """Async transaction manager for SQLite using aiosqlite.

    This class inherits from SQLiteTransactionMixin to share non-I/O methods
    with the sync version, ensuring consistency and reducing code duplication.
    """

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
        """Get isolation level.

        Returns:
            The current isolation level.
        """
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: IsolationLevel):
        """Set isolation level.

        Args:
            level: The isolation level to set.

        Raises:
            TransactionError: If a transaction is active or level is unsupported.
        """
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        self._check_no_active_transaction()
        self._validate_isolation_level(level)
        self._isolation_level = level

    async def _do_begin(self) -> None:
        """Begin SQLite transaction.

        Uses the shared _build_begin_sql() and _get_isolation_pragma() methods
        from SQLiteTransactionMixin for consistent behavior with sync version.
        """
        sql = self._build_begin_sql()
        self.log(logging.DEBUG, f"Executing: {sql}")
        await self.connection.execute(sql)

        pragma = self._get_isolation_pragma()
        if pragma:
            self.log(logging.DEBUG, f"Executing: {pragma}")
            await self.connection.execute(pragma)

    async def _do_commit(self) -> None:
        """Commit SQLite transaction."""
        await self.connection.commit()

    async def _do_rollback(self) -> None:
        """Rollback SQLite transaction."""
        await self.connection.rollback()

    async def _do_create_savepoint(self, name: str) -> None:
        """Create SQLite savepoint.

        Args:
            name: The name of the savepoint to create.

        Raises:
            TransactionError: If the savepoint cannot be created.
        """
        try:
            sql = f"SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            await self.connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to create savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def _do_release_savepoint(self, name: str) -> None:
        """Release SQLite savepoint.

        Args:
            name: The name of the savepoint to release.

        Raises:
            TransactionError: If the savepoint cannot be released.
        """
        try:
            sql = f"RELEASE SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            await self.connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to SQLite savepoint.

        Args:
            name: The name of the savepoint to rollback to.

        Raises:
            TransactionError: If the rollback fails.
        """
        try:
            sql = f"ROLLBACK TO SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            await self.connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e
