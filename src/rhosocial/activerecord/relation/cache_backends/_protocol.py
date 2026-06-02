# src/rhosocial/activerecord/relation/cache_backends/_protocol.py
"""
Abstract definitions for pluggable cache backends.

Provides:
- ``CacheBackend`` — protocol that every backend must implement
- ``CacheSerializer`` — JSON-based serializer (default), with msgpack and
  pickle alternatives
- ``CacheResult`` — value + metadata returned by backends that support
  proactive refresh (origin, age, TTL)
"""

from __future__ import annotations

import json
import logging
import pickle
import warnings
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from enum import Enum
from typing import (TYPE_CHECKING, Any, Callable, Dict, Generic, Optional,
                    Protocol, TypeVar, Union)

if TYPE_CHECKING:
    from ..cache import CacheConfig

T = TypeVar("T")

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

logger = logging.getLogger(__name__)


class _EnhancedJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles common Python types beyond the standard set."""
    def default(self, o: Any) -> Any:
        if isinstance(o, (datetime, date)):
            return {"__type__": "datetime", "value": o.isoformat()}
        if isinstance(o, time):
            return {"__type__": "time", "value": o.isoformat()}
        if isinstance(o, timedelta):
            return {"__type__": "timedelta", "value": o.total_seconds()}
        if isinstance(o, Enum):
            return {"__type__": "enum", "module": type(o).__module__, "class": type(o).__qualname__, "value": o.name}
        if isinstance(o, bytes):
            return {"__type__": "bytes", "value": o.hex()}
        if isinstance(o, set):
            return {"__type__": "set", "value": list(o)}
        if isinstance(o, complex):
            return {"__type__": "complex", "value": [o.real, o.imag]}
        if isinstance(o, range):
            return {"__type__": "range", "value": [o.start, o.stop, o.step]}
        return super().default(o)


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
    """Serializer for cache values.

    Default format is **JSON**, which is safe, cross-language, and
    human-readable.  Two alternative formats are available:

    * ``format="msgpack"`` — faster encoding/decoding and smaller payloads.
      Requires the ``msgpack`` package.
    * ``format="pickle"`` — supports arbitrary Python objects.
      **UNSAFE** — deserialising untrusted data can execute arbitrary code.
      Only use in trusted environments with known data.

    The JSON encoder handles ``datetime``, ``date``, ``time``,
    ``timedelta``, ``Enum``, ``bytes`` (hex), ``set`` (as list),
    ``complex``, and ``range`` out of the box.

    Usage::

        # default (JSON)
        ser = CacheSerializer()
        data = ser.serialize({"key": datetime.now()})
        restored = ser.deserialize(data)

        # msgpack (faster)
        ser = CacheSerializer(format="msgpack")

        # pickle (UNSAFE, trusted env only)
        ser = CacheSerializer(format="pickle")
    """

    FORMAT_JSON = "json"
    FORMAT_MSGPACK = "msgpack"
    FORMAT_PICKLE = "pickle"

    _FORMATS: Dict[str, str] = {
        "json": FORMAT_JSON,
        "msgpack": FORMAT_MSGPACK,
        "pickle": FORMAT_PICKLE,
    }

    def __init__(self, format: str = "json"):
        normalized = self._FORMATS.get(format.lower())
        if normalized is None:
            raise ValueError(
                f"Unknown serializer format {format!r}. "
                f"Choose from: {', '.join(self._FORMATS)}"
            )
        self._format = normalized
        if normalized == self.FORMAT_MSGPACK:
            try:
                import msgpack  # noqa: F401
            except ImportError:
                raise ImportError(
                    "msgpack format requires the 'msgpack' package. "
                    "Install it with: pip install msgpack"
                )
        elif normalized == self.FORMAT_PICKLE:
            warnings.warn(
                "Pickle deserialization is unsafe. Only use this format "
                "in trusted environments with known data sources. "
                "JSON is the recommended default.",
                UserWarning,
                stacklevel=2,
            )

    @property
    def format(self) -> str:
        return self._format

    def serialize(self, value: Any) -> bytes:
        if self._format == self.FORMAT_JSON:
            return json.dumps(value, cls=_EnhancedJSONEncoder, ensure_ascii=False).encode("utf-8")
        elif self._format == self.FORMAT_MSGPACK:
            import msgpack
            return msgpack.dumps(value)
        else:
            return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)

    def deserialize(self, data: bytes) -> Any:
        if self._format == self.FORMAT_JSON:
            return json.loads(data.decode("utf-8"))
        elif self._format == self.FORMAT_MSGPACK:
            import msgpack
            return msgpack.loads(data)
        else:
            return pickle.loads(data)
