# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_cache.py
"""
Tests for SQLite introspection cache management.

This module tests the cache management methods on the introspector object,
including invalidate_cache and clear_cache.
"""

import time

from rhosocial.activerecord.backend.introspection.types import IntrospectionScope


class TestCacheManagement:
    """Tests for cache management methods."""

    def test_clear_cache(self, backend_with_tables):
        """Test clear_cache clears all cache."""
        intro = backend_with_tables.introspector
        # First, populate cache
        intro.get_database_info()
        intro.list_tables()
        intro.list_columns("users")

        # Clear cache
        intro.clear_cache()

        # Verify cache is empty by checking internal cache dict
        assert len(intro._cache) == 0

    def test_cache_hit(self, backend_with_tables):
        """Test that cached results are returned."""
        intro = backend_with_tables.introspector
        db_info1 = intro.get_database_info()

        # Second call should return cached result
        db_info2 = intro.get_database_info()

        # Same object reference means it was cached
        assert db_info1 is db_info2

    def test_cache_miss_after_clear(self, backend_with_tables):
        """Test cache miss after clear."""
        intro = backend_with_tables.introspector
        db_info1 = intro.get_database_info()
        intro.clear_cache()
        db_info2 = intro.get_database_info()

        # Different object reference means cache was cleared
        assert db_info1 is not db_info2


class TestInvalidateCache:
    """Tests for invalidate_cache method."""

    def test_invalidate_all_scopes(self, backend_with_tables):
        """Test invalidating all caches."""
        intro = backend_with_tables.introspector
        # Populate multiple caches
        intro.get_database_info()
        intro.list_tables()
        intro.list_columns("users")
        intro.list_indexes("users")

        # Invalidate all
        intro.invalidate_cache()

        assert len(intro._cache) == 0

    def test_invalidate_specific_scope(self, backend_with_tables):
        """Test invalidating specific scope."""
        intro = backend_with_tables.introspector
        # Populate caches
        db_info = intro.get_database_info()
        tables = intro.list_tables()

        # Invalidate only database scope
        intro.invalidate_cache(scope=IntrospectionScope.DATABASE)

        # Database cache should be cleared, new result is a different object
        db_info2 = intro.get_database_info()
        assert db_info2 is not None
        assert db_info2 is not db_info

        # Table cache should still be cached (same object reference)
        tables2 = intro.list_tables()
        assert tables is tables2

    def test_invalidate_table_scope(self, backend_with_tables):
        """Test invalidating table scope."""
        intro = backend_with_tables.introspector
        # Populate caches
        tables = intro.list_tables()
        columns = intro.list_columns("users")

        # Invalidate table scope
        intro.invalidate_cache(scope=IntrospectionScope.TABLE)

        # Table cache should be cleared
        tables2 = intro.list_tables()
        assert tables is not tables2

        # Column cache should still be cached
        columns2 = intro.list_columns("users")
        assert columns is columns2

    def test_invalidate_specific_table(self, backend_with_tables):
        """Test invalidating cache for specific table."""
        intro = backend_with_tables.introspector
        # Populate caches
        users_info = intro.get_table_info("users")
        posts_info = intro.get_table_info("posts")

        # Invalidate only users table
        intro.invalidate_cache(scope=IntrospectionScope.TABLE, name="users")

        # Users table cache should be cleared
        users_info2 = intro.get_table_info("users")
        assert users_info is not users_info2

        # Posts table cache should still be cached
        posts_info2 = intro.get_table_info("posts")
        assert posts_info is posts_info2


class TestCacheExpiration:
    """Tests for cache expiration behavior."""

    def test_cache_ttl(self, backend_with_tables):
        """Test that cache has TTL configured."""
        intro = backend_with_tables.introspector
        assert hasattr(intro, "_cache_ttl")
        assert intro._cache_ttl > 0

    def test_expired_cache_not_returned(self, sqlite_backend):
        """Test that expired cache entries are not returned."""
        intro = sqlite_backend.introspector
        # Set very short TTL
        intro._cache_ttl = 0.01  # 10ms

        # Get database info
        db_info1 = intro.get_database_info()

        # Wait for cache to expire
        time.sleep(0.05)

        # Get again - should fetch fresh data
        db_info2 = intro.get_database_info()

        # Different objects because cache expired
        assert db_info1 is not db_info2


class TestCacheThreadSafety:
    """Tests for cache thread safety."""

    def test_cache_lock_exists(self, backend_with_tables):
        """Test that cache lock exists on introspector."""
        intro = backend_with_tables.introspector
        assert hasattr(intro, "_cache_lock")

    def test_concurrent_cache_access(self, backend_with_tables):
        """Test that cache lock prevents races when clearing and reading simultaneously.

        Note: SQLite connections are not thread-safe by default (check_same_thread=True).
        This test only verifies that the introspector's cache operations are protected
        by a lock, not that the full backend is thread-safe.
        """
        import threading

        intro = backend_with_tables.introspector
        # Pre-populate cache so threads only read, not query the DB
        intro.get_database_info()

        results = []
        errors = []

        def read_cache():
            try:
                for _ in range(20):
                    # Access the internal cache directly (thread-safe via lock)
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

        # Lock should prevent any exceptions
        assert len(errors) == 0
        assert len(results) > 0


class TestCacheKeys:
    """Tests for cache key generation."""

    def test_cache_key_generation(self, sqlite_backend):
        """Test that cache keys are generated correctly."""
        intro = sqlite_backend.introspector
        key = intro._make_cache_key(
            IntrospectionScope.TABLE,
            "users",
            schema="main"
        )

        assert "table" in key
        assert "users" in key
        assert "main" in key

    def test_cache_key_with_extra(self, sqlite_backend):
        """Test cache key with extra component."""
        intro = sqlite_backend.introspector
        key = intro._make_cache_key(
            IntrospectionScope.TABLE,
            schema="main",
            extra="True"
        )

        assert "table" in key
        assert "True" in key

    def test_cache_key_uniqueness(self, sqlite_backend):
        """Test that different parameters produce different keys."""
        intro = sqlite_backend.introspector
        key1 = intro._make_cache_key(IntrospectionScope.TABLE, "users")
        key2 = intro._make_cache_key(IntrospectionScope.TABLE, "posts")
        key3 = intro._make_cache_key(IntrospectionScope.COLUMN, "users")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
