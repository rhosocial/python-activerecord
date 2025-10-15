# src/rhosocial/activerecord/backend/errors.py
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


class ReturningNotSupportedError(DatabaseError):
    """Raised when RETURNING clause is not supported by the database"""
    pass


class IsolationLevelError(TransactionError):
    """Raised when attempting to change isolation level during active transaction."""
    pass


class WindowFunctionNotSupportedError(DatabaseError):
    """Raised when window functions are not supported by the database."""
    pass


class JsonOperationNotSupportedError(DatabaseError):
    """Raised when JSON operations are not supported by the database."""
    pass


class GroupingSetNotSupportedError(DatabaseError):
    """Raised when advanced grouping operations (CUBE, ROLLUP, GROUPING SETS) are not supported."""
    pass


class CTENotSupportedError(Exception):
    """Exception raised when CTE functionality is not supported."""
    pass
