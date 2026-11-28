# src/rhosocial/activerecord/backend/expression_registry/__init__.py
"""Expression registration: the kind tables, their collection, and the codec.

This namespace is independent of both the backends and the dialects:

* :class:`~.registry.ExpressionRegistry` is the table type — a
  ``kind -> fully qualified class name`` whitelist whose ``resolve_node``
  imports the class only when an artifact names the kind;
* :func:`~.registration.collect_expressions` turns one expression package into
  the mapping its owner publishes;
* :data:`~.core_registry.CORE_EXPRESSIONS` and
  :data:`~.core_registry.CORE_EXPRESSION_REGISTRY` are core's own;
* :mod:`.serialization` turns a tree into a ``{kind, params}`` artifact and
  back, resolving kinds through whichever table the caller supplies.

A backend publishes ``<NAME>_EXPRESSIONS`` (its own mapping) and
``<NAME>_EXPRESSION_REGISTRY`` (core's mapping merged with its own) in
``backend.impl.<name>.expression_registry``. Neither side imports the other's
implementation packages, and no dialect takes part in registration.

That merge is a **read-side** whitelist, not a render-support claim: admitting
a core kind says the reader can rebuild that node class from an artifact, not
that the backend's dialect implements a formatter for it. Formatting belongs to
the dialect and is independent of what any registry admits — and can itself
vary with the dialect's version (SQLite's RETURNING clause, for instance).
"""

from .core_registry import CORE_EXPRESSIONS, CORE_EXPRESSION_REGISTRY
from .registration import collect_expressions, merge_expressions
from .registry import ExpressionRegistry, RegistryError, RegistryReason
from .serialization import (
    ArtifactError,
    ExpressionDeserializationError,
    ExpressionSerializer,
    decode_artifact,
    deserialize,
    deserialize_json,
    deserialize_xml,
    encode_artifact,
    serialize,
    serialize_json,
    serialize_xml,
)

__all__ = [
    "ExpressionRegistry",
    "RegistryError",
    "RegistryReason",
    "collect_expressions",
    "merge_expressions",
    "CORE_EXPRESSIONS",
    "CORE_EXPRESSION_REGISTRY",
    "ExpressionSerializer",
    "ExpressionDeserializationError",
    "ArtifactError",
    "serialize",
    "deserialize",
    "serialize_json",
    "deserialize_json",
    "serialize_xml",
    "deserialize_xml",
    "encode_artifact",
    "decode_artifact",
]
