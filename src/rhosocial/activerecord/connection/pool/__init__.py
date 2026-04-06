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
"""

from .config import PoolConfig
from .stats import PoolStats
from .pooled_backend import PooledBackend
from .sync_pool import BackendPool
from .async_pool import AsyncBackendPool

__all__ = [
    "PoolConfig",
    "PoolStats",
    "PooledBackend",
    "BackendPool",
    "AsyncBackendPool",
]
