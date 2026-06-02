# src/rhosocial/activerecord/relation/cache_backends/redis.py
"""
Redis-backed distributed cache backend.

Key format: ``{prefix}{model_name}:{pk_value}:{relation_name}``

When ``record_origin=True``, each value is wrapped in a JSON envelope
with origin hostname and timestamp for observability.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import socket
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Optional

from ._protocol import CacheSerializer

if TYPE_CHECKING:
    from ..cache import CacheConfig

logger = logging.getLogger(__name__)


@dataclass
class RedisConfig:
    """Connection configuration for RedisCache.

    Usage::

        # explicit (recommended for production)
        config = RedisConfig(host="10.0.1.5", port=16379, password="secret")

        # from environment (REDIS_HOST / REDIS_PORT / REDIS_PASSWORD / …)
        # Use with care: picks up whatever REDIS_* vars happen to be set.
        # Mainly intended for testing and CI.
        config = RedisConfig.from_env()
    """

    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    prefix: str = "ar:cache:"
    socket_connect_timeout: int = 5

    @classmethod
    def from_env(cls, prefix: str = "REDIS_") -> RedisConfig:
        return cls(
            host=os.getenv(f"{prefix}HOST", "localhost"),
            port=int(os.getenv(f"{prefix}PORT", "6379")),
            password=os.getenv(f"{prefix}PASSWORD"),
            db=int(os.getenv(f"{prefix}DB", "0")),
            prefix=os.getenv(f"{prefix}PREFIX", "ar:cache:"),
            socket_connect_timeout=int(os.getenv(f"{prefix}SOCKET_CONNECT_TIMEOUT", "5")),
        )


class RedisCache:
    """Distributed cache backend backed by Redis.

    Two construction paths:

    1. Provide an existing ``redis.Redis`` client::

           import redis
           client = redis.Redis(host="localhost", port=6379, password="secret")
           cache = RedisCache(client=client)

    2. Provide a :class:`RedisConfig` — the client is created internally::

           config = RedisConfig(host="redis.example.com", port=6379)
           cache = RedisCache(config=config)

    Args:
        client: A ``redis.Redis`` (or compatible) instance.
        config: A :class:`RedisConfig` instance.
        prefix: Key prefix (overrides ``config.prefix`` when provided).
        serializer: Serializer for cache values.
        record_origin: Whether to embed origin metadata (default False).
        origin_name: Override for origin hostname (default: ``socket.gethostname()``).
    """

    def __init__(
        self,
        client: Any = None,
        config: Optional[RedisConfig] = None,
        prefix: Optional[str] = None,
        serializer: Optional[CacheSerializer] = None,
        record_origin: bool = False,
        origin_name: Optional[str] = None,
    ):
        if client is not None:
            self._client = client
        elif config is not None:
            import redis as _redis
            self._client = _redis.Redis(
                host=config.host,
                port=config.port,
                password=config.password or None,
                db=config.db,
                socket_connect_timeout=config.socket_connect_timeout,
            )
        else:
            raise TypeError("Either client= or config= must be provided to RedisCache")

        self._prefix = prefix or (config.prefix if config else "ar:cache:")
        self._serializer = serializer or CacheSerializer()
        self._record_origin = record_origin
        self._origin_name = origin_name or socket.gethostname()
        self._origin = self._origin_name if self._record_origin else None

    @property
    def origin(self) -> Optional[str]:
        return self._origin

    def _make_key(self, instance: Any, relation_name: str) -> str:
        cls = type(instance)
        pk_val = getattr(instance, instance.primary_key(), None)
        if pk_val is None:
            raise ValueError(
                f"Cannot build cache key for {cls.__name__}.{relation_name}: "
                f"instance has no primary key value"
            )
        return f"{self._prefix}{cls.__name__}:{pk_val}:{relation_name}"

    def get(self, instance: Any, relation_name: str, config: "CacheConfig"):
        if not config.enabled:
            return None
        key = self._make_key(instance, relation_name)
        payload = self._client.get(key)
        if payload is None:
            return None
        if self._record_origin:
            meta = json.loads(payload)
            ttl_remaining = max(0, meta["t"] + (config.ttl or 0) - time.time())
            logger.debug(
                "Cache HIT for %s, origin=%s, age=%.1fs, ttl_remaining=%.1f",
                key, meta["o"], time.time() - meta["t"], ttl_remaining,
            )
            return self._serializer.deserialize(base64.b64decode(meta["v"]))
        return self._serializer.deserialize(payload)

    def get_with_meta(
        self, instance: Any, relation_name: str, config: "CacheConfig"
    ) -> Optional["CacheResult"]:
        from ._protocol import CacheResult

        if not config.enabled:
            return None
        key = self._make_key(instance, relation_name)
        payload = self._client.get(key)
        if payload is None:
            return None
        if self._record_origin:
            meta = json.loads(payload)
            now = time.time()
            age = now - meta["t"]
            ttl_remaining = max(0, (config.ttl or 0) - age)
            value = self._serializer.deserialize(base64.b64decode(meta["v"]))
            logger.debug(
                "Cache HIT for %s, origin=%s, age=%.1fs, ttl_remaining=%.1f",
                key, meta["o"], age, ttl_remaining,
            )
            return CacheResult(
                value=value,
                age=age,
                origin=meta["o"],
                ttl=config.ttl,
            )
        return CacheResult(
            value=self._serializer.deserialize(payload),
            age=0.0,
            origin=None,
            ttl=config.ttl,
        )

    def set(self, instance: Any, relation_name: str, value: Any, config: "CacheConfig"):
        if not config.enabled:
            return
        key = self._make_key(instance, relation_name)
        data = self._serializer.serialize(value)
        if self._record_origin:
            payload = json.dumps({
                "v": base64.b64encode(data).decode(),
                "o": self._origin,
                "t": time.time(),
            })
        else:
            payload = data
        if config.ttl is not None:
            self._client.set(key, payload, ex=config.ttl)
        else:
            self._client.set(key, payload)

    def delete(self, instance: Any, relation_name: str, config: "CacheConfig" = None):
        if config is not None and not config.enabled:
            return
        key = self._make_key(instance, relation_name)
        self._client.delete(key)

    def invalidate_instance(self, instance: Any):
        """Delete all cached relations for an instance."""
        pattern = f"{self._prefix}{type(instance).__name__}:{getattr(instance, instance.primary_key(), '*')}:*"
        self._delete_pattern(pattern)

    def _delete_pattern(self, pattern: str):
        cursor = 0
        while True:
            cursor, keys = self._client.scan(cursor, match=pattern, count=100)
            if keys:
                self._client.delete(*keys)
            if cursor == 0:
                break
