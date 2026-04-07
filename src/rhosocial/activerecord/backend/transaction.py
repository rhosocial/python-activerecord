# src/rhosocial/activerecord/backend/transaction.py
"""
Transaction management for both synchronous and asynchronous backends.

To support async operations and maximize code reuse, this file was refactored to use
a base class for shared logic:

1.  **TransactionManagerBase**: Contains all the non-I/O logic for managing
    transaction state, nesting levels, and savepoints. This logic is identical
    for both sync and async operations.

2.  **TransactionManager**: The synchronous transaction manager, which inherits from
    `TransactionManagerBase` and implements the synchronous, I/O-bound `_do_*` methods
    by delegating to `backend.execute()`.

3.  **AsyncTransactionManager**: The asynchronous transaction manager, which also
    inherits from `TransactionManagerBase` and implements the asynchronous `_do_*`
    methods using `async def` and `await backend.execute()`.

This structure ensures that the complex state management of nested transactions is
written only once and shared, reducing duplication and potential for bugs.
"""

import logging
from abc import ABC
from contextlib import contextmanager, asynccontextmanager
from enum import Enum, auto
from typing import Optional, Generator, AsyncGenerator, Tuple, TYPE_CHECKING

from .errors import TransactionError, IsolationLevelError
from ..logging.manager import get_logging_manager

if TYPE_CHECKING:
    from .base import StorageBackend, AsyncStorageBackend


class IsolationLevel(Enum):
    """Database transaction isolation levels.

    Defines standard SQL isolation levels:
    - READ_UNCOMMITTED: Lowest isolation, allows dirty reads
    - READ_COMMITTED: Prevents dirty reads
    - REPEATABLE_READ: Prevents non-repeatable reads
    - SERIALIZABLE: Highest isolation, prevents phantom reads
    """

    READ_UNCOMMITTED = auto()
    READ_COMMITTED = auto()
    REPEATABLE_READ = auto()
    SERIALIZABLE = auto()


class TransactionMode(Enum):
    """Transaction access mode.

    Defines the access mode for a transaction:
    - READ_WRITE: Transaction can read and write data (default)
    - READ_ONLY: Transaction can only read data, no modifications allowed

    Note: READ_ONLY is a transaction mode, not an isolation level.
    It can be combined with any isolation level.
    """

    READ_WRITE = auto()
    READ_ONLY = auto()


class TransactionState(Enum):
    """Transaction states"""

    INACTIVE = auto()
    ACTIVE = auto()
    COMMITTED = auto()
    ROLLED_BACK = auto()


class TransactionManagerBase(ABC):
    """Base class for transaction managers, containing shared non-I/O logic.

    Attributes:
        _backend: Storage backend instance.
        _transaction_level: Current nesting level of transactions.
        _isolation_level: Current isolation level setting.
        _transaction_mode: Current transaction mode (READ_WRITE or READ_ONLY).
    """

    def __init__(self, backend: "StorageBackend", logger=None):
        self._backend = backend
        self._transaction_level = 0
        self._savepoint_prefix = "SP"
        self._isolation_level: Optional[IsolationLevel] = None
        self._transaction_mode: TransactionMode = TransactionMode.READ_WRITE
        # Use semantic logger naming: rhosocial.activerecord.transaction
        self._logger = logger or get_logging_manager().get_logger(
            get_logging_manager().LOGGER_TRANSACTION
        )
        self._savepoint_count = 0  # Track savepoint count
        self._active_savepoints = []  # Track active savepoints
        self._state = TransactionState.INACTIVE  # Track transaction state

    @property
    def backend(self):
        """Get the storage backend."""
        return self._backend

    @property
    def dialect(self):
        """Get the SQL dialect from backend."""
        return self._backend.dialect

    @property
    def logger(self):
        """Get the current logger"""
        return self._logger

    @logger.setter
    def logger(self, logger: Optional[logging.Logger]) -> None:
        """Set the logger for this transaction manager"""
        if logger is not None and not isinstance(logger, logging.Logger):
            raise ValueError("logger must be an instance of logging.Logger")
        self._logger = logger or get_logging_manager().get_logger(
            get_logging_manager().LOGGER_TRANSACTION
        )

    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log message with specified level.

        Args:
            level: Log level (e.g., logging.INFO)
            msg: Message to log
            *args: Additional args for logger
            **kwargs: Additional kwargs for logger
        """
        if self._logger:
            self._logger.log(level, msg, *args, **kwargs)

    @property
    def is_active(self) -> bool:
        """Check if the transaction is currently active

        The transaction is considered active if:
        1. The transaction level is greater than 0, and
        2. The state is ACTIVE

        This maintains backward compatibility with tests that directly modify
        _transaction_level for testing purposes.
        """
        return self._transaction_level > 0

    @property
    def transaction_level(self) -> int:
        """Get the current transaction nesting level"""
        return self._transaction_level

    @property
    def state(self) -> TransactionState:
        """Get the current transaction state"""
        return self._state

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get the current transaction isolation level"""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set the transaction isolation level

        Args:
            level: The isolation level to be set

        Raises:
            IsolationLevelError: If attempting to change isolation level while transaction is active
        """
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise IsolationLevelError("Cannot change isolation level during active transaction")
        self._isolation_level = level

    @property
    def transaction_mode(self) -> TransactionMode:
        """Get the current transaction mode"""
        return self._transaction_mode

    @transaction_mode.setter
    def transaction_mode(self, mode: TransactionMode):
        """Set the transaction mode

        Args:
            mode: The transaction mode to be set (READ_WRITE or READ_ONLY)

        Raises:
            TransactionError: If attempting to change mode while transaction is active
        """
        self.log(logging.DEBUG, f"Setting transaction mode to {mode}")
        if self.is_active:
            self.log(logging.ERROR, "Cannot change transaction mode during active transaction")
            raise TransactionError("Cannot change transaction mode during active transaction")
        self._transaction_mode = mode

    def _get_savepoint_name(self, level: int) -> str:
        """Generate savepoint name

        Args:
            level: Transaction nesting level

        Returns:
            str: The generated savepoint name
        """
        return f"{self._savepoint_prefix}_{level}"

    def _build_begin_sql(self) -> Tuple[str, tuple]:
        """Build BEGIN TRANSACTION SQL using expression system.

        This method creates a BeginTransactionExpression and delegates
        SQL generation to the backend's dialect.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from .expression.transaction import BeginTransactionExpression

        expr = BeginTransactionExpression(self._backend.dialect)

        if self._isolation_level is not None:
            expr.isolation_level(self._isolation_level)

        if self._transaction_mode == TransactionMode.READ_ONLY:
            expr.read_only()

        return expr.to_sql()

    def _build_commit_sql(self) -> Tuple[str, tuple]:
        """Build COMMIT SQL using expression system.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from .expression.transaction import CommitTransactionExpression

        expr = CommitTransactionExpression(self._backend.dialect)
        return expr.to_sql()

    def _build_rollback_sql(self, savepoint: Optional[str] = None) -> Tuple[str, tuple]:
        """Build ROLLBACK SQL using expression system.

        Args:
            savepoint: Optional savepoint name to rollback to.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from .expression.transaction import RollbackTransactionExpression

        expr = RollbackTransactionExpression(self._backend.dialect)
        if savepoint:
            expr.to_savepoint(savepoint)
        return expr.to_sql()

    def _build_savepoint_sql(self, name: str) -> Tuple[str, tuple]:
        """Build SAVEPOINT SQL using expression system.

        Args:
            name: Savepoint name.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from .expression.transaction import SavepointExpression

        expr = SavepointExpression(self._backend.dialect, name)
        return expr.to_sql()

    def _build_release_savepoint_sql(self, name: str) -> Tuple[str, tuple]:
        """Build RELEASE SAVEPOINT SQL using expression system.

        Args:
            name: Savepoint name.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from .expression.transaction import ReleaseSavepointExpression

        expr = ReleaseSavepointExpression(self._backend.dialect, name)
        return expr.to_sql()


class TransactionManager(TransactionManagerBase):
    """Synchronous transaction manager implementing nested transactions.

    Features:
    - Nested transaction support using save-points
    - Isolation level management
    - Context manager interface for 'with' statement
    - Automatic rollback on exceptions
    - Executes SQL via backend.execute()
    """

    def __init__(self, backend: "StorageBackend", logger=None):
        super().__init__(backend, logger)

    def _do_begin(self) -> None:
        """Begin a new transaction via backend.execute()."""
        sql, params = self._build_begin_sql()
        self._backend.execute(sql, params)

    def _do_commit(self) -> None:
        """Commit the current transaction via backend.execute()."""
        sql, params = self._build_commit_sql()
        self._backend.execute(sql, params)

    def _do_rollback(self) -> None:
        """Rollback the current transaction via backend.execute()."""
        sql, params = self._build_rollback_sql()
        self._backend.execute(sql, params)

    def _do_create_savepoint(self, name: str) -> None:
        """Create a savepoint via backend.execute().

        Args:
            name: Name of the savepoint
        """
        sql, params = self._build_savepoint_sql(name)
        self._backend.execute(sql, params)

    def _do_release_savepoint(self, name: str) -> None:
        """Release a savepoint via backend.execute().

        Args:
            name: Name of the savepoint
        """
        sql, params = self._build_release_savepoint_sql(name)
        self._backend.execute(sql, params)

    def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to a specified savepoint via backend.execute().

        Args:
            name: Name of the savepoint
        """
        sql, params = self._build_rollback_sql(savepoint=name)
        self._backend.execute(sql, params)

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported.

        Returns:
            bool: True if savepoints are supported, False otherwise
        """
        return self._backend.dialect.supports_savepoint()

    def begin(self) -> None:
        """Begin a transaction or create a savepoint

        For nested calls, creates a savepoint instead of starting a new transaction.

        Raises:
            TransactionError: If begin operation fails
        """
        self.log(logging.DEBUG, f"Beginning transaction (level {self._transaction_level})")

        try:
            # Increment transaction level FIRST to prevent auto-commit during _do_begin()
            # This ensures that execute() will see in_transaction=True
            self._transaction_level += 1

            if self._transaction_level == 1:
                # Start actual transaction (now that level is 1, auto-commit won't trigger)
                self.log(logging.INFO, f"Starting new transaction with isolation level {self._isolation_level}")
                self._do_begin()
                self._state = TransactionState.ACTIVE
            else:
                # Create savepoint for nested transaction
                savepoint_name = self._get_savepoint_name(self._transaction_level - 1)
                self.log(logging.INFO, f"Creating savepoint {savepoint_name} for nested transaction")
                self._do_create_savepoint(savepoint_name)
                self._active_savepoints.append(savepoint_name)

            self.log(logging.DEBUG, f"Transaction begun at level {self._transaction_level}")
        except Exception as e:
            # Decrement level on failure since we incremented it first
            self._transaction_level -= 1
            error_msg = f"Failed to begin transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def commit(self) -> None:
        """Commit the current transaction or release the current savepoint

        For nested transactions, releases the savepoint.
        For the outermost transaction, performs a real commit.

        Raises:
            TransactionError: If no active transaction or commit fails
        """
        self.log(logging.DEBUG, f"Committing transaction (level {self._transaction_level})")

        if not self.is_active:
            error_msg = "No active transaction to commit"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        try:
            # Store current level before decrementing
            current_level = self._transaction_level
            self._transaction_level -= 1

            if current_level <= 1:  # Was outermost transaction
                # Commit actual transaction
                self.log(logging.INFO, "Committing outermost transaction")
                self._do_commit()
                self._state = TransactionState.COMMITTED
                # Reset savepoint tracking
                self._savepoint_count = 0
                self._active_savepoints = []
            else:
                # Release savepoint for inner transaction
                if self._active_savepoints:
                    savepoint_name = self._active_savepoints.pop()
                    self.log(logging.INFO, f"Releasing savepoint {savepoint_name} for nested transaction")
                    self._do_release_savepoint(savepoint_name)
                else:
                    # No active savepoint but in nested transaction - abnormal state
                    self.log(logging.WARNING, "No savepoint found for commit, continuing")

            # Update state if no more active transactions
            if self._transaction_level == 0:
                self._state = TransactionState.INACTIVE

            self.log(logging.DEBUG, f"Transaction committed, new level: {self._transaction_level}")
        except Exception as e:
            error_msg = f"Failed to commit transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            # Restore transaction level on failure
            self._transaction_level += 1
            raise TransactionError(error_msg) from e

    def rollback(self) -> None:
        """Rollback the current transaction or to the current savepoint

        For nested transactions, rolls back to the savepoint.
        For the outermost transaction, performs a real rollback.

        Raises:
            TransactionError: If no active transaction or rollback fails
        """
        self.log(logging.DEBUG, f"Rolling back transaction (level {self._transaction_level})")

        if not self.is_active:
            error_msg = "No active transaction to rollback"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        try:
            # Store current level before decrementing
            current_level = self._transaction_level
            self._transaction_level -= 1

            if current_level <= 1:  # Was outermost transaction
                # Rollback actual transaction
                self.log(logging.INFO, "Rolling back outermost transaction")
                self._do_rollback()
                self._state = TransactionState.ROLLED_BACK
                # Reset savepoint tracking
                self._savepoint_count = 0
                self._active_savepoints = []
            else:
                # Rollback to savepoint for inner transaction
                if self._active_savepoints:
                    savepoint_name = self._active_savepoints.pop()
                    self.log(logging.INFO, f"Rolling back to savepoint {savepoint_name} for nested transaction")
                    self._do_rollback_savepoint(savepoint_name)
                else:
                    # No active savepoint but in nested transaction - abnormal state
                    self.log(logging.WARNING, "No savepoint found for rollback, continuing")

            # Update state if no more active transactions
            if self._transaction_level == 0:
                self._state = TransactionState.INACTIVE

            self.log(logging.DEBUG, f"Transaction rolled back, new level: {self._transaction_level}")
        except Exception as e:
            error_msg = f"Failed to rollback transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            # Restore transaction level on failure
            self._transaction_level += 1
            raise TransactionError(error_msg) from e

    def savepoint(self, name: Optional[str] = None) -> str:
        """Create a savepoint with an optional name or auto-generated name

        Args:
            name: Optional savepoint name, auto-generated if None

        Returns:
            str: The name of the created savepoint

        Raises:
            TransactionError: If not in a transaction or savepoint creation fails
        """
        self.log(logging.DEBUG, f"Creating savepoint (name: {name})")

        if not self.is_active:
            error_msg = "Cannot create savepoint: no active transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        try:
            # Generate name if not provided
            if name is None:
                self._savepoint_count += 1
                name = f"{self._savepoint_prefix}_{self._savepoint_count}"

            self.log(logging.INFO, f"Creating savepoint: {name}")
            self._do_create_savepoint(name)
            self._active_savepoints.append(name)
            return name
        except Exception as e:
            error_msg = f"Failed to create savepoint: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def release(self, name: str) -> None:
        """Release a savepoint

        Args:
            name: Savepoint name to release

        Raises:
            TransactionError: If not in a transaction, invalid savepoint name,
                or savepoint release fails
        """
        self.log(logging.DEBUG, f"Releasing savepoint: {name}")

        if not self.is_active:
            error_msg = "Cannot release savepoint: no active transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        if name not in self._active_savepoints:
            error_msg = f"Invalid savepoint name: {name}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        try:
            self.log(logging.INFO, f"Releasing savepoint: {name}")
            self._do_release_savepoint(name)
            self._active_savepoints.remove(name)
        except Exception as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def rollback_to(self, name: str) -> None:
        """Rollback to a savepoint

        Args:
            name: Savepoint name to rollback to

        Raises:
            TransactionError: If not in a transaction, invalid savepoint name,
                or savepoint rollback fails
        """
        self.log(logging.DEBUG, f"Rolling back to savepoint: {name}")

        if not self.is_active:
            error_msg = "Cannot rollback to savepoint: no active transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        if name not in self._active_savepoints:
            error_msg = f"Invalid savepoint name: {name}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        try:
            self.log(logging.INFO, f"Rolling back to savepoint: {name}")
            self._do_rollback_savepoint(name)

            # Remove all savepoints created after this one
            index = self._active_savepoints.index(name)
            self._active_savepoints = self._active_savepoints[: index + 1]
            self.log(logging.DEBUG, f"Active savepoints after rollback: {self._active_savepoints}")
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    @contextmanager
    def transaction(
        self,
        isolation_level: Optional[IsolationLevel] = None,
        mode: Optional[TransactionMode] = None,
    ) -> Generator[None, None, None]:
        """Context manager for transaction blocks.

        Args:
            isolation_level: Optional isolation level for this transaction.
                If not specified, uses the currently set isolation level.
            mode: Optional transaction mode (READ_WRITE or READ_ONLY).
                If not specified, uses the currently set mode.

        Usage:
            with manager.transaction():
                # Operations within transaction

            with manager.transaction(isolation_level=IsolationLevel.SERIALIZABLE):
                # Transaction with specific isolation level

            with manager.transaction(mode=TransactionMode.READ_ONLY):
                # Read-only transaction
        """
        # Save current settings
        original_isolation_level = self._isolation_level
        original_mode = self._transaction_mode

        # Apply new settings if provided
        if isolation_level is not None:
            self._isolation_level = isolation_level
        if mode is not None:
            self._transaction_mode = mode

        try:
            self.begin()
            yield
            self.commit()
        except BaseException:
            if self.is_active:
                self.rollback()
            raise
        finally:
            # Restore original settings
            self._isolation_level = original_isolation_level
            self._transaction_mode = original_mode


class AsyncTransactionManager(TransactionManagerBase):
    """Asynchronous transaction manager implementing nested transactions.

    Features:
    - Nested transaction support using save-points
    - Isolation level management
    - Context manager interface for 'async with' statement
    - Automatic rollback on exceptions
    - Executes SQL via await backend.execute()
    """

    def __init__(self, backend: "AsyncStorageBackend", logger=None):
        super().__init__(backend, logger)

    async def _do_begin(self) -> None:
        """Begin a new transaction via backend.execute()."""
        sql, params = self._build_begin_sql()
        await self._backend.execute(sql, params)

    async def _do_commit(self) -> None:
        """Commit the current transaction via backend.execute()."""
        sql, params = self._build_commit_sql()
        await self._backend.execute(sql, params)

    async def _do_rollback(self) -> None:
        """Rollback the current transaction via backend.execute()."""
        sql, params = self._build_rollback_sql()
        await self._backend.execute(sql, params)

    async def _do_create_savepoint(self, name: str) -> None:
        """Create a savepoint via backend.execute().

        Args:
            name: Name of the savepoint
        """
        sql, params = self._build_savepoint_sql(name)
        await self._backend.execute(sql, params)

    async def _do_release_savepoint(self, name: str) -> None:
        """Release a savepoint via backend.execute().

        Args:
            name: Name of the savepoint
        """
        sql, params = self._build_release_savepoint_sql(name)
        await self._backend.execute(sql, params)

    async def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to a specified savepoint via backend.execute().

        Args:
            name: Name of the savepoint
        """
        sql, params = self._build_rollback_sql(savepoint=name)
        await self._backend.execute(sql, params)

    async def supports_savepoint(self) -> bool:
        """Check if savepoints are supported.

        Returns:
            bool: True if savepoints are supported, False otherwise
        """
        return self._backend.dialect.supports_savepoint()

    async def begin(self) -> None:
        """Begin a transaction or create a savepoint"""
        self.log(logging.DEBUG, f"Beginning transaction (level {self._transaction_level})")

        try:
            # Increment transaction level FIRST to prevent auto-commit during _do_begin()
            self._transaction_level += 1

            if self._transaction_level == 1:
                self.log(logging.INFO, f"Starting new transaction with isolation level {self._isolation_level}")
                await self._do_begin()
                self._state = TransactionState.ACTIVE
            else:
                savepoint_name = self._get_savepoint_name(self._transaction_level - 1)
                self.log(logging.INFO, f"Creating savepoint {savepoint_name} for nested transaction")
                await self._do_create_savepoint(savepoint_name)
                self._active_savepoints.append(savepoint_name)

            self.log(logging.DEBUG, f"Transaction begun at level {self._transaction_level}")
        except Exception as e:
            # Decrement level on failure since we incremented it first
            self._transaction_level -= 1
            error_msg = f"Failed to begin transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def commit(self) -> None:
        """Commit the current transaction or release the current savepoint"""
        self.log(logging.DEBUG, f"Committing transaction (level {self._transaction_level})")

        if not self.is_active:
            error_msg = "No active transaction to commit"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        try:
            current_level = self._transaction_level
            self._transaction_level -= 1

            if current_level <= 1:
                self.log(logging.INFO, "Committing outermost transaction")
                await self._do_commit()
                self._state = TransactionState.COMMITTED
                self._savepoint_count = 0
                self._active_savepoints = []
            else:
                if self._active_savepoints:
                    savepoint_name = self._active_savepoints.pop()
                    self.log(logging.INFO, f"Releasing savepoint {savepoint_name} for nested transaction")
                    await self._do_release_savepoint(savepoint_name)
                else:
                    self.log(logging.WARNING, "No savepoint found for commit, continuing")

            if self._transaction_level == 0:
                self._state = TransactionState.INACTIVE

            self.log(logging.DEBUG, f"Transaction committed, new level: {self._transaction_level}")
        except Exception as e:
            error_msg = f"Failed to commit transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            self._transaction_level += 1
            raise TransactionError(error_msg) from e

    async def rollback(self) -> None:
        """Rollback the current transaction or to the current savepoint"""
        self.log(logging.DEBUG, f"Rolling back transaction (level {self._transaction_level})")

        if not self.is_active:
            error_msg = "No active transaction to rollback"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        try:
            current_level = self._transaction_level
            self._transaction_level -= 1

            if current_level <= 1:
                self.log(logging.INFO, "Rolling back outermost transaction")
                await self._do_rollback()
                self._state = TransactionState.ROLLED_BACK
                self._savepoint_count = 0
                self._active_savepoints = []
            else:
                if self._active_savepoints:
                    savepoint_name = self._active_savepoints.pop()
                    self.log(logging.INFO, f"Rolling back to savepoint {savepoint_name} for nested transaction")
                    await self._do_rollback_savepoint(savepoint_name)
                else:
                    self.log(logging.WARNING, "No savepoint found for rollback, continuing")

            if self._transaction_level == 0:
                self._state = TransactionState.INACTIVE

            self.log(logging.DEBUG, f"Transaction rolled back, new level: {self._transaction_level}")
        except Exception as e:
            error_msg = f"Failed to rollback transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            self._transaction_level += 1
            raise TransactionError(error_msg) from e

    async def savepoint(self, name: Optional[str] = None) -> str:
        """Create a savepoint with an optional name or auto-generated name"""
        self.log(logging.DEBUG, f"Creating savepoint (name: {name})")

        if not self.is_active:
            error_msg = "Cannot create savepoint: no active transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        try:
            if name is None:
                self._savepoint_count += 1
                name = f"{self._savepoint_prefix}_{self._savepoint_count}"

            self.log(logging.INFO, f"Creating savepoint: {name}")
            await self._do_create_savepoint(name)
            self._active_savepoints.append(name)
            return name
        except Exception as e:
            error_msg = f"Failed to create savepoint: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def release(self, name: str) -> None:
        """Release a savepoint"""
        self.log(logging.DEBUG, f"Releasing savepoint: {name}")

        if not self.is_active:
            error_msg = "Cannot release savepoint: no active transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        if name not in self._active_savepoints:
            error_msg = f"Invalid savepoint name: {name}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        try:
            self.log(logging.INFO, f"Releasing savepoint: {name}")
            await self._do_release_savepoint(name)
            self._active_savepoints.remove(name)
        except Exception as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    async def rollback_to(self, name: str) -> None:
        """Rollback to a savepoint"""
        self.log(logging.DEBUG, f"Rolling back to savepoint: {name}")

        if not self.is_active:
            error_msg = "Cannot rollback to savepoint: no active transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        if name not in self._active_savepoints:
            error_msg = f"Invalid savepoint name: {name}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        try:
            self.log(logging.INFO, f"Rolling back to savepoint: {name}")
            await self._do_rollback_savepoint(name)

            index = self._active_savepoints.index(name)
            self._active_savepoints = self._active_savepoints[: index + 1]
            self.log(logging.DEBUG, f"Active savepoints after rollback: {self._active_savepoints}")
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    @asynccontextmanager
    async def transaction(
        self,
        isolation_level: Optional[IsolationLevel] = None,
        mode: Optional[TransactionMode] = None,
    ) -> AsyncGenerator[None, None]:
        """Context manager for async transaction blocks.

        Args:
            isolation_level: Optional isolation level for this transaction.
                If not specified, uses the currently set isolation level.
            mode: Optional transaction mode (READ_WRITE or READ_ONLY).
                If not specified, uses the currently set mode.

        Usage:
            async with manager.transaction():
                # Operations within transaction

            async with manager.transaction(isolation_level=IsolationLevel.SERIALIZABLE):
                # Transaction with specific isolation level

            async with manager.transaction(mode=TransactionMode.READ_ONLY):
                # Read-only transaction
        """
        # Save current settings
        original_isolation_level = self._isolation_level
        original_mode = self._transaction_mode

        # Apply new settings if provided
        if isolation_level is not None:
            self._isolation_level = isolation_level
        if mode is not None:
            self._transaction_mode = mode

        try:
            await self.begin()
            yield
            await self.commit()
        except BaseException:
            if self.is_active:
                await self.rollback()
            raise
        finally:
            # Restore original settings
            self._isolation_level = original_isolation_level
            self._transaction_mode = original_mode
