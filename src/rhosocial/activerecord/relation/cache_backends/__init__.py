# src/rhosocial/activerecord/relation/cache_backends/__init__.py
"""
Pluggable cache backends for relation data caching.

Available backends:

* ``InMemoryCache`` — stores entries as instance attributes (default)
* ``RedisCache``    — distributed cache backed by Redis (requires ``redis>=5``)
* ``CacheBackend``, ``CacheSerializer``, ``CacheResult`` — shared protocol/utility types
"""

from ._protocol import CacheBackend, CacheResult, CacheSerializer, T  # noqa: F401
from .in_memory import InMemoryCache
from .redis import RedisCache, RedisConfig

__all__ = [
    "CacheBackend",
    "CacheResult",
    "CacheSerializer",
    "InMemoryCache",
    "RedisCache",
    "RedisConfig",
]
