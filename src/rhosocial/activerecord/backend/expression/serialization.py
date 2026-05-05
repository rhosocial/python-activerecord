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

import importlib
import inspect
from typing import Any, Dict, Type, TYPE_CHECKING

from .bases import BaseExpression

if TYPE_CHECKING:  # pragma: no cover
    from .dialect import SQLDialectBase


class ExpressionDeserializationError(Exception):
    """Raised when deserialization fails due to invalid spec or missing parameters."""

    pass


def serialize(expr: BaseExpression) -> Dict[str, Any]:
    """Serialize an expression instance into a JSON-serializable dict.

    The `dialect` is intentionally NOT embedded - it must be supplied at
    deserialization time. If an expression is incompatible with a given
    dialect, that failure occurs naturally at to_sql() time.

    Args:
        expr: The expression instance to serialize.

    Returns:
        ExpressionSpec dict with exactly three keys: type, module, params.

    Raises:
        NotImplementedError: If the expression class doesn't implement get_params().
    """
    params = _serialize_value(expr.get_params())
    return {
        "type": expr.__class__.__name__,
        "module": expr.__class__.__module__,
        "params": params,
    }


def _serialize_value(value: Any) -> Any:
    """Recursively serialize a value, handling BaseExpression instances and containers."""
    if isinstance(value, BaseExpression):
        return {"__expr__": serialize(value)}
    if isinstance(value, tuple):
        return {"__tuple__": [_serialize_value(item) for item in value]}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(val) for key, val in value.items()}
    return value


_MAX_NESTING_DEPTH = 64


def deserialize(
    spec: Dict[str, Any],
    dialect: "SQLDialectBase",
    _depth: int = 0,
) -> BaseExpression:
    """Reconstruct an expression from an ExpressionSpec dict.

    Args:
        spec: The serialized dict produced by serialize().
        dialect: The dialect instance to inject into all reconstructed expressions.
                 If an expression class is incompatible with this dialect,
                 the error surfaces naturally at to_sql() time.
        _depth: Internal parameter for nested expression depth tracking.

    Returns:
        A fully reconstructed BaseExpression instance

    Raises:
        ExpressionDeserializationError: On unknown type, missing required params,
                                       or excessive nesting depth.
    """
    if _depth > _MAX_NESTING_DEPTH:
        raise ExpressionDeserializationError(
            f"Expression nesting depth exceeds maximum ({_MAX_NESTING_DEPTH}). "
            f"This may be a malicious payload attempting to cause RecursionError."
        )

    type_name = spec.get("type")
    module_name = spec.get("module")
    params = spec.get("params", {})

    if not type_name or not module_name:
        raise ExpressionDeserializationError(
            f"Invalid spec: must have 'type' and 'module' fields. Got: {spec}"
        )

    try:
        expr_class = ExpressionRegistry.lookup(type_name, module_name)
    except ExpressionDeserializationError as e:
        raise ExpressionDeserializationError(
            f"Cannot find expression class '{type_name}' in module '{module_name}': {e}"
        ) from e

    if not issubclass(expr_class, BaseExpression):
        raise ExpressionDeserializationError(
            f"Class '{type_name}' in module '{module_name}' is not a subclass of BaseExpression"
        )

    deserialized_params = _deserialize_value(params, dialect, _depth + 1)
    try:
        return _reconstruct(expr_class, dialect, deserialized_params)
    except TypeError as e:
        raise ExpressionDeserializationError(
            f"Failed to reconstruct expression '{type_name}': {e}"
        ) from e


def _deserialize_value(value: Any, dialect: "SQLDialectBase", _depth: int = 0) -> Any:
    """Recursively deserialize a value, reconstructing nested BaseExpression instances."""
    if _depth > _MAX_NESTING_DEPTH:
        raise ExpressionDeserializationError(
            f"Expression nesting depth exceeds maximum ({_MAX_NESTING_DEPTH}). "
            f"This may be a malicious payload attempting to cause RecursionError."
        )

    if isinstance(value, dict):
        if "__tuple__" in value:
            return tuple(_deserialize_value(item, dialect, _depth + 1) for item in value["__tuple__"])
        if "__expr__" in value:
            return deserialize(value["__expr__"], dialect, _depth + 1)
        return {key: _deserialize_value(val, dialect, _depth + 1) for key, val in value.items()}
    if isinstance(value, list):
        return [_deserialize_value(item, dialect, _depth + 1) for item in value]
    if isinstance(value, tuple):
        return tuple(_deserialize_value(item, dialect, _depth + 1) for item in value)
    return value


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
            if pname == "self" or pname == "dialect":
                continue
            if pname == varargs_param:
                continue
            if pname in params:
                if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
                    pos_args.append(params[pname])
                else:
                    keyword_params[pname] = params[pname]
        return cls(dialect, *pos_args, *varargs, **keyword_params)

    valid_params = {}
    for pname, param in sig.parameters.items():
        if pname in ("self", "dialect"):
            continue
        if pname in params:
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                continue
            valid_params[pname] = params[pname]
    return cls(dialect, **valid_params)


class ExpressionFactory:
    """Dependency-injection style factory for expression instantiation.

    Wraps deserialize() with a bound dialect context.
    """

    def __init__(self, dialect: "SQLDialectBase"):
        self._dialect = dialect

    def create(self, type_name: str, **params: Any) -> BaseExpression:
        """Instantiate an expression by class name + keyword params.

        Note:
            The 'module' parameter is deprecated and ignored for security reasons.
            All expression classes must be pre-registered.

        Args:
            type_name: The class name of the expression (e.g., "Column", "Literal").
            **params: Constructor parameters for the expression class.
                      The 'module' parameter is deprecated and ignored.

        Returns:
            A BaseExpression instance.
        """
        params.pop("module", None)  # Deprecated, ignored for security
        return _reconstruct_by_name(type_name, self._dialect, params)

    def _create_from_spec(self, spec: Dict[str, Any]) -> BaseExpression:
        """Reconstruct an expression from an ExpressionSpec dict using the bound dialect."""
        return deserialize(spec, self._dialect)


def _reconstruct_by_name(
    type_name: str,
    dialect: "SQLDialectBase",
    params: Dict[str, Any],
) -> BaseExpression:
    """Reconstruct an expression by class name using registry or import."""
    try:
        expr_class = ExpressionRegistry.lookup(type_name, None)
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
    """Maps expression type names to their classes for deserialization.

    Pre-populated with all built-in expression classes.
    Allows registration of user-defined expression subclasses.
    """

    _registry: Dict[str, Type[BaseExpression]] = {}

    @classmethod
    def register(cls, expr_class: Type[BaseExpression]) -> None:
        """Register an expression class.

        Args:
            expr_class: The expression class to register.
        """
        cls._registry[expr_class.__name__] = expr_class

    @classmethod
    def lookup(cls, type_name: str, module: str = None) -> Type[BaseExpression]:
        """Look up an expression class by name.

        Lookup order: Check the in-memory registry only.

        Note:
            The `module` parameter is deprecated and ignored for security reasons.
            All expression classes must be pre-registered via ExpressionRegistry.register()
            or automatically registered via _auto_register_builtins().

        Args:
            type_name: The class name.
            module: Deprecated, ignored for security.

        Returns:
            The expression class.

        Raises:
            ExpressionDeserializationError: If class not found in registry.
        """
        if type_name in cls._registry:
            return cls._registry[type_name]

        raise ExpressionDeserializationError(
            f"Expression class '{type_name}' not found in registry. "
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
            aggregates,
            advanced_functions,
        )
        from . import introspection, transaction
        from . import statements as statements_pkg

        modules = [
            core,
            predicates,
            operators,
            query_parts,
            aggregates,
            advanced_functions,
            introspection,
            transaction,
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