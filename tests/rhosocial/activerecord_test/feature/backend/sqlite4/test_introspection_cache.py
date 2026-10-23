# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_cache.py
"""
Tests for SQLite introspection cache management.

This module tests the cache management methods on the introspector object,
including invalidate_cache and clear_cache.
"""

import time

from rhosocial.activerecord.backend.introspection import InMemoryIntrospectionCache
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

        # The cache reports its size; an empty cache has none.
        assert len(intro.cache) == 0

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

        assert len(intro.cache) == 0

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
        """The manager owns a cache, and its TTL is configured."""
        intro = backend_with_tables.introspector
        assert intro.cache.ttl > 0

    def test_cache_is_a_component_not_borrowed_state(self, sqlite_backend):
        """The cache is reachable and replaceable, and holds no state on the manager."""
        intro = sqlite_backend.introspector
        # The manager no longer carries cache fields of its own.
        assert not hasattr(intro, "_cache_ttl")
        assert not hasattr(intro, "_cache_lock")
        # ...and the component it owns can be swapped for another.
        from rhosocial.activerecord.backend.introspection import InMemoryIntrospectionCache
        replacement = InMemoryIntrospectionCache(ttl=1)
        intro._cache = replacement
        assert intro.cache is replacement

    def test_expired_cache_not_returned(self, sqlite_backend):
        """Test that expired cache entries are not returned."""
        intro = sqlite_backend.introspector
        # Set very short TTL on the cache component
        intro.cache.ttl = 0.01  # 10ms

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

    def test_cache_is_the_thing_that_is_thread_safe(self, backend_with_tables):
        """The lock belongs to the cache, because the cache holds the state.

        The introspector used to own a ``_cache_lock`` beside its dict. Both
        moved into the component, so this now asserts the component is the
        one protecting itself.
        """
        intro = backend_with_tables.introspector
        assert intro.cache._lock is not None

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
                    # Read through the cache's own entry point: the lock is
                    # inside the component and the caller never composes it.
                    results.append(intro.cache.get("table:main:users"))
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
        key = intro.cache.key(IntrospectionScope.TABLE, "users", schema="main")

        assert "table" in key
        assert "users" in key
        assert "main" in key

    def test_cache_key_with_extra(self, sqlite_backend):
        """Test cache key with extra component."""
        intro = sqlite_backend.introspector
        key = intro.cache.key(IntrospectionScope.TABLE, schema="main", extra="True")

        assert "table" in key
        assert "True" in key

    def test_cache_key_uniqueness(self, sqlite_backend):
        """Test that different parameters produce different keys."""
        intro = sqlite_backend.introspector
        key1 = intro.cache.key(IntrospectionScope.TABLE, "users")
        key2 = intro.cache.key(IntrospectionScope.TABLE, "posts")
        key3 = intro.cache.key(IntrospectionScope.COLUMN, "users")

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3


class CountingExecutor:
    """An executor that counts the questions put to the database."""

    def __init__(self, backend):
        from rhosocial.activerecord.backend.introspection.executor import (
            SyncIntrospectorExecutor,
        )
        self._inner = SyncIntrospectorExecutor(backend)
        self.calls = 0

    def execute(self, sql, params=()):
        self.calls += 1
        return self._inner.execute(sql, params)


def _walk(backend):
    """Ask everything the introspector knows, the way a caller would."""
    introspector = backend.introspector
    answers = 0
    for table in introspector.list_tables():
        answers += len(introspector.list_columns(table.name))
        answers += len(introspector.list_indexes(table.name))
        answers += 1 if introspector.get_primary_key(table.name) else 0
    return answers


class TestCacheRemovesQuestions:
    """What the cache does, stated as questions rather than milliseconds.

    Timings belong in the example script -- they move between machines and
    between runs. What does not move is the count: a cached pass asks the
    database nothing, and a pass with nothing cached asks it everything.
    """

    def _prepare(self, backend, ttl=None):
        introspector = backend.introspector
        if ttl is not None:
            introspector._cache = InMemoryIntrospectionCache(ttl=ttl)
        executor = CountingExecutor(backend)
        introspector._executor = executor
        return executor

    def test_uncached_pass_asks_the_database_every_time(self, backend_with_tables):
        executor = self._prepare(backend_with_tables, ttl=0)
        first = _walk(backend_with_tables)
        second_executor_calls = executor.calls
        _walk(backend_with_tables)

        assert executor.calls > 0
        assert executor.calls == second_executor_calls * 2, (
            "a cache with no TTL should ask the same number of questions "
            "twice, not answer the second walk from memory"
        )
        assert first >= 0

    def test_cached_pass_asks_nothing_the_second_time(self, backend_with_tables):
        executor = self._prepare(backend_with_tables)
        _walk(backend_with_tables)
        cold_calls = executor.calls
        assert cold_calls > 0

        executor.calls = 0
        _walk(backend_with_tables)
        assert executor.calls == 0, (
            "the second walk of the same schema should be answered from the "
            "cache; {} questions were put to the database".format(executor.calls)
        )

    def test_answers_survive_the_cache(self, backend_with_tables):
        """A cached answer is the same value, not a fresh but equal one."""
        introspector = backend_with_tables.introspector
        introspector.list_tables()
        tables_first = introspector.list_tables()
        tables_second = introspector.list_tables()
        assert tables_second is tables_first

    def test_the_cache_can_be_replaced_with_another_implementation(self, sqlite_backend):
        """The manager takes the cache it is given."""
        from rhosocial.activerecord.backend.introspection import IntrospectionCache

        class FixedCache:
            """A cache that answers everything from one entry."""

            ttl = 0

            def key(self, scope, *args, schema=None, extra=None):
                return "one"

            def get(self, key):
                return "sentinel"

            def set(self, key, data):
                pass

            def invalidate(self, scope=None, name=None):
                pass

            def clear(self):
                pass

            def __len__(self):
                return 1

        introspector = sqlite_backend.introspector
        replacement = FixedCache()
        assert isinstance(replacement, IntrospectionCache)
        introspector._cache = replacement
        assert introspector.cache is replacement
        # Every question now reaches the one entry, so every answer is it.
        assert introspector.list_tables() == "sentinel"
