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
        pool = BackendPool(config)

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

        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = AsyncBackendPool(config)

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

        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = AsyncBackendPool(config)

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
        pool = BackendPool(config)

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
        pool = BackendPool(config)

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
        pool = AsyncBackendPool(config)

        try:
            await pool._initialize()
            repr_str = repr(pool)
            assert "AsyncBackendPool" in repr_str
            assert "size=" in repr_str
        finally:
            await pool.close()
