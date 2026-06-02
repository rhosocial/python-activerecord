# src/rhosocial/activerecord/relation/cache_backends/in_memory.py
"""
In-memory cache backend.

Stores ``CacheEntry`` objects as instance attributes
(``_relation_cache_{name}["entry"]``), matching the original
``InstanceCache`` behavior exactly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..cache import CacheConfig


class InMemoryCache:
    """In-memory cache using instance attributes."""

    @property
    def origin(self) -> None:
        """InMemoryCache has no origin tracking."""
        return None

    @staticmethod
    def get_cache_attr_name(relation_name: str) -> str:
        return f"_relation_cache_{relation_name}"

    def get(self, instance: Any, relation_name: str, config: "CacheConfig"):
        if not config.enabled:
            return None
        cache = self._get_cache(instance, relation_name)
        if "entry" not in cache:
            return None
        entry = cache["entry"]
        if entry.is_expired():
            del cache["entry"]
            return None
        return entry.value

    def set(self, instance: Any, relation_name: str, value: Any, config: "CacheConfig"):
        if not config.enabled:
            return
        from ..cache import CacheEntry
        cache = self._get_cache(instance, relation_name)
        cache["entry"] = CacheEntry(value, config.ttl)

    def delete(self, instance: Any, relation_name: str, config: "CacheConfig" = None):
        if config is not None and not config.enabled:
            return
        attr = self.get_cache_attr_name(relation_name)
        if hasattr(instance, attr):
            cache = getattr(instance, attr)
            if "entry" in cache:
                del cache["entry"]

    def _get_cache(self, instance: Any, relation_name: str):
        attr = self.get_cache_attr_name(relation_name)
        if not hasattr(instance, attr):
            setattr(instance, attr, {})
        return getattr(instance, attr)
