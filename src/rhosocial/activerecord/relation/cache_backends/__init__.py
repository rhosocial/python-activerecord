# src/rhosocial/activerecord/relation/cache_backends/__init__.py
"""
Pluggable cache backends for relation data caching.

Available backends:

* ``InMemoryCache`` — stores entries as instance attributes (default)
* ``RedisCache`` — distributed, cross-container key/value store
"""

from ._protocol import CacheBackend, CacheResult, CacheSerializer, T
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
