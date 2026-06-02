# src/rhosocial/activerecord/relation/cache_backends/_protocol.py
"""
Abstract definitions for pluggable cache backends.

Provides:
- ``CacheBackend`` — protocol that every backend must implement
- ``CacheSerializer`` — default pickle-based serializer (used by RedisCache)
- ``CacheResult`` — value + metadata returned by backends that support
  proactive refresh (origin, age, TTL)
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Generic, Optional, Protocol, TypeVar

if TYPE_CHECKING:
    from ..cache import CacheConfig

T = TypeVar("T")


@dataclass
class CacheResult(Generic[T]):
    """Cache entry with metadata used for user-driven refresh decisions.

    The framework provides metadata but does NOT implement automatic
    proactive refresh or cache stampede protection — those are
    application-level concerns:

    * ``age`` — how long this entry has existed.  Application code can
      compare against TTL to decide whether a refresh is warranted.
    * ``origin`` — which container/process created the entry.  In a
      distributed setup the application can use this to assign refresh
      responsibility to a single owner.
    * ``ttl`` — the TTL that was set when the entry was stored.

    Example usage in a scheduled warm-up job::

        result = InstanceCache.get_with_meta(instance, "posts", config)
        if result is not None and result.age > 0.8 * result.ttl:
            fresh_data = loader.load(instance)
            InstanceCache.set(instance, "posts", fresh_data, config)

    Attributes:
        value: The cached value.
        age: Seconds since the entry was created.
        origin: Identifier of the origin that created this entry, or None.
        ttl: TTL in seconds that was applied when the entry was stored.
    """

    value: T
    age: float = 0.0
    origin: Optional[str] = None
    ttl: Optional[int] = None


class CacheBackend(Protocol[T]):
    """Cache backend protocol for relation data.

    Implementations must provide get/set/delete.
    The ``instance`` parameter is the model instance that owns the relation.
    """

    @property
    def origin(self) -> Optional[str]:
        """Return this backend's origin identifier, or None if unknown."""
        ...

    def get(
        self,
        instance: Any,
        relation_name: str,
        config: CacheConfig,
    ) -> Optional[T]:
        ...

    def set(
        self,
        instance: Any,
        relation_name: str,
        value: T,
        config: CacheConfig,
    ) -> None:
        ...

    def delete(
        self,
        instance: Any,
        relation_name: str,
        config: Optional[CacheConfig] = None,
    ) -> None:
        ...


class CacheSerializer:
    """Default serializer for remote cache backends.

    Uses pickle for flexibility. Can be subclassed to use JSON + type mapping.
    """

    @staticmethod
    def serialize(value: Any) -> bytes:
        return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def deserialize(data: bytes) -> Any:
        return pickle.loads(data)
