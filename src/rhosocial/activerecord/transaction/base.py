"""Base transaction manager implementation."""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Generator, Optional

from .enums import IsolationLevel
from .exceptions import IsolationLevelError

class TransactionManager(ABC):
    """Base transaction manager implementing nested transactions.

    Features:
    - Nested transaction support using save-points
    - Isolation level management
    - Context manager interface for 'with' statement
    - Automatic rollback on exceptions
    """

    def __init__(self):
        self._transaction_level = 0
        self._savepoint_prefix = "SP"
        self._isolation_level: Optional[IsolationLevel] = None
        self._active = False

    @property
    def is_active(self) -> bool:
        """Check if the transaction is currently active"""
        return self._active

    @property
    def transaction_level(self) -> int:
        """Get the current transaction nesting level"""
        return self._transaction_level

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
        if self.is_active:
            raise IsolationLevelError("Cannot change isolation level while transaction is active")
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
        """Begin a new transaction

        If already within a transaction, create a savepoint.
        If this is the first transaction, start a new one.
        """
        if self._transaction_level == 0:
            self._do_begin()
            self._active = True
        elif self.supports_savepoint():
            savepoint = self._get_savepoint_name(self._transaction_level)
            self._do_create_savepoint(savepoint)
        self._transaction_level += 1

    def commit(self) -> None:
        """Commit the current transaction

        If this is the outermost transaction, perform the actual commit.
        If this is a nested transaction, release the current savepoint.
        """
        if not self._active:
            return

        if self._transaction_level > 0:
            self._transaction_level -= 1
            if self._transaction_level == 0:
                self._do_commit()
                self._active = False
            elif self.supports_savepoint():
                savepoint = self._get_savepoint_name(self._transaction_level)
                self._do_release_savepoint(savepoint)

    def rollback(self) -> None:
        """Rollback the current transaction

        If this is the outermost transaction, perform the actual rollback.
        If this is a nested transaction, rollback to the previous savepoint.
        """
        if not self._active:
            return

        if self._transaction_level > 0:
            self._transaction_level -= 1
            if self._transaction_level == 0:
                self._do_rollback()
                self._active = False
            elif self.supports_savepoint():
                savepoint = self._get_savepoint_name(self._transaction_level)
                self._do_rollback_savepoint(savepoint)

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
            self.rollback()
            raise