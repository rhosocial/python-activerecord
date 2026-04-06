# src/rhosocial/activerecord/connection/pool/__init__.py
"""
Connection Pool Module.

Provides connection pool implementation for managing Backend instances.

Classes:
    PoolConfig: Connection pool configuration.
    PoolStats: Connection pool statistics.
    PooledBackend: Wrapper for pooled Backend instances.
    BackendPool: Synchronous connection pool.
    AsyncBackendPool: Asynchronous connection pool.

Context Functions (Synchronous):
    get_current_pool: Get current synchronous pool from context.
    get_current_transaction_backend: Get current synchronous transaction backend.
    get_current_connection_backend: Get current synchronous connection backend.
    get_current_backend: Get current synchronous backend for database operations.

Context Functions (Asynchronous):
    get_current_async_pool: Get current asynchronous pool from context.
    get_current_async_transaction_backend: Get current async transaction backend.
    get_current_async_connection_backend: Get current async connection backend.
    get_current_async_backend: Get current async backend for database operations.

Example:
    # Synchronous usage
    from rhosocial.activerecord.connection.pool import PoolConfig, BackendPool

    config = PoolConfig(
        min_size=2,
        max_size=10,
        backend_factory=lambda: SQLiteBackend(database=":memory:")
    )
    pool = BackendPool(config)

    with pool.connection() as backend:
        result = backend.execute("SELECT 1")

    pool.close()

    # Asynchronous usage
    from rhosocial.activerecord.connection.pool import PoolConfig, AsyncBackendPool

    config = PoolConfig(
        min_size=2,
        max_size=10,
        backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
    )
    pool = AsyncBackendPool(config)

    async with pool.connection() as backend:
        result = await backend.execute("SELECT 1")

    await pool.close()

    # Context awareness example (synchronous)
    from rhosocial.activerecord.connection.pool import (
        get_current_pool,
        get_current_connection_backend,
        get_current_transaction_backend
    )

    with pool.context():
        # Inside context, can sense the pool
        current_pool = get_current_pool()

        with pool.transaction() as backend:
            # Inside transaction, can sense both transaction and connection
            tx_backend = get_current_transaction_backend()
            conn_backend = get_current_connection_backend()

    # Context awareness example (asynchronous)
    from rhosocial.activerecord.connection.pool import (
        get_current_async_pool,
        get_current_async_connection_backend,
        get_current_async_transaction_backend
    )

    async with pool.context():
        # Inside context, can sense the async pool
        current_pool = get_current_async_pool()

        async with pool.transaction() as backend:
            # Inside transaction, can sense both transaction and connection
            tx_backend = get_current_async_transaction_backend()
            conn_backend = get_current_async_connection_backend()
"""

from .config import PoolConfig
from .stats import PoolStats
from .pooled_backend import PooledBackend
from .sync_pool import BackendPool, PoolContext
from .async_pool import AsyncBackendPool, AsyncPoolContext
from .context import (
    # Synchronous context functions
    get_current_pool,
    get_current_transaction_backend,
    get_current_connection_backend,
    get_current_backend,
    # Asynchronous context functions
    get_current_async_pool,
    get_current_async_transaction_backend,
    get_current_async_connection_backend,
    get_current_async_backend,
)

__all__ = [
    "PoolConfig",
    "PoolStats",
    "PooledBackend",
    "BackendPool",
    "PoolContext",
    "AsyncBackendPool",
    "AsyncPoolContext",
    # Synchronous context functions
    "get_current_pool",
    "get_current_transaction_backend",
    "get_current_connection_backend",
    "get_current_backend",
    # Asynchronous context functions
    "get_current_async_pool",
    "get_current_async_transaction_backend",
    "get_current_async_connection_backend",
    "get_current_async_backend",
]
