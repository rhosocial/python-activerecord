# src/rhosocial/activerecord/backend/impl/sqlite/async_transaction.py
"""Asynchronous SQLite transaction manager.

This module provides async transaction management for SQLite using aiosqlite.
It is kept separate from the sync transaction module to avoid forcing
aiosqlite as a dependency for users who only need synchronous operations.
"""
import logging
from typing import TYPE_CHECKING, Optional

from rhosocial.activerecord.backend.transaction import (
    AsyncTransactionManager,
    IsolationLevel,
    IsolationLevelError,
)

if TYPE_CHECKING:
    from .backend import AsyncSQLiteBackend


class AsyncSQLiteTransactionManager(AsyncTransactionManager):
    """Async transaction manager for SQLite using aiosqlite.

    All transaction operations are delegated to the base class
    which uses backend.execute() for SQL execution.
    """

    # SQLite supported isolation level mappings
    _SUPPORTED_LEVELS = {
        IsolationLevel.SERIALIZABLE: "IMMEDIATE",
        IsolationLevel.READ_UNCOMMITTED: "DEFERRED",
    }

    def __init__(self, backend: "AsyncSQLiteBackend", logger=None):
        super().__init__(backend, logger)
        # SQLite default isolation level is SERIALIZABLE
        self._isolation_level = IsolationLevel.SERIALIZABLE

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get the current transaction isolation level."""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set the transaction isolation level.

        SQLite only supports SERIALIZABLE and READ_UNCOMMITTED isolation levels.
        READ_UNCOMMITTED is achieved by setting PRAGMA read_uncommitted = 1
        and using BEGIN DEFERRED instead of BEGIN IMMEDIATE.

        Note: For async backend, the PRAGMA is set during _do_begin() since
        we cannot call async execute() in a sync setter.

        Args:
            level: The isolation level to be set

        Raises:
            IsolationLevelError: If attempting to change isolation level while transaction is active
                                 or if the isolation level is not supported by SQLite
        """
        self.log(logging.DEBUG, f"Setting isolation level to {level}")

        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise IsolationLevelError("Cannot change isolation level during active transaction")

        # Check if the isolation level is supported by SQLite
        if level is not None and level not in self._SUPPORTED_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            self.log(logging.ERROR, error_msg)
            raise IsolationLevelError(error_msg)

        self._isolation_level = level
        self.log(logging.INFO, f"Isolation level set to {level}")

    async def _do_begin(self) -> None:
        """Begin a new transaction via backend.execute().

        For SQLite, we need to set PRAGMA read_uncommitted before BEGIN
        if the isolation level is READ_UNCOMMITTED.
        """
        # Set PRAGMA read_uncommitted based on isolation level
        # SERIALIZABLE: read_uncommitted = 0 (default)
        # READ_UNCOMMITTED: read_uncommitted = 1
        if self._isolation_level is not None:
            pragma_value = 1 if self._isolation_level == IsolationLevel.READ_UNCOMMITTED else 0
            await self._backend.execute(f"PRAGMA read_uncommitted = {pragma_value}")

        # Call parent to execute BEGIN
        await super()._do_begin()
