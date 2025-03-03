import logging
from typing import Dict, Optional
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
        super().__init__(connection, logger)
        # SQLite uses autocommit mode by default
        self.connection.isolation_level = None
        self._isolation_level = IsolationLevel.SERIALIZABLE  # Default isolation level

    def _get_isolation_pragma(self) -> Optional[str]:
        """Get PRAGMA setting for corresponding isolation level"""
        if self._isolation_level == IsolationLevel.READ_UNCOMMITTED:
            return "PRAGMA read_uncommitted = 1"
        return "PRAGMA read_uncommitted = 0"

    def _get_savepoint_name(self, level: int) -> str:
        """Generate savepoint name for nested transactions

        Override base class method to match the expected naming format in tests.
        """
        return f"LEVEL{level}"

    @property
    def isolation_level(self) -> Optional[IsolationLevel]:
        """Get the current transaction isolation level"""
        return self._isolation_level

    @isolation_level.setter
    def isolation_level(self, level: Optional[IsolationLevel]):
        """Set the transaction isolation level"""
        self.log(logging.DEBUG, f"Setting isolation level to {level}")
        if self.is_active:
            self.log(logging.ERROR, "Cannot change isolation level during active transaction")
            raise TransactionError("Cannot change isolation level during active transaction")

        # Check if SQLite supports this isolation level
        if level not in self._ISOLATION_LEVELS:
            error_msg = f"Unsupported isolation level: {level}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

        self._isolation_level = level

    def _do_begin(self) -> None:
        """Begin SQLite transaction"""
        # Set isolation level
        level = self._ISOLATION_LEVELS.get(self._isolation_level)
        if level:
            sql = f"BEGIN {level} TRANSACTION"
            self.log(logging.DEBUG, f"Executing: {sql}")
            self.connection.execute(sql)

            # Set corresponding PRAGMA
            pragma = self._get_isolation_pragma()
            if pragma:
                self.log(logging.DEBUG, f"Executing: {pragma}")
                self.connection.execute(pragma)
        else:
            # Should never reach here due to validation in set_isolation_level
            error_msg = f"Unsupported isolation level: {self._isolation_level}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg)

    def _do_commit(self) -> None:
        """Commit SQLite transaction"""
        sql = "COMMIT"
        self.log(logging.DEBUG, f"Executing: {sql}")
        self.connection.execute(sql)

    def _do_rollback(self) -> None:
        """Rollback SQLite transaction"""
        sql = "ROLLBACK"
        self.log(logging.DEBUG, f"Executing: {sql}")
        self.connection.execute(sql)

    def _do_create_savepoint(self, name: str) -> None:
        """Create SQLite savepoint

        Args:
            name: Savepoint name
        """
        try:
            sql = f"SAVEPOINT {name}"
            self.log(logging.DEBUG, f"Executing: {sql}")
            self.connection.execute(sql)
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
            self.connection.execute(sql)
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
            self.connection.execute(sql)
        except Exception as e:
            error_msg = f"Failed to rollback to savepoint {name}: {str(e)}"
            self.log(logging.ERROR, error_msg)
            raise TransactionError(error_msg) from e

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported by SQLite"""
        return True  # SQLite always supports savepoints