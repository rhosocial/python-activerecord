# tests/rhosocial/activerecord_test/feature/connection/test_connection_pool.py
"""
Unit tests for connection pool implementation.

Tests PoolConfig, PoolStats, PooledBackend, BackendPool, and AsyncBackendPool.
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
    options = ExecutionOptions(stmt_type=StatementType.DDL if 'CREATE' in sql.upper() else StatementType.DML)
    return backend.execute(sql, params or [], options=options)


async def async_execute_sql(backend, sql: str, params=None):
    """Helper to execute SQL asynchronously with proper options."""
    options = ExecutionOptions(stmt_type=StatementType.DDL if 'CREATE' in sql.upper() else StatementType.DML)
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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

        try:
            with pool.connection() as backend:
                assert backend is not None
                stats = pool.get_stats()
                assert stats.current_in_use == 1

            stats = pool.get_stats()
            assert stats.current_in_use == 0
        finally:
            pool.close()

    def test_transaction_context_manager(self):
        """Test transaction context manager."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

        assert not pool.is_closed

        pool.close()

        assert pool.is_closed
        health = pool.health_check()
        assert health['closed'] is True

        # Acquire after close should fail
        with pytest.raises(RuntimeError, match="Pool is closed"):
            pool.acquire()

    def test_validation_on_borrow(self):
        """Test validation on borrow."""
        config = PoolConfig(
            min_size=1,
            max_size=2,
            validate_on_borrow=True,
            validation_query="SELECT 1",
            backend_factory=lambda: SQLiteBackend(database=":memory:")
        )
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
            backend_factory=lambda: AsyncSQLiteBackend(database=":memory:")
        )
        pool = AsyncBackendPool(config)

        backend = await pool.acquire()
        await pool.release(backend)

        assert not pool.is_closed

        await pool.close()

        assert pool.is_closed
        health = await pool.health_check()
        assert health['closed'] is True

        # Acquire after close should fail
        with pytest.raises(RuntimeError, match="Pool is closed"):
            await pool.acquire()
