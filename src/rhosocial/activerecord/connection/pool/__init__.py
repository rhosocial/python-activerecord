# src/rhosocial/activerecord/connection/pool/__init__.py
"""
Connection Pool Module.

Provides connection pool implementation for managing Backend instances.

.. note::
    The connection pool (BackendPool / AsyncBackendPool) uses a QueuePool strategy
    where connections can be acquired and released across different threads/tasks.
    This is suitable **only** for database backends whose drivers report
    ``threadsafety >= 2`` (i.e., connections can be safely shared across threads).

    **Suitable backends**: PostgreSQL (psycopg, threadsafety=2), and any backend
    whose driver guarantees thread-safe connection objects.

    **Unsuitable backends**: SQLite (``check_same_thread`` restriction),
    MySQL (mysql-connector-python, threadsafety=1), and any backend whose driver
    does not guarantee thread-safe connection sharing.

    For SQLite and MySQL, use ``BackendGroup`` with ``backend.context()`` instead.
    Each thread/task should manage its own connection lifecycle via context manager,
    which naturally avoids cross-thread issues.

Classes:
    PoolConfig: Connection pool configuration.
    PoolStats: Connection pool statistics.
    PooledBackend: Wrapper for pooled Backend instances.
    BackendPool: Synchronous connection pool (QueuePool strategy).
    AsyncBackendPool: Asynchronous connection pool.
    PoolContext: Synchronous pool context manager.
    AsyncPoolContext: Asynchronous pool context manager.

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
    # PostgreSQL — suitable for connection pool (threadsafety=2)
    from rhosocial.activerecord.connection.pool import PoolConfig, BackendPool
    from rhosocial.activerecord.backend.impl.postgres import PostgresBackend

    config = PoolConfig(
        min_size=2,
        max_size=10,
        backend_factory=lambda: PostgresBackend(host="localhost", database="mydb")
    )
    pool = BackendPool.create(config)

    with pool.connection() as backend:
        result = backend.execute("SELECT 1")

    pool.close()

    # SQLite/MySQL — use BackendGroup + backend.context() instead
    from rhosocial.activerecord.connection import BackendGroup
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

    group = BackendGroup(
        name="app",
        models=[User, Post],
        config=sqlite_config,
        backend_class=SQLiteBackend,
    )
    group.configure()

    # Each thread manages its own connection lifecycle
    backend = group.get_backend()
    with backend.context():
        result = backend.execute("SELECT 1")
    # Auto-disconnect on context exit — no cross-thread issues
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
