# src/rhosocial/activerecord/backend/impl/sqlite/transaction.py
"""SQLite transaction manager implementation.

This module provides SQLite-specific transaction management.
Since the base TransactionManager now provides all the common
implementation via backend.execute(), this module only needs to
set SQLite-specific default isolation level.
"""
import logging
from typing import TYPE_CHECKING, Optional

from rhosocial.activerecord.backend.transaction import (
    TransactionManager,
    IsolationLevel,
    IsolationLevelError,
)

if TYPE_CHECKING:
    from .backend import SQLiteBackend


class SQLiteTransactionManager(TransactionManager):
    """SQLite transaction manager with default isolation level.

    SQLite uses SERIALIZABLE as the default isolation level.
    All transaction operations are delegated to the base class
    which uses backend.execute() for SQL execution.

    SQLite supports only two isolation levels:
    - SERIALIZABLE (default): Uses BEGIN IMMEDIATE or BEGIN EXCLUSIVE
    - READ_UNCOMMITTED: Uses BEGIN DEFERRED and sets PRAGMA read_uncommitted = 1

    Other isolation levels (READ_COMMITTED, REPEATABLE_READ) are not supported.
    """

    # SQLite supported isolation level mappings
    _SUPPORTED_LEVELS = {
        IsolationLevel.SERIALIZABLE: "IMMEDIATE",
        IsolationLevel.READ_UNCOMMITTED: "DEFERRED",
    }

    def __init__(self, backend: "SQLiteBackend", logger=None):
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

        # Set PRAGMA read_uncommitted based on isolation level
        # SERIALIZABLE: read_uncommitted = 0 (default)
        # READ_UNCOMMITTED: read_uncommitted = 1
        if level is not None:
            pragma_value = 1 if level == IsolationLevel.READ_UNCOMMITTED else 0
            self._backend.execute(f"PRAGMA read_uncommitted = {pragma_value}")

        self._isolation_level = level
        self.log(logging.INFO, f"Isolation level set to {level}")
