# src/rhosocial/activerecord/relation/cache_backend.py
"""
Backward-compat re-export.  New code should import directly from
``rhosocial.activerecord.relation.cache_backends``.
"""
from .cache_backends import CacheBackend, CacheSerializer, InMemoryCache, RedisCache, RedisConfig, T

__all__ = [
    "CacheBackend",
    "CacheSerializer",
    "InMemoryCache",
    "RedisCache",
    "RedisConfig",
]
