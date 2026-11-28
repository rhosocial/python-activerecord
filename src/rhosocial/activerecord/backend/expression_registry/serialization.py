# src/rhosocial/activerecord/backend/expression_registry/serialization.py
"""
Expression serialization and deserialization utilities.

An artifact is a **bare node**: ``{"kind": ..., "params": {...}}`` and nothing
else (§4.11.3). There is no envelope around it, and no marker vocabulary
inside it.

* A node's **kind** is its identity -- derived from the class name (§4.11.1),
  computed and never stored, so the two cannot drift. Every node follows that
  rule, including the parameter node: its kind is ``parameter``.
* A nested node is a nested ``{"kind", "params"}``, recognised by its shape
  alone. No key says "this is a node": a marker is a dispatch, and a dispatch
  has to be agreed by every reader -- which is exactly what an artifact cannot
  assume, when the same bytes must be read by four languages.
* A parameter's value is carried **as-is**. The serializer does not name
  or convert a value type: whether ``json.dumps`` can write a value is that
  type's own contract, and the reader gets back exactly what was written.

Reading is the one moment a registry is needed: it is what turns a ``kind``
back into a class. The registry (:mod:`.registry`) is that table and nothing
more -- it registers, checks and dispatches *rendering*; the serializer never
consults it, because a node carries its own identity.

The artifact is untrusted input (§4.11.4), so a read fails explicitly and
names the kind: an unknown kind, a leftover envelope field, an unknown or
missing parameter.
"""

import inspect
import json
from typing import Any, Callable, Dict, Optional, Sequence

from ..expression.bases.bases import BaseExpression
from .core_registry import CORE_EXPRESSION_REGISTRY
from .registry import ExpressionRegistry


class ExpressionDeserializationError(Exception):
    """Raised when deserialization fails due to invalid spec or missing parameters."""

    pass


_DEFAULT_MAX_DEPTH = 64
_DEFAULT_WARN_THRESHOLD = 0.8


# ---------------------------------------------------------------------------
class ExpressionSerializer:
    """Serializer and deserializer for BaseExpression instances.

    Instance-based design allows different configurations for different use cases.

    Attributes:
        max_depth: Maximum nesting depth for both directions (default: 64).
                   If exceeded, an artifact read or write fails explicitly.
        allowed_types: Optional allowlist of expression **kind** names applied
                       during deserialization. Entries may be exact kinds or
                       shell-style globs (e.g. ``"column*"``). ``None``
                       (default) admits every kind the selected table holds.

    Example:
        # Default configuration
        serializer = ExpressionSerializer()
        spec = serializer.serialize(expr)
        restored = serializer.deserialize(spec)

        # Custom configuration
        deep_serializer = ExpressionSerializer(max_depth=128)

        # Read-only tool channel: only columns, values and SELECTs
        readonly = ExpressionSerializer(allowed_types=[
            "column", "parameter", "query_statement",
        ])
    """

    def __init__(
        self,
        max_depth: int = _DEFAULT_MAX_DEPTH,
        allowed_types: Optional[Sequence[str]] = None,
    ):
        if max_depth <= 0:
            raise ValueError("max_depth must be a positive integer")
        self.max_depth = max_depth
        self.allowed_types: Optional[tuple] = tuple(allowed_types) if allowed_types else None

    def serialize(self, expr: BaseExpression, _depth: int = 0) -> Dict[str, Any]:
        """Serialize to a bare `{kind, params}` artifact (§4.11.3).

        The same codec the module-level :func:serialize uses: an artifact is
        an artifact regardless of who asked for it, so this class configures
        rather than reimplements. Key order is fixed, and the dialect is absent
        so the artifact can be re-rendered elsewhere.
        """
        return encode_artifact(expr, _depth, self.max_depth)

    def deserialize(
        self,
        spec: Dict[str, Any],
        *,
        registry: Any = None,
    ) -> BaseExpression:
        """Rebuild from a bare `{kind, params}` artifact.

        The artifact is untrusted input (§4.11.4): unknown kinds, leftover
        envelope fields and unrecognised parameters all fail explicitly and
        name the kind. `allowed_types`, when set, restricts which kinds this
        reader may produce — a read-only channel can name only the kinds it
        means to accept.

        The read admits the kinds of ``registry``, or core's table when none is
        given. The dialect plays no part: the artifact carries no dialect, and
        the rebuilt tree is unbound — render it with ``to_sql(dialect)``.
        """
        if registry is None:
            registry = CORE_EXPRESSION_REGISTRY
        if self.allowed_types is not None:
            registry = self._restrict(registry)
        return decode_artifact(spec, registry=registry, _max_depth=self.max_depth)

    def _restrict(self, registry: "ExpressionRegistry"):
        """A registry view admitting only `allowed_types` kinds.

        Entries are kind names, optionally with shell-style globs (``"col*"``),
        because a kind is the only identity that crosses the wire (§7.2) —
        there is no import path left to prefix-match on.

        Built by copying, so restricting a read never narrows the registry the
        rest of the process uses. ``registry`` is already selected (explicit,
        or core) by the caller.
        """
        from fnmatch import fnmatchcase

        source = registry
        patterns = tuple(self.allowed_types)
        # Copy, then subtract, rather than rebuild from what matches: the
        # table's keys are the artifact kinds, and copying keeps exactly the
        # ones the channel admits.
        view = source.twin()
        for kind in view.node_kinds():
            if kind in patterns or any(fnmatchcase(kind, p) for p in patterns):
                continue
            view.unregister_node(kind)
        return view

    def serialize_json(
        self,
        expr: BaseExpression,
        *,
        default: Optional[Callable[[Any], Any]] = None,
    ) -> str:
        """Serialize an expression instance into a JSON string.

        Every value is left as its host type. A value ``json.dumps`` cannot
        write is the caller's responsibility: pass ``default`` to turn it into
        a JSON-native form. The serializer never guesses a type or rewrites a
        value.
        """
        return json.dumps(self.serialize(expr), default=default)

    def deserialize_json(
        self,
        spec_str: str,
        *,
        registry: Any = None,
        object_hook: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> BaseExpression:
        """Reconstruct an expression from a JSON string produced by
        :meth:`serialize_json`.

        ``object_hook`` is passed straight to ``json.loads`` for callers whose
        values need reconstruction. It is not used by the codec: a bare node
        is already recognised by its ``{kind, params}`` shape -- see
        :func:`decode_artifact`.
        """
        return self.deserialize(
            json.loads(spec_str, object_hook=object_hook), registry=registry
        )

    def serialize_xml(self, expr: BaseExpression) -> bytes:
        """Serialize an expression instance into an XML document (bytes).

        The spec (with the two reserved value wrappers) is rendered into
        an XML document by :mod:`xml_serialization`, which uses the standard
        library ``xml.etree.ElementTree``.
        """
        from . import xml_serialization

        return xml_serialization.serialize_xml(self.serialize(expr))

    def deserialize_xml(
        self,
        payload: bytes,
        *,
        registry: Any = None,
    ) -> BaseExpression:
        """Reconstruct an expression from an XML document produced by
        :meth:`serialize_xml`.
        """
        from . import xml_serialization

        spec = xml_serialization.deserialize_xml(payload)
        return self.deserialize(spec, registry=registry)


_default_serializer = ExpressionSerializer()


# ---------------------------------------------------------------------------
# Bare-node codec (§4.11.3 — the artifact IS the node: no envelope).
#
# Write and read are asymmetric about the registry (rules §7.2):
#
#   serialize   no registry at all — the node reports its own kind, derived
#               from the class name. Nothing is looked up, so serialization
#               works even when no registry was ever built.
#
#   deserialize takes a registry. That is the one moment a kind has to be
#               turned back into a class, and it is why the registry exists.
#               The dialect plays no part in it: the artifact is data, carries
#               no dialect, and rendering binds one at ``to_sql(dialect)``.
#
# The registry itself is an independent module that starts empty and knows
# nothing about which expressions exist; assembling the instances the owners
# publish belongs to :mod:`.registration` / :mod:`.core_registry`.
# ---------------------------------------------------------------------------


class ArtifactError(ExpressionDeserializationError):
    """Raised when an artifact cannot be read. Always names the kind."""


def _is_node(value):
    """Whether *value* has the shape of a nested artifact.

    A node is exactly ``{kind, params}`` and nothing else (§4.11.3), so the shape
    alone identifies one -- no marker key, and no reading of the parameter's
    declared type. Whether the position *wants* a node is a different question,
    and the constructor answers it: an ``isinstance`` against what that parameter
    accepts.

    The shape test deliberately does **not** consult the registry. Asking "is
    this kind registered?" here would answer ``False`` for an unregistered kind
    and pass the node through as a plain mapping, which is exactly the bypass the
    whitelist exists to prevent. An unregistered kind must reach
    :func:`decode_artifact` and be refused by name.
    """
    return (
        isinstance(value, dict)
        and set(value) == {"kind", "params"}
        and isinstance(value.get("kind"), str)
        and bool(value["kind"])
        and isinstance(value.get("params"), dict)
    )


def encode_artifact(expr, _depth=0, _max_depth=_DEFAULT_MAX_DEPTH):
    """Encode one node as a bare `{kind, params}` artifact. No registry.

    Key order is fixed: ``kind`` then ``params``, params in constructor order.
    Two encodings of the same tree are thus byte-identical and comparable.
    """
    if _depth > _max_depth:
        raise ArtifactError(f"expression nesting depth exceeds {_max_depth}")
    kind = expr.kind()
    params = expr.get_params()
    if not isinstance(params, dict):
        raise ArtifactError(
            f"kind '{kind}'.get_params() returned {type(params).__name__}, "
            f"expected a dict of constructor parameters"
        )
    return {"kind": kind, "params": _encode_value(params, _depth + 1, _max_depth)}


def _encode_value(value, depth, max_depth=_DEFAULT_MAX_DEPTH):
    if isinstance(value, BaseExpression):
        # A nested node is its own artifact -- the same {kind, params} a
        # top-level node is. No marker: the shape says what it is, and a marker
        # would be a second, weaker spelling of the same fact.
        return encode_artifact(value, depth, max_depth)
    # Containers are structural parameters; a parameter's own value is
    # carried as-is. Whether json.dumps can write it is the value type's
    # contract, not the serializer's.
    if isinstance(value, (list, tuple)):
        return [_encode_value(i, depth + 1, max_depth) for i in value]
    if isinstance(value, dict):
        return {k: _encode_value(v, depth + 1, max_depth) for k, v in value.items()}
    return value


def _decode_value(value, depth, registry, max_depth=_DEFAULT_MAX_DEPTH):
    if depth > max_depth:
        raise ArtifactError(f"artifact nesting depth exceeds {max_depth}")
    if isinstance(value, dict):
        if _is_node(value):
            return decode_artifact(value, depth + 1, registry, _max_depth=max_depth)
        # Any other object is a plain mapping parameter, handed through
        # untouched. There are no markers left to dispatch on: a value that was
        # not JSON-native travelled as a scalar its own kind names, so nothing
        # here has to recognise a spelling in order to undo it.
        return {k: _decode_value(v, depth + 1, registry, max_depth) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode_value(i, depth + 1, registry, max_depth) for i in value]
    if isinstance(value, tuple):
        # The XML and dataclass paths hand back real tuples rather than lists,
        # and their items need decoding just as much.
        return tuple(_decode_value(i, depth + 1, registry, max_depth) for i in value)
    return value


def decode_artifact(obj, _depth=0, registry=None, _max_depth=_DEFAULT_MAX_DEPTH):
    """Rebuild one node from a bare `{kind, params}` artifact.

    Args:
        obj: The artifact node — external, untrusted input.
        registry: The registry to resolve kinds through. When omitted,
            :data:`CORE_EXPRESSION_REGISTRY` answers. Pass a backend's table to admit the
            kinds that backend's expression package declares.

    The rebuilt tree is **unbound**: the artifact carries no dialect, so
    rendering binds one with ``to_sql(dialect)``.
    """

    if _depth > _max_depth:
        raise ArtifactError(f"artifact nesting depth exceeds {_max_depth}")
    if registry is None:
        registry = CORE_EXPRESSION_REGISTRY
    if not isinstance(obj, dict):
        raise ArtifactError(
            f"an artifact node must be an object with 'kind' and 'params', got "
            f"{type(obj).__name__}"
        )
    extra = sorted(set(obj) - {"kind", "params"})
    if extra:
        raise ArtifactError(
            f"artifact node has unexpected field(s) {extra}; a bare node carries "
            f"exactly 'kind' and 'params' (§4.11.3) — leftover envelope fields "
            f"are an explicit failure, not something to pass through"
        )
    kind = obj.get("kind")
    if not isinstance(kind, str) or not kind:
        raise ArtifactError(
            f"artifact node has no usable 'kind' (got {kind!r}); the kind is the "
            f"node's identity and is mandatory"
        )
    # A registry refusal is a decode failure, restated in the decode layer's
    # own vocabulary: the registry is a lower layer and must not know what a
    # reader catches. One exception type reaches the caller however the kind
    # was rejected — unknown, or refused by this channel's allowlist.
    from .registry import RegistryError as _RegistryError

    try:
        cls = registry.resolve_node(kind)
    except _RegistryError as exc:
        raise ExpressionDeserializationError(str(exc)) from exc

    raw = obj.get("params", {})
    if not isinstance(raw, dict):
        raise ArtifactError(
            f"kind '{kind}' has non-object 'params' ({type(raw).__name__})"
        )
    params = _decode_value(raw, _depth + 1, registry, _max_depth)

    sig = inspect.signature(cls.__init__)
    accepted, var_positional, var_keyword = {}, None, None
    for pname, param in sig.parameters.items():
        if pname in ("self", "dialect"):
            continue
        if param.kind is inspect.Parameter.VAR_KEYWORD:
            var_keyword = pname
        elif param.kind is inspect.Parameter.VAR_POSITIONAL:
            var_positional = pname
        else:
            accepted[pname] = param
    if var_keyword is not None:
        raise ArtifactError(
            f"kind '{kind}' accepts **{var_keyword}, so its parameters cannot be "
            f"matched by name; per §4.11.4 a parameter whose identity depends on "
            f"how many extras arrived cannot be validated on read"
        )

    known = set(accepted) | ({var_positional} if var_positional else set())
    unknown = sorted(set(params) - known)
    if unknown:
        raise ArtifactError(
            f"kind '{kind}' does not accept parameter(s) {unknown}; it accepts "
            f"{sorted(known)}"
        )
    missing = sorted(n for n, p in accepted.items() if p.default is p.empty and n not in params)
    if missing:
        raise ArtifactError(f"kind '{kind}' is missing required parameter(s) {missing}")

    if var_positional:
        varargs = params.pop(var_positional, None)
        if varargs is not None and not isinstance(varargs, (list, tuple)):
            raise ArtifactError(
                f"kind '{kind}' takes '*{var_positional}' as a list, got "
                f"{type(varargs).__name__}"
            )
        lead = []
        for pname in sig.parameters:
            if pname == var_positional:
                break
            if pname in ("self", "dialect") or pname not in params:
                continue
            lead.append(pname)
        kwargs = {n: params[n] for n in accepted if n in params and n not in lead}
        args = [params[n] for n in lead] + list(varargs or [])
    else:
        kwargs, args = params, []

    # Keep the constructor contract: a class whose signature declares
    # ``dialect`` still receives the parameter, but never a real dialect.
    # Binding happens at render (``to_sql(dialect)``), not on read.
    if "dialect" in sig.parameters:
        first = next((n for n in sig.parameters if n != "self"), None)
        return cls(None, *args, **kwargs) if first == "dialect" else cls(*args, **kwargs, dialect=None)
    return cls(*args, **kwargs)


def serialize(expr: BaseExpression) -> Dict[str, Any]:
    """Serialize an expression into a bare `{kind, params}` artifact (§4.11.3).

    No registry: the node reports its own kind, derived from its class name.
    The dialect is deliberately absent so the same artifact can be re-rendered
    by a different dialect later.

    Args:
        expr: The expression instance to serialize.

    Returns:
        A dict with exactly two keys, in this order: `kind` and `params`.
    """
    return encode_artifact(expr)


def deserialize(
    spec: Dict[str, Any],
    *,
    registry: Any = None,
) -> BaseExpression:
    """Rebuild an expression from a bare `{kind, params}` artifact.

    The artifact is untrusted input (§4.11.4): an unknown kind, a leftover
    envelope field, or an unknown or missing parameter each fail explicitly and
    name the kind. This is the only place a registry is needed — it is what
    turns a `kind` back into a class.

    The artifact carries **no dialect**, and construction does not need one.
    ``deserialize(spec)`` resolves core's kinds and returns an unbound tree that
    renders through ``to_sql(dialect)``. To read a backend's own kinds, pass
    that backend's published table (``registry=SQLITE_EXPRESSION_REGISTRY``,
    for example): the read admits exactly the kinds the table holds. There is
    no implicit selection through a dialect.

    Args:
        spec: The artifact produced by :func:serialize.
        registry: Registry used to resolve kinds. Defaults to
            :data:`CORE_EXPRESSION_REGISTRY`. Pass a backend's table to admit that backend's
            kinds; pass a narrowed table to build a read-only channel.
    """
    return decode_artifact(spec, registry=registry)


def serialize_json(
    expr: BaseExpression,
    *,
    default: Optional[Callable[[Any], Any]] = None,
) -> str:
    """Serialize an expression into JSON, forwarding ``default`` to json.dumps.

    Convenience wrapper around ``_default_serializer.serialize_json()``.
    """
    return _default_serializer.serialize_json(expr, default=default)


def deserialize_json(
    spec_str: str,
    *,
    registry: Any = None,
    object_hook: Optional[Callable[[Dict[str, Any]], Any]] = None,
) -> BaseExpression:
    """Reconstruct an expression from JSON, forwarding ``object_hook`` to loads.

    Convenience wrapper around ``_default_serializer.deserialize_json()``.
    """
    return _default_serializer.deserialize_json(
        spec_str, registry=registry, object_hook=object_hook
    )


def serialize_xml(expr: BaseExpression) -> bytes:
    """Serialize an expression instance into an XML document (bytes).

    Convenience wrapper around ``_default_serializer.serialize_xml()``.
    """
    return _default_serializer.serialize_xml(expr)


def deserialize_xml(
    payload: bytes,
    *,
    registry: Any = None,
) -> BaseExpression:
    """Reconstruct an expression from an XML document (bytes).

    Convenience wrapper around ``_default_serializer.deserialize_xml()``.
    """
    return _default_serializer.deserialize_xml(payload, registry=registry)
