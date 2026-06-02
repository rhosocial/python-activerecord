# src/rhosocial/activerecord/relation/cache.py
"""
Caching implementation for relation data.
Provides configurable caching with TTL and size limits.

Backend Architecture
--------------------
``InstanceCache`` is the public proxy that delegates to a pluggable
``CacheBackend``.  The default backend is ``InMemoryCache`` (same
behavior as before).  Call ``InstanceCache.set_backend(...)`` at
application startup to switch to a distributed backend.

Available backends (in :mod:`rhosocial.activerecord.relation.cache_backends`):

* ``InMemoryCache`` — stores entries as instance attributes
* ``RedisCache`` — distributed, cross-container key/value store

Cache Stampede & Proactive Refresh
----------------------------------
The framework does NOT implement proactive refresh or cache stampede
protection.  These are application-level concerns because:

1. **Stale reads are a business decision.**  Some data can be served
   stale (stale-while-revalidate), some must be absolutely fresh.
   The framework cannot guess which category a relation falls into.

2. **Refresh cadence depends on access patterns.**  Low-frequency
   relations should not be refreshed on every read; high-frequency
   ones might need pre-warming.  Only the application knows.

3. **The framework has no background thread.**  It runs entirely
   in the request path.  Any "proactive" behaviour would degrade
   the very request it serves.

What the framework provides as building blocks:

* ``InstanceCache.get_with_meta()`` — returns age, origin, TTL so
  the application can decide whether to refresh.
* ``InstanceCache.set()`` — updates a cache entry at any time.
* ``origin`` metadata on ``CacheResult`` — distinguishes which
  container/process created the entry (useful for distributed
  refresh ownership).

Capacity Planning
-----------------
Cache entries are stored as deserialised Python objects (InMemory) or
serialised bytes (Redis, etc.).  Estimate memory before enabling caching
on large or high‑cardinality relations:

* **InMemory** — each cached result set is a plain Python list of model
  instances.  A relation returning 10 000 rows can consume megabytes
  *per entry*, multiplied by distinct parent-relation key pairs.
  Monitor ``InstanceCache`` growth or set a TTL to bound it.

* **Redis / distributed** — serialised bytes add overhead (JSON/pickle
  framing).  Use ``MEMORY USAGE <key>`` (Redis) or equivalent tools
  to measure real footprint.  Account for peak‑load key count × size.

The framework applies no built‑in memory cap or eviction policy —
configure these at the backend level (Redis ``maxmemory`` + ``allkeys-lru``,
or wrap ``InMemoryCache`` with a size‑limited dict).

Suggested approaches for the application:

+---------------------------+-------------------------------------------+
| Strategy                 | Implementation                             |
+===========================+===========================================+
| Scheduled warm-up        | APScheduler / cron triggers a script that |
|                           | calls the relation and refreshes cache.   |
+---------------------------+-------------------------------------------+
| Read-triggered refresh   | After ``get_with_meta()``, if age >       |
|                          | threshold and origin matches, call        |
|                          | loader + ``set()`` (soft inline refresh). |
+---------------------------+-------------------------------------------+
| Stale-while-revalidate   | Serve the stale value, asynchronously     |
|                           | enqueue a refresh task (Celery / thread). |
+---------------------------+-------------------------------------------+
| Mutex-based stampede     | Use Redis SETNX to let only one process   |
| protection               | re-generate the cache while others wait.  |
+---------------------------+-------------------------------------------+
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Optional, Dict, Generic, TypeVar

from .cache_backends import CacheBackend, CacheResult, InMemoryCache


@dataclass
class CacheConfig:
    """Configuration for relation caching.

    Attributes:
        enabled: Whether caching is enabled
        ttl: Time-to-live in seconds
        max_size: Maximum number of entries
    """

    enabled: bool = True
    ttl: Optional[int] = 300
    max_size: Optional[int] = 1000


class GlobalCacheConfig:
    """Thread-safe singleton for global cache configuration."""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.config = CacheConfig()
            return cls._instance

    @classmethod
    def set_config(cls, **kwargs):
        """Update global cache settings."""
        with cls._lock:
            for key, value in kwargs.items():
                if hasattr(cls._instance.config, key):
                    setattr(cls._instance.config, key, value)


class CacheEntry:
    """Single cache entry with expiration tracking.

    Args:
        value: Cached value
        ttl: Time-to-live in seconds
    """

    def __init__(self, value: Any, ttl: Optional[int] = None):
        self.value = value
        self.created_at = datetime.now()
        self.last_access = self.created_at
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)

    def touch(self) -> None:
        """Update last access time."""
        self.last_access = datetime.now()


class RelationCache:
    """Thread-safe cache manager for relation data.

    Args:
        config: Cache configuration, uses global if None
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        self.relation_name = None
        self._cache: Dict[tuple, CacheEntry] = {}
        self._lock = Lock()
        self.config = config or GlobalCacheConfig().config

    def get(self, instance: Any) -> Optional[Any]:
        """Get cached value for instance."""
        if not self.config.enabled:
            return None

        with self._lock:
            key = (id(instance), self.relation_name)
            entry = self._cache.get(key)

            if entry is None or entry.is_expired():
                if entry:
                    del self._cache[key]
                return None

            entry.touch()
            return entry.value

    def set(self, instance: Any, value: Any) -> None:
        """Cache value for instance."""
        if not self.config.enabled:
            return

        with self._lock:
            key = (id(instance), self.relation_name)

            if self.config.max_size and len(self._cache) >= self.config.max_size:
                if key not in self._cache:
                    oldest_key = min(
                        self._cache.keys(),
                        key=lambda k: self._cache[k].last_access
                    )
                    del self._cache[oldest_key]

            self._cache[key] = CacheEntry(value, self.config.ttl)

    def delete(self, instance: Any) -> None:
        """Remove cached value for instance."""
        with self._lock:
            key = (id(instance), self.relation_name)
            self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()


T = TypeVar("T")


class InstanceCache(Generic[T]):
    """
    Instance-level cache management system.

    Delegates to a pluggable ``CacheBackend``.  By default uses
    ``InMemoryCache``, which stores data on the model instance
    as before — fully backward compatible.

    Usage::

        # default (InMemoryCache) — no change needed
        value = InstanceCache.get(instance, "posts", config)

        # switch globally to Redis
        from rhosocial.activerecord.relation.cache_backends import RedisCache
        InstanceCache.set_backend(RedisCache(...))
    """

    _backend: CacheBackend = InMemoryCache()

    @classmethod
    def set_backend(cls, backend: CacheBackend) -> None:
        """Replace the active cache backend (affects all instances)."""
        cls._backend = backend

    @staticmethod
    def get_cache_attr_name(relation_name: str) -> str:
        """Generate attribute name for storing cache on the instance.

        Args:
            relation_name: Name of the relation

        Returns:
            Attribute name to use for this relation's cache
        """
        return f"_relation_cache_{relation_name}"

    @staticmethod
    def get_instance_cache(instance: Any, relation_name: str) -> Dict:
        """Get or create cache dict on the instance.

        .. deprecated::
            Only used by ``InMemoryCache``.  Prefer using ``InstanceCache.get``
            directly for backend-agnostic access.

        Args:
            instance: Model instance
            relation_name: Name of the relation

        Returns:
            Cache dictionary for this instance and relation
        """
        cache_attr = InstanceCache.get_cache_attr_name(relation_name)

        # Create cache dict if it doesn't exist
        if not hasattr(instance, cache_attr):
            setattr(instance, cache_attr, {})

        return getattr(instance, cache_attr)

    @staticmethod
    def get(instance: Any, relation_name: str, config: CacheConfig) -> Optional[T]:
        """Get cached relation value via the active backend.

        Args:
            instance: Model instance
            relation_name: Name of the relation
            config: Cache configuration

        Returns:
            Cached value or None if not found or expired
        """
        return InstanceCache._backend.get(instance, relation_name, config)

    @staticmethod
    def set(instance: Any, relation_name: str, value: T, config: CacheConfig) -> None:
        """Store relation value via the active backend.

        Args:
            instance: Model instance
            relation_name: Name of the relation
            value: Value to cache
            config: Cache configuration
        """
        InstanceCache._backend.set(instance, relation_name, value, config)

    @staticmethod
    def get_with_meta(
        instance: Any, relation_name: str, config: CacheConfig
    ) -> Optional[CacheResult[T]]:
        """Get cached relation value with metadata.

        Returns a ``CacheResult`` that includes age, origin and TTL info
        when the active backend supports it.  Falls back to a basic result
        when the backend only exposes the plain ``get()`` interface.

        Args:
            instance: Model instance
            relation_name: Name of the relation
            config: Cache configuration

        Returns:
            ``CacheResult`` with value and metadata, or None on miss/expiry
        """
        backend = InstanceCache._backend

        # Prefer rich metadata path (RedisCache with record_origin=True)
        getter = getattr(backend, "get_with_meta", None)
        if getter is not None:
            return getter(instance, relation_name, config)

        # Fallback: plain get() — can only provide value + backend origin
        value = backend.get(instance, relation_name, config)
        if value is None:
            return None
        return CacheResult(
            value=value,
            age=0.0,
            origin=backend.origin,
            ttl=config.ttl,
        )

    @staticmethod
    def delete(instance: Any, relation_name: str, config: Optional[CacheConfig] = None):
        """Remove cached relation value via the active backend.

        Args:
            instance: Model instance
            relation_name: Name of the relation
            config: Cache configuration (optional, if provided and disabled, no action taken)
        """
        InstanceCache._backend.delete(instance, relation_name, config)