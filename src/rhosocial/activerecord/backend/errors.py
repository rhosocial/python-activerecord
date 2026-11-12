"""Database error hierarchy with semantic categories.

Concrete error classes keep their names and raise sites. Semantic base classes
let an application catch by intent (data problem, missing record, policy,
concurrency, infrastructure) without checking each concrete class.

Every concrete class is still a :class:`DatabaseError`, so existing
``except DatabaseError`` handlers keep working.
"""

from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import List, Tuple


class DatabaseError(Exception):
    """Base class for database errors.

    Attributes:
        retryable: Advisory hint. ``True`` means a retry may succeed; it is not
            an automatic retry policy. Concrete classes and backends override it.
        transient: ``True`` for infrastructure failures that are expected to pass
            on retry (timeouts, lost connections); ``None`` when unknown.
        operation: Optional operation label attached by a backend.
        sqlstate: Optional SQLSTATE attached by a backend.
        driver_code: Optional driver error code attached by a backend.
        backend: Optional backend name attached by a backend.
    """

    retryable = False
    transient = None
    operation: Optional[str] = None
    sqlstate: Optional[str] = None
    driver_code: Optional[Any] = None
    backend: Optional[str] = None


# ---------------------------------------------------------------------------
# Semantic categories
# ---------------------------------------------------------------------------


class DataError(DatabaseError):
    """The data itself is invalid or violates a constraint."""

    retryable = False


class RecordError(DatabaseError):
    """The record does not exist or cannot be addressed by primary key."""

    retryable = False


class PolicyError(DatabaseError):
    """The framework refused the operation for policy reasons.

    Attributes:
        model_name: Model the policy applies to, when known.
        operation: Refused operation, when known.
    """

    retryable = False
    model_name: Optional[str] = None


class ConcurrencyError(DatabaseError):
    """A concurrent writer caused the operation to lose a race."""

    retryable = True


class InfrastructureError(DatabaseError):
    """The connection or runtime environment failed the operation.

    ``retryable`` stays False by default: authentication and permission
    failures do not improve on retry. Backends mark transient failures with
    ``attach_diagnostics(..., transient=True)``.
    """

    retryable = False


# ---------------------------------------------------------------------------
# Concrete errors
# ---------------------------------------------------------------------------


class ConnectionError(InfrastructureError):
    """Connection error"""

    pass


class TransactionError(DatabaseError):
    """Transaction error"""

    pass


class QueryError(DatabaseError):
    """Query error"""

    pass


class ValidationError(DataError):
    """Data validation error"""

    pass


class ReadOnlyError(PolicyError):
    """A write was attempted on a read-only model.

    Raised before any statement is issued, so a refused write leaves the
    database untouched. Carries the operation name and the model so callers
    can report which write was refused.
    """

    def __init__(self, model_name: str, operation: str):
        self.model_name = model_name
        self.operation = operation
        super().__init__(
            f"{operation} is not allowed on read-only model '{model_name}'. "
            f"{model_name} declares read_only() True (ReadOnlyMixin); the framework "
            f"refuses framework-level writes for it."
        )


class LockError(ConcurrencyError):
    """Lock error"""

    pass


class DeadlockError(LockError):
    """Deadlock error"""

    pass


class IntegrityError(DataError):
    """Integrity constraint error"""

    pass


class StaleRecordError(ConcurrencyError):
    """The record version no longer matches the stored row.

    Raised by optimistic locking when the UPDATE affects no rows because the
    stored version no longer matches the value the record was loaded with.
    Zero rows has two possible causes: another process updated the row, or the
    row was deleted. The message names both possibilities instead of asserting
    only the first, because distinguishing them would need another query and
    would still race with concurrent writers.

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
        message: str = (
            "Record version does not match; the row may have been updated or "
            "deleted by another process"
        ),
    ) -> None:
        self.model = model
        self.primary_key = primary_key
        self.expected_version = expected_version
        self.operation = operation
        super().__init__(message)


class TypeConversionError(DataError):
    """Type conversion error"""

    pass


class OperationalError(InfrastructureError):
    """Operational error (timeout, connection lost, etc.)"""

    pass


class RecordNotFound(RecordError):
    """Record not found"""

    pass


class UnaddressableRecordError(RecordError):
    """A keyless model was asked for single-row access by primary key.

    ``primary_key()`` returning ``None`` declares a relation with no single-row
identity,
    so ``find_one(pk)``, ``find_all([pk])``, and updating or deleting by
    primary key are not expressible. Raised in place of the incidental failures
    such ``getattr(instance, None)`` would otherwise produce, which surface as
    a bare ``TypeError: attribute name must be string, not 'NoneType'``.

    Selecting a row by some other criterion stays available: use
    ``where(...).one()``.
    """

    def __init__(self, model_name: str, operation: str):
        self.model_name = model_name
        self.operation = operation
        super().__init__(
            f"{operation} needs a primary key, but '{model_name}' declares "
            f"primary_key() None and so has no single-row identity. "
            f"Select with {model_name}.query().where(...).one() instead, or declare "
            f"a primary key if the relation really has one."
        )


class BulkOperationError(DatabaseError):
    """Base class for bulk operation errors"""

    pass


class BulkValidationError(BulkOperationError, DataError):
    """Bulk validation failed, contains indices and error messages of failed records.

    Inherits both :class:`BulkOperationError` (bulk semantics) and
    :class:`DataError` (invalid data), so either catch group works.
    """

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
    requested and the database backend does not support it.

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

    This error is raised when an isolation level is requested and the
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


def attach_diagnostics(
    error: DatabaseError,
    *,
    operation: Optional[str] = None,
    sqlstate: Optional[str] = None,
    driver_code: Optional[Any] = None,
    backend: Optional[str] = None,
    transient: Optional[bool] = None,
) -> DatabaseError:
    """Attach driver context to an error without changing its type or message.

    Backends call this right before raising, so callers and logs can tell
    which operation, SQLSTATE, or driver code produced the failure.

    Args:
        error: The error instance to annotate; returned unchanged.
        operation: Operation label such as ``"insert"`` or ``"connect"``.
        sqlstate: Driver SQLSTATE, when the driver exposes one.
        driver_code: Driver-specific numeric or string error code.
        backend: Backend name such as ``"mysql"``.
        transient: Whether an infrastructure failure is expected to pass on
            retry. A transient infrastructure error becomes ``retryable``.

    Returns:
        The same error instance, annotated.
    """
    if operation is not None:
        error.operation = operation
    if sqlstate is not None:
        error.sqlstate = sqlstate
    if driver_code is not None:
        error.driver_code = driver_code
    if backend is not None:
        error.backend = backend
    if transient is not None:
        error.transient = transient
        if transient and isinstance(error, InfrastructureError):
            error.retryable = True
    return error
