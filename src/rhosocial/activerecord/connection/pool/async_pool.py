# src/rhosocial/activerecord/connection/pool/async_pool.py
"""
Asynchronous connection pool module.

Provides AsyncBackendPool class for managing connection pools of asynchronous Backend instances.
"""

import asyncio
import inspect
import logging
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, Any, AsyncGenerator

from .config import PoolConfig
from .stats import PoolStats
from .pooled_backend import PooledBackend

logger = logging.getLogger(__name__)


class AsyncBackendPool:
    """Asynchronous connection pool.

    Manages Async Backend instance pooling with support for warmup, validation, timeout, etc.

    Supports two connection management modes:

    - **Persistent mode**: Connections are established at creation/warmup time
      and stay connected across acquire/release cycles.
      Suitable for async backends where connection establishment is expensive.

    - **Transient mode**: Connections are established on acquire and
      disconnected on release (controlled by ``auto_connect_on_acquire`` /
      ``auto_disconnect_on_release``).
      Suitable for lightweight async backends or when explicit connection
      lifecycle control is needed.

    .. note::
        The async pool runs on a single-threaded event loop, so cross-thread
        connection issues do not apply. The connection mode primarily controls
        whether connections are maintained across operations.

    Attributes:
        config: Connection pool configuration.
        stats: Connection pool statistics.

    Example:
        # Create connection pool (with warmup)
        config = PoolConfig(
            min_size=2,
            max_size=10,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

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

        Note: This does not warmup connections. Use create() class method
        for immediate warmup, or connections will be created lazily on first acquire.

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

        # Resolve effective connection mode from config
        # For async pools, default to persistent since there's no cross-thread concern
        self._effective_mode: str  # "persistent" or "transient"
        if config.connection_mode == "auto":
            # Async pool runs on single-threaded event loop; persistent is safe
            self._effective_mode = "persistent"
        else:
            self._effective_mode = config.connection_mode

        self._is_persistent = (self._effective_mode == "persistent")

        logger.debug(
            f"AsyncBackendPool initialized with connection_mode={self._effective_mode} "
            f"(requested={config.connection_mode})"
        )

    @property
    def connection_mode(self) -> str:
        """Effective connection management mode.

        Returns:
            ``"persistent"`` or ``"transient"``
        """
        return self._effective_mode

    @classmethod
    async def create(cls, config: PoolConfig) -> 'AsyncBackendPool':
        """Create and initialize connection pool with warmup.

        This is the recommended way to create an async pool, as it mirrors
        the synchronous BackendPool behavior of warming up connections immediately.

        Args:
            config: Connection pool configuration

        Returns:
            Initialized AsyncBackendPool with min_size connections ready

        Example:
            config = PoolConfig(min_size=2, max_size=10, ...)
            pool = await AsyncBackendPool.create(config)
            # Pool is ready with 2 connections warmed up
        """
        pool = cls(config)
        await pool._initialize()
        return pool

    async def _initialize(self) -> None:
        """Asynchronous initialization, warmup connections."""
        if self._initialized:
            return

        self._semaphore = asyncio.Semaphore(self.config.max_size)

        for _ in range(self.config.min_size):
            try:
                pooled = await self._create_backend(connect=self._is_persistent)
                if pooled:
                    self._available.append(pooled)
                    self._stats.current_available += 1
            except Exception:
                # Warmup failure does not prevent pool creation
                self._stats.total_errors += 1

        self._initialized = True

    async def _create_backend(self, connect: bool = True) -> Optional[PooledBackend]:
        """Create new Backend instance.

        Args:
            connect: Whether to connect the backend immediately.
                     In persistent mode, defaults to True.
                     In transient mode, set to False to skip connection.

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

            # Connect if requested
            if connect and hasattr(backend, 'connect'):
                if inspect.iscoroutinefunction(backend.connect):
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
                if inspect.iscoroutinefunction(pooled.backend.disconnect):
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
            self._stats.total_validation_failures += 1
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

            if inspect.iscoroutinefunction(pooled.backend.execute):
                result = await pooled.backend.execute(self.config.validation_query, [], options=options)
            else:
                result = pooled.backend.execute(self.config.validation_query, [], options=options)
            return result is not None
        except Exception:
            pooled.is_healthy = False
            self._stats.total_validation_failures += 1
            return False

    async def _reconnect_backend(self, pooled: PooledBackend) -> bool:
        """Attempt to reconnect a backend whose connection has gone stale.

        Used in persistent mode when validation fails — instead of simply
        destroying the backend, we try to reconnect it so it can be reused.

        Args:
            pooled: PooledBackend instance to reconnect

        Returns:
            True if reconnection succeeded
        """
        try:
            if hasattr(pooled.backend, 'disconnect'):
                if inspect.iscoroutinefunction(pooled.backend.disconnect):
                    await pooled.backend.disconnect()
                else:
                    pooled.backend.disconnect()
            if hasattr(pooled.backend, 'connect'):
                if inspect.iscoroutinefunction(pooled.backend.connect):
                    await pooled.backend.connect()
                else:
                    pooled.backend.connect()
            pooled.is_healthy = True
            logger.debug("Successfully reconnected stale backend in persistent mode")
            return True
        except Exception as e:
            logger.error(f"Failed to reconnect backend: {e}")
            return False

    async def _async_connect(self, backend: Any) -> None:
        """Connect a backend, handling both sync and async connect methods.

        Args:
            backend: Backend instance to connect
        """
        if hasattr(backend, 'connect'):
            if inspect.iscoroutinefunction(backend.connect):
                await backend.connect()
            else:
                backend.connect()

    async def acquire(self, timeout: Optional[float] = None) -> Any:
        """Acquire a Backend instance.

        Gets an available Backend instance from the pool. If no connection is
        available and max size not reached, creates a new connection. If max
        size reached, waits until a connection is available or timeout.

        In persistent mode, connections are already established; acquire simply
        returns a connected backend without calling connect().

        In transient mode, if ``auto_connect_on_acquire=True``, connect() is
        called on the backend before returning it.

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
                        # In persistent mode, try to reconnect before giving up
                        if self._is_persistent and await self._reconnect_backend(pooled):
                            # Reconnection succeeded, continue with this backend
                            pass
                        else:
                            await self._destroy_backend(pooled)
                            self._stats.current_available -= 1
                            continue

                pooled.mark_used()
                self._in_use[id(pooled.backend)] = pooled
                self._stats.current_available -= 1
                self._stats.current_in_use += 1
                self._stats.total_acquired += 1
                self._stats.last_acquired_at = datetime.now()

                # In transient mode, auto-connect if configured
                if not self._is_persistent and self.config.auto_connect_on_acquire:
                    try:
                        await self._async_connect(pooled.backend)
                    except Exception as e:
                        self._in_use.pop(id(pooled.backend), None)
                        self._stats.current_in_use -= 1
                        pooled.mark_unhealthy()
                        await self._destroy_backend(pooled)
                        logger.error(f"Failed to connect acquired backend: {e}")
                        continue

                return pooled.backend

            # Create new connection
            try:
                # In persistent mode, connect immediately; in transient mode, connect if configured
                should_connect = self._is_persistent or (
                    not self._is_persistent and self.config.auto_connect_on_acquire
                )
                pooled = await self._create_backend(connect=should_connect)
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

        In persistent mode, the connection stays connected; the backend is
        simply returned to the available pool.

        In transient mode, if ``auto_disconnect_on_release=True``, disconnect()
        is called before returning the backend to the pool.

        Args:
            backend: Backend instance to release
        """
        async with self._lock:
            backend_id = id(backend)
            pooled = self._in_use.pop(backend_id, None)

            if pooled is None:
                return

            self._stats.current_in_use -= 1
            self._stats.total_released += 1
            self._stats.last_released_at = datetime.now()

            # In transient mode, auto-disconnect if configured
            if not self._is_persistent and self.config.auto_disconnect_on_release:
                try:
                    if hasattr(pooled.backend, 'disconnect'):
                        if inspect.iscoroutinefunction(pooled.backend.disconnect):
                            await pooled.backend.disconnect()
                        else:
                            pooled.backend.disconnect()
                except Exception as e:
                    logger.error(f"Error during disconnect in release: {e}")
                    pooled.mark_unhealthy()

            if self.config.validate_on_return:
                if not await self._validate_backend(pooled):
                    await self._destroy_backend(pooled)
                    self._semaphore.release()
                    return

            if pooled.is_expired(self.config.max_lifetime):
                await self._destroy_backend(pooled)
                self._semaphore.release()
                return

            # Check if should be destroyed (not returned to pool)
            if not pooled.is_healthy:
                await self._destroy_backend(pooled)
                self._semaphore.release()
                return

            # Return to pool for reuse
            pooled.reset()
            self._available.append(pooled)
            self._stats.current_available += 1

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
        If already in a transaction context, reuses that transaction.

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

        # Check if already in a transaction context - reuse it
        existing_tx = ctx.get_current_async_transaction_backend()
        if existing_tx is not None:
            # Reuse existing transaction
            yield existing_tx
            return

        # Check if already in a connection context - use that connection
        existing_conn = ctx.get_current_async_connection_backend()

        if existing_conn is not None:
            # Use existing connection, start transaction on it
            tx_token = ctx._set_async_transaction_backend(existing_conn)
            try:
                await existing_conn.begin_transaction()
                yield existing_conn
                await existing_conn.commit_transaction()
            except Exception:
                await existing_conn.rollback_transaction()
                raise
            finally:
                ctx._reset_async_transaction_backend(tx_token)
            return

        # No existing context - acquire new connection
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

    async def close(self, timeout: Optional[float] = None, force: bool = False) -> None:
        """Close connection pool gracefully.

        Waits for active connections to be returned before closing.
        If timeout is reached and force is False, raises RuntimeError.
        If force is True, forcefully closes all connections after timeout.

        In both persistent and transient modes, all connections are
        disconnected during close.

        Args:
            timeout: Maximum time to wait for active connections (seconds).
                     None uses config.close_timeout. 0 means no wait.
            force: If True, forcefully close after timeout.
                   If False (default), raise RuntimeError on timeout.

        Raises:
            RuntimeError: If timeout reached and force=False, or if pool already closed

        Example:
            # Graceful close with default timeout
            await pool.close()

            # Quick close for tests
            await pool.close(timeout=0.1)

            # Force close (for emergency cleanup)
            await pool.close(timeout=1.0, force=True)
        """
        if timeout is None:
            timeout = self.config.close_timeout

        deadline = time.time() + timeout

        async with self._lock:
            if self._closed:
                raise RuntimeError("Pool is already closed")

            # Mark as closed to prevent new acquires
            self._closed = True

            # Wait for active connections to be returned
            if self._in_use and timeout > 0:
                check_interval = 0.01  # Check every 10ms
                while self._in_use and time.time() < deadline:
                    # Release lock temporarily to allow release() to proceed
                    self._lock.release()
                    try:
                        await asyncio.sleep(min(check_interval, deadline - time.time()))
                    finally:
                        await self._lock.acquire()

            # Check if all connections returned
            if self._in_use:
                if not force:
                    # Reopen pool (connections still active)
                    self._closed = False
                    in_use_count = len(self._in_use)
                    raise RuntimeError(
                        f"Pool close timeout: {in_use_count} connection(s) still in use. "
                        f"Use force=True to forcefully close, or ensure all connections "
                        f"are properly returned using context managers."
                    )
                # Force close: destroy in-use connections
                for pooled in list(self._in_use.values()):
                    await self._destroy_backend(pooled)
                self._in_use.clear()
                self._stats.current_in_use = 0

            # Destroy all available connections
            while self._available:
                pooled = self._available.popleft()
                await self._destroy_backend(pooled)
                self._stats.current_available -= 1

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
            'connection_mode': self._effective_mode,
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
            f"AsyncBackendPool(mode={self._effective_mode}, "
            f"size={self._stats.current_total}, "
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
