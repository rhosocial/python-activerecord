# tests/rhosocial/activerecord_test/feature/backend/introspection/test_introspection_cache_async.py
"""Async twin of test_introspection_cache.py for SQLite introspection cache management."""

import asyncio

import pytest

from rhosocial.activerecord.backend.introspection.types import IntrospectionScope


class TestAsyncCacheManagement:
    """Tests for cache management methods."""

    @pytest.mark.asyncio
    async def test_clear_cache(self, async_backend_with_tables):
        """Test clear_cache clears all cache."""
        intro = async_backend_with_tables.introspector
        await intro.get_database_info()
        await intro.list_tables()
        await intro.list_columns("users")

        intro.clear_cache()

        assert len(intro._cache) == 0

    @pytest.mark.asyncio
    async def test_cache_hit(self, async_backend_with_tables):
        """Test that cached results are returned."""
        intro = async_backend_with_tables.introspector
        db_info1 = await intro.get_database_info()
        db_info2 = await intro.get_database_info()

        assert db_info1 is db_info2

    @pytest.mark.asyncio
    async def test_cache_miss_after_clear(self, async_backend_with_tables):
        """Test cache miss after clear."""
        intro = async_backend_with_tables.introspector
        db_info1 = await intro.get_database_info()
        intro.clear_cache()
        db_info2 = await intro.get_database_info()

        assert db_info1 is not db_info2


class TestAsyncInvalidateCache:
    """Tests for invalidate_cache method."""

    @pytest.mark.asyncio
    async def test_invalidate_all_scopes(self, async_backend_with_tables):
        """Test invalidating all caches."""
        intro = async_backend_with_tables.introspector
        await intro.get_database_info()
        await intro.list_tables()
        await intro.list_columns("users")
        await intro.list_indexes("users")

        intro.invalidate_cache()

        assert len(intro._cache) == 0

    @pytest.mark.asyncio
    async def test_invalidate_specific_scope(self, async_backend_with_tables):
        """Test invalidating specific scope."""
        intro = async_backend_with_tables.introspector
        db_info = await intro.get_database_info()
        tables = await intro.list_tables()

        intro.invalidate_cache(scope=IntrospectionScope.DATABASE)

        db_info2 = await intro.get_database_info()
        assert db_info2 is not None
        assert db_info2 is not db_info

        tables2 = await intro.list_tables()
        assert tables is tables2

    @pytest.mark.asyncio
    async def test_invalidate_table_scope(self, async_backend_with_tables):
        """Test invalidating table scope."""
        intro = async_backend_with_tables.introspector
        tables = await intro.list_tables()
        columns = await intro.list_columns("users")

        intro.invalidate_cache(scope=IntrospectionScope.TABLE)

        tables2 = await intro.list_tables()
        assert tables is not tables2

        columns2 = await intro.list_columns("users")
        assert columns is columns2

    @pytest.mark.asyncio
    async def test_invalidate_specific_table(self, async_backend_with_tables):
        """Test invalidating cache for specific table."""
        intro = async_backend_with_tables.introspector
        users_info = await intro.get_table_info("users")
        posts_info = await intro.get_table_info("posts")

        intro.invalidate_cache(scope=IntrospectionScope.TABLE, name="users")

        users_info2 = await intro.get_table_info("users")
        assert users_info is not users_info2

        posts_info2 = await intro.get_table_info("posts")
        assert posts_info is posts_info2


class TestAsyncCacheExpiration:
    """Tests for cache expiration behavior."""

    @pytest.mark.asyncio
    async def test_cache_ttl(self, async_backend_with_tables):
        """Test that cache has TTL configured."""
        intro = async_backend_with_tables.introspector
        assert hasattr(intro, "_cache_ttl")
        assert intro._cache_ttl > 0

    @pytest.mark.asyncio
    async def test_expired_cache_not_returned(self, async_sqlite_memory_backend):
        """Test that expired cache entries are not returned."""
        intro = async_sqlite_memory_backend.introspector
        intro._cache_ttl = 0.01

        db_info1 = await intro.get_database_info()

        await asyncio.sleep(0.05)

        db_info2 = await intro.get_database_info()

        assert db_info1 is not db_info2


class TestAsyncCacheThreadSafety:
    """Tests for cache lock safety."""

    @pytest.mark.asyncio
    async def test_cache_lock_exists(self, async_backend_with_tables):
        """Test that cache lock exists on introspector."""
        intro = async_backend_with_tables.introspector
        assert hasattr(intro, "_cache_lock")

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self, async_backend_with_tables):
        """Test that cache operations are protected by a lock under concurrent access."""
        import threading

        intro = async_backend_with_tables.introspector
        await intro.get_database_info()

        results = []
        errors = []

        def read_cache():
            try:
                for _ in range(20):
                    with intro._cache_lock:
                        cached = dict(intro._cache)
                    results.append(cached)
            except Exception as e:
                errors.append(e)

        def clear_cache():
            try:
                for _ in range(5):
                    intro.clear_cache()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_cache) for _ in range(3)]
        threads.append(threading.Thread(target=clear_cache))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) > 0


class TestAsyncCacheKeys:
    """Tests for cache key generation."""

    @pytest.mark.asyncio
    async def test_cache_key_generation(self, async_sqlite_memory_backend):
        """Test that cache keys are generated correctly."""
        intro = async_sqlite_memory_backend.introspector
        key = intro._make_cache_key(IntrospectionScope.TABLE, "users", schema="main")

        assert "table" in key
        assert "users" in key
        assert "main" in key

    @pytest.mark.asyncio
    async def test_cache_key_with_extra(self, async_sqlite_memory_backend):
        """Test cache key with extra component."""
        intro = async_sqlite_memory_backend.introspector
        key = intro._make_cache_key(IntrospectionScope.TABLE, schema="main", extra="True")

        assert "table" in key
        assert "True" in key

    @pytest.mark.asyncio
    async def test_cache_key_uniqueness(self, async_sqlite_memory_backend):
        """Test that different parameters produce different keys."""
        intro = async_sqlite_memory_backend.introspector
        key1 = intro._make_cache_key(IntrospectionScope.TABLE, "users")
        key2 = intro._make_cache_key(IntrospectionScope.TABLE, "posts")
        key3 = intro._make_cache_key(IntrospectionScope.COLUMN, "users")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
