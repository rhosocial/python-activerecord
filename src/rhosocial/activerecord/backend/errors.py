# src/rhosocial/activerecord/backend/errors.py
from typing import Any, TYPE_CHECKING

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


class StaleRecordError(DatabaseError):
    """The record was changed by another process before this update.

    Raised by optimistic locking when the UPDATE affects no rows because the
    stored version no longer matches the value the record was loaded with.
    It is a :class:`DatabaseError` subclass, so existing ``except
    DatabaseError`` handlers keep catching it, while callers can opt into
    :class:`StaleRecordError` to tell a normal concurrency conflict apart
    from connection failures, constraint violations and other database
    errors.

    Attributes:
        model: The model class whose row is stale.
        primary_key: Primary key value of the stale row (a dict for composite
            primary keys).
        expected_version: The version the UPDATE tried to match.
        operation: The operation that failed (currently ``"update"``).
    """

    def __init__(
        self,
        model: type,
        primary_key: Any,
        expected_version: int,
        operation: str = "update",
        message: str = "Record was updated by another process",
    ) -> None:
        self.model = model
        self.primary_key = primary_key
        self.expected_version = expected_version
        self.operation = operation
        super().__init__(message)


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
