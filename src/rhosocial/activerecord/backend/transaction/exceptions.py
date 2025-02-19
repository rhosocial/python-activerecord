"""Exceptions for transaction management."""

class TransactionError(Exception):
    """Base exception for transaction related errors."""
    pass

class IsolationLevelError(TransactionError):
    """Raised when attempting to change isolation level during active transaction."""
    pass