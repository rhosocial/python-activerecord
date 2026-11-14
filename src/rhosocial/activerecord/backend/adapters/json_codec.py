# src/rhosocial/activerecord/backend/adapters/json_codec.py
"""
JSON codec for the neutral adapter types.

The neutral types (geometry, vector, bit string, range, multirange and MAC
address) are duck-typed by this codec: an object participates when it exposes

* ``to_json_value()`` -- returning a JSON-serializable canonical value, and
* a stable lowercase type tag through ``json_type_tag`` (``type_tag`` and
  ``json_tag`` are accepted as aliases so backends may keep their own spelling);

and its class exposes ``from_json_value(value)`` for decoding.  Classes can
also be wired into the decoder explicitly with :func:`register_type`, which is
what supports types that do not advertise a tag attribute.

Nothing from the sibling ``geometry``/``vector``/... modules is imported at
module import time.  The built-in tag -> class table is resolved lazily on
first use, so this module has no import cycles and works even when a family
module is not loaded.

Tagged mode is off by default.  When enabled, the canonical value is wrapped in
a ``__type__`` envelope so mixed JSON documents (for example a JSON/JSONB
column holding several neutral types) can be decoded without knowing the field
types:

* dict payload -- the marker is merged into the payload::

      {"__type__": "geometry", "type": "Point", "coordinates": [1.0, 2.0]}

* non-dict payload -- the value is moved under ``value``::

      {"__type__": "vector", "value": [1.0, 2.0]}

``object_hook`` rebuilds an instance only when the ``__type__`` marker names a
registered tag; every other dict is returned untouched.  The standard
:mod:`json` module is never monkey-patched: callers opt in explicitly::

    codec = AdapterJSONCodec()
    json.dumps(value, default=codec.default)

    codec = AdapterJSONCodec(tagged=True)
    text = codec.dumps(value)
    value = codec.loads(text)

Note: documents that already use ``__type__`` for an unrelated purpose must be
decoded with plain :func:`json.loads`, or with ``object_hook=None``.
"""

from __future__ import annotations

import importlib
import json
from typing import Any, Dict, Iterable, Optional, Tuple, Type

__all__ = [
    "AdapterJSONCodec",
    "register_type",
    "unregister_type",
    "registered_types",
]

#: Attribute names searched (in order) for the object's stable type tag.
_TAG_ATTRIBUTES: Tuple[str, ...] = (
    "json_type_tag",
    "type_tag",
    "json_tag",
    "__json_type_tag__",
)

#: Tags defined by the neutral adapter package, resolved lazily to avoid
#: importing the family modules (and their dependencies) at import time.
_DEFAULT_TYPE_SPECS: Dict[str, Tuple[str, str]] = {
    "geometry": ("rhosocial.activerecord.backend.adapters.geometry", "Geometry"),
    "vector": ("rhosocial.activerecord.backend.adapters.vector", "Vector"),
    "bitstring": ("rhosocial.activerecord.backend.adapters.bitstring", "BitString"),
    "range": ("rhosocial.activerecord.backend.adapters.range", "Range"),
    "multirange": ("rhosocial.activerecord.backend.adapters.range", "Multirange"),
    "mac_address": ("rhosocial.activerecord.backend.adapters.network", "MacAddress"),
}

#: Explicit tag -> class mapping; lazy defaults are cached here once resolved.
_registered: Dict[str, Type[Any]] = {}


def register_type(tag: str, cls: Type[Any]) -> None:
    """Register ``cls`` as the decoder for ``tag``.

    Registration is optional for types that declare a ``json_type_tag``
    attribute; it is required for types that do not, and it also lets callers
    override which class rebuilds an existing tag.

    Args:
        tag: Lowercase type tag, for example ``"geometry"`` or ``"vector"``.
        cls: Class exposing ``to_json_value`` and ``from_json_value``.

    Raises:
        ValueError: If ``tag`` is not a non-empty string.
        TypeError: If ``cls`` is not a class or lacks the JSON methods.
    """
    if not isinstance(tag, str) or not tag.strip():
        raise ValueError("tag must be a non-empty string")
    if not isinstance(cls, type):
        raise TypeError(f"cls must be a class, got {type(cls).__name__}")
    for method in ("to_json_value", "from_json_value"):
        if not callable(getattr(cls, method, None)):
            raise TypeError(f"{cls.__name__} must define {method}() to be registered as a JSON type")
    _registered[tag.strip().lower()] = cls


def unregister_type(tag: str) -> None:
    """Remove an explicit registration for ``tag`` (no-op when absent)."""
    _registered.pop(tag.strip().lower(), None)


def registered_types() -> Dict[str, Type[Any]]:
    """Return a copy of the tag -> class registry, resolving lazy defaults."""
    for tag in _DEFAULT_TYPE_SPECS:
        _resolve_type(tag)
    return dict(_registered)


def _resolve_type(tag: str) -> Optional[Type[Any]]:
    """Return the class registered for ``tag``, importing a lazy default if needed."""
    cls = _registered.get(tag)
    if cls is not None:
        return cls
    spec = _DEFAULT_TYPE_SPECS.get(tag)
    if spec is None:
        return None
    module_name, attr_name = spec
    try:
        module = importlib.import_module(module_name)
        cls = getattr(module, attr_name, None)
    except (ImportError, AttributeError):
        return None
    if isinstance(cls, type) and callable(getattr(cls, "from_json_value", None)):
        _registered.setdefault(tag, cls)
        return cls
    return None


def _iter_registered_types() -> Iterable[Tuple[str, Type[Any]]]:
    """Yield ``(tag, class)`` pairs, including lazily resolved defaults."""
    for tag, cls in list(_registered.items()):
        yield tag, cls
    for tag in _DEFAULT_TYPE_SPECS:
        if tag in _registered:
            continue
        cls = _resolve_type(tag)
        if cls is not None:
            yield tag, cls


def _tag_attribute(obj: Any) -> Optional[str]:
    """Return the tag declared on ``obj`` itself, if any."""
    for attr in _TAG_ATTRIBUTES:
        tag = getattr(obj, attr, None)
        if isinstance(tag, str) and tag.strip():
            return tag.strip().lower()
    return None


def _detect_tag(obj: Any) -> Optional[str]:
    """Return the stable tag for a neutral object, or ``None``."""
    tag = _tag_attribute(obj)
    if tag is not None:
        return tag
    for tag, cls in _iter_registered_types():
        if isinstance(obj, cls):
            return tag
    return None


class AdapterJSONCodec:
    """JSON encoder/decoder helpers for the neutral adapter types.

    Attributes:
        tagged: When ``True``, :meth:`default` emits a ``__type__`` marker.
            Off by default so canonical values (notably GeoJSON) are not
            polluted.  Decoding is marker-driven either way.
    """

    tagged: bool = False

    def __init__(self, tagged: Optional[bool] = None) -> None:
        if tagged is not None:
            self.tagged = bool(tagged)

    def default(self, obj: Any) -> Any:
        """Encode one neutral object, or raise ``TypeError`` for anything else.

        Suitable for passing as ``default=`` to :func:`json.dumps`.
        """
        to_json_value = getattr(obj, "to_json_value", None)
        if not callable(to_json_value):
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        tag = _detect_tag(obj)
        if tag is None:
            raise TypeError(
                f"Object of type {type(obj).__name__} is not JSON serializable: "
                "neutral JSON types must declare a type tag or be registered with register_type()"
            )

        value = to_json_value()
        if not self.tagged:
            return value
        if isinstance(value, dict):
            tagged_value = dict(value)
            tagged_value["__type__"] = tag
            return tagged_value
        return {"__type__": tag, "value": value}

    def object_hook(self, value: Dict[str, Any]) -> Any:
        """Rebuild a neutral instance when a registered ``__type__`` marker is present.

        Any other dict -- including one whose ``__type__`` tag is unknown -- is
        returned unchanged.
        """
        tag = value.get("__type__")
        if not isinstance(tag, str):
            return value
        cls = _resolve_type(tag.strip().lower())
        if cls is None:
            return value
        from_json_value = getattr(cls, "from_json_value", None)
        if not callable(from_json_value):
            return value

        payload = {key: item for key, item in value.items() if key != "__type__"}
        if set(payload) == {"value"}:
            return from_json_value(payload["value"])
        return from_json_value(payload)

    def dumps(self, obj: Any, **kwargs: Any) -> str:
        """Serialize ``obj`` using this codec's ``default`` hook.

        Keyword arguments are forwarded to :func:`json.dumps`.  An explicit
        ``default`` (other than ``None``) is respected unchanged.
        """
        if kwargs.get("default") is None:
            kwargs["default"] = self.default
        return json.dumps(obj, **kwargs)

    def loads(self, text: str, **kwargs: Any) -> Any:
        """Deserialize ``text`` using this codec's ``object_hook``.

        Keyword arguments are forwarded to :func:`json.loads`.  Pass
        ``object_hook=None`` to disable tag reconstruction.
        """
        kwargs.setdefault("object_hook", self.object_hook)
        return json.loads(text, **kwargs)
