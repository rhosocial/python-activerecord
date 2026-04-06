# src/rhosocial/activerecord/connection/pool/sync_pool.py
"""
Synchronous connection pool module.

Provides BackendPool class for managing connection pools of synchronous Backend instances.
"""

import threading
import time
from collections import deque
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any, Generator

from .config import PoolConfig
from .stats import PoolStats
from .pooled_backend import PooledBackend


class BackendPool:
    """Synchronous connection pool.

    Manages Backend instance pooling with support for warmup, validation, timeout, etc.

    Attributes:
        config: Connection pool configuration.
        stats: Connection pool statistics.

    Example:
        # Create connection pool
        config = PoolConfig(
            min_size=2,
            max_size=10,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

        # Method 1: Manual acquire/release
        backend = pool.acquire()
        try:
            result = backend.execute("SELECT 1")
        finally:
            pool.release(backend)

        # Method 2: Context manager
        with pool.connection() as backend:
            result = backend.execute("SELECT 1")

        # Method 3: Transaction
        with pool.transaction() as backend:
            backend.execute("INSERT INTO users (name) VALUES (?)", ["Alice"])

        # Close pool
        pool.close()
    """

    def __init__(self, config: PoolConfig):
        """Initialize connection pool.

        Args:
            config: Connection pool configuration
        """
        self.config = config
        self._available: deque[PooledBackend] = deque()
        self._in_use: Dict[int, PooledBackend] = {}  # id(backend) -> PooledBackend
        self._stats = PoolStats()
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._closed = False

        # Warmup connections
        self._warmup()

    def _warmup(self) -> None:
        """Warmup minimum number of connections."""
        for _ in range(self.config.min_size):
            try:
                pooled = self._create_backend()
                if pooled:
                    self._available.append(pooled)
                    self._stats.current_available += 1
            except Exception:
                # Warmup failure does not prevent pool creation
                self._stats.total_errors += 1

    def _create_backend(self) -> Optional[PooledBackend]:
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
                backend = self._create_backend_from_config()
            else:
                raise ValueError(
                    "Either backend_factory or backend_config is required "
                    "to create Backend instances"
                )

            pooled = PooledBackend(
                backend=backend,
                pool_key=str(id(self))
            )
            self._stats.total_created += 1
            return pooled
        except Exception:
            self._stats.total_errors += 1
            raise

    def _create_backend_from_config(self) -> Any:
        """Create Backend instance from config dictionary.

        Returns:
            Backend instance

        Raises:
            ValueError: If backend type is not supported
        """
        config = self.config.backend_config
        backend_type = config.get('type', 'sqlite')

        if backend_type == 'sqlite':
            from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
            # Extract SQLite-specific config
            database = config.get('database', ':memory:')
            return SQLiteBackend(database=database)
        else:
            raise ValueError(
                f"Unsupported backend type: {backend_type}. "
                f"Only 'sqlite' is built-in. For other backends, "
                f"provide backend_factory instead."
            )

    def _destroy_backend(self, pooled: PooledBackend) -> None:
        """Destroy Backend instance.

        Args:
            pooled: PooledBackend instance to destroy
        """
        try:
            if hasattr(pooled.backend, 'disconnect'):
                pooled.backend.disconnect()
        except Exception:
            pass
        finally:
            self._stats.total_destroyed += 1

    def _validate_backend(self, pooled: PooledBackend) -> bool:
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
            result = pooled.backend.execute(self.config.validation_query, [], options=options)
            return result is not None
        except Exception:
            pooled.is_healthy = False
            self._stats.total_validation_failures += 1
            return False

    def acquire(self, timeout: Optional[float] = None) -> Any:
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
        if timeout is None:
            timeout = self.config.timeout

        deadline = time.time() + timeout

        with self._condition:
            while True:
                if self._closed:
                    raise RuntimeError("Pool is closed")

                # Try to get from available pool
                while self._available:
                    pooled = self._available.popleft()

                    # Validate connection
                    if self.config.validate_on_borrow:
                        if not self._validate_backend(pooled):
                            self._destroy_backend(pooled)
                            self._stats.current_available -= 1
                            continue

                    # Mark as in use
                    pooled.mark_used()
                    self._in_use[id(pooled.backend)] = pooled
                    self._stats.current_available -= 1
                    self._stats.current_in_use += 1
                    self._stats.total_acquired += 1
                    self._stats.last_acquired_at = datetime.now()

                    return pooled.backend

                # Can create new connection
                if self._stats.current_total < self.config.max_size:
                    try:
                        pooled = self._create_backend()
                        if pooled:
                            pooled.mark_used()
                            self._in_use[id(pooled.backend)] = pooled
                            self._stats.current_in_use += 1
                            self._stats.total_acquired += 1
                            self._stats.last_acquired_at = datetime.now()
                            return pooled.backend
                    except Exception:
                        # Creation failed, continue waiting
                        pass

                # Wait for available connection
                remaining = deadline - time.time()
                if remaining <= 0:
                    self._stats.total_timeouts += 1
                    raise TimeoutError(
                        f"Failed to acquire connection within {timeout} seconds. "
                        f"Pool stats: available={self._stats.current_available}, "
                        f"in_use={self._stats.current_in_use}"
                    )

                self._condition.wait(remaining)

    def release(self, backend: Any) -> None:
        """Release Backend instance.

        Returns Backend instance to the pool for reuse.

        Args:
            backend: Backend instance to release
        """
        with self._lock:
            backend_id = id(backend)
            pooled = self._in_use.pop(backend_id, None)

            if pooled is None:
                # Does not belong to this pool
                return

            # Validate connection
            if self.config.validate_on_return:
                if not self._validate_backend(pooled):
                    self._destroy_backend(pooled)
                    self._stats.current_in_use -= 1
                    self._condition.notify()
                    return

            # Check if exceeded max lifetime
            if pooled.is_expired(self.config.max_lifetime):
                self._destroy_backend(pooled)
                self._stats.current_in_use -= 1
                self._condition.notify()
                return

            # Return to pool
            pooled.reset()
            self._available.append(pooled)
            self._stats.current_available += 1
            self._stats.current_in_use -= 1
            self._stats.total_released += 1
            self._stats.last_released_at = datetime.now()

            self._condition.notify()

    @contextmanager
    def connection(self, timeout: Optional[float] = None) -> Generator[Any, None, None]:
        """Context manager for acquiring connection.

        Automatically acquires and releases connection.

        Args:
            timeout: Acquire timeout (seconds)

        Yields:
            Backend instance

        Example:
            with pool.connection() as backend:
                result = backend.execute("SELECT 1")
        """
        backend = self.acquire(timeout)
        try:
            yield backend
        finally:
            self.release(backend)

    @contextmanager
    def transaction(self, timeout: Optional[float] = None) -> Generator[Any, None, None]:
        """Transaction context manager, ensures connection exclusivity.

        Acquires connection and starts transaction, auto commits or rolls back.

        Args:
            timeout: Acquire timeout (seconds)

        Yields:
            Backend instance

        Example:
            with pool.transaction() as backend:
                backend.execute("INSERT INTO users (name) VALUES (?)", ["Alice"])
                # Auto commit or rollback
        """
        backend = self.acquire(timeout)
        try:
            backend.begin_transaction()
            yield backend
            backend.commit_transaction()
        except Exception:
            backend.rollback_transaction()
            raise
        finally:
            self.release(backend)

    def close(self) -> None:
        """Close connection pool.

        Destroys all connections, pool cannot be used after closing.
        """
        with self._lock:
            self._closed = True

            # Destroy all available connections
            while self._available:
                pooled = self._available.popleft()
                self._destroy_backend(pooled)
                self._stats.current_available -= 1

            # Destroy all in-use connections (forced)
            for pooled in list(self._in_use.values()):
                self._destroy_backend(pooled)
            self._in_use.clear()
            self._stats.current_in_use = 0

            self._condition.notify_all()

    def get_stats(self) -> PoolStats:
        """Get statistics.

        Returns a copy of current statistics.

        Returns:
            PoolStats instance
        """
        with self._lock:
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

    def health_check(self) -> Dict[str, Any]:
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
        with self._lock:
            return self._stats.current_total

    def __len__(self) -> int:
        """Return current total connections."""
        return self.size

    def __repr__(self) -> str:
        """Return readable representation."""
        return (
            f"BackendPool(size={self._stats.current_total}, "
            f"available={self._stats.current_available}, "
            f"in_use={self._stats.current_in_use}, "
            f"closed={self._closed})"
        )
