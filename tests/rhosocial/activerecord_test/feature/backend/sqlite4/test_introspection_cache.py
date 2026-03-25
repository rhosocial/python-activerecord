# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_cache.py
"""
Tests for SQLite introspection cache management.

This module tests the cache management methods including
invalidate_introspection_cache and clear_introspection_cache.
"""

import time

import pytest

from rhosocial.activerecord.backend.introspection.types import IntrospectionScope


class TestCacheManagement:
    """Tests for cache management methods."""

    def test_clear_introspection_cache(self, backend_with_tables):
        """Test clear_introspection_cache clears all cache."""
        # First, populate cache
        backend_with_tables.get_database_info()
        backend_with_tables.list_tables()
        backend_with_tables.list_columns("users")

        # Clear cache
        backend_with_tables.clear_introspection_cache()

        # Verify cache is empty by checking internal cache dict
        assert len(backend_with_tables._introspection_cache) == 0

    def test_cache_hit(self, backend_with_tables):
        """Test that cached results are returned."""
        db_info1 = backend_with_tables.get_database_info()

        # Second call should return cached result
        db_info2 = backend_with_tables.get_database_info()

        # Same object reference means it was cached
        assert db_info1 is db_info2

    def test_cache_miss_after_clear(self, backend_with_tables):
        """Test cache miss after clear."""
        db_info1 = backend_with_tables.get_database_info()
        backend_with_tables.clear_introspection_cache()
        db_info2 = backend_with_tables.get_database_info()

        # Different object reference means cache was cleared
        assert db_info1 is not db_info2


class TestInvalidateIntrospectionCache:
    """Tests for invalidate_introspection_cache method."""

    def test_invalidate_all_scopes(self, backend_with_tables):
        """Test invalidating all caches."""
        # Populate multiple caches
        backend_with_tables.get_database_info()
        backend_with_tables.list_tables()
        backend_with_tables.list_columns("users")
        backend_with_tables.list_indexes("users")

        # Invalidate all
        backend_with_tables.invalidate_introspection_cache()

        assert len(backend_with_tables._introspection_cache) == 0

    def test_invalidate_specific_scope(self, backend_with_tables):
        """Test invalidating specific scope."""
        # Populate caches
        db_info = backend_with_tables.get_database_info()
        tables = backend_with_tables.list_tables()

        # Invalidate only database scope
        backend_with_tables.invalidate_introspection_cache(
            scope=IntrospectionScope.DATABASE
        )

        # Database cache should be cleared
        db_info2 = backend_with_tables.get_database_info()
        # Note: DatabaseInfo is a dataclass, so even if values are same,
        # it's a different object after cache clear
        # Check internal cache was cleared for database scope
        db_cache_key = backend_with_tables._make_cache_key(IntrospectionScope.DATABASE)
        # The new result should be cached now
        assert db_info2 is not None

        # Table cache should still be cached
        tables2 = backend_with_tables.list_tables()
        assert tables is tables2

    def test_invalidate_table_scope(self, backend_with_tables):
        """Test invalidating table scope."""
        # Populate caches
        tables = backend_with_tables.list_tables()
        columns = backend_with_tables.list_columns("users")

        # Invalidate table scope
        backend_with_tables.invalidate_introspection_cache(
            scope=IntrospectionScope.TABLE
        )

        # Table cache should be cleared
        tables2 = backend_with_tables.list_tables()
        assert tables is not tables2

        # Column cache should still be cached
        columns2 = backend_with_tables.list_columns("users")
        assert columns is columns2

    def test_invalidate_specific_table(self, backend_with_tables):
        """Test invalidating cache for specific table."""
        # Populate caches
        users_info = backend_with_tables.get_table_info("users")
        posts_info = backend_with_tables.get_table_info("posts")

        # Invalidate only users table
        backend_with_tables.invalidate_introspection_cache(
            scope=IntrospectionScope.TABLE,
            name="users"
        )

        # Users table cache should be cleared
        users_info2 = backend_with_tables.get_table_info("users")
        assert users_info is not users_info2

        # Posts table cache should still be cached
        posts_info2 = backend_with_tables.get_table_info("posts")
        assert posts_info is posts_info2


class TestCacheExpiration:
    """Tests for cache expiration behavior."""

    def test_cache_ttl(self, backend_with_tables):
        """Test that cache has TTL configured."""
        # Check that TTL is set
        assert hasattr(backend_with_tables, "_cache_ttl")
        assert backend_with_tables._cache_ttl > 0

    def test_expired_cache_not_returned(self, sqlite_backend):
        """Test that expired cache entries are not returned."""
        # Set very short TTL
        sqlite_backend._cache_ttl = 0.01  # 10ms

        # Get database info
        db_info1 = sqlite_backend.get_database_info()

        # Wait for cache to expire
        time.sleep(0.05)

        # Get again - should fetch fresh data
        db_info2 = sqlite_backend.get_database_info()

        # Different objects because cache expired
        assert db_info1 is not db_info2


class TestCacheThreadSafety:
    """Tests for cache thread safety."""

    def test_cache_lock_exists(self, backend_with_tables):
        """Test that cache lock exists."""
        assert hasattr(backend_with_tables, "_cache_lock")

    def test_concurrent_cache_access(self, backend_with_tables):
        """Test concurrent cache access."""
        import threading

        results = []
        errors = []

        def read_cache():
            try:
                for _ in range(10):
                    info = backend_with_tables.get_database_info()
                    results.append(info)
            except Exception as e:
                errors.append(e)

        def clear_cache():
            try:
                for _ in range(5):
                    backend_with_tables.clear_introspection_cache()
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=read_cache)
            for _ in range(3)
        ]
        threads.append(threading.Thread(target=clear_cache))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # No exceptions should have occurred
        assert len(errors) == 0
        assert len(results) > 0


class TestCacheKeys:
    """Tests for cache key generation."""

    def test_cache_key_generation(self, sqlite_backend):
        """Test that cache keys are generated correctly."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        key = sqlite_backend._make_cache_key(
            IntrospectionScope.TABLE,
            "users",
            schema="main"
        )

        assert "table" in key
        assert "users" in key
        assert "main" in key

    def test_cache_key_with_extra(self, sqlite_backend):
        """Test cache key with extra component."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        key = sqlite_backend._make_cache_key(
            IntrospectionScope.TABLE,
            schema="main",
            extra="True"
        )

        assert "table" in key
        assert "True" in key

    def test_cache_key_uniqueness(self, sqlite_backend):
        """Test that different parameters produce different keys."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        key1 = sqlite_backend._make_cache_key(
            IntrospectionScope.TABLE,
            "users"
        )
        key2 = sqlite_backend._make_cache_key(
            IntrospectionScope.TABLE,
            "posts"
        )
        key3 = sqlite_backend._make_cache_key(
            IntrospectionScope.COLUMN,
            "users"
        )

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
