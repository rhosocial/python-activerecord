# src/rhosocial/activerecord/connection/pool/context.py
"""
Context variables and helper functions for connection pool context awareness.

This module provides the infrastructure for classes to sense the current
connection pool context, including the active pool, transaction, and connection.
"""

import contextvars
from typing import Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .sync_pool import BackendPool
    from .async_pool import AsyncBackendPool


# Context variables for connection pool state
# Synchronous pool context
_current_pool: contextvars.ContextVar[Optional['BackendPool']] = \
    contextvars.ContextVar('connection_pool', default=None)

# Asynchronous pool context
_current_async_pool: contextvars.ContextVar[Optional['AsyncBackendPool']] = \
    contextvars.ContextVar('async_connection_pool', default=None)

# Transaction backend context (works for both sync and async)
_current_transaction_backend: contextvars.ContextVar[Optional[Any]] = \
    contextvars.ContextVar('transaction_backend', default=None)

# Connection backend context (works for both sync and async)
_current_connection_backend: contextvars.ContextVar[Optional[Any]] = \
    contextvars.ContextVar('connection_backend', default=None)

# Async-specific transaction backend context
_current_async_transaction_backend: contextvars.ContextVar[Optional[Any]] = \
    contextvars.ContextVar('async_transaction_backend', default=None)

# Async-specific connection backend context
_current_async_connection_backend: contextvars.ContextVar[Optional[Any]] = \
    contextvars.ContextVar('async_connection_backend_context', default=None)


def get_current_pool() -> Optional['BackendPool']:
    """Get the current synchronous pool from context.

    Returns:
        The current BackendPool or None if not in a pool context.
    """
    return _current_pool.get()


def get_current_async_pool() -> Optional['AsyncBackendPool']:
    """Get the current asynchronous pool from context.

    Returns:
        The current AsyncBackendPool or None if not in a pool context.
    """
    return _current_async_pool.get()


def get_current_transaction_backend() -> Optional[Any]:
    """Get the current synchronous transaction backend from context.

    Returns:
        The current transaction backend (StorageBackend)
        or None if not in a transaction context.
    """
    return _current_transaction_backend.get()


def get_current_async_transaction_backend() -> Optional[Any]:
    """Get the current asynchronous transaction backend from context.

    Returns:
        The current async transaction backend (AsyncStorageBackend)
        or None if not in an async transaction context.
    """
    return _current_async_transaction_backend.get()


def get_current_connection_backend() -> Optional[Any]:
    """Get the current synchronous connection backend from context.

    Returns:
        The current connection backend (StorageBackend)
        or None if not in a connection context.

    Note:
        When inside a transaction context, this returns the same backend
        as get_current_transaction_backend().
    """
    return _current_connection_backend.get()


def get_current_async_connection_backend() -> Optional[Any]:
    """Get the current asynchronous connection backend from context.

    Returns:
        The current async connection backend (AsyncStorageBackend)
        or None if not in an async connection context.

    Note:
        When inside an async transaction context, this returns the same backend
        as get_current_async_transaction_backend().
    """
    return _current_async_connection_backend.get()


def get_current_backend() -> Optional[Any]:
    """Get the current synchronous backend for database operations.

    This is a convenience function that returns the most appropriate backend:
    1. Transaction backend if in a transaction
    2. Connection backend if in a connection context
    3. None otherwise

    Returns:
        The current backend for database operations or None.
    """
    return (
        get_current_transaction_backend() or
        get_current_connection_backend()
    )


def get_current_async_backend() -> Optional[Any]:
    """Get the current asynchronous backend for database operations.

    This is a convenience function that returns the most appropriate async backend:
    1. Async transaction backend if in an async transaction
    2. Async connection backend if in an async connection context
    3. None otherwise

    Returns:
        The current async backend for database operations or None.
    """
    return (
        get_current_async_transaction_backend() or
        get_current_async_connection_backend()
    )


# Internal functions for setting/resetting context (used by pool implementations)

def _set_pool(pool: Optional['BackendPool']) -> contextvars.Token:
    """Set the current synchronous pool in context."""
    return _current_pool.set(pool)


def _reset_pool(token: contextvars.Token) -> None:
    """Reset the synchronous pool context."""
    _current_pool.reset(token)


def _set_async_pool(pool: Optional['AsyncBackendPool']) -> contextvars.Token:
    """Set the current async pool in context."""
    return _current_async_pool.set(pool)


def _reset_async_pool(token: contextvars.Token) -> None:
    """Reset the async pool context."""
    _current_async_pool.reset(token)


def _set_transaction_backend(backend: Optional[Any]) -> contextvars.Token:
    """Set the current synchronous transaction backend in context."""
    return _current_transaction_backend.set(backend)


def _reset_transaction_backend(token: contextvars.Token) -> None:
    """Reset the synchronous transaction backend context."""
    _current_transaction_backend.reset(token)


def _set_connection_backend(backend: Optional[Any]) -> contextvars.Token:
    """Set the current synchronous connection backend in context."""
    return _current_connection_backend.set(backend)


def _reset_connection_backend(token: contextvars.Token) -> None:
    """Reset the synchronous connection backend context."""
    _current_connection_backend.reset(token)


def _set_async_transaction_backend(backend: Optional[Any]) -> contextvars.Token:
    """Set the current async transaction backend in context."""
    return _current_async_transaction_backend.set(backend)


def _reset_async_transaction_backend(token: contextvars.Token) -> None:
    """Reset the async transaction backend context."""
    _current_async_transaction_backend.reset(token)


def _set_async_connection_backend(backend: Optional[Any]) -> contextvars.Token:
    """Set the current async connection backend in context."""
    return _current_async_connection_backend.set(backend)


def _reset_async_connection_backend(token: contextvars.Token) -> None:
    """Reset the async connection backend context."""
    _current_async_connection_backend.reset(token)


__all__ = [
    # Public helper functions - synchronous
    'get_current_pool',
    'get_current_transaction_backend',
    'get_current_connection_backend',
    'get_current_backend',
    # Public helper functions - asynchronous
    'get_current_async_pool',
    'get_current_async_transaction_backend',
    'get_current_async_connection_backend',
    'get_current_async_backend',
]
