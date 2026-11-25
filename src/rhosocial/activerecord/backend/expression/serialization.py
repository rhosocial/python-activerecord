# src/rhosocial/activerecord/backend/expression/serialization.py
"""
Expression serialization and deserialization utilities.

An artifact is a **bare node**: ``{"kind": ..., "params": {...}}`` and nothing
else (§4.11.3). There is no envelope around it, and no marker vocabulary
inside it.

* A node's **kind** is its identity -- derived from the class name (§4.11.1),
  computed and never stored, so the two cannot drift. A literal is the one
  node whose kind is not its class name: one class carries every value, and
  the wire still names them apart, because a date's spelling and a string's
  are the same bytes and the kind is what tells them apart.
* A nested node is a nested ``{"kind", "params"}``, recognised by its shape
  alone. No key says "this is a node": a marker is a dispatch, and a dispatch
  has to be agreed by every reader -- which is exactly what an artifact cannot
  assume, when the same bytes must be read by four languages.
* Every value is a JSON scalar. A host type JSON cannot spell -- bytes, a
  timedelta, a Decimal, a date -- travels as the text its kind names, and the
  kind is what says how to read it back. A tuple travels as an array.

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
from typing import Any, Dict, Optional, Sequence, TYPE_CHECKING

from .bases import BaseExpression
from .core import Literal
from .values import LiteralKind

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
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

    def deserialize(
        self,
        spec: Dict[str, Any],
        dialect: Optional["SQLDialectBase"] = None,
        *,
        registry: Any = None,
    ) -> BaseExpression:
        """Rebuild from a bare `{kind, params}` artifact.

        The artifact is untrusted input (§4.11.4): unknown kinds, leftover
        envelope fields and unrecognised parameters all fail explicitly and
        name the kind. `allowed_types`, when set, restricts which kinds this
        reader may produce — a read-only channel can name only the kinds it
        means to accept.

        The dialect is optional because it is only needed to *render*: the
        artifact carries no dialect, and a tree rebuilt without one renders
        through ``to_sql(dialect)``. Which kinds are admitted is decided by,
        in order, an explicit ``registry``, the dialect's
        ``artifact_registry()`` when a dialect was supplied, or core's
        registry. When a dialect is supplied it is also bound onto the rebuilt
        tree, so the existing ``restored.to_sql()`` call sites keep working.
        """
        if registry is None:
            registry = _registry_for(dialect)
        if self.allowed_types is not None:
            registry = self._restrict(registry)
        return decode_artifact(spec, dialect, registry=registry)

    def _restrict(self, registry: "ExpressionRegistry"):
        """A registry view admitting only `allowed_types` kinds.

        Entries are kind names, optionally with shell-style globs (``"col*"``),
        because a kind is the only identity that crosses the wire (§7.2) —
        there is no import path left to prefix-match on.

        Built by copying, so restricting a read never narrows the registry the
        rest of the process uses. ``registry`` is already selected (explicit,
        dialect, or core) by the caller.
        """
        from fnmatch import fnmatchcase

        source = registry
        patterns = tuple(self.allowed_types)
        # Copy, then subtract, rather than rebuild from what matches. Rebuilding
        # re-derives each key from the class behind it, which files all fourteen
        # value kinds under ``literal`` -- and an artifact carrying a value would
        # then be refused by a table that looks perfectly populated.
        view = source.twin()
        for kind in view.node_kinds():
            if kind in patterns or any(fnmatchcase(kind, p) for p in patterns):
                continue
            view.unregister_node(kind)
        return view

    def serialize_json(self, expr: BaseExpression) -> str:
        """Serialize an expression instance into a JSON string.

        By the time the artifact exists every value is already a JSON scalar or
        one of the two reserved wrappers (§``codec``), so ``json.dumps`` needs no
        hook: there is nothing left that it would not know how to write.
        """
        return json.dumps(self.serialize(expr))

    def deserialize_json(
        self,
        spec_str: str,
        dialect: Optional["SQLDialectBase"] = None,
        *,
        registry: Any = None,
    ) -> BaseExpression:
        """Reconstruct an expression from a JSON string produced by
        :meth:`serialize_json`.

        No ``object_hook`` here either. A bare scalar's type is declared by the
        kind that holds it, so converting it is the node's business, not the
        parser's -- see :func:`decode_artifact`.
        """
        return self.deserialize(json.loads(spec_str), dialect, registry=registry)

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
        dialect: Optional["SQLDialectBase"] = None,
        *,
        registry: Any = None,
    ) -> BaseExpression:
        """Reconstruct an expression from an XML document produced by
        :meth:`serialize_xml`.
        """
        from . import xml_serialization

        spec = xml_serialization.deserialize_xml(payload)
        return self.deserialize(spec, dialect, registry=registry)


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
#               The dialect is optional: it decides *which* registry answers
#               (the backend's own table) and is bound for rendering, but the
#               artifact is data and carries no dialect.
#
# The registry itself is an independent module that starts empty and knows
# nothing about which expressions exist; assembling the instances the owners
# publish is each owner's business, below.
# ---------------------------------------------------------------------------

#: The framework's core registry. Created empty, like any other; it is filled
#: by :func:`core_registry`, and only when someone actually needs it. A caller
#: who only serializes never pays for it.
_core_registry = None

#: The packages core owns. ``backend.transaction`` is here because expressions
#: carry its vocabulary -- ``IsolationLevel`` and ``TransactionMode`` are
#: parameters of the transaction statements, so a reader that cannot resolve
#: them fails on an artifact the library itself produced. A package list is a
#: statement about which types the artifact format admits, and it has to be as
#: wide as the vocabulary -- which is why it is checked against real instances
#: rather than assumed complete.
#:
#: No backend package belongs here. A backend's own kinds are the backend's to
#: assemble (:func:`registry_for_packages` with that backend's package, based on
#: :func:`core_registry`), so core never names a backend and a backend never
#: leaks into core's table.
_CORE_EXPRESSION_PACKAGES = (
    "rhosocial.activerecord.backend.expression",
    "rhosocial.activerecord.backend.transaction",
)


class ArtifactError(ExpressionDeserializationError):
    """Raised when an artifact cannot be read. Always names the kind."""


def _declares_a_formatter(cls):
    """Whether *cls* resolves to a concrete ``format_method``.

    Asked by definition site, not by presence on ``vars(cls)``: a base such as
    ``DeclaredValueType`` supplies one for its subclasses, and that is a real
    declaration. Only the sentinel on :class:`BaseExpression` means "none".
    """
    for klass in cls.__mro__:
        if "format_method" in vars(klass):
            return klass is not BaseExpression
    return False


def _register_expression_packages(registry, packages):
    """Register the expression classes found in *packages* into *registry*.

    This is the assembly walk, and it deliberately lives here rather than in
    the registry module: *which* expressions an owner ships is that owner's
    decision. The registry itself neither discovers nor knows.

    A package may expose its expressions from a single module rather than a
    package (the dummy backend does), and ``walk_packages`` needs ``__path__``;
    anything without one is treated as the leaf it already is. A package that
    cannot be imported is skipped: a backend that is not installed is not an
    error, and the caller's own package list is what made it optional.

    Kind collisions are collected across the whole walk before reporting, so
    one run names every ambiguous kind. A collision is a real defect — the kind
    comes from the class name (§4.11.1), so two same-named classes produce one
    ambiguous kind and no artifact could say which it meant.

    Args:
        registry: Mutable registry to fill. It may already hold kinds, and a
            package class claiming one of those with a different class is
            reported as a collision like any other.
        packages: Importable package or module names to walk, in order.

    Returns:
        The number of classes this walk examined.
    """
    import importlib
    import pkgutil

    from .registry import RegistryError, RegistryReason

    ordered = []
    for pkgname in packages:
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
                    # A leading underscore is *not* a reason to skip: the
                    # dummy backend's own nodes are named that way and they
                    # round-trip like any other. Whatever is concrete and can
                    # render is a kind.
                    # A class that cannot name a formatter is not a node (§4.8),
                    # so it is not a kind. The test is the *resolved*
                    # ``format_method``: a base that supplies none inherits
                    # BaseExpression's sentinel, and registering it would put a
                    # name in the whitelist that no artifact could ever carry
                    # usefully -- it resolves, then raises on render.
                    if not _declares_a_formatter(obj):
                        continue
                    # The class says whether it belongs in the default table.
                    # A node whose rendered SQL is caller-vouched text opts out:
                    # the table is what a reader resolves an untrusted artifact
                    # against, so admitting such a kind would hand the artifact
                    # the choice of raw SQL. A caller that trusts its artifacts
                    # registers the class itself -- this is a default, not a ban,
                    # and the decision lives next to the class rather than in a
                    # list here that would have to be kept in step.
                    if not obj.REGISTER_BY_DEFAULT:
                        continue
                    ordered.append(obj)

    # Identity dedup: importing a package can leave more than one live class
    # object for one source definition (a reload during the walk). Same class,
    # so not a collision.
    seen, collisions = set(), []
    for obj in ordered:
        if id(obj) in seen:
            continue
        seen.add(id(obj))
        try:
            registry.register_node(obj)
        except RegistryError as exc:
            # Collected rather than propagated: one run names every collision.
            collisions.append(exc)
    if collisions:
        detail = "; ".join(str(exc) for exc in collisions)
        raise RegistryError(RegistryReason.SPEC_INVALID, detail)
    return len(seen)


def registry_for_packages(*packages, base=None, register_values=True, freeze=True):
    """Assemble a registry from expression packages.

    This is the one assembly entry point. An owner — core, or a backend —
    passes the packages it owns, and gets a registry holding exactly those
    kinds. Overlap with another owner is expressed by ``base``: a backend passes
    ``base=core_registry()`` to say "core's kinds, plus mine", which is the
    only way the composition is written down. There is no list of backends
    anywhere in core.

    Args:
        *packages: Importable package or module names to walk, in order. A
            package that cannot be imported is skipped, so listing a backend
            that is not installed is not an error.
        base: Optional registry to start from. It is copied, never mutated:
            the returned registry is independent even when *base* is frozen.
        register_values: Whether to admit every value kind
            (:meth:`ExpressionRegistry.register_value_kinds`). True by
            default because an artifact that carries any value names a value
            kind, and a table without them refuses every such artifact.
        freeze: Whether to :meth:`ExpressionRegistry.freeze` the result. True
            by default: an assembled registry is a published value.

    Returns:
        A new registry holding ``base``'s kinds plus the classes the packages
        declare, frozen unless ``freeze=False``.
    """
    from .registry import ExpressionRegistry

    built = base.twin() if base is not None else ExpressionRegistry()
    if register_values:
        built.register_value_kinds()
    if packages:
        _register_expression_packages(built, packages)
    if freeze:
        built.freeze()
    return built


def core_registry():
    """Core's own registry: the kinds core owns, and nothing else.

    Cached and frozen. A backend's kinds are deliberately absent: a backend
    composes ``core_registry()`` with its own packages, so core never has to
    know which backends exist.

    Returns:
        The frozen registry assembled from
        :data:`_CORE_EXPRESSION_PACKAGES`.
    """
    global _core_registry
    if _core_registry is None:
        # Build into a local and publish only on success: a half-populated
        # instance cached under the module global would make every later call
        # fail with a confusing "no such kind" instead of the real cause.
        _core_registry = registry_for_packages(*_CORE_EXPRESSION_PACKAGES)
    return _core_registry


def default_registry():
    """**Deprecated** alias of :func:`core_registry`.

    This name used to mean "core plus the backends bundled in this distribution"
    (SQLite and dummy). Those are backends, and each maintains its own registry
    now; reading a backend kind through this name required whoever registered
    it to mutate a process-global table, which made the outcome depend on test
    order. Use :func:`core_registry` for core kinds, or
    ``dialect.artifact_registry()`` for the kinds a backend's dialect can read.

    Returns:
        The same frozen registry :func:`core_registry` returns.
    """
    return core_registry()


def _registry_for(dialect=None, registry=None):
    """The registry a read resolves kinds through, in documented order.

    Selection order:

    1. an explicit ``registry`` the caller supplied;
    2. ``dialect.artifact_registry()`` when a dialect was supplied — that is
       the backend's own composed table, the kinds its dialect can read;
    3. :func:`core_registry`.

    The dialect is only ever consulted for *names*; the artifact itself carries
    no dialect, and a tree rebuilt without one renders through
    ``to_sql(dialect)``.
    """
    if registry is not None:
        return registry
    if dialect is not None:
        getter = getattr(dialect, "artifact_registry", None)
        if callable(getter):
            selected = getter()
            if selected is not None:
                return selected
    return core_registry()


def _kind_of(expr):
    """The node's kind — the only place a kind is defined.

    Usually that is the class name (§4.11.1). A literal is the one node whose
    kind depends on what it holds: one class carries all twelve value kinds, and
    the wire still names them separately, because a date's spelling and a
    string's are the same bytes and the kind is what tells them apart.
    """
    if isinstance(expr, Literal):
        if expr.value_kind is None:
            raise ArtifactError(
                f"a literal carrying {type(expr.value).__name__} has no value "
                f"kind, so no artifact can name it; the kind is what tells a "
                f"date's spelling apart from a string's"
            )
        return expr.value_kind.wire
    return type(expr).kind()


def _unpack_value(kind, params):
    """Restore a value parameter from the spelling its kind declares.

    Only the value kinds have a payload to restore, and only the one parameter
    a literal carries. The kind is what says a date arrived as its ISO text, so
    the conversion happens here rather than in the constructor: a caller who
    writes ``Literal(d, "2020-01-02")`` meant a string, and the same constructor
    reading an artifact meant a date. Those two callers must not agree by
    accident, so the artifact path is explicit about which one it is.
    """
    try:
        value_kind = LiteralKind.by_wire(kind)
    except ValueError:
        return params
    if "value" not in params:
        return params
    unpacked = dict(params)
    unpacked["value"] = value_kind.unpack(params["value"])
    return unpacked


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
    """A host value as JSON carries it, given the kind it belongs to.

    The kind names the value, and the kind knows the spelling: bytes and
    timedelta take the two reserved wrappers (wire §5), date/time/datetime and
    Decimal take their canonical text because JSON has neither a date nor an
    exact decimal, and int/float/bool/str/None *are* JSON scalars. So this is
    :meth:`LiteralKind.pack` rather than a second, parallel table of the same
    rules -- the conversion lives with the declaration of the type.
    """
    return LiteralKind.of(value).pack(value)


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
    return {"kind": kind, "params": _encode_value(params, _depth + 1)}


def _encode_value(value, depth):
    if isinstance(value, BaseExpression):
        # A nested node is its own artifact -- the same {kind, params} a
        # top-level node is. No marker: the shape says what it is, and a marker
        # would be a second, weaker spelling of the same fact.
        return encode_artifact(value, depth)
    if isinstance(value, Literal):
        # The host value, written in the spelling its kind names -- and every one
        # of those spellings is a JSON scalar, because that is the only thing a
        # cross-language reader can be asked to parse. The kind declares what it
        # is; there is no wrapper left to unwrap.
        return _encode_scalar(value.value)
    # A tuple goes out as an array, like a list. JSON draws no distinction and
    # the artifact must not invent one: a parameter that needs to know it was a
    # tuple is a parameter that should have been a node or a value.
    if isinstance(value, (list, tuple)):
        return [_encode_value(i, depth + 1) for i in value]
    if isinstance(value, dict):
        return {k: _encode_value(v, depth + 1) for k, v in value.items()}
    # Anything left has to be a JSON scalar. A str enum is one (it is a str), and
    # the value vocabulary covers the rest; a type it does not name raises there
    # rather than being written out as something no reader can parse.
    return _encode_scalar(value)


def _decode_value(value, dialect, depth, registry):
    if depth > _DEFAULT_MAX_DEPTH:
        raise ArtifactError(f"artifact nesting depth exceeds {_DEFAULT_MAX_DEPTH}")
    if isinstance(value, dict):
        if _is_node(value):
            return decode_artifact(value, dialect, depth + 1, registry)
        # Any other object is a plain mapping parameter, handed through
        # untouched. There are no markers left to dispatch on: a value that was
        # not JSON-native travelled as a scalar its own kind names, so nothing
        # here has to recognise a spelling in order to undo it.
        return {k: _decode_value(v, dialect, depth + 1, registry) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode_value(i, dialect, depth + 1, registry) for i in value]
    if isinstance(value, tuple):
        # The XML and dataclass paths hand back real tuples rather than lists,
        # and their items need decoding just as much.
        return tuple(_decode_value(i, dialect, depth + 1, registry) for i in value)
    return value


def decode_artifact(obj, dialect=None, _depth=0, registry=None):
    """Rebuild one node from a bare `{kind, params}` artifact.

    Args:
        obj: The artifact node — external, untrusted input.
        dialect: The dialect to bind to the rebuilt tree, or ``None``. It is
            optional because it is only needed to *render*: the artifact
            carries no dialect, and a tree rebuilt without one renders through
            ``to_sql(dialect)``. When supplied it also selects the registry
            (see *registry*).
        registry: The registry to resolve kinds through. When omitted the
            selection order is ``dialect.artifact_registry()`` if a dialect was
            supplied, otherwise :func:`core_registry`. Pass your own to control
            exactly which kinds this read may produce.
    """

    if _depth > _DEFAULT_MAX_DEPTH:
        raise ArtifactError(f"artifact nesting depth exceeds {_DEFAULT_MAX_DEPTH}")
    if registry is None:
        registry = _registry_for(dialect)
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
    params = _unpack_value(kind, params)

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
    dialect: Optional["SQLDialectBase"] = None,
    *,
    registry: Any = None,
) -> BaseExpression:
    """Rebuild an expression from a bare `{kind, params}` artifact.

    The artifact is untrusted input (§4.11.4): an unknown kind, a leftover
    envelope field, or an unknown or missing parameter each fail explicitly and
    name the kind. This is the only place a registry is needed — it is what
    turns a `kind` back into a class.

    The artifact carries **no dialect**, and construction does not need one.
    ``deserialize(spec)`` is the dialect-free path: it resolves core's kinds and
    returns an unbound tree that renders through ``to_sql(dialect)``. When a
    dialect is supplied it both selects the kinds (through
    ``dialect.artifact_registry()``) and is bound onto the rebuilt tree, so
    ``restored.to_sql()`` keeps working for existing call sites.

    Args:
        spec: The artifact produced by :func:serialize.
        dialect: The dialect whose backend can read the artifact, or ``None``.
            It is bound to the rebuilt tree when supplied. If a node is
            incompatible with it, that surfaces at `to_sql()` time.
        registry: Registry used to resolve kinds. Selection order is: this
            argument, then ``dialect.artifact_registry()`` when a dialect was
            supplied, then :func:`core_registry`. Pass your own to control
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
    dialect: Optional["SQLDialectBase"] = None,
    *,
    registry: Any = None,
) -> BaseExpression:
    """Reconstruct an expression from a JSON string.

    Convenience wrapper around ``_default_serializer.deserialize_json()``.
    """
    return _default_serializer.deserialize_json(spec_str, dialect, registry=registry)


def serialize_xml(expr: BaseExpression) -> bytes:
    """Serialize an expression instance into an XML document (bytes).

    Convenience wrapper around ``_default_serializer.serialize_xml()``.
    """
    return _default_serializer.serialize_xml(expr)


def deserialize_xml(
    payload: bytes,
    dialect: Optional["SQLDialectBase"] = None,
    *,
    registry: Any = None,
) -> BaseExpression:
    """Reconstruct an expression from an XML document (bytes).

    Convenience wrapper around ``_default_serializer.deserialize_xml()``.
    """
    return _default_serializer.deserialize_xml(payload, dialect, registry=registry)
