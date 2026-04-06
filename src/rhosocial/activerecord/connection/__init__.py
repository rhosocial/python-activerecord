# src/rhosocial/activerecord/connection/__init__.py
"""
Connection Management Module.

Provides classes for managing database connections across multiple ActiveRecord models.
This module is independent of the Worker module and can be used in:
- Web applications (FastAPI, Flask, etc.)
- CLI tools
- Cron jobs
- Worker pools

Classes:
    ConnectionGroup: Manage connections for a group of Model classes
    AsyncConnectionGroup: Async version of ConnectionGroup
    ConnectionManager: Manage multiple named connection groups
    AsyncConnectionManager: Async version of ConnectionManager
    PoolConfig: Connection pool configuration
    PoolStats: Connection pool statistics
    PooledBackend: Wrapper for pooled Backend instances
    BackendPool: Synchronous connection pool
    AsyncBackendPool: Asynchronous connection pool

Example:
    # Single database connection
    from rhosocial.activerecord.connection import ConnectionGroup

    with ConnectionGroup(
        name="main",
        models=[User, Post],
        config=MySQLConnectionConfig(host="localhost"),
        backend_class=MySQLBackend,
    ) as group:
        user = User.find_one(1)

    # Multiple databases
    from rhosocial.activerecord.connection import ConnectionManager

    manager = ConnectionManager()
    manager.create_group(name="main", config=main_config, ...)
    manager.create_group(name="stats", config=stats_config, ...)

    with manager:
        # All connections configured
        user = User.find_one(1)
        log = Log.create(...)

    # Connection pool usage
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
"""

from .group import ConnectionGroup, AsyncConnectionGroup
from .manager import ConnectionManager, AsyncConnectionManager
from .pool import (
    PoolConfig,
    PoolStats,
    PooledBackend,
    BackendPool,
    AsyncBackendPool,
)

__all__ = [
    "ConnectionGroup",
    "AsyncConnectionGroup",
    "ConnectionManager",
    "AsyncConnectionManager",
    "PoolConfig",
    "PoolStats",
    "PooledBackend",
    "BackendPool",
    "AsyncBackendPool",
]
