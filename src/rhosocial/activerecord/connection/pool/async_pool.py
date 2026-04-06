# src/rhosocial/activerecord/connection/pool/async_pool.py
"""
Asynchronous connection pool module.

Provides AsyncBackendPool class for managing connection pools of asynchronous Backend instances.
"""

import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator

from .config import PoolConfig
from .stats import PoolStats
from .pooled_backend import PooledBackend


class AsyncBackendPool:
    """Asynchronous connection pool.

    Manages Async Backend instance pooling with support for warmup, validation, timeout, etc.

    Attributes:
        config: Connection pool configuration.
        stats: Connection pool statistics.

    Example:
        # Create connection pool
        config = PoolConfig(
            min_size=2,
            max_size=10,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = AsyncBackendPool(config)

        # Method 1: Manual acquire/release
        backend = await pool.acquire()
        try:
            result = await backend.execute("SELECT 1")
        finally:
            await pool.release(backend)

        # Method 2: Context manager
        async with pool.connection() as backend:
            result = await backend.execute("SELECT 1")

        # Method 3: Transaction
        async with pool.transaction() as backend:
            await backend.execute("INSERT INTO users (name) VALUES (?)", ["Alice"])

        # Close pool
        await pool.close()
    """

    def __init__(self, config: PoolConfig):
        """Initialize connection pool.

        Args:
            config: Connection pool configuration
        """
        self.config = config
        self._available: deque[PooledBackend] = deque()
        self._in_use: Dict[int, PooledBackend] = {}
        self._stats = PoolStats()
        self._lock = asyncio.Lock()
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._closed = False
        self._initialized = False

    async def _initialize(self) -> None:
        """Asynchronous initialization, warmup connections."""
        if self._initialized:
            return

        self._semaphore = asyncio.Semaphore(self.config.max_size)

        for _ in range(self.config.min_size):
            try:
                pooled = await self._create_backend()
                if pooled:
                    self._available.append(pooled)
                    self._stats.current_available += 1
            except Exception:
                # Warmup failure does not prevent pool creation
                self._stats.total_errors += 1

        self._initialized = True

    async def _create_backend(self) -> Optional[PooledBackend]:
        """Create new Backend instance.

        Returns:
            Newly created PooledBackend instance, None on failure

        Raises:
            Exception: If creation fails
        """
        try:
            if self.config.backend_factory:
                backend = self.config.backend_factory()
            elif self.config.backend_config:
                # Create backend from config
                backend = await self._create_backend_from_config()
            else:
                raise ValueError(
                    "Either backend_factory or backend_config is required "
                    "to create Backend instances"
                )

            # Async connection
            if hasattr(backend, 'connect'):
                if asyncio.iscoroutinefunction(backend.connect):
                    await backend.connect()
                else:
                    backend.connect()

            pooled = PooledBackend(
                backend=backend,
                pool_key=str(id(self))
            )
            self._stats.total_created += 1
            return pooled
        except Exception:
            self._stats.total_errors += 1
            raise

    async def _create_backend_from_config(self) -> Any:
        """Create Backend instance from config dictionary.

        Returns:
            Backend instance

        Raises:
            ValueError: If backend type is not supported
        """
        config = self.config.backend_config
        backend_type = config.get('type', 'sqlite')

        if backend_type == 'sqlite':
            from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
            # Extract SQLite-specific config
            database = config.get('database', ':memory:')
            return AsyncSQLiteBackend(database=database)
        else:
            raise ValueError(
                f"Unsupported backend type: {backend_type}. "
                f"Only 'sqlite' is built-in. For other backends, "
                f"provide backend_factory instead."
            )

    async def _destroy_backend(self, pooled: PooledBackend) -> None:
        """Destroy Backend instance.

        Args:
            pooled: PooledBackend instance to destroy
        """
        try:
            if hasattr(pooled.backend, 'disconnect'):
                if asyncio.iscoroutinefunction(pooled.backend.disconnect):
                    await pooled.backend.disconnect()
                else:
                    pooled.backend.disconnect()
        except Exception:
            pass
        finally:
            self._stats.total_destroyed += 1

    async def _validate_backend(self, pooled: PooledBackend) -> bool:
        """Validate if connection is valid.

        Args:
            pooled: PooledBackend instance to validate

        Returns:
            True if connection is valid
        """
        if not pooled.is_healthy:
            return False

        if pooled.is_expired(self.config.max_lifetime):
            return False

        # Skip validation if no validation query
        if self.config.validation_query is None:
            return True

        try:
            # Execute validation query
            from rhosocial.activerecord.backend.options import ExecutionOptions
            from rhosocial.activerecord.backend.schema import StatementType
            options = ExecutionOptions(stmt_type=StatementType.DQL)

            if asyncio.iscoroutinefunction(pooled.backend.execute):
                result = await pooled.backend.execute(self.config.validation_query, [], options=options)
            else:
                result = pooled.backend.execute(self.config.validation_query, [], options=options)
            return result is not None
        except Exception:
            pooled.is_healthy = False
            self._stats.total_validation_failures += 1
            return False

    async def acquire(self, timeout: Optional[float] = None) -> Any:
        """Acquire a Backend instance.

        Gets an available Backend instance from the pool. If no connection is
        available and max size not reached, creates a new connection. If max
        size reached, waits until a connection is available or timeout.

        Args:
            timeout: Timeout (seconds), None uses config timeout

        Returns:
            Backend instance

        Raises:
            RuntimeError: If pool is closed
            TimeoutError: If cannot acquire connection within timeout
        """
        # Ensure initialized
        if not self._initialized:
            await self._initialize()

        if timeout is None:
            timeout = self.config.timeout

        if self._closed:
            raise RuntimeError("Pool is closed")

        # Try to acquire semaphore with timeout
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=timeout)
        except asyncio.TimeoutError:
            self._stats.total_timeouts += 1
            raise TimeoutError(
                f"Failed to acquire connection within {timeout} seconds. "
                f"Pool stats: available={self._stats.current_available}, "
                f"in_use={self._stats.current_in_use}"
            )

        async with self._lock:
            if self._closed:
                self._semaphore.release()
                raise RuntimeError("Pool is closed")

            # Try to get from available pool
            while self._available:
                pooled = self._available.popleft()

                if self.config.validate_on_borrow:
                    if not await self._validate_backend(pooled):
                        await self._destroy_backend(pooled)
                        self._stats.current_available -= 1
                        continue

                pooled.mark_used()
                self._in_use[id(pooled.backend)] = pooled
                self._stats.current_available -= 1
                self._stats.current_in_use += 1
                self._stats.total_acquired += 1
                self._stats.last_acquired_at = datetime.now()

                return pooled.backend

            # Create new connection
            try:
                pooled = await self._create_backend()
                if pooled:
                    pooled.mark_used()
                    self._in_use[id(pooled.backend)] = pooled
                    self._stats.current_in_use += 1
                    self._stats.total_acquired += 1
                    self._stats.last_acquired_at = datetime.now()
                    return pooled.backend
            except Exception:
                self._semaphore.release()
                raise

        # Should not reach here
        self._semaphore.release()
        raise RuntimeError("Failed to acquire connection")

    async def release(self, backend: Any) -> None:
        """Release Backend instance.

        Returns Backend instance to the pool for reuse.

        Args:
            backend: Backend instance to release
        """
        async with self._lock:
            backend_id = id(backend)
            pooled = self._in_use.pop(backend_id, None)

            if pooled is None:
                return

            if self.config.validate_on_return:
                if not await self._validate_backend(pooled):
                    await self._destroy_backend(pooled)
                    self._stats.current_in_use -= 1
                    self._semaphore.release()
                    return

            if pooled.is_expired(self.config.max_lifetime):
                await self._destroy_backend(pooled)
                self._stats.current_in_use -= 1
                self._semaphore.release()
                return

            pooled.reset()
            self._available.append(pooled)
            self._stats.current_available += 1
            self._stats.current_in_use -= 1
            self._stats.total_released += 1
            self._stats.last_released_at = datetime.now()

            self._semaphore.release()

    def context(self) -> 'AsyncPoolContext':
        """Get async pool context manager.

        Returns an async context manager that sets this pool in the current context.

        Returns:
            AsyncPoolContext instance

        Example:
            async with pool.context():
                # Inside context, AsyncActiveRecord can sense the pool
                users = await AsyncUser.query().all()
        """
        return AsyncPoolContext(self)

    @asynccontextmanager
    async def connection(self, timeout: Optional[float] = None) -> AsyncGenerator[Any, None]:
        """Async context manager for acquiring connection.

        Automatically acquires and releases connection.
        If already in a connection context, reuses that connection.

        Args:
            timeout: Acquire timeout (seconds)

        Yields:
            Backend instance

        Example:
            async with pool.connection() as backend:
                result = await backend.execute("SELECT 1")
        """
        from . import context as ctx

        # Check if already in a connection context
        existing_conn = ctx.get_current_async_connection_backend()
        if existing_conn is not None:
            # Reuse existing connection
            yield existing_conn
            return

        backend = await self.acquire(timeout)
        conn_token = ctx._set_async_connection_backend(backend)
        try:
            yield backend
        finally:
            ctx._reset_async_connection_backend(conn_token)
            await self.release(backend)

    @asynccontextmanager
    async def transaction(self, timeout: Optional[float] = None) -> AsyncGenerator[Any, None]:
        """Async transaction context manager, ensures connection exclusivity.

        Acquires connection and starts transaction, auto commits or rolls back.

        Args:
            timeout: Acquire timeout (seconds)

        Yields:
            Backend instance

        Example:
            async with pool.transaction() as backend:
                await backend.execute("INSERT INTO users (name) VALUES (?)", ["Alice"])
                # Auto commit or rollback
        """
        from . import context as ctx

        backend = await self.acquire(timeout)
        tx_token = ctx._set_async_transaction_backend(backend)
        conn_token = ctx._set_async_connection_backend(backend)
        try:
            await backend.begin_transaction()
            yield backend
            await backend.commit_transaction()
        except Exception:
            await backend.rollback_transaction()
            raise
        finally:
            ctx._reset_async_connection_backend(conn_token)
            ctx._reset_async_transaction_backend(tx_token)
            await self.release(backend)

    async def close(self) -> None:
        """Close connection pool.

        Destroys all connections, pool cannot be used after closing.
        """
        async with self._lock:
            self._closed = True

            while self._available:
                pooled = self._available.popleft()
                await self._destroy_backend(pooled)
                self._stats.current_available -= 1

            for pooled in list(self._in_use.values()):
                await self._destroy_backend(pooled)
            self._in_use.clear()
            self._stats.current_in_use = 0

    def get_stats(self) -> PoolStats:
        """Get statistics.

        Returns a copy of current statistics.

        Returns:
            PoolStats instance
        """
        return PoolStats(
            total_created=self._stats.total_created,
            total_destroyed=self._stats.total_destroyed,
            total_acquired=self._stats.total_acquired,
            total_released=self._stats.total_released,
            total_timeouts=self._stats.total_timeouts,
            total_errors=self._stats.total_errors,
            total_validation_failures=self._stats.total_validation_failures,
            current_available=self._stats.current_available,
            current_in_use=self._stats.current_in_use,
            created_at=self._stats.created_at,
            last_acquired_at=self._stats.last_acquired_at,
            last_released_at=self._stats.last_released_at,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Health check.

        Returns pool health status.

        Returns:
            Dictionary containing health status
        """
        stats = self.get_stats()
        return {
            'healthy': not self._closed and stats.total_errors < stats.total_created,
            'closed': self._closed,
            'utilization': stats.utilization_rate,
            'stats': {
                'available': stats.current_available,
                'in_use': stats.current_in_use,
                'total': stats.current_total,
                'errors': stats.total_errors,
            }
        }

    @property
    def is_closed(self) -> bool:
        """Check if pool is closed."""
        return self._closed

    @property
    def size(self) -> int:
        """Current total connections."""
        return self._stats.current_total

    def __len__(self) -> int:
        """Return current total connections."""
        return self.size

    def __repr__(self) -> str:
        """Return readable representation."""
        return (
            f"AsyncBackendPool(size={self._stats.current_total}, "
            f"available={self._stats.current_available}, "
            f"in_use={self._stats.current_in_use}, "
            f"closed={self._closed})"
        )


class AsyncPoolContext:
    """Async context manager for setting pool context.

    This class provides the context() method functionality for AsyncBackendPool.

    Attributes:
        _pool: The AsyncBackendPool instance.
        _pool_token: Token for resetting pool context.
    """

    def __init__(self, pool: 'AsyncBackendPool'):
        """Initialize AsyncPoolContext.

        Args:
            pool: The AsyncBackendPool instance.
        """
        self._pool = pool
        self._pool_token = None

    async def __aenter__(self) -> 'AsyncPoolContext':
        """Enter context, set pool in context."""
        from . import context as ctx
        self._pool_token = ctx._set_async_pool(self._pool)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context, reset pool context."""
        from . import context as ctx
        if self._pool_token is not None:
            ctx._reset_async_pool(self._pool_token)
