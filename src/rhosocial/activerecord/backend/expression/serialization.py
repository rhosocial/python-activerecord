# src/rhosocial/activerecord/backend/expression/serialization.py
"""
Expression serialization and deserialization utilities.

The class index below is a **deserialization support table**, not the
expression registry: the serializer never consults it (a node carries its own
identity), and the registry (:mod:`.registry`) does registration, checking
and dispatch of *rendering*, not of classes. Deserializing a spec resolves
the class through this table — temporarily still keyed by fully-qualified
class name; the kind whitelist arrives with the bare-node rewrite.

Reserved special keys in serialized param dicts:
    "__tuple__"  →  Python tuple value (since tuple is not JSON native)
    "__expr__"   →  Nested BaseExpression instance
    "__vdc__"    →  Dataclass value (FQN + field values), structurally encoded
                    so BaseExpression / Enum / nested-dataclass fields round-trip.
    "__b64__"    →  bytes, base64 (wire §5)
    "__dur__"    →  timedelta, ISO 8601 duration (wire §5)

IMPORTANT: User-defined expression params MUST NOT use these reserved keys
in their get_params() return values. Using these keys will cause data
corruption or deserialization errors.
"""

import inspect
import base64
import datetime
import decimal
import json
import uuid
from dataclasses import is_dataclass
from typing import Any, Dict, Optional, Sequence, TYPE_CHECKING

from .bases import BaseExpression
from .values import B64_KEY, DUR_KEY

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase


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
        max_depth: Maximum nesting depth for deserialization (default: 64).
                   If exceeded, ExpressionDeserializationError is raised.
        warn_threshold: Depth threshold for serialization warnings (default: 0.8).
                        When serialized depth exceeds max_depth * warn_threshold,
                        a warning is issued to alert potential deserialization issues.
        allowed_types: Optional allowlist of expression class FQNs applied during
                       deserialization. Entries may be exact FQNs or module
                       prefixes ending with ".*" (e.g. "rhosocial…expression.core.*").
                       ``None`` (default) allows any registered expression class.

    Example:
        # Default configuration
        serializer = ExpressionSerializer()
        spec = serializer.serialize(expr)
        restored = serializer.deserialize(spec, dialect)

        # Custom configuration
        deep_serializer = ExpressionSerializer(max_depth=128, warn_threshold=0.9)
        deep_serializer.serialize(deep_expr)  # May issue warning

        # Read-only tool channel: only value/predicate/SELECT expressions
        readonly = ExpressionSerializer(allowed_types=[
            "rhosocial.activerecord.backend.expression.core.*",
            "rhosocial.activerecord.backend.expression.predicates.*",
            "rhosocial.activerecord.backend.expression.statements.dql.QueryStatement",
        ])
    """

    def __init__(
        self,
        max_depth: int = _DEFAULT_MAX_DEPTH,
        warn_threshold: float = _DEFAULT_WARN_THRESHOLD,
        allowed_types: Optional[Sequence[str]] = None,
    ):
        if max_depth <= 0:
            raise ValueError("max_depth must be a positive integer")
        if not 0 < warn_threshold <= 1:
            raise ValueError("warn_threshold must be between 0 and 1")
        self.max_depth = max_depth
        self.warn_threshold = warn_threshold
        self.allowed_types: Optional[tuple] = tuple(allowed_types) if allowed_types else None
        self._warn_issued: bool = False

    def _type_allowed(self, fqn: str) -> bool:
        """Check whether an expression class FQN passes the allowlist.

        Entries ending with ".*" act as module-prefix wildcards; others
        must match the FQN exactly. ``None`` allowlist means unrestricted.
        """
        if self.allowed_types is None:
            return True
        for entry in self.allowed_types:
            if entry.endswith(".*"):
                prefix = entry[:-2]
                if fqn == prefix or fqn.startswith(prefix + "."):
                    return True
            elif fqn == entry:
                return True
        return False

    def serialize(self, expr: BaseExpression, _depth: int = 0) -> Dict[str, Any]:
        """Serialize to a bare `{kind, params}` artifact (§4.11.3).

        The same codec the module-level :func:serialize uses: an artifact is
        an artifact regardless of who asked for it, so this class configures
        rather than reimplements. Key order is fixed, and the dialect is absent
        so the artifact can be re-rendered elsewhere.
        """
        return encode_artifact(expr, _depth)

    def _serialize_value(self, value: Any, depth: int) -> Any:
        """Recursively serialize a value, handling BaseExpression instances and containers."""
        if isinstance(value, BaseExpression):
            return self.serialize(value, _depth=depth)
        if is_dataclass(value) and not isinstance(value, type):
            # Structurally encode a dataclass so its BaseExpression / Enum /
            # nested-dataclass fields also round-trip.
            import dataclasses

            return {
                "__vdc__": [
                    f"{type(value).__module__}.{type(value).__qualname__}",
                    {
                        f.name: self._serialize_value(getattr(value, f.name), depth + 1)
                        for f in dataclasses.fields(value)
                    },
                ]
            }
        if isinstance(value, tuple):
            return {"__tuple__": [self._serialize_value(item, depth + 1) for item in value]}
        if isinstance(value, list):
            return [self._serialize_value(item, depth + 1) for item in value]
        if isinstance(value, dict):
            return {key: self._serialize_value(val, depth + 1) for key, val in value.items()}
        return _encode_scalar(value)

    def deserialize(
        self,
        spec: Dict[str, Any],
        dialect: "SQLDialectBase",
        registry: Any = None,
    ) -> BaseExpression:
        """Rebuild from a bare `{kind, params}` artifact.

        The artifact is untrusted input (§4.11.4): unknown kinds, leftover
        envelope fields and unrecognised parameters all fail explicitly and
        name the kind. `allowed_types`, when set, restricts which kinds this
        reader may produce — a read-only channel can name only the kinds it
        means to accept.
        """
        if self.allowed_types is not None:
            registry = self._restrict(registry)
        return decode_artifact(spec, dialect, registry=registry)

    def _restrict(self, registry: Any):
        """A registry view admitting only `allowed_types` kinds.

        Entries are kind names, optionally with shell-style globs (``"col*"``),
        because a kind is the only identity that crosses the wire (§7.2) —
        there is no import path left to prefix-match on.

        Built by copying, so restricting a read never narrows the registry the
        rest of the process uses.
        """
        from fnmatch import fnmatchcase

        from .registry import ExpressionRegistry

        source = registry if registry is not None else default_registry()
        patterns = tuple(self.allowed_types)
        view = ExpressionRegistry()
        for kind in source.node_kinds():
            if kind in patterns or any(fnmatchcase(kind, p) for p in patterns):
                view.register_node(source.resolve_node(kind))
        for name in list(getattr(source, "_enums", {})):
            view.register_enum(source.resolve_enum(name))
        for name in list(getattr(source, "_dataclasses", {})):
            view.register_dataclass(source.resolve_dataclass(name))
        return view

    def serialize_json(self, expr: BaseExpression) -> str:
        """Serialize an expression instance into a JSON string.

        By the time the artifact exists every value is already a JSON scalar or
        one of the two reserved wrappers (§``codec``), so ``json.dumps`` needs no
        hook: there is nothing left that it would not know how to write.
        """
        return json.dumps(self.serialize(expr))

    def deserialize_json(self, spec_str: str, dialect: "SQLDialectBase") -> BaseExpression:
        """Reconstruct an expression from a JSON string produced by
        :meth:`serialize_json`.

        No ``object_hook`` here either. A bare scalar's type is declared by the
        kind that holds it, so converting it is the node's business, not the
        parser's -- see :func:`decode_artifact`.
        """
        return self.deserialize(json.loads(spec_str), dialect)

    def serialize_xml(self, expr: BaseExpression) -> bytes:
        """Serialize an expression instance into an XML document (bytes).

        The spec (with the two reserved value wrappers) is rendered into
        an XML document by :mod:`xml_serialization`, which uses the standard
        library ``xml.etree.ElementTree``.
        """
        from . import xml_serialization

        return xml_serialization.serialize_xml(self.serialize(expr))

    def deserialize_xml(self, payload: bytes, dialect: "SQLDialectBase") -> BaseExpression:
        """Reconstruct an expression from an XML document produced by
        :meth:`serialize_xml`.
        """
        from . import xml_serialization

        spec = xml_serialization.deserialize_xml(payload)
        return self.deserialize(spec, dialect)


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
#
# The registry itself is an independent module that starts empty and knows
# nothing about which expressions exist; building the instance the framework
# hands out is the framework's business, below.
# ---------------------------------------------------------------------------

#: The framework's default registry instance. Created empty, like any other; it
#: is filled by :func:_populate_default_registry, and only when someone
#: actually deserializes. A caller who only serializes never pays for it.
_default_registry = None

#: Packages the framework registers into its default instance: the core
#: expressions plus the backends built into this distribution.
#:
#: ``backend.transaction`` is here because expressions carry its vocabulary.
#: ``IsolationLevel`` and ``TransactionMode`` are parameters of the transaction
#: statements, so a reader that cannot resolve them fails on an artifact the
#: library itself produced. A package list is a statement about which types the
#: artifact format admits, and it has to be as wide as the vocabulary -- which
#: is why it is checked against real instances rather than assumed complete.
_FRAMEWORK_PACKAGES = (
    "rhosocial.activerecord.backend.expression",
    "rhosocial.activerecord.backend.transaction",
    "rhosocial.activerecord.backend.impl.sqlite.expression",
    "rhosocial.activerecord.backend.impl.dummy.expression",
)

#: Reserved keys. A user-defined parameter must never collide with these; a
#: collision is reported at encode time rather than corrupting the artifact.
_RESERVED = ("__expr__", "__tuple__", "__enum__", "__dataclass__", "__b64__", "__dur__")


class ArtifactError(ExpressionDeserializationError):
    """Raised when an artifact cannot be read. Always names the kind."""


def _populate_default_registry(registry):
    """Register the framework's expressions into a registry instance.

    This is the assembly point, and it deliberately lives here rather than in
    the registry module: *which* expressions the framework ships is a decision
    of the framework. The registry itself neither discovers nor knows.

    Kind collisions are collected across the whole walk before reporting, so
    one run names every ambiguous kind. A collision is a real defect — the kind
    comes from the class name (§4.11.1), so two same-named classes produce one
    ambiguous kind and no artifact could say which it meant.
    """
    import importlib
    import pkgutil

    from .registry import RegistryError, RegistryReason

    by_kind = {}
    ordered = []
    for pkgname in _FRAMEWORK_PACKAGES:
        try:
            pkg = importlib.import_module(pkgname)
        except Exception:
            continue  # a backend that is not installed is not an error
        # A backend may expose its expressions from a single module rather
        # than a package (the dummy backend does), and `walk_packages` needs
        # `__path__`. Walk a package; treat anything without one as the leaf
        # it already is.
        if hasattr(pkg, "__path__"):
            modnames = [
                m for _, m, _ in pkgutil.walk_packages(
                    path=pkg.__path__, prefix=pkgname + ".", onerror=lambda x: None
                )
            ]
        else:
            modnames = [pkgname]
        for modname in modnames:
            try:
                mod = importlib.import_module(modname)
            except Exception:
                continue
            for name in dir(mod):
                obj = getattr(mod, name, None)
                if not isinstance(obj, type) or obj.__module__ != modname:
                    continue
                if issubclass(obj, BaseExpression):
                    if obj is BaseExpression or getattr(obj, "__abstractmethods__", None):
                        continue
                    ordered.append(obj)
                elif issubclass(obj, __import__("enum").Enum):
                    try:
                        registry.register_enum(obj)
                    except RegistryError:
                        pass
                elif __import__("dataclasses").is_dataclass(obj):
                    try:
                        registry.register_dataclass(obj)
                    except RegistryError:
                        pass

    # Identity dedup: importing a package can leave more than one live class
    # object for one source definition (a reload during the walk). Same class,
    # so not a collision.
    seen, collisions = set(), []
    for obj in ordered:
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        kind = obj.kind()
        previous = by_kind.get(kind)
        if previous is None:
            by_kind[kind] = obj
            registry.register_node(obj)
        elif previous is not obj:
            collisions.append((kind, previous, obj))
    if collisions:
        detail = "; ".join(
            f"kind '{k}' is claimed by both {a.__module__}.{a.__name__} and "
            f"{b.__module__}.{b.__name__}" for k, a, b in collisions
        )
        raise RegistryError(RegistryReason.SPEC_INVALID, detail)
    return len(by_kind)


def default_registry():
    """The framework's default registry, built on first use.

    Returns:
        A registry holding this framework's core and built-in backend
        expressions. Empty until something deserializes, because serializing
        never needs it.
    """
    global _default_registry
    if _default_registry is None:
        from .registry import ExpressionRegistry

        # Build into a local and publish only on success: a half-populated
        # instance cached under the module global would make every later call
        # fail with a confusing "no such kind" instead of the real cause.
        built = ExpressionRegistry()
        _populate_default_registry(built)
        _default_registry = built
    return _default_registry


def _kind_of(expr):
    """The node's kind, from its class — the only place a kind is defined."""
    return type(expr).kind()


def _check_reserved(params, kind):
    clash = [k for k in params if k in _RESERVED]
    if clash:
        raise ArtifactError(
            f"kind '{kind}' has parameter(s) {clash} colliding with reserved "
            f"artifact keys {list(_RESERVED)}; rename them so the artifact can "
            f"carry this expression"
        )


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


def _encode_scalar(value):
    """A host value as JSON carries it.

    Four things cannot be written as they stand, and only these: bytes and
    timedelta get the two reserved wrappers (wire §5); date/time/datetime and
    Decimal get their canonical text, because JSON has no date and no exact
    decimal. Everything else -- int, float, bool, str, None -- *is* a JSON
    scalar and is returned untouched.

    Reading does not consult this function. The class that holds the value
    converts its serialized form back (``TypedValue.normalise``), because it is
    the only thing that knows what the value is.
    """
    if isinstance(value, (bytes, bytearray)):
        return {B64_KEY: base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, datetime.timedelta):
        return {DUR_KEY: _format_duration(value)}
    if isinstance(value, (datetime.date, datetime.time, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _format_duration(value):
    """A duration as ISO 8601: ``P1DT2H3M4.5S``, empty parts omitted."""
    total = value.total_seconds()
    sign = "-" if total < 0 else ""
    days, rest = divmod(abs(total), 86400)
    hours, rest = divmod(rest, 3600)
    minutes, seconds = divmod(rest, 60)
    out = [sign, "P"]
    if days:
        out.append(f"{int(days)}D")
    if hours or minutes or seconds:
        out.append("T")
        if hours:
            out.append(f"{int(hours)}H")
        if minutes:
            out.append(f"{int(minutes)}M")
        if seconds:
            out.append(f"{seconds:.6f}".rstrip("0").rstrip(".") + "S")
    if len(out) == 2:
        out.append("T0S")
    return "".join(out)


def _encode_enum_member(value):
    """Enum as `[short class name, member]` — resolved by whitelist on read."""
    return {"__enum__": [type(value).__name__, value.name]}


def _resolve_or_fail(resolve, name):
    """Ask the registry for `name`, restating a refusal in decode vocabulary.

    See :func:`decode_artifact` — the reader sees one exception type whether
    the name was unknown or withheld by this channel's allowlist.
    """
    from .registry import RegistryError as _RegistryError

    try:
        return resolve(name)
    except _RegistryError as exc:
        raise ExpressionDeserializationError(str(exc)) from exc


def _decode_enum_member(obj, registry):
    name, member = obj["__enum__"]
    enum_cls = _resolve_or_fail(registry.resolve_enum, name)
    try:
        return enum_cls[member]
    except KeyError:
        raise ArtifactError(
            f"enum '{name}' has no member '{member}'; valid members are "
            f"{[m.name for m in enum_cls]}"
        ) from None


def _decode_dataclass(payload, dialect, depth, registry):
    """Rebuild a dataclass by short name through the registry whitelist.

    Never `importlib`: the payload is external input, so importing whatever
    module a name points at is a code-execution path, not a type lookup (§4.11.4).
    """
    import dataclasses

    name, fields = payload
    cls = _resolve_or_fail(registry.resolve_dataclass, name)
    known = {f.name for f in dataclasses.fields(cls)}
    unknown = sorted(set(fields) - known)
    if unknown:
        raise ArtifactError(
            f"dataclass '{name}' has no field(s) {unknown}; its fields are "
            f"{sorted(known)}"
        )
    return cls(**{k: _decode_value(v, dialect, depth + 1, registry) for k, v in fields.items()})


def encode_artifact(expr, _depth=0):
    """Encode one node as a bare `{kind, params}` artifact. No registry.

    Key order is fixed (`kind` then `params`, params in constructor order),
    so two encodings of the same tree are byte-identical and can be compared.
    """
    if _depth > _DEFAULT_MAX_DEPTH:
        raise ArtifactError(f"expression nesting depth exceeds {_DEFAULT_MAX_DEPTH}")
    kind = _kind_of(expr)
    params = expr.get_params()
    if not isinstance(params, dict):
        raise ArtifactError(
            f"kind '{kind}'.get_params() returned {type(params).__name__}, "
            f"expected a dict of constructor parameters"
        )
    _check_reserved(params, kind)
    return {"kind": kind, "params": _encode_value(params, _depth + 1)}


def _encode_value(value, depth):
    import enum as _enum_mod
    from .values import TypedValue

    if isinstance(value, BaseExpression):
        # A nested node is its own artifact -- the same {kind, params} a
        # top-level node is. No marker: the shape says what it is, and a marker
        # would be a second, weaker spelling of the same fact.
        return encode_artifact(value, depth)
    if isinstance(value, TypedValue):
        # The host value, written in its natural JSON form. Only the two types
        # JSON cannot express at all are wrapped (wire §5); everything else --
        # a date's ISO text, a Decimal's exact text, a UUID's canonical form --
        # is already a scalar and needs no marker, because the kind that holds
        # it declares what it is.
        return _encode_scalar(value.value)
    if isinstance(value, _enum_mod.Enum):
        return _encode_enum_member(value)
    if is_dataclass(value) and not isinstance(value, type):
        import dataclasses

        fields = {
            f.name: _encode_value(getattr(value, f.name), depth + 1)
            for f in dataclasses.fields(value)
        }
        return {"__dataclass__": [type(value).__name__, fields]}
    if isinstance(value, tuple):
        return {"__tuple__": [_encode_value(i, depth + 1) for i in value]}
    if isinstance(value, list):
        return [_encode_value(i, depth + 1) for i in value]
    if isinstance(value, dict):
        return {k: _encode_value(v, depth + 1) for k, v in value.items()}
    return _encode_scalar(value)


def _decode_value(value, dialect, depth, registry):
    if depth > _DEFAULT_MAX_DEPTH:
        raise ArtifactError(f"artifact nesting depth exceeds {_DEFAULT_MAX_DEPTH}")
    if isinstance(value, dict):
        if _is_node(value):
            return decode_artifact(value, dialect, depth + 1, registry)
        if "__enum__" in value:
            return _decode_enum_member(value, registry)
        if "__dataclass__" in value:
            return _decode_dataclass(value["__dataclass__"], dialect, depth, registry)
        if "__tuple__" in value:
            return tuple(_decode_value(i, dialect, depth + 1, registry) for i in value["__tuple__"])
        if "__b64__" in value or "__dur__" in value:
            # The wrapper *is* the serialized form; the class that holds the
            # value converts it (``TypedValue.normalise``).
            return value
        # Any other dict is a plain mapping parameter, handed through untouched.
        return {k: _decode_value(v, dialect, depth + 1, registry) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode_value(i, dialect, depth + 1, registry) for i in value]
    if isinstance(value, tuple):
        # XML and dataclass paths hand back real tuples rather than the
        # ``__tuple__`` marker, and their items need decoding just as much.
        return tuple(_decode_value(i, dialect, depth + 1, registry) for i in value)
    return value


def decode_artifact(obj, dialect, _depth=0, registry=None):
    """Rebuild one node from a bare `{kind, params}` artifact.

    Args:
        obj: The artifact node — external, untrusted input.
        dialect: The dialect to bind to the rebuilt tree.
        registry: The registry to resolve kinds and enum / dataclass names
            through. Defaults to the framework's own instance; pass your own to
            control exactly which kinds this read may produce.
    """

    if _depth > _DEFAULT_MAX_DEPTH:
        raise ArtifactError(f"artifact nesting depth exceeds {_DEFAULT_MAX_DEPTH}")
    if registry is None:
        registry = default_registry()
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
    params = _decode_value(raw, dialect, _depth + 1, registry)

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

    if "dialect" in sig.parameters:
        first = next((n for n in sig.parameters if n != "self"), None)
        return cls(dialect, *args, **kwargs) if first == "dialect" else cls(*args, **kwargs, dialect=dialect)
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
    dialect: "SQLDialectBase",
    registry: Any = None,
) -> BaseExpression:
    """Rebuild an expression from a bare `{kind, params}` artifact.

    The artifact is untrusted input (§4.11.4): an unknown kind, a leftover
    envelope field, or an unknown or missing parameter each fail explicitly and
    name the kind. This is the only place a registry is needed — it is what
    turns a `kind` back into a class.

    Args:
        spec: The artifact produced by :func:serialize.
        dialect: The dialect to bind to the rebuilt tree. If a node is
            incompatible with it, that surfaces at `to_sql()` time.
        registry: Registry used to resolve kinds and enum / dataclass names.
            Defaults to the framework's own instance; pass your own to control
            exactly which kinds this read may produce.
    """
    return decode_artifact(spec, dialect, registry=registry)


def serialize_json(expr: BaseExpression) -> str:
    """Serialize an expression instance into a JSON string.

    Convenience wrapper around ``_default_serializer.serialize_json()``.
    """
    return _default_serializer.serialize_json(expr)


def deserialize_json(
    spec_str: str,
    dialect: "SQLDialectBase",
) -> BaseExpression:
    """Reconstruct an expression from a JSON string.

    Convenience wrapper around ``_default_serializer.deserialize_json()``.
    """
    return _default_serializer.deserialize_json(spec_str, dialect)


def serialize_xml(expr: BaseExpression) -> bytes:
    """Serialize an expression instance into an XML document (bytes).

    Convenience wrapper around ``_default_serializer.serialize_xml()``.
    """
    return _default_serializer.serialize_xml(expr)


def deserialize_xml(
    payload: bytes,
    dialect: "SQLDialectBase",
) -> BaseExpression:
    """Reconstruct an expression from an XML document (bytes).

    Convenience wrapper around ``_default_serializer.deserialize_xml()``.
    """
    return _default_serializer.deserialize_xml(payload, dialect)
