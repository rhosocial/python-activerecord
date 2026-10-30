# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_async_introspection_cache.py
"""The async introspection manager caches, and it is the same manager.

The sync cache has its own tests; this file exists because the async half
was once broken in a way no sync test could see. The async manager did not
inherit the manager base, so every method reached for a cache that was
never created and construction failed outright. Async introspection had
therefore stopped working while the sync suite stayed green.

The assertions below are about the contract, not the fix: a manager owns a
cache, a second pass asks the database nothing, and invalidating makes a
schema change visible. If the async manager ever drifts away from the sync
one again, one of these fails.
"""

from rhosocial.activerecord.backend.impl.sqlite.introspection import (
    AsyncSQLiteIntrospector,
)
from rhosocial.activerecord.backend.introspection import (
    InMemoryIntrospectionCache,
    IntrospectionCache,
)
from rhosocial.activerecord.backend.introspection.executor import (
    AsyncIntrospectorExecutor,
)


class CountingExecutor:
    """An executor that counts the questions put to the database."""

    def __init__(self, backend):
        self._inner = AsyncIntrospectorExecutor(backend)
        self.calls = 0

    async def execute(self, sql, params=()):
        self.calls += 1
        return await self._inner.execute(sql, params)


def _install_counting(backend, cache=None):
    """Replace the manager with one whose executor can be counted.

    Built through the public seam: ``set_introspector`` takes a manager,
    and the manager takes its cache. No private field is touched, so this
    stays valid however the manager is stored.
    """
    executor = CountingExecutor(backend)
    backend.set_introspector(
        AsyncSQLiteIntrospector(backend, executor, cache=cache)
    )
    return executor


async def _walk(backend):
    """Ask everything the introspector knows, the way a caller would."""
    introspector = backend.introspector
    answers = 0
    for table in await introspector.list_tables():
        answers += len(await introspector.list_columns(table.name))
        answers += len(await introspector.list_indexes(table.name))
        answers += 1 if await introspector.get_primary_key(table.name) else 0
    return answers


async def test_the_async_manager_owns_a_cache(async_sqlite_backend):
    """A cache object, plus the operations the manager promises over it."""
    introspector = async_sqlite_backend.introspector
    assert isinstance(introspector.cache, IntrospectionCache)
    introspector.invalidate_cache()
    introspector.clear_cache()


async def test_cached_pass_asks_nothing_the_second_time(async_backend_with_tables):
    executor = _install_counting(async_backend_with_tables)

    await _walk(async_backend_with_tables)
    cold_calls = executor.calls
    assert cold_calls > 0

    executor.calls = 0
    await _walk(async_backend_with_tables)
    assert executor.calls == 0, (
        "the second walk of the same schema should be answered from the "
        "cache; {} questions were put to the database".format(executor.calls)
    )


async def test_uncached_pass_asks_the_database_every_time(async_backend_with_tables):
    executor = _install_counting(
        async_backend_with_tables, cache=InMemoryIntrospectionCache(ttl=0)
    )

    await _walk(async_backend_with_tables)
    first = executor.calls
    await _walk(async_backend_with_tables)
    assert executor.calls == first * 2, (
        "a cache with no TTL should ask the same number of questions twice, "
        "not answer the second walk from memory"
    )


async def test_invalidate_makes_a_schema_change_visible(async_backend_with_tables):
    """The reason invalidation exists: the answer outlived the schema."""
    backend = async_backend_with_tables
    introspector = backend.introspector

    before = [t.name for t in await introspector.list_tables()]
    assert "added_later" not in before

    await backend.executescript(
        "CREATE TABLE added_later (id INTEGER PRIMARY KEY, note TEXT)"
    )

    stale = [t.name for t in await introspector.list_tables()]
    assert "added_later" not in stale, (
        "the cache should still hold the pre-DDL answer until invalidated -- "
        "if it does not, this test is no longer observing the cache"
    )

    introspector.invalidate_cache()
    after = [t.name for t in await introspector.list_tables()]
    assert "added_later" in after


async def test_the_cache_can_be_replaced_with_another_implementation(
    async_sqlite_backend,
):
    """A different cache, plugged in through the property."""

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

    introspector = async_sqlite_backend.introspector
    replacement = FixedCache()
    assert isinstance(replacement, IntrospectionCache)

    introspector.cache = replacement
    assert introspector.cache is replacement
    assert await introspector.list_tables() == "sentinel"


async def test_the_cache_can_be_given_at_construction(async_backend_with_tables):
    """Injection at creation, so a backend can choose in one place."""
    cache = InMemoryIntrospectionCache(ttl=0)
    executor = _install_counting(async_backend_with_tables, cache=cache)
    assert async_backend_with_tables.introspector.cache is cache
    assert executor.calls == 0
