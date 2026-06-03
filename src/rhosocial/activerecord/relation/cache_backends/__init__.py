# src/rhosocial/activerecord/relation/cache_backends/__init__.py
"""
Pluggable cache backends for relation data caching.

Available backends for this release:

* ``InMemoryCache`` — stores entries as instance attributes (default)

Redis and serializer support are intentionally not introduced in this release.
The implementation files are kept in-tree for follow-up external cache design.
"""

from ._protocol import CacheBackend, T
from .in_memory import InMemoryCache

# Not introduced in this release; keep source for follow-up external cache design.
# from ._protocol import CacheResult, CacheSerializer
# from .redis import RedisCache, RedisConfig

__all__ = [
    "CacheBackend",
    "InMemoryCache",
]
