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

    def __init__(self, connection):
        """Initialize SQLite transaction manager

        Args:
            connection: SQLite database connection
        """
        super().__init__()
        self._connection = connection
        # SQLite uses autocommit mode by default
        self._connection.isolation_level = None

    def _get_isolation_pragma(self) -> Optional[str]:
        """Get PRAGMA setting for corresponding isolation level"""
        if self._isolation_level == IsolationLevel.READ_UNCOMMITTED:
            return "PRAGMA read_uncommitted = 1"
        return "PRAGMA read_uncommitted = 0"

    def _do_begin(self) -> None:
        """Begin SQLite transaction"""
        try:
            # Set isolation level
            if self._isolation_level:
                level = self._ISOLATION_LEVELS.get(self._isolation_level)
                if level:
                    self._connection.execute(f"BEGIN {level} TRANSACTION")
                    # Set corresponding PRAGMA
                    pragma = self._get_isolation_pragma()
                    if pragma:
                        self._connection.execute(pragma)
                else:
                    raise TransactionError(f"Unsupported isolation level: {self._isolation_level}")
            else:
                # Use default isolation level (SERIALIZABLE)
                self._connection.execute("BEGIN IMMEDIATE TRANSACTION")
        except Exception as e:
            raise TransactionError(f"Failed to begin transaction: {str(e)}")

    def _do_commit(self) -> None:
        """Commit SQLite transaction"""
        try:
            self._connection.execute("COMMIT")
        except Exception as e:
            raise TransactionError(f"Failed to commit transaction: {str(e)}")

    def _do_rollback(self) -> None:
        """Rollback SQLite transaction"""
        try:
            self._connection.execute("ROLLBACK")
        except Exception as e:
            raise TransactionError(f"Failed to rollback transaction: {str(e)}")

    def _do_create_savepoint(self, name: str) -> None:
        """Create SQLite savepoint

        Args:
            name: Savepoint name
        """
        try:
            self._connection.execute(f"SAVEPOINT {name}")
        except Exception as e:
            raise TransactionError(f"Failed to create savepoint {name}: {str(e)}")

    def _do_release_savepoint(self, name: str) -> None:
        """Release SQLite savepoint

        Args:
            name: Savepoint name
        """
        try:
            self._connection.execute(f"RELEASE SAVEPOINT {name}")
        except Exception as e:
            raise TransactionError(f"Failed to release savepoint {name}: {str(e)}")

    def _do_rollback_savepoint(self, name: str) -> None:
        """Rollback to SQLite savepoint

        Args:
            name: Savepoint name
        """
        try:
            self._connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
        except Exception as e:
            raise TransactionError(f"Failed to rollback to savepoint {name}: {str(e)}")

    def supports_savepoint(self) -> bool:
        """Check if savepoints are supported

        Returns:
            bool: Always True for SQLite
        """
        return True