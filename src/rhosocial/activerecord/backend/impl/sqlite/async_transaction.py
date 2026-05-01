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
    TransactionMode,
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
        # SQLite-specific BEGIN transaction type (DEFERRED|IMMEDIATE|EXCLUSIVE)
        # When None, the type is derived from isolation_level
        self._begin_type: Optional[str] = None

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

    @property
    def begin_type(self) -> Optional[str]:
        """Get the SQLite BEGIN transaction type.

        When set, overrides the default mapping from isolation level.
        """
        return self._begin_type

    @begin_type.setter
    def begin_type(self, value: Optional[str]):
        """Set the SQLite BEGIN transaction type.

        When set, overrides the default mapping from isolation level.
        Set to None to revert to isolation level-based mapping.

        Args:
            value: One of "DEFERRED", "IMMEDIATE", "EXCLUSIVE", or None.

        Raises:
            IsolationLevelError: If called during active transaction.
            ValueError: If value is not a valid SQLite transaction type.
        """
        if self.is_active:
            raise IsolationLevelError("Cannot change begin type during active transaction")
        if value is not None and value.upper() not in ("DEFERRED", "IMMEDIATE", "EXCLUSIVE"):
            raise ValueError(
                f"Invalid SQLite begin type: {value}. "
                "Must be one of ('DEFERRED', 'IMMEDIATE', 'EXCLUSIVE')"
            )
        self._begin_type = value.upper() if value else None

    def _build_begin_sql(self) -> tuple:
        """Build BEGIN TRANSACTION SQL with SQLite-specific options."""
        from rhosocial.activerecord.backend.expression.transaction import BeginTransactionExpression

        expr = BeginTransactionExpression(self._backend.dialect)

        if self._begin_type is not None:
            # Explicit begin_type overrides isolation level mapping
            expr.begin_type(self._begin_type)
        elif self._isolation_level is not None:
            expr.isolation_level(self._isolation_level)

        if self._transaction_mode == TransactionMode.READ_ONLY:
            expr.read_only()

        return expr.to_sql()

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
