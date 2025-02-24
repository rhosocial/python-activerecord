import logging
from typing import Dict, Optional, List
from ...transaction import TransactionManager, IsolationLevel
from ...errors import TransactionError


class SQLiteTransactionManager(TransactionManager):
    """SQLite transaction manager implementation"""

    # SQLite supported isolation level mappings
    _ISOLATION_LEVELS: Dict[IsolationLevel, str] = {
        IsolationLevel.SERIALIZABLE: "IMMEDIATE",  # SQLite defaults to SERIALIZABLE
        IsolationLevel.READ_UNCOMMITTED: "DEFERRED",
        # SQLite does not support READ_COMMITTED and REPEATABLE_READ
    }

    def __init__(self, connection, logger=None):
        """Initialize SQLite transaction manager

        Args:
            connection: SQLite database connection
            logger: Optional logger instance
        """
        self._connection = connection
        # SQLite uses autocommit mode by default
        self._connection.isolation_level = None
        self._savepoint_count = 0  # Track savepoint count
        self._active_savepoints = []  # Track active savepoints
        self._is_active = False  # Track transaction state
        self._isolation_level = IsolationLevel.SERIALIZABLE  # Default isolation level
        self._transaction_level = 0  # Track nesting level
        self._logger = logger or logging.getLogger('transaction')

    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log message using current logger

        Args:
            level: Log level (e.g. logging.INFO)
            msg: Log message
            *args: Format string arguments
            **kwargs: Additional logging arguments
        """
        if self._logger:
            self._logger.log(level, msg, *args, **kwargs)

    @property
    def logger(self) -> logging.Logger:
        """Get current logger instance"""
        return self._logger

    @logger.setter
    def logger(self, logger: Optional[logging.Logger]) -> None:
        """Set logger instance

        Args:
            logger: Logger instance or None to use default
        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise ValueError("logger must be an instance of logging.Logger")
        self._logger = logger or logging.getLogger('transaction')

    def _get_isolation_pragma(self) -> Optional[str]:
        """Get PRAGMA setting for corresponding isolation level"""
        if self._isolation_level == IsolationLevel.READ_UNCOMMITTED:
            return "PRAGMA read_uncommitted = 1"
        return "PRAGMA read_uncommitted = 0"

    def set_isolation_level(self, level: IsolationLevel) -> None:
        """Set transaction isolation level

        Args:
            level: Isolation level to set

        Raises:
            TransactionError: If isolation level is not supported or
                if transaction is already active
        """
        self.log(logging.DEBUG, f"Setting isolation level to {level}")

        if self.is_active:
            error_msg = "Cannot change isolation level during active transaction"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        # Check if isolation level is supported by SQLite
        if level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        self._isolation_level = level
        self.log(logging.INFO, f"Isolation level set to {level}")

    @property
    def is_active(self) -> bool:
        """Check if a transaction is currently active"""
        return self._transaction_level > 0

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
                self._is_active = True
            else:
                # Create savepoint for nested transaction
                savepoint_name = f"LEVEL{self._transaction_level}"
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
            self._transaction_level -= 1

            if self._transaction_level == 0:
                # Commit actual transaction
                self.log(logging.INFO, "Committing outermost transaction")
                self._do_commit()
                self._is_active = False
                # Reset savepoint tracking
                self._savepoint_count = 0
                self._active_savepoints = []
            else:
                # Release savepoint for inner transaction
                savepoint_name = self._active_savepoints.pop()
                self.log(logging.INFO, f"Releasing savepoint {savepoint_name} for nested transaction")
                self._do_release_savepoint(savepoint_name)

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
            self._transaction_level -= 1

            if self._transaction_level == 0:
                # Rollback actual transaction
                self.log(logging.INFO, "Rolling back outermost transaction")
                self._do_rollback()
                self._is_active = False
                # Reset savepoint tracking
                self._savepoint_count = 0
                self._active_savepoints = []
            else:
                # Rollback to savepoint for inner transaction
                savepoint_name = self._active_savepoints.pop()
                self.log(logging.INFO, f"Rolling back to savepoint {savepoint_name} for nested transaction")
                self._do_rollback_savepoint(savepoint_name)

            self.log(logging.DEBUG, f"Transaction rolled back, new level: {self._transaction_level}")
        except Exception as e:
            error_msg = f"Failed to rollback transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            # Restore transaction level on failure
            self._transaction_level += 1
            raise TransactionError(error_msg) from e

    def _do_begin(self) -> None:
        """Begin SQLite transaction"""
        try:
            # Set isolation level
            level = self._ISOLATION_LEVELS.get(self._isolation_level)
            if level:
                sql = f"BEGIN {level} TRANSACTION"
                self.log(logging.DEBUG, f"Executing: {sql}")
                self._connection.execute(sql)

                # Set corresponding PRAGMA
                pragma = self._get_isolation_pragma()
                if pragma:
                    self.log(logging.DEBUG, f"Executing: {pragma}")
                    self._connection.execute(pragma)
            else:
                # Should never reach here due to validation in set_isolation_level
                error_msg = f"Unsupported isolation level: {self._isolation_level}"
                self.log(logging.ERROR, error_msg)
                raise TransactionError(error_msg)
        except Exception as e:
            error_msg = f"Failed to begin transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def _do_commit(self) -> None:
        """Commit SQLite transaction"""
        try:
            sql = "COMMIT"
            self.log(logging.DEBUG, f"Executing: {sql}")
            self._connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to commit transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def _do_rollback(self) -> None:
        """Rollback SQLite transaction"""
        try:
            sql = "ROLLBACK"
            self.log(logging.DEBUG, f"Executing: {sql}")
            self._connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to rollback transaction: {str(e)}"
            self.log(logging.ERROR, error_msg)
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
                name = f"SP_{self._savepoint_count}"

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

    def _do_create_savepoint(self, name: str) -> None:
        """Create SQLite savepoint

        Args:
            name: Savepoint name
        """
        try:
            sql = f"SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            self._connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to create savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def _do_release_savepoint(self, name: str) -> None:
        """Release SQLite savepoint

        Args:
            name: Savepoint name
        """
        try:
            sql = f"RELEASE SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            self._connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to release savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to SQLite savepoint

        Args:
            name: Savepoint name
        """
        try:
            sql = f"ROLLBACK TO SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            self._connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported

        Returns:
            bool: Always True for SQLite
        """
        return True