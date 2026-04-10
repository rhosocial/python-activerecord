# src/rhosocial/activerecord/connection/__init__.py
"""
Connection Management Module.

Provides classes for managing database backend instances across multiple
ActiveRecord models. This module is independent of the Worker module and
can be used in:
- Web applications (FastAPI, Flask, etc.)
- CLI tools
- Cron jobs
- Worker pools

NOTE: Despite the "connection" module naming, this module manages
**backend instances**, not connections. The module name "connection"
reflects the user-facing purpose: conveniently managing groups of
related ActiveRecord classes' backend instances and providing
connection convenience. The actual management target is the backend.

This module does NOT manage connection timing. Users are responsible for
deciding when to connect and disconnect, with the following options:

1. Manual: Call ``backend.connect()`` / ``backend.introspect_and_adapt()``
   / ``backend.disconnect()`` directly.
2. Convenience: Use ``with backend.context() as ctx:`` for on-demand
   connection lifecycle control ("connect on demand, disconnect after use").

Classes:
    BackendGroup: Manage backend instances for a group of Model classes
    AsyncBackendGroup: Async version of BackendGroup
    BackendManager: Manage multiple named backend groups
    AsyncBackendManager: Async version of BackendManager
    PoolConfig: Connection pool configuration
    PoolStats: Connection pool statistics
    PooledBackend: Wrapper for pooled Backend instances
    BackendPool: Synchronous connection pool
    AsyncBackendPool: Asynchronous connection pool

Deprecated Aliases:
    ConnectionGroup: Alias for BackendGroup (will be removed in a future version)
    AsyncConnectionGroup: Alias for AsyncBackendGroup (will be removed)
    ConnectionManager: Alias for BackendManager (will be removed)
    AsyncConnectionManager: Alias for AsyncBackendManager (will be removed)

Example:
    # Single database
    from rhosocial.activerecord.connection import BackendGroup

    group = BackendGroup(
        name="main",
        models=[User, Post],
        config=MySQLConnectionConfig(host="localhost"),
        backend_class=MySQLBackend,
    )
    group.configure()

    with group.get_backend().context() as ctx:
        user = User.find_one(1)

    group.disconnect()

    # Multiple databases
    from rhosocial.activerecord.connection import BackendManager

    manager = BackendManager()
    manager.create_group(name="main", config=main_config, ...)
    manager.create_group(name="stats", config=stats_config, ...)
    manager.configure_all()

    with manager.get_group("main").get_backend().context() as ctx:
        user = User.find_one(1)

    manager.disconnect_all()

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

import warnings

from .group import BackendGroup, AsyncBackendGroup
from .manager import BackendManager, AsyncBackendManager
from .pool import (
    PoolConfig,
    PoolStats,
    PooledBackend,
    BackendPool,
    AsyncBackendPool,
)

# Deprecated aliases for backward compatibility
def __getattr__(name):
    """Provide deprecated aliases for backward compatibility."""
    aliases = {
        "ConnectionGroup": ("BackendGroup", BackendGroup),
        "AsyncConnectionGroup": ("AsyncBackendGroup", AsyncBackendGroup),
        "ConnectionManager": ("BackendManager", BackendManager),
        "AsyncConnectionManager": ("AsyncBackendManager", AsyncBackendManager),
    }
    if name in aliases:
        new_name, cls = aliases[name]
        warnings.warn(
            f"{name} is deprecated, use {new_name} instead. "
            f"{name} will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )
        return cls
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BackendGroup",
    "AsyncBackendGroup",
    "BackendManager",
    "AsyncBackendManager",
    "PoolConfig",
    "PoolStats",
    "PooledBackend",
    "BackendPool",
    "AsyncBackendPool",
    # Deprecated aliases (for backward compatibility)
    "ConnectionGroup",
    "AsyncConnectionGroup",
    "ConnectionManager",
    "AsyncConnectionManager",
]
