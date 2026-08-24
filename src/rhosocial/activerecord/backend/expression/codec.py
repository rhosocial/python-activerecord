# src/rhosocial/activerecord/backend/expression/codec.py
"""
JSON value codecs for non-JSON-native Python values.

The goal is "expression (via its serialized spec) <-> JSON string".
The standard library ``json`` handles all container walking, escaping and
parsing; it only cannot serialize a handful of non-native Python values
(datetime, Decimal, bytes, UUID, set, Enum, ...) on its own. Those values
are delegated to :func:`encode_value` / :func:`decode_value`, which are
registered by type and may be extended by developers via
:func:`register_codec`.

Encoded form for a non-native value::

    {"__value__": [<tag>, <payload>]}
"""

import base64
import importlib
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple
from uuid import UUID

# tag -> (py_type, encode(value)->payload, decode(payload)->value)
_CODECS: Dict[str, Tuple[Optional[type], Callable[[Any], Any], Callable[[Any], Any]]] = {}


def register_codec(
    tag: str,
    py_type: Optional[type],
    encode: Callable[[Any], Any],
    decode: Callable[[Any], Any],
) -> None:
    """Register a value codec.

    ``encode(value)`` must return a JSON-safe payload; ``decode(payload)``
    must reconstruct the original Python value. A ``tag`` must be unique and
    should not collide with existing reserved keys. Passing ``py_type=None``
    registers a catch-all codec (lowest priority, tried last).
    """
    if tag in _CODECS:
        raise ValueError(f"Codec tag '{tag}' is already registered")
    _CODECS[tag] = (py_type, encode, decode)


def _encode_enum(value):
    return [f"{type(value).__module__}.{type(value).__qualname__}", value.name]


def _decode_enum(payload):
    class_path, member_name = payload
    mod_name, _, qualname = class_path.rpartition(".")
    cls = getattr(importlib.import_module(mod_name), qualname)
    return cls[member_name]


_DEFAULT_CODECS: Dict[str, Tuple[Optional[type], Callable[[Any], Any], Callable[[Any], Any]]] = {
    "dt": (datetime, lambda v: v.isoformat(), lambda p: datetime.fromisoformat(p)),
    "d": (date, lambda v: v.isoformat(), lambda p: date.fromisoformat(p)),
    "tm": (time, lambda v: v.isoformat(), lambda p: time.fromisoformat(p)),
    "dec": (Decimal, str, Decimal),
    "b": (bytes, lambda v: base64.b64encode(v).decode("ascii"), lambda p: base64.b64decode(p)),
    "ba": (bytearray, lambda v: base64.b64encode(v).decode("ascii"), lambda p: bytearray(base64.b64decode(p))),
    "uuid": (UUID, str, UUID),
    "set": (set, list, lambda p: set(p)),
    "fset": (frozenset, list, lambda p: frozenset(p)),
    "enum": (Enum, _encode_enum, _decode_enum),
}

for _tag, (_t, _e, _dd) in _DEFAULT_CODECS.items():
    _CODECS[_tag] = (_t, _e, _dd)


def encode_value(value: Any) -> Optional[Dict[str, Any]]:
    """Encode a non-JSON-native value into ``{"__value__": [tag, payload]}``.

    Returns ``None`` when the value is JSON-native (or unknown).
    """
    # Most-specific types first; Enum is a base class so check it last.
    for tag, (py_type, encode, _decode) in _CODECS.items():
        if py_type is None:
            continue
        if isinstance(value, py_type):
            return {"__value__": [tag, encode(value)]}
    return None


def decode_value(obj: Any) -> Any:
    """object_hook for ``json.loads``: reverse :func:`encode_value`.

    Any dict other than a ``__value__`` container is returned untouched.
    """
    if isinstance(obj, dict) and "__value__" in obj and len(obj) == 1:
        payload = obj["__value__"]
        tag = payload[0]
        entry = _CODECS.get(tag)
        if entry is not None:
            _py_type, _encode, decode = entry
            return decode(payload[1])
    return obj