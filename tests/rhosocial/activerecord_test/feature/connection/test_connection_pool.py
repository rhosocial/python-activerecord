# tests/rhosocial/activerecord_test/feature/connection/test_connection_pool.py
"""
Unit tests for connection pool implementation.

Tests PoolConfig, PoolStats, PooledBackend, BackendPool, and AsyncBackendPool.

.. note::
    BackendPool uses a QueuePool strategy where connections can be acquired and
    released across different threads. This is suitable **only** for backends whose
    driver reports ``threadsafety >= 2`` (e.g., PostgreSQL with psycopg).

    For SQLite and MySQL (threadsafety < 2), use ``BackendGroup`` with
    ``backend.context()`` instead. See ``TestConcurrentAccess`` for details on
    why using BackendPool with SQLite in multi-threaded scenarios produces
    cross-thread warnings.

.. rubric:: aiosqlite Thread Leak (Fixed)

Prior to the connection-mode refactoring, the async pool tests could hang on
process exit across **all** Python versions.  The root cause was a two-part bug:

1. **Missing ``join()`` after ``aiosqlite.Connection.close()``**.
   ``aiosqlite.Connection`` inherits from ``threading.Thread`` with
   ``daemon=False``.  Calling ``close()`` only signals the background thread
   to stop; it does **not** ``join()`` it.  If ``join()`` is never called,
   the non-daemon thread keeps running and prevents the Python process from
   exiting.  Fix: added ``conn.join(timeout=5.0)`` after ``await conn.close()``
   in ``AsyncSQLiteBackend.disconnect()``.

2. **Double ``connect()`` leaking the first aiosqlite thread**.
   In transient mode with ``validate_on_borrow=True`` (the default), the
   ``acquire()`` flow was: (a) validation calls ``execute()`` which
   **auto-connects** the backend (creating an aiosqlite thread), then (b)
   ``auto_connect_on_acquire`` calls ``connect()`` again.  Because
   ``AsyncSQLiteBackend.connect()`` had no guard against re-connection, the
   old ``_connection`` was silently overwritten — its background thread was
   never ``close()``-ed or ``join()``-ed, becoming a permanent non-daemon
   thread.  Fix: added a guard in ``connect()`` that calls ``disconnect()``
   first if ``self._connection is not None``.
"""

from datetime import datetime, timedelta

import pytest

from rhosocial.activerecord.connection.pool import (
    PoolConfig,
    PoolStats,
    PooledBackend,
    BackendPool,
    AsyncBackendPool,
)
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


def execute_sql(backend, sql: str, params=None):
    """Helper to execute SQL with proper options."""
    sql_upper = sql.upper().strip()
    if 'CREATE' in sql_upper or 'DROP' in sql_upper or 'ALTER' in sql_upper:
        stmt_type = StatementType.DDL
    elif sql_upper.startswith('SELECT'):
        stmt_type = StatementType.DQL
    else:
        stmt_type = StatementType.DML
    options = ExecutionOptions(stmt_type=stmt_type)
    return backend.execute(sql, params or [], options=options)


async def async_execute_sql(backend, sql: str, params=None):
    """Helper to execute SQL asynchronously with proper options."""
    sql_upper = sql.upper().strip()
    if 'CREATE' in sql_upper or 'DROP' in sql_upper or 'ALTER' in sql_upper:
        stmt_type = StatementType.DDL
    elif sql_upper.startswith('SELECT'):
        stmt_type = StatementType.DQL
    else:
        stmt_type = StatementType.DML
    options = ExecutionOptions(stmt_type=stmt_type)
    return await backend.execute(sql, params or [], options=options)


# ============================================================
# PoolConfig Tests
# ============================================================

class TestPoolConfig:
    """Tests for PoolConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PoolConfig(backend_factory=lambda: None)

        assert config.min_size == 1
        assert config.max_size == 10
        assert config.timeout == 30.0
        assert config.idle_timeout == 300.0
        assert config.max_lifetime == 3600.0
        assert config.validate_on_borrow is True
        assert config.validate_on_return is False
        assert config.validation_query == "SELECT 1"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = PoolConfig(
            min_size=5,
            max_size=20,
            timeout=60.0,
            idle_timeout=600.0,
            max_lifetime=7200.0,
            validate_on_borrow=False,
            validate_on_return=True,
            validation_query="SELECT 1 FROM DUAL",
            backend_factory=lambda: None
        )

        assert config.min_size == 5
        assert config.max_size == 20
        assert config.timeout == 60.0
        assert config.idle_timeout == 600.0
        assert config.max_lifetime == 7200.0
        assert config.validate_on_borrow is False
        assert config.validate_on_return is True
        assert config.validation_query == "SELECT 1 FROM DUAL"

    def test_invalid_min_size(self):
        """Test that negative min_size raises ValueError."""
        with pytest.raises(ValueError, match="min_size must be >= 0"):
            PoolConfig(min_size=-1, backend_factory=lambda: None)

    def test_invalid_max_size(self):
        """Test that max_size < 1 raises ValueError."""
        with pytest.raises(ValueError, match="max_size must be >= 1"):
            PoolConfig(max_size=0, backend_factory=lambda: None)

    def test_min_exceeds_max(self):
        """Test that min_size > max_size raises ValueError."""
        with pytest.raises(ValueError, match="min_size cannot exceed max_size"):
            PoolConfig(min_size=10, max_size=5, backend_factory=lambda: None)

    def test_invalid_timeout(self):
        """Test that timeout <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="timeout must be > 0"):
            PoolConfig(timeout=0, backend_factory=lambda: None)

        with pytest.raises(ValueError, match="timeout must be > 0"):
            PoolConfig(timeout=-1, backend_factory=lambda: None)

    def test_invalid_idle_timeout(self):
        """Test that idle_timeout < 0 raises ValueError."""
        with pytest.raises(ValueError, match="idle_timeout must be >= 0"):
            PoolConfig(idle_timeout=-1, backend_factory=lambda: None)

    def test_invalid_max_lifetime(self):
        """Test that max_lifetime <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="max_lifetime must be > 0"):
            PoolConfig(max_lifetime=0, backend_factory=lambda: None)

    def test_validation_query_none_with_validation_enabled(self):
        """Test that validation_query=None with validation enabled raises ValueError."""
        with pytest.raises(ValueError, match="validation_query cannot be None"):
            PoolConfig(
                validate_on_borrow=True,
                validation_query=None,
                backend_factory=lambda: None
            )

    def test_validation_disabled_no_query(self):
        """Test that validation can be disabled without query."""
        config = PoolConfig(
            validate_on_borrow=False,
            validate_on_return=False,
            validation_query=None,
            backend_factory=lambda: None
        )
        assert config.validation_query is None

    def test_clone(self):
        """Test clone method."""
        config = PoolConfig(
            min_size=2,
            max_size=10,
            backend_factory=lambda: None
        )
        cloned = config.clone(min_size=5, timeout=60.0)

        assert cloned.min_size == 5
        assert cloned.max_size == 10
        assert cloned.timeout == 60.0
        assert config.min_size == 2  # Original unchanged


# ============================================================
# PoolStats Tests
# ============================================================

class TestPoolStats:
    """Tests for PoolStats class."""

    def test_default_stats(self):
        """Test default statistics values."""
        stats = PoolStats()

        assert stats.total_created == 0
        assert stats.total_destroyed == 0
        assert stats.total_acquired == 0
        assert stats.total_released == 0
        assert stats.total_timeouts == 0
        assert stats.total_errors == 0
        assert stats.total_validation_failures == 0
        assert stats.current_available == 0
        assert stats.current_in_use == 0
        assert stats.created_at is not None

    def test_current_total(self):
        """Test current_total property."""
        stats = PoolStats(current_available=3, current_in_use=2)
        assert stats.current_total == 5

    def test_utilization_rate(self):
        """Test utilization_rate property."""
        stats = PoolStats(current_available=3, current_in_use=2)
        assert stats.utilization_rate == 0.4  # 2/5

        stats = PoolStats(current_available=0, current_in_use=0)
        assert stats.utilization_rate == 0.0

    def test_uptime(self):
        """Test uptime property."""
        stats = PoolStats(created_at=datetime.now() - timedelta(seconds=10))
        assert stats.uptime >= 10.0

    def test_acquire_rate(self):
        """Test acquire_rate property."""
        stats = PoolStats(
            total_acquired=100,
            created_at=datetime.now() - timedelta(seconds=10)
        )
        # Use approximate comparison due to timing
        assert stats.acquire_rate > 9.0  # Approximately 10

    def test_error_rate(self):
        """Test error_rate property."""
        stats = PoolStats(
            total_acquired=50,
            total_released=50,
            total_errors=10
        )
        assert stats.error_rate == 0.1  # 10/100

    def test_to_dict(self):
        """Test to_dict method."""
        stats = PoolStats(
            total_created=10,
            current_available=3,
            current_in_use=2
        )
        d = stats.to_dict()

        assert d['total_created'] == 10
        assert d['current_available'] == 3
        assert d['current_in_use'] == 2
        assert d['current_total'] == 5
        assert 'utilization_rate' in d
        assert 'uptime' in d


# ============================================================
# PooledBackend Tests
# ============================================================

class TestPooledBackend:
    """Tests for PooledBackend class."""

    def test_basic_creation(self):
        """Test basic PooledBackend creation."""
        backend = object()  # Mock backend
        pooled = PooledBackend(backend=backend, pool_key="test-pool")

        assert pooled.backend is backend
        assert pooled.pool_key == "test-pool"
        assert pooled.use_count == 0
        assert pooled.is_healthy is True
        assert pooled.created_at is not None

    def test_mark_used(self):
        """Test mark_used method."""
        pooled = PooledBackend(backend=object(), pool_key="test")

        pooled.mark_used()
        assert pooled.use_count == 1

        pooled.mark_used()
        assert pooled.use_count == 2

    def test_is_expired(self):
        """Test is_expired method."""
        # Create backend with old timestamp
        old_time = datetime.now() - timedelta(seconds=100)
        pooled = PooledBackend(
            backend=object(),
            pool_key="test",
            created_at=old_time
        )

        assert pooled.is_expired(50) is True   # 100s > 50s
        assert pooled.is_expired(200) is False  # 100s < 200s

    def test_is_idle(self):
        """Test is_idle method."""
        old_time = datetime.now() - timedelta(seconds=100)
        pooled = PooledBackend(
            backend=object(),
            pool_key="test",
            last_used_at=old_time
        )

        assert pooled.is_idle(50) is True   # 100s > 50s
        assert pooled.is_idle(200) is False  # 100s < 200s

    def test_age(self):
        """Test age method."""
        old_time = datetime.now() - timedelta(seconds=10)
        pooled = PooledBackend(
            backend=object(),
            pool_key="test",
            created_at=old_time
        )

        assert pooled.age() >= 10.0

    def test_idle_time(self):
        """Test idle_time method."""
        old_time = datetime.now() - timedelta(seconds=5)
        pooled = PooledBackend(
            backend=object(),
            pool_key="test",
            last_used_at=old_time
        )

        assert pooled.idle_time() >= 5.0

    def test_reset(self):
        """Test reset method."""
        pooled = PooledBackend(backend=object(), pool_key="test")
        pooled.is_healthy = False

        pooled.reset()
        assert pooled.is_healthy is True

    def test_mark_unhealthy(self):
        """Test mark_unhealthy method."""
        pooled = PooledBackend(backend=object(), pool_key="test")

        pooled.mark_unhealthy()
        assert pooled.is_healthy is False

    def test_repr(self):
        """Test __repr__ method."""
        pooled = PooledBackend(backend=object(), pool_key="test-pool")
        repr_str = repr(pooled)

        assert "PooledBackend" in repr_str
        assert "test-pool" in repr_str


# ============================================================
# BackendPool Tests
# ============================================================

class TestBackendPool:
    """Tests for BackendPool class."""

    def test_pool_creation_with_factory(self):
        """Test pool creation with backend_factory."""
        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            assert pool.size >= 2  # min_size warmed up
            assert not pool.is_closed

            stats = pool.get_stats()
            assert stats.total_created >= 2
            assert stats.current_available >= 2
        finally:
            pool.close()

    def test_pool_creation_with_config(self):
        """Test pool creation with backend_config."""
        config = PoolConfig(
            min_size=0,
            max_size=5,
            backend_config={
                'type': 'sqlite',
                'database': ':memory:'
            }
        )
        pool = BackendPool.create(config)

        try:
            assert pool.size == 0  # min_size=0, no warmup
        finally:
            pool.close()

    def test_acquire_release(self):
        """Test basic acquire and release."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            backend = pool.acquire()
            try:
                assert backend is not None
                stats = pool.get_stats()
                assert stats.current_in_use == 1
                assert stats.total_acquired == 1
            finally:
                pool.release(backend)

            stats = pool.get_stats()
            assert stats.current_in_use == 0
            assert stats.current_available >= 1
            assert stats.total_released == 1
        finally:
            pool.close()

    def test_connection_context_manager(self):
        """Test connection context manager."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            with pool.connection() as backend:
                assert backend is not None
                stats = pool.get_stats()
                assert stats.current_in_use == 1

            stats = pool.get_stats()
            assert stats.current_in_use == 0
        finally:
            pool.close()

    def test_transaction_context_manager(self, tmp_path):
        """Test transaction context manager."""
        # Use a file database instead of :memory: because with auto_disconnect_on_release=True,
        # connections are disconnected when released, so :memory: database would lose data.
        db_file = tmp_path / "test_tx.db"
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=str(db_file))
        )
        pool = BackendPool.create(config)

        try:
            # Create table first
            with pool.connection() as backend:
                execute_sql(backend, "CREATE TABLE test_tx (id INTEGER PRIMARY KEY, value TEXT)")

            # Test successful transaction
            with pool.transaction() as backend:
                execute_sql(backend, "INSERT INTO test_tx (value) VALUES (?)", ["test1"])

            # Verify data was committed
            with pool.connection() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DQL)
                result = backend.execute("SELECT COUNT(*) FROM test_tx", [], options=options)
                assert result.data[0]['COUNT(*)'] == 1

            # Test failed transaction (rollback)
            try:
                with pool.transaction() as backend:
                    execute_sql(backend, "INSERT INTO test_tx (value) VALUES (?)", ["test2"])
                    raise ValueError("Simulated error")
            except ValueError:
                pass

            # Verify data was rolled back
            with pool.connection() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DQL)
                result = backend.execute("SELECT COUNT(*) FROM test_tx", [], options=options)
                assert result.data[0]['COUNT(*)'] == 1  # Only test1 committed
        finally:
            pool.close()

    def test_max_size_limit(self):
        """Test that max_size limit is enforced."""
        config = PoolConfig(
            min_size=0,
            max_size=2,
            timeout=1.0,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # Acquire all connections
            backend1 = pool.acquire()
            backend2 = pool.acquire()

            assert pool.size == 2

            # Third acquire should timeout
            with pytest.raises(TimeoutError):
                pool.acquire(timeout=0.5)

            # Release one
            pool.release(backend1)

            # Now acquire should work
            backend3 = pool.acquire()
            pool.release(backend2)
            pool.release(backend3)
        finally:
            pool.close()

    def test_health_check(self):
        """Test health_check method."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            health = pool.health_check()

            assert health['healthy'] is True
            assert health['closed'] is False
            assert 'stats' in health
        finally:
            pool.close()

    def test_close(self):
        """Test pool close."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            close_timeout=0.1,  # Quick timeout for tests
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        assert not pool.is_closed

        pool.close(timeout=0.1)

        assert pool.is_closed
        health = pool.health_check()
        assert health['closed'] is True

        # Acquire after close should fail
        with pytest.raises(RuntimeError, match="Pool is closed"):
            pool.acquire()

    def test_close_after_connections_returned(self):
        """Test pool closes immediately after all connections are returned.

        This test verifies that close() does not wait or hang when all
        connections have been properly returned to the pool.
        """
        config = PoolConfig(
            min_size=1,
            max_size=3,
            close_timeout=0.1,  # Quick timeout for tests
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # Acquire multiple connections
            backend1 = pool.acquire()
            backend2 = pool.acquire()
            backend3 = pool.acquire()

            stats = pool.get_stats()
            assert stats.current_in_use == 3
            assert stats.current_available == 0

            # Return all connections
            pool.release(backend1)
            pool.release(backend2)
            pool.release(backend3)

            stats = pool.get_stats()
            assert stats.current_in_use == 0
            assert stats.current_available == 3

            # Close should complete immediately without waiting
            pool.close(timeout=0.1)

            assert pool.is_closed
            health = pool.health_check()
            assert health['closed'] is True
            assert health['stats']['available'] == 0
            assert health['stats']['in_use'] == 0
        except Exception:
            pool.close(timeout=0.1, force=True)
            raise

    def test_close_with_context_manager(self):
        """Test pool closes properly after using context managers."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            close_timeout=0.1,  # Quick timeout for tests
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # Use connection context manager
            with pool.connection() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DQL)
                backend.execute("SELECT 1", [], options=options)

            # Use transaction context manager
            with pool.transaction() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DQL)
                backend.execute("SELECT 1", [], options=options)

            # All connections returned, close should be immediate
            pool.close(timeout=0.1)

            assert pool.is_closed
        except Exception:
            pool.close(timeout=0.1, force=True)
            raise

    def test_close_timeout_raises_error(self):
        """Test that close() raises error when connections are still in use."""
        config = PoolConfig(
            min_size=0,
            max_size=2,
            close_timeout=0.1,  # Quick timeout for tests
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        # Acquire a connection but don't return it
        backend = pool.acquire()

        try:
            stats = pool.get_stats()
            assert stats.current_in_use == 1

            # Close should timeout and raise error
            with pytest.raises(RuntimeError, match="Pool close timeout"):
                pool.close(timeout=0.1)

            # Pool should NOT be closed
            assert not pool.is_closed

            # Connection should still be usable
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            backend.execute("SELECT 1", [], options=options)
        finally:
            pool.release(backend)
            pool.close(timeout=0.1)

    def test_close_force_destroys_connections(self):
        """Test that close(force=True) destroys in-use connections."""
        config = PoolConfig(
            min_size=0,
            max_size=2,
            close_timeout=0.1,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        # Acquire a connection but don't return it
        backend = pool.acquire()

        stats = pool.get_stats()
        assert stats.current_in_use == 1

        # Force close should succeed
        pool.close(timeout=0.1, force=True)

        # Pool should be closed
        assert pool.is_closed

        # Verify pool state after force close
        health = pool.health_check()
        assert health['closed'] is True
        assert health['stats']['in_use'] == 0
        assert health['stats']['available'] == 0

    def test_validation_on_borrow(self):
        """Test validation on borrow."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            with pool.connection() as backend:
                assert backend is not None

            stats = pool.get_stats()
            # Validation should succeed, no failures
            assert stats.total_validation_failures == 0
        finally:
            pool.close()

    def test_stats_tracking(self):
        """Test statistics tracking."""
        config = PoolConfig(
            min_size=0,
            max_size=3,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            backend1 = pool.acquire()
            backend2 = pool.acquire()
            pool.release(backend1)
            pool.release(backend2)

            stats = pool.get_stats()
            assert stats.total_created >= 2
            assert stats.total_acquired == 2
            assert stats.total_released == 2
            assert stats.total_timeouts == 0
        finally:
            pool.close()


# ============================================================
# AsyncBackendPool Tests
# ============================================================

class TestAsyncBackendPool:
    """Tests for AsyncBackendPool class."""

    @pytest.mark.asyncio
    async def test_pool_creation_with_factory(self):
        """Test async pool creation with backend_factory."""
        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # Initialize pool
            backend = await pool.acquire()
            await pool.release(backend)

            assert not pool.is_closed
            stats = pool.get_stats()
            assert stats.total_created >= 1
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_pool_creation_with_config(self):
        """Test async pool creation with backend_config."""
        config = PoolConfig(
            min_size=0,
            max_size=5,
            backend_config={
                'type': 'sqlite',
                'database': ':memory:'
            }
        )
        pool = await AsyncBackendPool.create(config)

        try:
            backend = await pool.acquire()
            await pool.release(backend)

            assert pool.size >= 1
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_acquire_release(self):
        """Test async acquire and release."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            backend = await pool.acquire()
            try:
                assert backend is not None
                stats = pool.get_stats()
                assert stats.current_in_use == 1
                assert stats.total_acquired == 1
            finally:
                await pool.release(backend)

            stats = pool.get_stats()
            assert stats.current_in_use == 0
            assert stats.current_available >= 1
            assert stats.total_released == 1
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_connection_context_manager(self):
        """Test async connection context manager."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            async with pool.connection() as backend:
                assert backend is not None
                stats = pool.get_stats()
                assert stats.current_in_use == 1

            stats = pool.get_stats()
            assert stats.current_in_use == 0
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_transaction_context_manager(self):
        """Test async transaction context manager."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # Create table first
            async with pool.connection() as backend:
                await async_execute_sql(backend, "CREATE TABLE test_tx (id INTEGER PRIMARY KEY, value TEXT)")

            # Test successful transaction
            async with pool.transaction() as backend:
                await async_execute_sql(backend, "INSERT INTO test_tx (value) VALUES (?)", ["test1"])

            # Verify data was committed
            async with pool.connection() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DQL)
                result = await backend.execute("SELECT COUNT(*) FROM test_tx", [], options=options)
                assert result.data[0]['COUNT(*)'] == 1

            # Test failed transaction (rollback)
            try:
                async with pool.transaction() as backend:
                    await async_execute_sql(backend, "INSERT INTO test_tx (value) VALUES (?)", ["test2"])
                    raise ValueError("Simulated error")
            except ValueError:
                pass

            # Verify data was rolled back
            async with pool.connection() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DQL)
                result = await backend.execute("SELECT COUNT(*) FROM test_tx", [], options=options)
                assert result.data[0]['COUNT(*)'] == 1  # Only test1 committed
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_max_size_limit(self):
        """Test that max_size limit is enforced for async pool."""
        config = PoolConfig(
            min_size=0,
            max_size=2,
            timeout=1.0,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # Acquire all connections
            backend1 = await pool.acquire()
            backend2 = await pool.acquire()

            assert pool.size == 2

            # Third acquire should timeout
            with pytest.raises(TimeoutError):
                await pool.acquire(timeout=0.5)

            # Release one
            await pool.release(backend1)

            # Now acquire should work
            backend3 = await pool.acquire()
            await pool.release(backend2)
            await pool.release(backend3)
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test async health_check method."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            backend = await pool.acquire()
            await pool.release(backend)

            health = await pool.health_check()

            assert health['healthy'] is True
            assert health['closed'] is False
            assert 'stats' in health
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_close(self):
        """Test async pool close."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            close_timeout=0.1,  # Quick timeout for tests
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        backend = await pool.acquire()
        await pool.release(backend)

        assert not pool.is_closed

        await pool.close(timeout=0.1)

        assert pool.is_closed
        health = await pool.health_check()
        assert health['closed'] is True

        # Acquire after close should fail
        with pytest.raises(RuntimeError, match="Pool is closed"):
            await pool.acquire()

    @pytest.mark.asyncio
    async def test_close_after_connections_returned(self):
        """Test async pool closes immediately after all connections are returned.

        This test verifies that close() does not wait or hang when all
        connections have been properly returned to the pool.
        """
        config = PoolConfig(
            min_size=1,
            max_size=3,
            close_timeout=0.1,  # Quick timeout for tests
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # Acquire multiple connections
            backend1 = await pool.acquire()
            backend2 = await pool.acquire()
            backend3 = await pool.acquire()

            stats = pool.get_stats()
            assert stats.current_in_use == 3
            assert stats.current_available == 0

            # Return all connections
            await pool.release(backend1)
            await pool.release(backend2)
            await pool.release(backend3)

            stats = pool.get_stats()
            assert stats.current_in_use == 0
            assert stats.current_available == 3

            # Close should complete immediately without waiting
            await pool.close(timeout=0.1)

            assert pool.is_closed
            health = await pool.health_check()
            assert health['closed'] is True
            assert health['stats']['available'] == 0
            assert health['stats']['in_use'] == 0
        except Exception:
            await pool.close(timeout=0.1, force=True)
            raise

    @pytest.mark.asyncio
    async def test_close_with_context_manager(self):
        """Test async pool closes properly after using context managers."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            close_timeout=0.1,  # Quick timeout for tests
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # Use connection context manager
            async with pool.connection() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DQL)
                await backend.execute("SELECT 1", [], options=options)

            # Use transaction context manager
            async with pool.transaction() as backend:
                options = ExecutionOptions(stmt_type=StatementType.DQL)
                await backend.execute("SELECT 1", [], options=options)

            # All connections returned, close should be immediate
            await pool.close(timeout=0.1)

            assert pool.is_closed
        except Exception:
            await pool.close(timeout=0.1, force=True)
            raise

    @pytest.mark.asyncio
    async def test_close_timeout_raises_error(self):
        """Test that async close() raises error when connections are still in use."""
        config = PoolConfig(
            min_size=0,
            max_size=2,
            close_timeout=0.1,  # Quick timeout for tests
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        # Acquire a connection but don't return it
        backend = await pool.acquire()

        try:
            stats = pool.get_stats()
            assert stats.current_in_use == 1

            # Close should timeout and raise error
            with pytest.raises(RuntimeError, match="Pool close timeout"):
                await pool.close(timeout=0.1)

            # Pool should NOT be closed
            assert not pool.is_closed

            # Connection should still be usable
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            await backend.execute("SELECT 1", [], options=options)
        finally:
            await pool.release(backend)
            await pool.close(timeout=0.1)

    @pytest.mark.asyncio
    async def test_close_force_destroys_connections(self):
        """Test that async close(force=True) destroys in-use connections."""
        config = PoolConfig(
            min_size=0,
            max_size=2,
            close_timeout=0.1,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        # Acquire a connection but don't return it
        backend = await pool.acquire()

        stats = pool.get_stats()
        assert stats.current_in_use == 1

        # Force close should succeed
        await pool.close(timeout=0.1, force=True)

        # Pool should be closed
        assert pool.is_closed

        # Verify pool state after force close
        health = await pool.health_check()
        assert health['closed'] is True
        assert health['stats']['in_use'] == 0
        assert health['stats']['available'] == 0


# ============================================================
# Coverage Enhancement Tests
# ============================================================

class TestPooledBackendCoverage:
    """Tests for PooledBackend edge cases."""

    def test_hold_time_when_not_acquired(self):
        """Test hold_time returns 0 when acquired_at is None."""
        pooled = PooledBackend(backend=object(), pool_key="test")
        pooled.acquired_at = None
        assert pooled.hold_time() == 0.0

    def test_is_expired_when_created_at_none(self):
        """Test is_expired returns False when created_at is None."""
        pooled = PooledBackend(backend=object(), pool_key="test")
        pooled.created_at = None
        assert pooled.is_expired(100) is False

    def test_is_idle_when_last_used_at_none(self):
        """Test is_idle returns False when last_used_at is None."""
        pooled = PooledBackend(backend=object(), pool_key="test")
        pooled.last_used_at = None
        assert pooled.is_idle(100) is False

    def test_age_when_created_at_none(self):
        """Test age returns 0 when created_at is None."""
        pooled = PooledBackend(backend=object(), pool_key="test")
        pooled.created_at = None
        assert pooled.age() == 0.0

    def test_idle_time_when_last_used_at_none(self):
        """Test idle_time returns 0 when last_used_at is None."""
        pooled = PooledBackend(backend=object(), pool_key="test")
        pooled.last_used_at = None
        assert pooled.idle_time() == 0.0


class TestPoolStatsCoverage:
    """Tests for PoolStats properties."""

    def test_avg_lifetime(self):
        """Test avg_lifetime calculation."""
        stats = PoolStats(total_created=10)
        # avg_lifetime = elapsed / total_created
        assert stats.avg_lifetime > 0

    def test_avg_lifetime_no_connections(self):
        """Test avg_lifetime returns 0 when no connections created."""
        stats = PoolStats(total_created=0)
        assert stats.avg_lifetime == 0.0

    def test_uptime_when_created_at_none(self):
        """Test uptime returns 0 when created_at is None."""
        stats = PoolStats()
        stats.created_at = None
        assert stats.uptime == 0.0


class TestSyncPoolCoverage:
    """Tests for sync pool edge cases."""

    def test_warmup_failure_handled(self):
        """Test that warmup failures are handled gracefully."""
        call_count = [0]

        def failing_factory():
            call_count[0] += 1
            if call_count[0] <= 2:  # Fail first 2 calls (warmup)
                raise RuntimeError("Connection failed")
            return SQLiteBackend(database=":memory:")

        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=failing_factory
        )
        pool = BackendPool.create(config)

        try:
            # Pool should still be created despite warmup failures
            stats = pool.get_stats()
            assert stats.total_errors >= 2
            # Acquire should succeed (third call)
            backend = pool.acquire()
            pool.release(backend)
        finally:
            pool.close()

    def test_create_backend_without_factory_or_config(self):
        """Test that creating backend without factory or config raises ValueError."""
        config = PoolConfig(
            min_size=0,
            max_size=5,
            backend_factory=None
        )
        config.backend_config = {}  # Clear config

        pool = BackendPool.create(config)

        try:
            # Directly test _create_backend which raises the error
            with pytest.raises(ValueError, match="Either backend_factory or backend_config is required"):
                pool._create_backend()
        finally:
            pool.close()

    def test_unsupported_backend_type(self):
        """Test that unsupported backend type raises ValueError."""
        config = PoolConfig(
            min_size=0,
            max_size=5,
            backend_config={
                'type': 'unsupported_db',
                'database': 'test'
            }
        )
        pool = BackendPool.create(config)

        try:
            # Directly test _create_backend which raises the error
            with pytest.raises(ValueError, match="Unsupported backend type"):
                pool._create_backend()
        finally:
            pool.close()

    def test_backend_config_creates_sqlite(self):
        """Test that backend_config can create SQLite backend."""
        config = PoolConfig(
            min_size=0,
            max_size=5,
            backend_config={
                'type': 'sqlite',
                'database': ':memory:'
            }
        )
        pool = BackendPool.create(config)

        try:
            backend = pool.acquire()
            result = execute_sql(backend, "SELECT 1")
            assert result is not None
            pool.release(backend)
        finally:
            pool.close()

    def test_validate_unhealthy_connection(self):
        """Test that unhealthy connections fail validation."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            validate_on_borrow=True,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            backend = pool.acquire()
            pooled = pool._in_use.get(id(backend))
            if pooled:
                pooled.is_healthy = False
            pool.release(backend)

            # Next acquire should handle the unhealthy connection
            backend2 = pool.acquire()
            pool.release(backend2)
        finally:
            pool.close()

    def test_validate_expired_connection(self):
        """Test that expired connections fail validation."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            max_lifetime=0.1,
            validate_on_borrow=True,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            backend = pool.acquire()
            pooled = pool._in_use.get(id(backend))
            if pooled:
                pooled.created_at = datetime.now() - timedelta(seconds=10)
            pool.release(backend)

            import time
            time.sleep(0.2)

            backend2 = pool.acquire()
            pool.release(backend2)
        finally:
            pool.close()

    def test_validate_with_exception(self):
        """Test validation when execute raises exception."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            validate_on_borrow=True,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            backend = pool.acquire()
            pool.release(backend)
            # Access internal pooled backend and corrupt it
            if pool._available:
                pooled = pool._available[0]
                # Replace backend with object that will fail validation
                pooled.backend = object()

            # Next acquire should detect validation failure
            backend2 = pool.acquire()
            pool.release(backend2)
        finally:
            pool.close()

    def test_release_unknown_backend(self):
        """Test releasing a backend that doesn't belong to the pool."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # Create a backend not from this pool
            unknown_backend = SQLiteBackend(database=":memory:")
            # Release should silently ignore
            pool.release(unknown_backend)

            stats = pool.get_stats()
            assert stats.total_released == 0
        finally:
            pool.close()

    def test_release_with_validation_failure(self):
        """Test release when validate_on_return fails."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            validate_on_return=True,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            backend = pool.acquire()
            pooled = pool._in_use.get(id(backend))
            if pooled:
                pooled.is_healthy = False
            pool.release(backend)

            # Connection should be destroyed due to validation failure
            stats = pool.get_stats()
            assert stats.current_available == 0 or stats.total_destroyed > 0
        finally:
            pool.close()

    def test_release_expired_connection(self):
        """Test release when connection is expired."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            max_lifetime=0.1,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            backend = pool.acquire()
            pooled = pool._in_use.get(id(backend))
            if pooled:
                pooled.created_at = datetime.now() - timedelta(seconds=10)
            pool.release(backend)

            # Connection should be destroyed due to expiration
            stats = pool.get_stats()
            assert stats.total_destroyed > 0
        finally:
            pool.close()


class TestAsyncPoolCoverage:
    """Tests for async pool edge cases."""

    @pytest.mark.asyncio
    async def test_async_warmup_failure_handled(self):
        """Test that async warmup failures are handled gracefully."""
        call_count = [0]

        # backend_factory should be a regular function returning backend instance
        # The pool will call connect() asynchronously
        def failing_factory():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise RuntimeError("Connection failed")
            return AsyncSQLiteBackend(database=":memory:")

        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=failing_factory
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # Async pool uses lazy initialization - need to call _initialize first
            await pool._initialize()
            stats = pool.get_stats()
            assert stats.total_errors >= 2
            backend = await pool.acquire()
            await pool.release(backend)
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_async_create_backend_without_factory_or_config(self):
        """Test that creating async backend without factory or config raises ValueError."""
        config = PoolConfig(
            min_size=0,
            max_size=5,
            backend_factory=None
        )
        config.backend_config = {}

        pool = await AsyncBackendPool.create(config)

        try:
            # Directly test _create_backend which raises the error
            with pytest.raises(ValueError, match="Either backend_factory or backend_config is required"):
                await pool._create_backend()
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_async_unsupported_backend_type(self):
        """Test that unsupported backend type raises ValueError."""
        config = PoolConfig(
            min_size=0,
            max_size=5,
            backend_config={
                'type': 'unsupported_db',
                'database': 'test'
            }
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # Directly test _create_backend which raises the error
            with pytest.raises(ValueError, match="Unsupported backend type"):
                await pool._create_backend()
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_async_backend_config_creates_sqlite(self):
        """Test that backend_config can create async SQLite backend."""
        config = PoolConfig(
            min_size=0,
            max_size=5,
            backend_config={
                'type': 'sqlite',
                'database': ':memory:'
            }
        )
        pool = await AsyncBackendPool.create(config)

        try:
            backend = await pool.acquire()
            result = await async_execute_sql(backend, "SELECT 1")
            assert result is not None
            await pool.release(backend)
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_async_validate_unhealthy_connection(self):
        """Test that unhealthy connections fail validation in async pool."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            validate_on_borrow=True,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            backend = await pool.acquire()
            pooled = pool._in_use.get(id(backend))
            if pooled:
                pooled.is_healthy = False
            await pool.release(backend)

            backend2 = await pool.acquire()
            await pool.release(backend2)
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_async_validate_expired_connection(self):
        """Test that expired connections fail validation in async pool."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            max_lifetime=0.1,
            validate_on_borrow=True,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            backend = await pool.acquire()
            pooled = pool._in_use.get(id(backend))
            if pooled:
                pooled.created_at = datetime.now() - timedelta(seconds=10)
            await pool.release(backend)

            import asyncio
            await asyncio.sleep(0.2)

            backend2 = await pool.acquire()
            await pool.release(backend2)
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_async_release_unknown_backend(self):
        """Test releasing a backend that doesn't belong to the async pool."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            unknown_backend = AsyncSQLiteBackend(database=":memory:")
            await pool.release(unknown_backend)

            stats = pool.get_stats()
            assert stats.total_released == 0
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_async_release_with_validation_failure(self):
        """Test async release when validate_on_return fails."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            validate_on_return=True,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            backend = await pool.acquire()
            pooled = pool._in_use.get(id(backend))
            if pooled:
                pooled.is_healthy = False
            await pool.release(backend)

            stats = pool.get_stats()
            assert stats.current_available == 0 or stats.total_destroyed > 0
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_async_release_expired_connection(self):
        """Test async release when connection is expired."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            max_lifetime=0.1,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            backend = await pool.acquire()
            pooled = pool._in_use.get(id(backend))
            if pooled:
                pooled.created_at = datetime.now() - timedelta(seconds=10)
            await pool.release(backend)

            stats = pool.get_stats()
            assert stats.total_destroyed > 0
        finally:
            await pool.close()


class TestPoolContextCoverage:
    """Tests for PoolContext and AsyncPoolContext coverage."""

    def test_pool_context_enter_exit(self):
        """Test PoolContext __enter__ and __exit__ methods."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # Use context manager
            with pool.context() as ctx:
                assert ctx is not None
                # Pool should be set in context
                from rhosocial.activerecord.connection.pool import context as ctx_module
                current_pool = ctx_module.get_current_pool()
                assert current_pool is pool
            # After exit, pool context should be reset
        finally:
            pool.close()

    def test_pool_context_size_property(self):
        """Test pool size property."""
        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # Size should include min_size warmup connections
            assert pool.size >= 0
            assert len(pool) == pool.size
        finally:
            pool.close()

    def test_validate_with_validation_query(self):
        """Test validation with a custom validation query."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            backend = pool.acquire()
            pool.release(backend)
            # Connection should pass validation
        finally:
            pool.close()

    def test_validate_expired_on_borrow(self):
        """Test that expired connections are rejected on borrow."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            max_lifetime=0.1,
            validate_on_borrow=True,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            backend = pool.acquire()
            pooled = pool._in_use.get(id(backend))
            if pooled:
                # Make it expired
                pooled.created_at = datetime.now() - timedelta(seconds=10)
            pool.release(backend)

            # Acquire again - should create new connection since old one expired
            backend2 = pool.acquire()
            pool.release(backend2)

            stats = pool.get_stats()
            assert stats.total_destroyed >= 1
        finally:
            pool.close()

    @pytest.mark.asyncio
    async def test_async_pool_context_enter_exit(self):
        """Test AsyncPoolContext __aenter__ and __aexit__ methods."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # Use context manager
            async with pool.context() as ctx:
                assert ctx is not None
                # Pool should be set in context
                from rhosocial.activerecord.connection.pool import context as ctx_module
                current_pool = ctx_module.get_current_async_pool()
                assert current_pool is pool
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_async_pool_size_property(self):
        """Test async pool size property."""
        config = PoolConfig(
            min_size=2,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            await pool._initialize()
            assert pool.size >= 0
            assert len(pool) == pool.size
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_async_validate_with_validation_query(self):
        """Test async validation with a custom validation query."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            backend = await pool.acquire()
            await pool.release(backend)
        finally:
            await pool.close()

    @pytest.mark.asyncio
    async def test_async_pool_health_check(self):
        """Test async pool health check."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            await pool._initialize()
            health = await pool.health_check()
            assert health['healthy'] is True
            assert health['closed'] is False
        finally:
            await pool.close()

    def test_sync_pool_health_check(self):
        """Test sync pool health check."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            health = pool.health_check()
            assert health['healthy'] is True
            assert health['closed'] is False
            assert 'utilization' in health
            assert 'stats' in health
        finally:
            pool.close()

    def test_pool_repr(self):
        """Test pool __repr__ method."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            repr_str = repr(pool)
            assert "BackendPool" in repr_str
            assert "size=" in repr_str
            assert "available=" in repr_str
            assert "in_use=" in repr_str
        finally:
            pool.close()

    @pytest.mark.asyncio
    async def test_async_pool_repr(self):
        """Test async pool __repr__ method."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            await pool._initialize()
            repr_str = repr(pool)
            assert "AsyncBackendPool" in repr_str
            assert "size=" in repr_str
        finally:
            await pool.close()


# ============================================================
# Concurrency Tests
# ============================================================

class TestConcurrentAccess:
    """Tests for concurrent access to connection pool.

    .. warning::
        These tests use SQLite with the default ``check_same_thread=True`` to
        **demonstrate** the cross-thread issue that arises when using BackendPool
        (QueuePool strategy) with a backend whose driver does not guarantee
        thread-safe connection sharing (threadsafety < 2).

        The first two tests (``test_concurrent_acquire_release`` and
        ``test_concurrent_acquire_with_limit``) will produce SQLite cross-thread
        warnings during execution. This is **expected and intentional** — the
        warnings serve as a demonstration of why BackendPool should NOT be used
        with SQLite or MySQL in multi-threaded scenarios.

        For production use with SQLite/MySQL, prefer ``BackendGroup`` with
        ``backend.context()`` so each thread manages its own connection lifecycle.
    """

    def test_concurrent_acquire_release(self):
        """Test concurrent acquire and release operations.

        .. warning::
            This test produces SQLite cross-thread warnings. This is intentional —
            it demonstrates why BackendPool (QueuePool) is unsuitable for SQLite.
            Connections are created by worker threads and later disconnected by the
            main thread in ``pool.close()``, which violates SQLite's
            ``check_same_thread`` constraint.

            For production use with SQLite, use ``BackendGroup`` with
            ``backend.context()`` instead.
        """
        import threading
        import time

        config = PoolConfig(
            min_size=1,
            max_size=5,
            # NOTE: Using default check_same_thread=True.
            # This will produce cross-thread warnings because connections created
            # by worker threads are later disconnected by the main thread in
            # pool.close(). This is exactly the problem this test demonstrates.
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)
        errors = []
        success_count = [0]
        lock = threading.Lock()

        def worker(worker_id):
            try:
                for _ in range(5):  # Each worker does 5 acquire/release cycles
                    backend = pool.acquire(timeout=5.0)
                    try:
                        # Simulate some work
                        time.sleep(0.01)
                        options = ExecutionOptions(stmt_type=StatementType.DQL)
                        backend.execute("SELECT 1", [], options=options)
                    finally:
                        pool.release(backend)
                    with lock:
                        success_count[0] += 1
            except Exception as e:
                with lock:
                    errors.append((worker_id, str(e)))

        try:
            # Create 10 concurrent workers
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # All operations should succeed
            assert len(errors) == 0, f"Errors: {errors}"
            assert success_count[0] == 50  # 10 workers * 5 cycles

            # Verify pool state
            stats = pool.get_stats()
            assert stats.current_in_use == 0
        finally:
            # Cross-thread warnings are produced here: the main thread calls
            # pool.close() which disconnects connections created by worker threads.
            pool.close(timeout=0.1)

    def test_concurrent_acquire_with_limit(self):
        """Test that concurrent acquires respect max_size limit.

        .. warning::
            This test produces SQLite cross-thread warnings for the same reason
            as ``test_concurrent_acquire_release``. See that test's docstring
            for details.
        """
        import threading

        config = PoolConfig(
            min_size=0,
            max_size=2,  # Only 2 connections allowed
            timeout=0.5,  # Short timeout
            # NOTE: Using default check_same_thread=True — cross-thread warnings
            # will appear on pool.close() for the same reason as
            # test_concurrent_acquire_release.
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)
        acquired_count = [0]
        timeout_count = [0]
        lock = threading.Lock()

        def acquire_and_hold():
            try:
                backend = pool.acquire(timeout=0.3)
                with lock:
                    acquired_count[0] += 1
                # Hold connection for a while
                import time
                time.sleep(0.2)
                pool.release(backend)
            except TimeoutError:
                with lock:
                    timeout_count[0] += 1

        try:
            # 5 threads trying to acquire, but only 2 connections available
            threads = [threading.Thread(target=acquire_and_hold) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Some should succeed, some should timeout
            assert acquired_count[0] >= 2  # At least 2 should get connections
            assert timeout_count[0] >= 1  # At least 1 should timeout
        finally:
            # Cross-thread warnings produced here (same reason as above)
            pool.close(timeout=0.1)

    def test_multiple_connections_isolation(self):
        """Test that multiple connections are isolated and operations don't interfere.

        This test uses a shared SQLite file database to verify that:
        1. Multiple connections can work concurrently without data corruption
        2. Each connection's operations are atomic and isolated
        3. No deadlocks occur during concurrent operations
        """
        import threading
        import tempfile
        import os

        # Create a temporary file database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            # Use check_same_thread=False for multi-threaded access
            config = PoolConfig(
                min_size=1,
                max_size=5,
                backend_factory=lambda: SQLiteBackend(database=db_path, check_same_thread=False)
            )
            pool = BackendPool.create(config)

            # Create shared table
            with pool.connection() as backend:
                execute_sql(backend, """
                    CREATE TABLE isolation_test (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        thread_id INTEGER NOT NULL,
                        value TEXT NOT NULL,
                        created_at REAL NOT NULL
                    )
                """)

            results = {}
            errors = []
            lock = threading.Lock()
            num_threads = 5
            operations_per_thread = 10

            def worker(thread_id):
                """Each thread performs multiple insert operations."""
                thread_results = []
                try:
                    for op_num in range(operations_per_thread):
                        with pool.connection() as backend:
                            # Insert data with thread identifier
                            value = f"thread_{thread_id}_op_{op_num}"
                            execute_sql(backend,
                                f"INSERT INTO isolation_test (thread_id, value, created_at) VALUES ({thread_id}, '{value}', julianday('now'))"
                            )

                            # Immediately verify the insert
                            result = execute_sql(backend,
                                f"SELECT value FROM isolation_test WHERE thread_id = {thread_id} ORDER BY id DESC LIMIT 1"
                            )
                            thread_results.append((op_num, result.data[0]['value'] if result.data else None))

                except Exception as e:
                    with lock:
                        errors.append((thread_id, str(e)))

                with lock:
                    results[thread_id] = thread_results

            # Start all threads
            threads = []
            for i in range(num_threads):
                t = threading.Thread(target=worker, args=(i,))
                threads.append(t)
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join(timeout=30.0)

            # Verify results
            assert len(errors) == 0, f"Errors occurred: {errors}"

            # Each thread should have completed all operations
            for thread_id in range(num_threads):
                assert thread_id in results
                assert len(results[thread_id]) == operations_per_thread

            # Verify data integrity in database
            with pool.connection() as backend:
                # Count total records
                count_result = execute_sql(backend, "SELECT COUNT(*) as cnt FROM isolation_test")
                expected_count = num_threads * operations_per_thread
                assert count_result.data[0]['cnt'] == expected_count, \
                    f"Expected {expected_count} records, got {count_result.data[0]['cnt']}"

                # Verify each thread's records
                for thread_id in range(num_threads):
                    thread_result = execute_sql(backend,
                        f"SELECT COUNT(*) as cnt FROM isolation_test WHERE thread_id = {thread_id}"
                    )
                    assert thread_result.data[0]['cnt'] == operations_per_thread, \
                        f"Thread {thread_id} expected {operations_per_thread} records, got {thread_result.data[0]['cnt']}"

                    # Verify all values are correct
                    values_result = execute_sql(backend,
                        f"SELECT value FROM isolation_test WHERE thread_id = {thread_id} ORDER BY id"
                    )
                    for i, row in enumerate(values_result.data):
                        expected_value = f"thread_{thread_id}_op_{i}"
                        assert row['value'] == expected_value, \
                            f"Thread {thread_id} op {i}: expected '{expected_value}', got '{row['value']}'"

            pool.close(timeout=1.0)

        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_concurrent_transactions_isolation(self):
        """Test that concurrent transactions on different connections are isolated.

        This test verifies transaction isolation - each transaction should see
        a consistent view of the database.
        """
        import threading
        import tempfile
        import os
        import time

        # Create a temporary file database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            # Use check_same_thread=False for multi-threaded access
            config = PoolConfig(
                min_size=2,
                max_size=5,
                backend_factory=lambda: SQLiteBackend(database=db_path, check_same_thread=False)
            )
            pool = BackendPool.create(config)

            # Create shared table
            with pool.connection() as backend:
                execute_sql(backend, """
                    CREATE TABLE tx_isolation_test (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        value INTEGER NOT NULL
                    )
                """)
                # Insert initial data
                execute_sql(backend, "INSERT INTO tx_isolation_test (name, value) VALUES ('initial', 0)")

            errors = []
            lock = threading.Lock()
            barrier = threading.Barrier(3)  # Synchronize threads

            def reader_thread():
                """Reader thread that reads data during concurrent transactions."""
                try:
                    barrier.wait(timeout=5.0)  # Synchronize start
                    time.sleep(0.1)  # Let writers start their transactions

                    with pool.connection() as backend:
                        # Should only see committed data
                        result = execute_sql(backend, "SELECT COUNT(*) as cnt FROM tx_isolation_test")
                        count = result.data[0]['cnt']

                        # We should see at least the initial record
                        # But might not see uncommitted data from writers
                        assert count >= 1, f"Expected at least 1 record, got {count}"

                except Exception as e:
                    with lock:
                        errors.append(('reader', str(e)))

            def writer_thread(thread_name, value):
                """Writer thread that performs a transaction."""
                try:
                    barrier.wait(timeout=5.0)  # Synchronize start

                    with pool.transaction() as backend:
                        # Insert data
                        execute_sql(backend,
                            f"INSERT INTO tx_isolation_test (name, value) VALUES ('{thread_name}', {value})"
                        )
                        time.sleep(0.2)  # Hold transaction open briefly
                        # Transaction will commit on exit

                except Exception as e:
                    with lock:
                        errors.append((thread_name, str(e)))

            # Start threads
            threads = [
                threading.Thread(target=reader_thread),
                threading.Thread(target=writer_thread, args=('writer1', 100)),
                threading.Thread(target=writer_thread, args=('writer2', 200)),
            ]

            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=10.0)

            # Verify results
            assert len(errors) == 0, f"Errors occurred: {errors}"

            # Verify final state
            with pool.connection() as backend:
                result = execute_sql(backend, "SELECT COUNT(*) as cnt FROM tx_isolation_test")
                assert result.data[0]['cnt'] == 3, "Should have 3 records (initial + 2 writers)"

                # Verify writer1's data
                w1_result = execute_sql(backend, "SELECT value FROM tx_isolation_test WHERE name = 'writer1'")
                assert w1_result.data[0]['value'] == 100

                # Verify writer2's data
                w2_result = execute_sql(backend, "SELECT value FROM tx_isolation_test WHERE name = 'writer2'")
                assert w2_result.data[0]['value'] == 200

            pool.close(timeout=1.0)

        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)


# ============================================================
# Nested Context Tests
# ============================================================

class TestNestedContext:
    """Tests for nested connection contexts."""

    def test_nested_connection_context_reuses_same_backend(self):
        """Test that nested connection contexts reuse the same backend."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            with pool.connection() as outer_backend:
                outer_id = id(outer_backend)

                with pool.connection() as inner_backend:
                    inner_id = id(inner_backend)

                    # Should be the same connection (reused)
                    assert inner_backend is outer_backend
                    assert inner_id == outer_id

                # After exiting inner context, outer should still be active
                stats = pool.get_stats()
                assert stats.current_in_use == 1

            # After exiting both contexts, connection should be released
            stats = pool.get_stats()
            assert stats.current_in_use == 0
        finally:
            pool.close(timeout=0.1)

    def test_nested_transaction_context_reuses_same_backend(self):
        """Test that nested transaction contexts reuse the same backend."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            with pool.transaction() as outer_backend:
                outer_id = id(outer_backend)

                with pool.transaction() as inner_backend:
                    inner_id = id(inner_backend)

                    # Should be the same connection (reused)
                    assert inner_backend is outer_backend
                    assert inner_id == outer_id

                # After exiting inner context, transaction should still be active
                # (not committed yet)
                stats = pool.get_stats()
                assert stats.current_in_use == 1

            # After exiting both contexts, connection should be released
            stats = pool.get_stats()
            assert stats.current_in_use == 0
        finally:
            pool.close(timeout=0.1)

    def test_mixed_nested_contexts(self):
        """Test mixed nested connection and transaction contexts."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            with pool.connection() as conn_backend:
                conn_id = id(conn_backend)

                with pool.transaction() as tx_backend:
                    tx_id = id(tx_backend)

                    # Transaction should reuse the connection
                    assert tx_backend is conn_backend
                    assert tx_id == conn_id

                # After transaction commits, connection is still held
                stats = pool.get_stats()
                assert stats.current_in_use == 1

            # After all contexts exit
            stats = pool.get_stats()
            assert stats.current_in_use == 0
        finally:
            pool.close(timeout=0.1)


# ============================================================
# Boundary Condition Tests
# ============================================================

class TestBoundaryConditions:
    """Tests for boundary conditions."""

    def test_min_size_zero_no_warmup(self):
        """Test that min_size=0 does not warmup connections."""
        config = PoolConfig(
            min_size=0,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # No connections should be created at startup
            stats = pool.get_stats()
            assert stats.current_total == 0
            assert stats.current_available == 0
            assert stats.current_in_use == 0

            # Acquire should create a connection on demand
            backend = pool.acquire()
            stats = pool.get_stats()
            assert stats.current_total == 1
            assert stats.current_in_use == 1

            pool.release(backend)
            stats = pool.get_stats()
            assert stats.current_available == 1
        finally:
            pool.close(timeout=0.1)

    def test_max_size_one_single_connection(self):
        """Test that max_size=1 allows only one connection."""
        config = PoolConfig(
            min_size=0,
            max_size=1,
            timeout=0.5,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # Acquire the only connection
            backend1 = pool.acquire()
            stats = pool.get_stats()
            assert stats.current_in_use == 1
            assert stats.current_total == 1

            # Second acquire should timeout
            with pytest.raises(TimeoutError):
                pool.acquire(timeout=0.2)

            # Release and acquire again
            pool.release(backend1)
            backend2 = pool.acquire()
            stats = pool.get_stats()
            assert stats.current_in_use == 1

            pool.release(backend2)
        finally:
            pool.close(timeout=0.1)

    def test_min_equals_max(self):
        """Test pool where min_size equals max_size."""
        config = PoolConfig(
            min_size=3,
            max_size=3,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # Should have exactly 3 connections warmed up
            stats = pool.get_stats()
            assert stats.current_total == 3
            assert stats.current_available == 3

            # Acquire all 3
            backends = [pool.acquire() for _ in range(3)]
            stats = pool.get_stats()
            assert stats.current_in_use == 3
            assert stats.current_available == 0

            # Fourth acquire should wait (would exceed max)
            with pytest.raises(TimeoutError):
                pool.acquire(timeout=0.2)

            # Release one
            pool.release(backends[0])
            stats = pool.get_stats()
            assert stats.current_in_use == 2
            assert stats.current_available == 1

            # Now acquire should work
            backend = pool.acquire()
            pool.release(backend)

            # Release remaining
            for b in backends[1:]:
                pool.release(b)
        finally:
            pool.close(timeout=0.1)


# ============================================================
# Connection Recovery Tests
# ============================================================

class TestConnectionRecovery:
    """Tests for connection recovery after disconnect."""

    def test_acquire_after_backend_disconnect(self):
        """Test that pool creates new connection after backend is marked unhealthy."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            validate_on_borrow=True,  # Enable validation
            validation_query="SELECT 1",
            connection_mode="transient",  # Transient mode: destroy and recreate on validation failure
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # Acquire a connection
            backend1 = pool.acquire()
            pool.release(backend1)

            # Mark the pooled backend as unhealthy (simulates broken connection)
            with pool._lock:
                if pool._available:
                    pooled = pool._available[0]
                    pooled.mark_unhealthy()

            # Acquire again - validation should fail and new connection created
            backend2 = pool.acquire()

            # New connection should be valid
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = backend2.execute("SELECT 1", [], options=options)
            assert result is not None

            pool.release(backend2)

            # Check stats - should show validation failure and new creation
            stats = pool.get_stats()
            assert stats.total_validation_failures >= 1
            assert stats.total_created >= 2  # Initial + new after failure
        finally:
            pool.close(timeout=0.1)

    def test_validation_failure_creates_new_connection(self):
        """Test that validation failure triggers new connection creation."""
        config = PoolConfig(
            min_size=0,
            max_size=5,
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # Create a connection
            backend = pool.acquire()
            pool.release(backend)

            stats = pool.get_stats()
            assert stats.current_available == 1

            # Manually mark the pooled backend as unhealthy
            # This simulates a broken connection
            with pool._lock:
                if pool._available:
                    pooled = pool._available[0]
                    pooled.mark_unhealthy()

            # Acquire again - validation should detect unhealthy and create new
            backend2 = pool.acquire()
            stats = pool.get_stats()

            # Should have created a new connection (old one destroyed)
            assert stats.total_validation_failures >= 1

            pool.release(backend2)
        finally:
            pool.close(timeout=0.1)

    def test_pool_survives_all_connections_broken(self):
        """Test that pool can recover when all connections are broken."""
        config = PoolConfig(
            min_size=0,
            max_size=3,
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)

        try:
            # Create and break 3 connections
            backends = []
            for _ in range(3):
                b = pool.acquire()
                backends.append(b)

            # Release all
            for b in backends:
                pool.release(b)

            # Break all connections
            for b in backends:
                b.disconnect()

            # Try to acquire - should create new connections
            new_backend = pool.acquire()
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = new_backend.execute("SELECT 1", [], options=options)
            assert result is not None

            pool.release(new_backend)
        finally:
            pool.close(timeout=0.1)


# ============================================================
# Async Concurrency Tests
# ============================================================

class TestAsyncConcurrentAccess:
    """Tests for async concurrent access to connection pool."""

    @pytest.mark.asyncio
    async def test_concurrent_acquire_release(self):
        """Test async concurrent acquire and release operations."""
        import asyncio

        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)
        errors = []
        success_count = [0]

        async def worker(worker_id):
            try:
                for _ in range(5):  # Each worker does 5 acquire/release cycles
                    backend = await pool.acquire(timeout=5.0)
                    try:
                        # Simulate some work
                        await asyncio.sleep(0.01)
                        options = ExecutionOptions(stmt_type=StatementType.DQL)
                        await backend.execute("SELECT 1", [], options=options)
                    finally:
                        await pool.release(backend)
                    success_count[0] += 1
            except Exception as e:
                errors.append((worker_id, str(e)))

        try:
            # Create 10 concurrent workers
            tasks = [worker(i) for i in range(10)]
            await asyncio.gather(*tasks)

            # All operations should succeed
            assert len(errors) == 0, f"Errors: {errors}"
            assert success_count[0] == 50  # 10 workers * 5 cycles

            # Verify pool state
            stats = pool.get_stats()
            assert stats.current_in_use == 0
        finally:
            await pool.close(timeout=0.1)

    @pytest.mark.asyncio
    async def test_concurrent_acquire_with_limit(self):
        """Test that async concurrent acquires respect max_size limit."""
        import asyncio

        config = PoolConfig(
            min_size=0,
            max_size=2,  # Only 2 connections allowed
            timeout=0.5,  # Short timeout
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)
        acquired_count = [0]
        timeout_count = [0]

        async def acquire_and_hold():
            try:
                backend = await pool.acquire(timeout=0.3)
                acquired_count[0] += 1
                # Hold connection for a while
                await asyncio.sleep(0.2)
                await pool.release(backend)
            except TimeoutError:
                timeout_count[0] += 1

        try:
            # 5 tasks trying to acquire, but only 2 connections available
            tasks = [acquire_and_hold() for _ in range(5)]
            await asyncio.gather(*tasks)

            # Some should succeed, some should timeout
            assert acquired_count[0] >= 2  # At least 2 should get connections
            assert timeout_count[0] >= 1  # At least 1 should timeout
        finally:
            await pool.close(timeout=0.1)

    @pytest.mark.asyncio
    async def test_multiple_connections_isolation(self):
        """Test that multiple async connections are isolated and operations don't interfere.

        This test uses a shared SQLite file database to verify that:
        1. Multiple connections can work concurrently without data corruption
        2. Each connection's operations are atomic and isolated
        3. No deadlocks occur during concurrent operations
        """
        import asyncio
        import tempfile
        import os

        # Create a temporary file database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            config = PoolConfig(
                min_size=1,
                max_size=5,
                backend_factory=lambda: AsyncSQLiteBackend(database=db_path)
            )
            pool = await AsyncBackendPool.create(config)

            # Create shared table
            async with pool.connection() as backend:
                await async_execute_sql(backend, """
                    CREATE TABLE isolation_test (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        task_id INTEGER NOT NULL,
                        value TEXT NOT NULL,
                        created_at REAL NOT NULL
                    )
                """)

            results = {}
            errors = []
            num_tasks = 5
            operations_per_task = 10

            async def worker(task_id):
                """Each task performs multiple insert operations."""
                task_results = []
                try:
                    for op_num in range(operations_per_task):
                        async with pool.connection() as backend:
                            # Insert data with task identifier
                            value = f"task_{task_id}_op_{op_num}"
                            await async_execute_sql(backend,
                                f"INSERT INTO isolation_test (task_id, value, created_at) VALUES ({task_id}, '{value}', julianday('now'))"
                            )

                            # Immediately verify the insert
                            result = await async_execute_sql(backend,
                                f"SELECT value FROM isolation_test WHERE task_id = {task_id} ORDER BY id DESC LIMIT 1"
                            )
                            task_results.append((op_num, result.data[0]['value'] if result.data else None))

                except Exception as e:
                    errors.append((task_id, str(e)))

                results[task_id] = task_results

            # Run all tasks concurrently
            tasks = [worker(i) for i in range(num_tasks)]
            await asyncio.gather(*tasks)

            # Verify results
            assert len(errors) == 0, f"Errors occurred: {errors}"

            # Each task should have completed all operations
            for task_id in range(num_tasks):
                assert task_id in results
                assert len(results[task_id]) == operations_per_task

            # Verify data integrity in database
            async with pool.connection() as backend:
                # Count total records
                count_result = await async_execute_sql(backend, "SELECT COUNT(*) as cnt FROM isolation_test")
                expected_count = num_tasks * operations_per_task
                assert count_result.data[0]['cnt'] == expected_count, \
                    f"Expected {expected_count} records, got {count_result.data[0]['cnt']}"

                # Verify each task's records
                for task_id in range(num_tasks):
                    task_result = await async_execute_sql(backend,
                        f"SELECT COUNT(*) as cnt FROM isolation_test WHERE task_id = {task_id}"
                    )
                    assert task_result.data[0]['cnt'] == operations_per_task, \
                        f"Task {task_id} expected {operations_per_task} records, got {task_result.data[0]['cnt']}"

                    # Verify all values are correct
                    values_result = await async_execute_sql(backend,
                        f"SELECT value FROM isolation_test WHERE task_id = {task_id} ORDER BY id"
                    )
                    for i, row in enumerate(values_result.data):
                        expected_value = f"task_{task_id}_op_{i}"
                        assert row['value'] == expected_value, \
                            f"Task {task_id} op {i}: expected '{expected_value}', got '{row['value']}'"

            await pool.close(timeout=1.0)

        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)

    @pytest.mark.asyncio
    async def test_concurrent_transactions_isolation(self):
        """Test that concurrent async transactions on different connections are isolated.

        This test verifies transaction isolation - each transaction should see
        a consistent view of the database.
        """
        import asyncio
        import tempfile
        import os

        # Create a temporary file database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            config = PoolConfig(
                min_size=2,
                max_size=5,
                backend_factory=lambda: AsyncSQLiteBackend(database=db_path)
            )
            pool = await AsyncBackendPool.create(config)

            # Create shared table
            async with pool.connection() as backend:
                await async_execute_sql(backend, """
                    CREATE TABLE tx_isolation_test (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        value INTEGER NOT NULL
                    )
                """)
                # Insert initial data
                await async_execute_sql(backend, "INSERT INTO tx_isolation_test (name, value) VALUES ('initial', 0)")

            errors = []

            async def reader_task():
                """Reader task that reads data during concurrent transactions."""
                try:
                    await asyncio.sleep(0.1)  # Let writers start their transactions

                    async with pool.connection() as backend:
                        # Should only see committed data
                        result = await async_execute_sql(backend, "SELECT COUNT(*) as cnt FROM tx_isolation_test")
                        count = result.data[0]['cnt']

                        # We should see at least the initial record
                        assert count >= 1, f"Expected at least 1 record, got {count}"

                except Exception as e:
                    errors.append(('reader', str(e)))

            async def writer_task(task_name, value):
                """Writer task that performs a transaction."""
                try:
                    async with pool.transaction() as backend:
                        # Insert data
                        await async_execute_sql(backend,
                            f"INSERT INTO tx_isolation_test (name, value) VALUES ('{task_name}', {value})"
                        )
                        await asyncio.sleep(0.2)  # Hold transaction open briefly
                        # Transaction will commit on exit

                except Exception as e:
                    errors.append((task_name, str(e)))

            # Run all tasks concurrently
            await asyncio.gather(
                reader_task(),
                writer_task('writer1', 100),
                writer_task('writer2', 200),
            )

            # Verify results
            assert len(errors) == 0, f"Errors occurred: {errors}"

            # Verify final state
            async with pool.connection() as backend:
                result = await async_execute_sql(backend, "SELECT COUNT(*) as cnt FROM tx_isolation_test")
                assert result.data[0]['cnt'] == 3, "Should have 3 records (initial + 2 writers)"

                # Verify writer1's data
                w1_result = await async_execute_sql(backend, "SELECT value FROM tx_isolation_test WHERE name = 'writer1'")
                assert w1_result.data[0]['value'] == 100

                # Verify writer2's data
                w2_result = await async_execute_sql(backend, "SELECT value FROM tx_isolation_test WHERE name = 'writer2'")
                assert w2_result.data[0]['value'] == 200

            await pool.close(timeout=1.0)

        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)


# ============================================================
# Async Nested Context Tests
# ============================================================

class TestAsyncNestedContext:
    """Tests for async nested connection contexts."""

    @pytest.mark.asyncio
    async def test_nested_connection_context_reuses_same_backend(self):
        """Test that nested async connection contexts reuse the same backend."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            async with pool.connection() as outer_backend:
                outer_id = id(outer_backend)

                async with pool.connection() as inner_backend:
                    inner_id = id(inner_backend)

                    # Should be the same connection (reused)
                    assert inner_backend is outer_backend
                    assert inner_id == outer_id

                # After exiting inner context, outer should still be active
                stats = pool.get_stats()
                assert stats.current_in_use == 1

            # After exiting both contexts, connection should be released
            stats = pool.get_stats()
            assert stats.current_in_use == 0
        finally:
            await pool.close(timeout=0.1)

    @pytest.mark.asyncio
    async def test_nested_transaction_context_reuses_same_backend(self):
        """Test that nested async transaction contexts reuse the same backend."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            async with pool.transaction() as outer_backend:
                outer_id = id(outer_backend)

                async with pool.transaction() as inner_backend:
                    inner_id = id(inner_backend)

                    # Should be the same connection (reused)
                    assert inner_backend is outer_backend
                    assert inner_id == outer_id

                # After exiting inner context, transaction should still be active
                stats = pool.get_stats()
                assert stats.current_in_use == 1

            # After exiting both contexts, connection should be released
            stats = pool.get_stats()
            assert stats.current_in_use == 0
        finally:
            await pool.close(timeout=0.1)


# ============================================================
# Async Boundary Condition Tests
# ============================================================

class TestAsyncBoundaryConditions:
    """Tests for async boundary conditions."""

    @pytest.mark.asyncio
    async def test_min_size_zero_no_warmup(self):
        """Test that min_size=0 does not warmup connections."""
        config = PoolConfig(
            min_size=0,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # No connections should be created at startup
            stats = pool.get_stats()
            assert stats.current_total == 0
            assert stats.current_available == 0
            assert stats.current_in_use == 0

            # Acquire should create a connection on demand
            backend = await pool.acquire()
            stats = pool.get_stats()
            assert stats.current_total == 1
            assert stats.current_in_use == 1

            await pool.release(backend)
            stats = pool.get_stats()
            assert stats.current_available == 1
        finally:
            await pool.close(timeout=0.1)

    @pytest.mark.asyncio
    async def test_max_size_one_single_connection(self):
        """Test that max_size=1 allows only one connection."""
        config = PoolConfig(
            min_size=0,
            max_size=1,
            timeout=0.5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # Acquire the only connection
            backend1 = await pool.acquire()
            stats = pool.get_stats()
            assert stats.current_in_use == 1
            assert stats.current_total == 1

            # Second acquire should timeout
            with pytest.raises(TimeoutError):
                await pool.acquire(timeout=0.2)

            # Release and acquire again
            await pool.release(backend1)
            backend2 = await pool.acquire()
            stats = pool.get_stats()
            assert stats.current_in_use == 1

            await pool.release(backend2)
        finally:
            await pool.close(timeout=0.1)

    @pytest.mark.asyncio
    async def test_min_equals_max(self):
        """Test async pool where min_size equals max_size."""
        config = PoolConfig(
            min_size=3,
            max_size=3,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        # Use create() to warmup connections (same as sync pool)
        pool = await AsyncBackendPool.create(config)

        try:
            # Should have exactly 3 connections warmed up
            stats = pool.get_stats()
            assert stats.current_total == 3
            assert stats.current_available == 3

            # Acquire all 3
            backends = [await pool.acquire() for _ in range(3)]
            stats = pool.get_stats()
            assert stats.current_in_use == 3
            assert stats.current_available == 0

            # Fourth acquire should wait (would exceed max)
            with pytest.raises(TimeoutError):
                await pool.acquire(timeout=0.2)

            # Release one
            await pool.release(backends[0])
            stats = pool.get_stats()
            assert stats.current_in_use == 2
            assert stats.current_available == 1

            # Now acquire should work
            backend = await pool.acquire()
            await pool.release(backend)

            # Release remaining
            for b in backends[1:]:
                await pool.release(b)
        finally:
            await pool.close(timeout=0.1)


# ============================================================
# Async Connection Recovery Tests
# ============================================================

class TestAsyncConnectionRecovery:
    """Tests for async connection recovery after disconnect."""

    @pytest.mark.asyncio
    async def test_acquire_after_backend_disconnect(self):
        """Test that async pool creates new connection after backend is marked unhealthy."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            validate_on_borrow=True,  # Enable validation
            validation_query="SELECT 1",
            connection_mode="transient",  # Transient mode: destroy and recreate on validation failure
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # Acquire a connection
            backend1 = await pool.acquire()
            await pool.release(backend1)

            # Mark the pooled backend as unhealthy (simulates broken connection)
            async with pool._lock:
                if pool._available:
                    pooled = pool._available[0]
                    pooled.mark_unhealthy()

            # Acquire again - validation should fail and new connection created
            backend2 = await pool.acquire()

            # New connection should be valid
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = await backend2.execute("SELECT 1", [], options=options)
            assert result is not None

            await pool.release(backend2)

            # Check stats - should show validation failure and new creation
            stats = pool.get_stats()
            assert stats.total_validation_failures >= 1
            assert stats.total_created >= 2  # Initial + new after failure
        finally:
            await pool.close(timeout=0.1)

    @pytest.mark.asyncio
    async def test_pool_survives_all_connections_broken(self):
        """Test that async pool can recover when all connections are broken."""
        config = PoolConfig(
            min_size=0,
            max_size=3,
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)

        try:
            # Create and break 3 connections
            backends = []
            for _ in range(3):
                b = await pool.acquire()
                backends.append(b)

            # Release all
            for b in backends:
                await pool.release(b)

            # Break all connections
            for b in backends:
                await b.disconnect()

            # Try to acquire - should create new connections
            new_backend = await pool.acquire()
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = await new_backend.execute("SELECT 1", [], options=options)
            assert result is not None

            await pool.release(new_backend)
        finally:
            await pool.close(timeout=0.1)


# ============================================================
# Connection Mode Tests
# ============================================================

class TestConnectionModeConfig:
    """Tests for PoolConfig connection_mode field."""

    def test_default_connection_mode(self):
        """Test default connection_mode is 'auto'."""
        config = PoolConfig(backend_factory=lambda: None)
        assert config.connection_mode == "auto"

    def test_persistent_connection_mode(self):
        """Test explicit persistent connection mode."""
        config = PoolConfig(
            connection_mode="persistent",
            backend_factory=lambda: None
        )
        assert config.connection_mode == "persistent"

    def test_transient_connection_mode(self):
        """Test explicit transient connection mode."""
        config = PoolConfig(
            connection_mode="transient",
            backend_factory=lambda: None
        )
        assert config.connection_mode == "transient"

    def test_invalid_connection_mode(self):
        """Test invalid connection_mode raises ValueError."""
        with pytest.raises(ValueError, match="connection_mode must be"):
            PoolConfig(
                connection_mode="invalid",
                backend_factory=lambda: None
            )

    def test_auto_connect_ignored_warning_in_persistent_mode(self, caplog):
        """Test that auto_connect_on_acquire is warned in persistent mode."""
        import logging
        with caplog.at_level(logging.WARNING):
            config = PoolConfig(
                connection_mode="persistent",
                auto_connect_on_acquire=True,
                backend_factory=lambda: None
            )
        assert "persistent" in caplog.text
        assert "ignores" in caplog.text

    def test_clone_preserves_connection_mode(self):
        """Test that clone preserves connection_mode."""
        config = PoolConfig(
            connection_mode="persistent",
            backend_factory=lambda: None
        )
        cloned = config.clone()
        assert cloned.connection_mode == "persistent"

    def test_clone_can_override_connection_mode(self):
        """Test that clone can override connection_mode."""
        config = PoolConfig(
            connection_mode="persistent",
            backend_factory=lambda: None
        )
        cloned = config.clone(connection_mode="transient")
        assert cloned.connection_mode == "transient"


class TestSyncPersistentMode:
    """Tests for synchronous BackendPool in persistent mode."""

    def test_auto_mode_matches_threadsafety(self):
        """Test that auto mode selects connection mode based on backend threadsafety."""
        # SQLite's threadsafety varies by Python version:
        # - Python 3.8-3.11: sqlite3.threadsafety = 1 → transient
        # - Python 3.12+: sqlite3.threadsafety = 3 → persistent
        import sqlite3
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)
        try:
            expected_mode = "persistent" if sqlite3.threadsafety >= 2 else "transient"
            assert pool.connection_mode == expected_mode
        finally:
            pool.close(timeout=0.1)

    def test_explicit_persistent_mode_with_sqlite(self):
        """Test explicit persistent mode overrides auto-detection."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            connection_mode="persistent",
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)
        try:
            assert pool.connection_mode == "persistent"
            # In persistent mode, warmup should connect immediately
            stats = pool.get_stats()
            assert stats.current_available >= 1

            # Acquire should NOT call connect again
            backend = pool.acquire()
            assert backend is not None
            # Connection should already be established
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = backend.execute("SELECT 1", [], options=options)
            assert result is not None

            # Release should NOT disconnect in persistent mode
            pool.release(backend)
            # Backend should still be connected after release
            result2 = backend.execute("SELECT 1", [], options=options)
            assert result2 is not None
        finally:
            pool.close(timeout=0.1)

    def test_persistent_mode_warmup_connects(self):
        """Test that persistent mode connects during warmup."""
        config = PoolConfig(
            min_size=2,
            max_size=5,
            connection_mode="persistent",
            validate_on_borrow=False,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)
        try:
            stats = pool.get_stats()
            assert stats.current_available == 2
            # All warmed up connections should be usable immediately
            backend1 = pool.acquire()
            backend2 = pool.acquire()
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            assert backend1.execute("SELECT 1", [], options=options) is not None
            assert backend2.execute("SELECT 1", [], options=options) is not None
            pool.release(backend1)
            pool.release(backend2)
        finally:
            pool.close(timeout=0.1)

    def test_persistent_mode_reconnection_on_validation_failure(self):
        """Test that persistent mode reconnects when validation fails."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            connection_mode="persistent",
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)
        try:
            # Acquire and release
            backend1 = pool.acquire()
            pool.release(backend1)

            # Mark as unhealthy
            with pool._lock:
                if pool._available:
                    pooled = pool._available[0]
                    pooled.mark_unhealthy()

            # Acquire again - persistent mode should reconnect
            backend2 = pool.acquire()
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = backend2.execute("SELECT 1", [], options=options)
            assert result is not None
            pool.release(backend2)

            # In persistent mode, reconnection reuses the same backend
            # so total_created may not increase
            stats = pool.get_stats()
            assert stats.total_validation_failures >= 1
        finally:
            pool.close(timeout=0.1)


class TestSyncTransientMode:
    """Tests for synchronous BackendPool in transient mode."""

    def test_explicit_transient_mode(self):
        """Test explicit transient mode behavior."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            connection_mode="transient",
            auto_connect_on_acquire=True,
            auto_disconnect_on_release=True,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)
        try:
            assert pool.connection_mode == "transient"

            backend = pool.acquire()
            assert backend is not None
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = backend.execute("SELECT 1", [], options=options)
            assert result is not None

            # Release should disconnect in transient mode
            pool.release(backend)
        finally:
            pool.close(timeout=0.1)

    def test_transient_mode_no_auto_connect(self):
        """Test transient mode with auto_connect_on_acquire=False."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            connection_mode="transient",
            auto_connect_on_acquire=False,
            auto_disconnect_on_release=False,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)
        try:
            backend = pool.acquire()
            # Backend should NOT be connected automatically
            # User must call connect() manually
            pool.release(backend)
        finally:
            pool.close(timeout=0.1)

    def test_transient_mode_destroy_on_validation_failure(self):
        """Test that transient mode destroys and recreates on validation failure."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            connection_mode="transient",
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)
        try:
            backend1 = pool.acquire()
            pool.release(backend1)

            # Mark as unhealthy
            with pool._lock:
                if pool._available:
                    pooled = pool._available[0]
                    pooled.mark_unhealthy()

            # Acquire again - transient mode should destroy and create new
            backend2 = pool.acquire()
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = backend2.execute("SELECT 1", [], options=options)
            assert result is not None
            pool.release(backend2)

            stats = pool.get_stats()
            assert stats.total_validation_failures >= 1
            assert stats.total_created >= 2  # Original + new after failure
        finally:
            pool.close(timeout=0.1)


class TestAsyncConnectionMode:
    """Tests for AsyncBackendPool connection modes."""

    @pytest.mark.asyncio
    async def test_auto_mode_defaults_to_persistent(self):
        """Test that auto mode defaults to persistent for async pool."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)
        try:
            assert pool.connection_mode == "persistent"
        finally:
            await pool.close(timeout=0.1)

    @pytest.mark.asyncio
    async def test_persistent_mode_stays_connected(self):
        """Test persistent mode: connections stay connected across acquire/release."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            connection_mode="persistent",
            validate_on_borrow=False,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)
        try:
            backend = await pool.acquire()
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = await backend.execute("SELECT 1", [], options=options)
            assert result is not None

            # Release should NOT disconnect
            await pool.release(backend)

            # Backend should still be usable
            result2 = await backend.execute("SELECT 1", [], options=options)
            assert result2 is not None
        finally:
            await pool.close(timeout=0.1)

    @pytest.mark.asyncio
    async def test_transient_mode_connect_disconnect(self):
        """Test transient mode: connect on acquire, disconnect on release."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            connection_mode="transient",
            auto_connect_on_acquire=True,
            auto_disconnect_on_release=True,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)
        try:
            assert pool.connection_mode == "transient"

            backend = await pool.acquire()
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = await backend.execute("SELECT 1", [], options=options)
            assert result is not None

            await pool.release(backend)
        finally:
            await pool.close(timeout=0.1)

    @pytest.mark.asyncio
    async def test_persistent_mode_reconnection(self):
        """Test persistent mode reconnection on validation failure."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            connection_mode="persistent",
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)
        try:
            backend1 = await pool.acquire()
            await pool.release(backend1)

            # Mark as unhealthy
            async with pool._lock:
                if pool._available:
                    pooled = pool._available[0]
                    pooled.mark_unhealthy()

            # Acquire - persistent mode should reconnect
            backend2 = await pool.acquire()
            options = ExecutionOptions(stmt_type=StatementType.DQL)
            result = await backend2.execute("SELECT 1", [], options=options)
            assert result is not None
            await pool.release(backend2)

            stats = pool.get_stats()
            assert stats.total_validation_failures >= 1
        finally:
            await pool.close(timeout=0.1)


class TestHealthCheckConnectionMode:
    """Tests for health_check() including connection_mode in result."""

    def test_health_check_includes_connection_mode(self):
        """Test that health_check includes connection_mode."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            connection_mode="persistent",
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool.create(config)
        try:
            health = pool.health_check()
            assert 'connection_mode' in health
            assert health['connection_mode'] == 'persistent'
        finally:
            pool.close(timeout=0.1)

    @pytest.mark.asyncio
    async def test_async_health_check_includes_connection_mode(self):
        """Test that async health_check includes connection_mode."""
        config = PoolConfig(
            min_size=1,
            max_size=5,
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = await AsyncBackendPool.create(config)
        try:
            health = await pool.health_check()
            assert 'connection_mode' in health
            assert health['connection_mode'] == 'persistent'
        finally:
            await pool.close(timeout=0.1)
