# src/rhosocial/activerecord/relation/cache_backend.py
"""
Backward-compat re-export.  New code should import directly from
``rhosocial.activerecord.relation.cache_backends``.
"""
from .cache_backends import CacheBackend, InMemoryCache, T

# Not introduced in this release; keep source for follow-up external cache design.
# from .cache_backends import CacheSerializer, RedisCache, RedisConfig

__all__ = [
    "CacheBackend",
    "InMemoryCache",
]
