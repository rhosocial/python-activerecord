# src/rhosocial/activerecord/relation/cache.py
"""
Caching implementation for relation data.
Provides configurable caching with TTL and size limits.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Optional, Dict, Generic, TypeVar


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
        self.ttl = ttl

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)


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

            return entry.value

    def set(self, instance: Any, value: Any) -> None:
        """Cache value for instance."""
        if not self.config.enabled:
            return

        with self._lock:
            if self.config.max_size and len(self._cache) >= self.config.max_size:
                self._cache.clear()

            key = (id(instance), self.relation_name)
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


T = TypeVar('T')


class InstanceCache(Generic[T]):
    """
    Instance-level cache management system.

    Instead of using a shared cache at the descriptor level, this system
    stores cache data directly on each model instance, ensuring proper
    isolation between instances.
    """

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
        """Get cached relation value from the instance.

        Args:
            instance: Model instance
            relation_name: Name of the relation
            config: Cache configuration

        Returns:
            Cached value or None if not found or expired
        """
        if not config.enabled:
            return None

        cache = InstanceCache.get_instance_cache(instance, relation_name)

        if "entry" not in cache:
            return None

        entry = cache["entry"]
        if entry.is_expired():
            # Remove expired entry
            del cache["entry"]
            return None

        return entry.value

    @staticmethod
    def set(instance: Any, relation_name: str, value: T, config: CacheConfig) -> None:
        """Store relation value in the instance cache.

        Args:
            instance: Model instance
            relation_name: Name of the relation
            value: Value to cache
            config: Cache configuration
        """
        if not config.enabled:
            return

        cache = InstanceCache.get_instance_cache(instance, relation_name)
        cache["entry"] = CacheEntry(value, config.ttl)

    @staticmethod
    def delete(instance: Any, relation_name: str) -> None:
        """Remove cached relation value from the instance.

        Args:
            instance: Model instance
            relation_name: Name of the relation
        """
        cache_attr = InstanceCache.get_cache_attr_name(relation_name)

        if hasattr(instance, cache_attr):
            cache = getattr(instance, cache_attr)
            if "entry" in cache:
                del cache["entry"]
