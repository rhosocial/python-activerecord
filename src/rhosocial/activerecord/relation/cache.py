"""
Caching implementation for relation data.
Provides configurable caching with TTL and size limits.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Optional, Dict

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