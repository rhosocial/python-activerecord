# src/rhosocial/activerecord/backend/errors.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List, Tuple


class DatabaseError(Exception):
    """Base class for database errors"""

    pass


class ConnectionError(DatabaseError):
    """Connection error"""

    pass


class TransactionError(DatabaseError):
    """Transaction error"""

    pass


class QueryError(DatabaseError):
    """Query error"""

    pass


class ValidationError(DatabaseError):
    """Data validation error"""

    pass


class LockError(DatabaseError):
    """Lock error"""

    pass


class DeadlockError(LockError):
    """Deadlock error"""

    pass


class IntegrityError(DatabaseError):
    """Integrity constraint error"""

    pass


class TypeConversionError(DatabaseError):
    """Type conversion error"""

    pass


class OperationalError(DatabaseError):
    """Operational error (timeout, connection lost, etc.)"""

    pass


class RecordNotFound(DatabaseError):
    """Record not found"""

    pass


class BulkOperationError(DatabaseError):
    """Base class for bulk operation errors"""

    pass


class BulkValidationError(BulkOperationError):
    """Bulk validation failed, contains indices and error messages of failed records"""

    def __init__(self, errors: "List[Tuple[int, str]]", message: str = "Bulk validation failed"):
        self.errors = errors
        details = "; ".join(f"[{idx}] {msg}" for idx, msg in errors)
        super().__init__(f"{message}: {details}")


class BulkStateError(BulkOperationError):
    """Record state does not meet bulk operation requirements"""

    pass


class IsolationLevelError(TransactionError):
    """Raised when attempting to change isolation level during active transaction."""

    pass


class UnsupportedTransactionModeError(TransactionError):
    """Raised when requesting an unsupported transaction mode.

    This error is raised when a transaction mode (e.g., READ ONLY) is
    requested but the database backend does not support it.

    Attributes:
        feature: The unsupported feature name.
        backend: The backend name.
    """

    def __init__(self, feature: str, backend: str, message: str = ""):
        self.feature = feature
        self.backend = backend
        error_msg = f"{backend} does not support {feature}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)


class UnsupportedIsolationLevelError(TransactionError):
    """Raised when requesting an unsupported isolation level.

    This error is raised when an isolation level is requested but the
    database backend does not support it.

    Attributes:
        isolation_level: The unsupported isolation level name.
        backend: The backend name.
    """

    def __init__(self, isolation_level: str, backend: str, message: str = ""):
        self.isolation_level = isolation_level
        self.backend = backend
        error_msg = f"{backend} does not support isolation level: {isolation_level}"
        if message:
            error_msg = f"{error_msg}. {message}"
        super().__init__(error_msg)
