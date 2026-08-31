# src/rhosocial/activerecord/backend/expression/serialization.py
"""
Expression serialization and deserialization utilities.

This module provides functions to serialize expression objects to JSON-compatible
dictionaries and reconstruct them from those dictionaries. The `dialect` is
intentionally NOT serialized - it must be supplied at deserialization time.

Reserved special keys in serialized param dicts:
    "__tuple__"  →  Python tuple value (since tuple is not JSON native)
    "__expr__"   →  Nested BaseExpression instance
    "__cast__"   →  TypeConversionMixin cast chain (list of target types),
                    captured at serialize time and re-applied at deserialize
                    time via cast() so fluent-API cast state round-trips.
    "__vdc__"    →  Dataclass value (FQN + field values), structurally encoded
                    so BaseExpression / Enum / nested-dataclass fields round-trip.
    "__value__"  →  Non-JSON-native scalar encoded via a registered codec.

IMPORTANT: User-defined expression params MUST NOT use these reserved keys
in their get_params() return values. Using these keys will cause data
corruption or deserialization errors.
"""

import inspect
import json
import warnings
from dataclasses import is_dataclass
from typing import Any, Dict, Optional, Sequence, Type, TYPE_CHECKING

from .bases import BaseExpression
from .codec import decode_value as _codec_decode_value
from .codec import encode_value as _codec_encode_value
from .codec import register_codec

if TYPE_CHECKING:  # pragma: no cover
    from .dialect import SQLDialectBase


class ExpressionDeserializationError(Exception):
    """Raised when deserialization fails due to invalid spec or missing parameters."""

    pass


_DEFAULT_MAX_DEPTH = 64
_DEFAULT_WARN_THRESHOLD = 0.8


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
            "rhosocial.activerecord.backend.expression.statements.dql.QueryExpression",
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
        """Serialize an expression instance into a JSON-serializable dict.

        The `dialect` is intentionally NOT embedded - it must be supplied at
        deserialization time. If an expression is incompatible with a given
        dialect, that failure occurs naturally at to_sql() time.

        Args:
            expr: The expression instance to serialize.
            _depth: Internal parameter for nested expression depth tracking.

        Returns:
            ExpressionSpec dict with exactly two keys: type (FQN), params.

        Raises:
            NotImplementedError: If the expression class doesn't implement get_params().
        """
        warn_level = int(self.max_depth * self.warn_threshold)
        if _depth >= warn_level and not self._warn_issued:
            warnings.warn(
                f"Expression serialization depth ({_depth}) exceeds warning threshold "
                f"({warn_level}). Deserialization may fail with max_depth={self.max_depth}. "
                "Consider simplifying the expression tree or increasing max_depth.",
                stacklevel=2,
            )
            self._warn_issued = True

        params = self._serialize_value(expr.get_params(), _depth + 1)
        cast_types = getattr(expr, "cast_types", None)
        if cast_types:
            params["__cast__"] = list(cast_types)
        return {
            "type": f"{expr.__class__.__module__}.{expr.__class__.__name__}",
            "params": params,
        }

    def _serialize_value(self, value: Any, depth: int) -> Any:
        """Recursively serialize a value, handling BaseExpression instances and containers."""
        if isinstance(value, BaseExpression):
            return {"__expr__": self.serialize(value, _depth=depth)}
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
        encoded = _codec_encode_value(value)
        if encoded is not None:
            return encoded
        return value

    def deserialize(self, spec: Dict[str, Any], dialect: "SQLDialectBase") -> BaseExpression:
        """Reconstruct an expression from an ExpressionSpec dict.

        This is the entry point for deserialization. All depth tracking and
        recursive processing happens internally.

        Args:
            spec: The serialized dict produced by serialize().
            dialect: The dialect instance to inject into all reconstructed expressions.
                     If an expression class is incompatible with this dialect,
                     the error surfaces naturally at to_sql() time.

        Returns:
            A fully reconstructed BaseExpression instance

        Raises:
            ExpressionDeserializationError: On unknown type, missing required params,
                                           or excessive nesting depth.
        """
        return self._deserialize_expression(spec, dialect, depth=0)

    def _deserialize_expression(
        self,
        spec: Dict[str, Any],
        dialect: "SQLDialectBase",
        depth: int,
    ) -> BaseExpression:
        """Deserialize an expression with depth tracking."""
        if depth > self.max_depth:
            raise ExpressionDeserializationError(
                f"Expression nesting depth exceeds maximum ({self.max_depth}). "
                "This may be a malicious payload attempting to cause RecursionError."
            )

        fqn = spec.get("type") or ""
        if not fqn:
            raise ExpressionDeserializationError(f"Invalid spec: missing 'type' field. Got: {spec}")

        if "." not in fqn:
            raise ExpressionDeserializationError(
                f"'type' must be a fully qualified name (module.ClassName), got '{fqn}'"
            )

        if not self._type_allowed(fqn):
            raise ExpressionDeserializationError(
                f"Expression type '{fqn}' is not in the allowed types list"
            )

        try:
            expr_class = ExpressionRegistry.lookup(fqn)
        except ExpressionDeserializationError as e:
            raise ExpressionDeserializationError(f"Cannot find expression class '{fqn}': {e}") from e

        if not issubclass(expr_class, BaseExpression):
            raise ExpressionDeserializationError(f"'{fqn}' is not a BaseExpression subclass")

        params = spec.get("params", {})
        deserialized_params = self._deserialize_value(params, dialect, depth + 1)
        cast_types = None
        if isinstance(deserialized_params, dict) and "__cast__" in deserialized_params:
            cast_types = deserialized_params.pop("__cast__")
        try:
            expr = _reconstruct(expr_class, dialect, deserialized_params)
        except TypeError as e:
            raise ExpressionDeserializationError(f"Failed to reconstruct expression '{fqn}': {e}") from e
        if cast_types:
            if not hasattr(expr, "cast"):
                raise ExpressionDeserializationError(
                    f"'{fqn}' carries '__cast__' but does not support cast()"
                )
            for target_type in cast_types:
                expr = expr.cast(target_type)
        return expr

    def _deserialize_value(self, value: Any, dialect: "SQLDialectBase", depth: int) -> Any:
        """Recursively deserialize a value with depth tracking."""
        if depth > self.max_depth:
            raise ExpressionDeserializationError(
                f"Expression nesting depth exceeds maximum ({self.max_depth}). "
                "This may be a malicious payload attempting to cause RecursionError."
            )

        if isinstance(value, dict):
            if "__value__" in value:
                return _codec_decode_value(value)
            if "__tuple__" in value:
                return tuple(self._deserialize_value(item, dialect, depth + 1) for item in value["__tuple__"])
            if "__vdc__" in value:
                return self._deserialize_dataclass(value["__vdc__"], dialect, depth)
            if "__expr__" in value:
                inner_spec = {
                    "type": value["__expr__"].get("type"),
                    "params": value["__expr__"].get("params", {}),
                }
                return self._deserialize_expression(inner_spec, dialect, depth + 1)
            return {key: self._deserialize_value(val, dialect, depth + 1) for key, val in value.items()}
        if isinstance(value, list):
            return [self._deserialize_value(item, dialect, depth + 1) for item in value]
        if isinstance(value, tuple):
            return tuple(self._deserialize_value(item, dialect, depth + 1) for item in value)
        return value

    def _deserialize_dataclass(self, payload: Any, dialect: "SQLDialectBase", depth: int) -> Any:
        """Reconstruct a dataclass encoded via the ``__vdc__`` reserved key."""
        import dataclasses
        import importlib

        fqn, fields = payload
        mod, _, qual = fqn.rpartition(".")
        cls = getattr(importlib.import_module(mod), qual)
        kwargs = {
            name: self._deserialize_value(val, dialect, depth + 1)
            for name, val in fields.items()
        }
        return cls(**kwargs)


    def serialize_json(self, expr: BaseExpression) -> str:
        """Serialize an expression instance into a JSON string.

        The JSON container walking/escaping is delegated to the standard
        library ``json``; only non-JSON-native values (datetime, Decimal,
        bytes, UUID, set, Enum, ...) are encoded via :func:`register_codec`
        codecs through the ``json.dumps(default=...)`` hook.
        """
        return json.dumps(self.serialize(expr), default=_codec_encode_value)

    def deserialize_json(self, spec_str: str, dialect: "SQLDialectBase") -> BaseExpression:
        """Reconstruct an expression from a JSON string produced by
        :meth:`serialize_json`.

        Non-JSON-native values are restored through the registered codecs
        via the ``json.loads(object_hook=...)`` hook.
        """
        restored = json.loads(spec_str, object_hook=_codec_decode_value)
        return self.deserialize(restored, dialect)

    def serialize_xml(self, expr: BaseExpression) -> bytes:
        """Serialize an expression instance into an XML document (bytes).

        The spec (with codec-encoded ``__value__`` markers) is rendered into
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


def serialize(expr: BaseExpression) -> Dict[str, Any]:
    """Serialize an expression instance into a JSON-serializable dict.

    This is a convenience function that uses a default ExpressionSerializer instance.
    For custom configuration, use ExpressionSerializer directly.

    Args:
        expr: The expression instance to serialize.

    Returns:
        ExpressionSpec dict with exactly two keys: type (FQN), params.
    """
    return _default_serializer.serialize(expr)


def deserialize(
    spec: Dict[str, Any],
    dialect: "SQLDialectBase",
) -> BaseExpression:
    """Reconstruct an expression from an ExpressionSpec dict.

    This is a convenience function that uses a default ExpressionSerializer instance.
    For custom configuration, use ExpressionSerializer directly.

    Args:
        spec: The serialized dict produced by serialize().
        dialect: The dialect instance to inject into all reconstructed expressions.

    Returns:
        A fully reconstructed BaseExpression instance
    """
    return _default_serializer.deserialize(spec, dialect)


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


def _reconstruct(
    cls: Type[BaseExpression],
    dialect: "SQLDialectBase",
    params: Dict[str, Any],
) -> BaseExpression:
    """Reconstruct an expression instance, handling VAR_POSITIONAL/VAR_KEYWORD parameters."""
    params = dict(params)
    sig = inspect.signature(cls.__init__)

    varargs_param = None
    varkwargs_param = None
    for name, param in sig.parameters.items():
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            varargs_param = name
        elif param.kind == inspect.Parameter.VAR_KEYWORD:
            varkwargs_param = name

    if varargs_param and varargs_param in params:
        varargs = params.pop(varargs_param)
        pos_args = []
        keyword_params = {}
        named = {"self", "dialect", varargs_param}
        for pname, param in sig.parameters.items():
            if pname in named:
                continue
            if pname in params:
                if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                    pos_args.append(params.pop(pname))
                else:
                    keyword_params[pname] = params.pop(pname)
        if varkwargs_param:
            # leftover keys that are not named parameters belong to **kwargs
            keyword_params[varkwargs_param] = params
        return cls(dialect, *pos_args, *varargs, **keyword_params)

    # Partition params: named ones vs. extras for **kwargs.
    named_keys = {
        pname
        for pname, param in sig.parameters.items()
        if pname not in ("self", "dialect")
        and param.kind != inspect.Parameter.VAR_KEYWORD
    }
    named_params = {p: v for p, v in params.items() if p in named_keys}
    extra_params = {
        p: v
        for p, v in params.items()
        if p not in named_keys and p not in ("self", "dialect") and p != varkwargs_param
    }

    valid_params = {p: v for p, v in named_params.items()}

    # Unified convention: dialect is the first positional parameter of every
    # expression class, including DataType value objects (optional there —
    # types may be declared before a dialect exists). Detect whether the
    # class accepts a dialect at all so it is only injected when supported.
    if "dialect" not in sig.parameters:
        return cls(**valid_params, **extra_params)
    first_param = next(
        (p for p in sig.parameters if p != "self"),
        None,
    )
    if first_param == "dialect":
        return cls(dialect, **valid_params, **extra_params)
    return cls(**{**valid_params, "dialect": dialect}, **extra_params)


class ExpressionFactory:
    """Dependency-injection style factory for expression instantiation.

    Uses ExpressionSerializer for serialization/deserialization.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        serializer: ExpressionSerializer = None,
    ):
        self._dialect = dialect
        self._serializer = serializer or ExpressionSerializer()

    def create(self, type_name: str, **params: Any) -> BaseExpression:
        """Instantiate an expression by class name + keyword params.

        Args:
            type_name: The class name of the expression (e.g., "Column", "Literal").
            **params: Constructor parameters for the expression class.

        Returns:
            A BaseExpression instance.
        """
        return _reconstruct_by_name(type_name, self._dialect, params)

    def _create_from_spec(self, spec: Dict[str, Any]) -> BaseExpression:
        """Reconstruct an expression from an ExpressionSpec dict using the bound dialect."""
        return self._serializer.deserialize(spec, self._dialect)

    def serialize(self, expr: BaseExpression) -> Dict[str, Any]:
        """Serialize an expression using the factory's serializer."""
        return self._serializer.serialize(expr)


def _reconstruct_by_name(
    type_name: str,
    dialect: "SQLDialectBase",
    params: Dict[str, Any],
) -> BaseExpression:
    """Reconstruct an expression by class name using registry or import."""
    try:
        expr_class = ExpressionRegistry.lookup(type_name)
    except ExpressionDeserializationError as e:
        raise ExpressionDeserializationError(
            f"Expression class '{type_name}' not found in registry. "
            f"Please register it first using ExpressionRegistry.register()."
        ) from e
    try:
        return _reconstruct(expr_class, dialect, params)
    except TypeError as e:
        raise ExpressionDeserializationError(f"Failed to reconstruct expression '{type_name}': {e}") from e


class ExpressionRegistry:
    """Maps expression FQN to their classes for deserialization.

    Pre-populated with all built-in expression classes.
    Allows registration of user-defined expression subclasses.
    """

    _registry: Dict[str, Type[BaseExpression]] = {}

    @classmethod
    def register(cls, expr_class: Type[BaseExpression]) -> None:
        """Register an expression class using its FQN as key.

        Args:
            expr_class: The expression class to register.
        """
        fqn = f"{expr_class.__module__}.{expr_class.__name__}"
        cls._registry[fqn] = expr_class

    @classmethod
    def lookup(cls, fqn: str) -> Type[BaseExpression]:
        """Look up an expression class by FQN or short class name.

        Lookup order:
            1. Direct FQN lookup (e.g., "rhosocial.activerecord.backend.expression.core.Column")
            2. Short name fallback (e.g., "Column") - only if unambiguous

        Note:
            All expression classes must be pre-registered via ExpressionRegistry.register()
            or automatically registered via _auto_register_builtins().

        Args:
            fqn: The fully qualified name or short class name.

        Returns:
            The expression class.

        Raises:
            ExpressionDeserializationError: If class not found or ambiguous.
        """
        if fqn in cls._registry:
            return cls._registry[fqn]

        if "." not in fqn:
            matches = [cls_ for key, cls_ in cls._registry.items() if key.rsplit(".", 1)[-1] == fqn]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                fqns = [k for k in cls._registry if k.rsplit(".", 1)[-1] == fqn]
                raise ExpressionDeserializationError(f"Ambiguous short name '{fqn}': found in {fqns}. Use FQN.")

        raise ExpressionDeserializationError(
            f"Expression class '{fqn}' not found in registry. "
            f"Please register it first using ExpressionRegistry.register()."
        )

    @classmethod
    def _auto_register_builtins(cls) -> None:
        """Auto-register all built-in expression classes.

        Walks the whole ``backend/expression`` package tree (including
        ``statements/``, ``collation.py``, ``datetime.py``, ``xml.py`` and
        ``types/``) and registers every class defined there that subclasses
        :class:`~rhosocial.activerecord.backend.expression.bases.BaseExpression`.
        Registration is idempotent: re-exported classes resolve to the same FQN.
        """
        import pkgutil
        import importlib

        pkg = importlib.import_module(__name__.rsplit(".", 1)[0])

        for _, modname, _ in pkgutil.walk_packages(
            path=pkg.__path__,
            prefix=pkg.__name__ + ".",
            onerror=lambda x: None,
        ):
            try:
                sub_mod = importlib.import_module(modname)
            except Exception:
                continue
            for name in dir(sub_mod):
                obj = getattr(sub_mod, name, None)
                if (
                    isinstance(obj, type)
                    and obj.__module__ == modname
                    and issubclass(obj, BaseExpression)
                    and obj is not BaseExpression
                ):
                    cls.register(obj)


ExpressionRegistry._auto_register_builtins()
