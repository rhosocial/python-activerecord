# src/rhosocial/activerecord/backend/expression/serialization.py
"""
Expression serialization and deserialization utilities.

This module provides functions to serialize expression objects to JSON-compatible
dictionaries and reconstruct them from those dictionaries. The `dialect` is
intentionally NOT serialized - it must be supplied at deserialization time.

Reserved special keys in serialized param dicts:
    "__tuple__"  →  Python tuple value (since tuple is not JSON native)
    "__expr__"   →  Nested BaseExpression instance

IMPORTANT: User-defined expression params MUST NOT use these reserved keys
in their get_params() return values. Using these keys will cause data
corruption or deserialization errors.
"""

import inspect
import warnings
from typing import Any, Dict, Type, TYPE_CHECKING

from .bases import BaseExpression

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

    Example:
        # Default configuration
        serializer = ExpressionSerializer()
        spec = serializer.serialize(expr)
        restored = serializer.deserialize(spec, dialect)

        # Custom configuration
        deep_serializer = ExpressionSerializer(max_depth=128, warn_threshold=0.9)
        deep_serializer.serialize(deep_expr)  # May issue warning
    """

    def __init__(
        self,
        max_depth: int = _DEFAULT_MAX_DEPTH,
        warn_threshold: float = _DEFAULT_WARN_THRESHOLD,
    ):
        if max_depth <= 0:
            raise ValueError("max_depth must be a positive integer")
        if not 0 < warn_threshold <= 1:
            raise ValueError("warn_threshold must be between 0 and 1")
        self.max_depth = max_depth
        self.warn_threshold = warn_threshold
        self._warn_issued: bool = False

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
        return {
            "type": f"{expr.__class__.__module__}.{expr.__class__.__name__}",
            "params": params,
        }

    def _serialize_value(self, value: Any, depth: int) -> Any:
        """Recursively serialize a value, handling BaseExpression instances and containers."""
        if isinstance(value, BaseExpression):
            return {"__expr__": self.serialize(value, _depth=depth)}
        if isinstance(value, tuple):
            return {"__tuple__": [self._serialize_value(item, depth + 1) for item in value]}
        if isinstance(value, list):
            return [self._serialize_value(item, depth + 1) for item in value]
        if isinstance(value, dict):
            return {key: self._serialize_value(val, depth + 1) for key, val in value.items()}
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
            raise ExpressionDeserializationError(
                f"Invalid spec: missing 'type' field. Got: {spec}"
            )

        if "." not in fqn:
            raise ExpressionDeserializationError(
                f"'type' must be a fully qualified name (module.ClassName), got '{fqn}'"
            )

        try:
            expr_class = ExpressionRegistry.lookup(fqn)
        except ExpressionDeserializationError as e:
            raise ExpressionDeserializationError(
                f"Cannot find expression class '{fqn}': {e}"
            ) from e

        if not issubclass(expr_class, BaseExpression):
            raise ExpressionDeserializationError(
                f"'{fqn}' is not a BaseExpression subclass"
            )

        params = spec.get("params", {})
        deserialized_params = self._deserialize_value(params, dialect, depth + 1)
        try:
            return _reconstruct(expr_class, dialect, deserialized_params)
        except TypeError as e:
            raise ExpressionDeserializationError(
                f"Failed to reconstruct expression '{fqn}': {e}"
            ) from e

    def _deserialize_value(self, value: Any, dialect: "SQLDialectBase", depth: int) -> Any:
        """Recursively deserialize a value with depth tracking."""
        if depth > self.max_depth:
            raise ExpressionDeserializationError(
                f"Expression nesting depth exceeds maximum ({self.max_depth}). "
                "This may be a malicious payload attempting to cause RecursionError."
            )

        if isinstance(value, dict):
            if "__tuple__" in value:
                return tuple(
                    self._deserialize_value(item, dialect, depth + 1)
                    for item in value["__tuple__"]
                )
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


def _reconstruct(
    cls: Type[BaseExpression],
    dialect: "SQLDialectBase",
    params: Dict[str, Any],
) -> BaseExpression:
    """Reconstruct an expression instance, handling VAR_POSITIONAL parameters."""
    params = dict(params)
    sig = inspect.signature(cls.__init__)

    varargs_param = None
    for name, param in sig.parameters.items():
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            varargs_param = name
            break

    if varargs_param and varargs_param in params:
        varargs = params.pop(varargs_param)
        pos_args = []
        keyword_params = {}
        for pname, param in sig.parameters.items():
            if pname in ("self", "dialect"):
                continue
            if pname == varargs_param:
                continue
            if pname in params:
                if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                    pos_args.append(params[pname])
                else:
                    keyword_params[pname] = params[pname]
        return cls(dialect, *pos_args, *varargs, **keyword_params)

    valid_params = {}
    for pname, _ in sig.parameters.items():
        if pname in ("self", "dialect"):
            continue
        if pname in params:
            valid_params[pname] = params[pname]
    return cls(dialect, **valid_params)


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
        raise ExpressionDeserializationError(
            f"Failed to reconstruct expression '{type_name}': {e}"
        ) from e


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
            matches = [
                cls_
                for key, cls_ in cls._registry.items()
                if key.rsplit(".", 1)[-1] == fqn
            ]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                fqns = [k for k in cls._registry if k.rsplit(".", 1)[-1] == fqn]
                raise ExpressionDeserializationError(
                    f"Ambiguous short name '{fqn}': found in {fqns}. Use FQN."
                )

        raise ExpressionDeserializationError(
            f"Expression class '{fqn}' not found in registry. "
            f"Please register it first using ExpressionRegistry.register()."
        )

    @classmethod
    def _auto_register_builtins(cls) -> None:
        """Auto-register all built-in expression classes."""
        import pkgutil
        import importlib
        from . import (
            core,
            predicates,
            operators,
            query_parts,
            query_sources,
            aggregates,
            advanced_functions,
        )
        from . import introspection, transaction, graph
        from . import statements as statements_pkg

        modules = [
            core,
            predicates,
            operators,
            query_parts,
            query_sources,
            aggregates,
            advanced_functions,
            introspection,
            transaction,
            graph,
        ]

        for mod in modules:
            for name in dir(mod):
                obj = getattr(mod, name, None)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseExpression)
                    and obj is not BaseExpression
                ):
                    cls.register(obj)

        for _, modname, _ in pkgutil.walk_packages(
            path=statements_pkg.__path__,
            prefix=statements_pkg.__name__ + ".",
            onerror=lambda x: None,
        ):
            sub_mod = importlib.import_module(modname)
            for name in dir(sub_mod):
                obj = getattr(sub_mod, name, None)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseExpression)
                    and obj is not BaseExpression
                ):
                    cls.register(obj)


ExpressionRegistry._auto_register_builtins()