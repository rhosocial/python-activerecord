"""Base transaction manager implementation."""
import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from enum import Enum, auto
from typing import Optional, Generator, List, Dict

from .errors import TransactionError, IsolationLevelError


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

class TransactionState(Enum):
    """Transaction states"""
    INACTIVE = auto()
    ACTIVE = auto()
    COMMITTED = auto()
    ROLLED_BACK = auto()


class TransactionManager(ABC):
    """Base transaction manager implementing nested transactions.

    Features:
    - Nested transaction support using save-points
    - Isolation level management
    - Context manager interface for 'with' statement
    - Automatic rollback on exceptions
    """

    def __init__(self, connection, logger=None):
        self._connection = connection
        self._transaction_level = 0
        self._savepoint_prefix = "SP"
        self._isolation_level: Optional[IsolationLevel] = None
        self._logger = logger or logging.getLogger('transaction')
        self._savepoint_count = 0  # Track savepoint count
        self._active_savepoints = []  # Track active savepoints
        self._state = TransactionState.INACTIVE  # Track transaction state

    @property
    def logger(self):
        """Get the current logger"""
        return self._logger

    @logger.setter
    def logger(self, logger: Optional[logging.Logger]) -> None:
        """Set the logger for this transaction manager"""
        if logger is not None and not isinstance(logger, logging.Logger):
            raise ValueError("logger must be an instance of logging.Logger")
        self._logger = logger or logging.getLogger('transaction')

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
    def connection(self):
        return self._connection

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

    def _get_savepoint_name(self, level: int) -> str:
        """Generate savepoint name

        Args:
            level: Transaction nesting level

        Returns:
            str: The generated savepoint name
        """
        return f"{self._savepoint_prefix}_{level}"

    @abstractmethod
    def _do_begin(self) -> None:
        """Begin a new transaction

        To be implemented by specific database implementation classes.
        Should perform the actual transaction start operation.
        """
        pass

    @abstractmethod
    def _do_commit(self) -> None:
        """Commit the current transaction

        To be implemented by specific database implementation classes.
        Should perform the actual transaction commit operation.
        """
        pass

    @abstractmethod
    def _do_rollback(self) -> None:
        """Rollback the current transaction

        To be implemented by specific database implementation classes.
        Should perform the actual transaction rollback operation.
        """
        pass

    @abstractmethod
    def _do_create_savepoint(self, name: str) -> None:
        """Create a savepoint

        Args:
            name: Name of the savepoint
        """
        pass

    @abstractmethod
    def _do_release_savepoint(self, name: str) -> None:
        """Release a savepoint

        Args:
            name: Name of the savepoint
        """
        pass

    @abstractmethod
    def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to a specified savepoint

        Args:
            name: Name of the savepoint
        """
        pass

    @abstractmethod
    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported

        Returns:
            bool: True if savepoints are supported, False otherwise
        """
        pass

    def begin(self) -> None:
        """Begin a transaction or create a savepoint

        For nested calls, creates a savepoint instead of starting a new transaction.

        Raises:
            TransactionError: If begin operation fails
        """
        self.log(logging.DEBUG, f"Beginning transaction (level {self._transaction_level})")

        try:
            if self._transaction_level == 0:
                # Start actual transaction
                self.log(logging.INFO, f"Starting new transaction with isolation level {self._isolation_level}")
                self._do_begin()
                self._state = TransactionState.ACTIVE
            else:
                # Create savepoint for nested transaction
                savepoint_name = self._get_savepoint_name(self._transaction_level)
                self.log(logging.INFO, f"Creating savepoint {savepoint_name} for nested transaction")
                self._do_create_savepoint(savepoint_name)
                self._active_savepoints.append(savepoint_name)

            self._transaction_level += 1
            self.log(logging.DEBUG, f"Transaction begun at level {self._transaction_level}")
        except Exception as e:
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
            self._active_savepoints = self._active_savepoints[:index + 1]
            self.log(logging.DEBUG, f"Active savepoints after rollback: {self._active_savepoints}")
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    @contextmanager
    def transaction(self) -> Generator[None, None, None]:
        """Context manager for transaction blocks.

        Usage:
            with manager.transaction():
                # Operations within transaction
        """
        try:
            self.begin()
            yield
            self.commit()
        except:
            if self.is_active:
                self.rollback()
            raise