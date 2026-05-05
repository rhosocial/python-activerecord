# src/rhosocial/activerecord/backend/expression/serialization.py
"""
Expression serialization and deserialization utilities.

This module provides functions to serialize expression objects to JSON-compatible
dictionaries and reconstruct them from those dictionaries. The `dialect` is
intentionally NOT serialized - it must be supplied at deserialization time.
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
        return serialize(value)
    if isinstance(value, tuple):
        return {"__tuple__": [_serialize_value(item) for item in value]}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(val) for key, val in value.items()}
    return value


def deserialize(
    spec: Dict[str, Any],
    dialect: "SQLDialectBase",
) -> BaseExpression:
    """Reconstruct an expression from an ExpressionSpec dict.

    Args:
        spec: The serialized dict produced by serialize().
        dialect: The dialect instance to inject into all reconstructed expressions.
                 If an expression class is incompatible with this dialect,
                 the error surfaces naturally at to_sql() time.

    Returns:
        A fully reconstructed BaseExpression instance

    Raises:
        ExpressionDeserializationError: On unknown type or missing required params
    """
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

    deserialized_params = _deserialize_value(params, dialect)
    try:
        return _reconstruct(expr_class, dialect, deserialized_params)
    except TypeError as e:
        raise ExpressionDeserializationError(
            f"Failed to reconstruct expression '{type_name}': {e}"
        ) from e


def _deserialize_value(value: Any, dialect: "SQLDialectBase") -> Any:
    """Recursively deserialize a value, reconstructing nested BaseExpression instances."""
    if isinstance(value, dict):
        if "__tuple__" in value:
            return tuple(_deserialize_value(item, dialect) for item in value["__tuple__"])
        if "type" in value and "module" in value and "params" in value:
            return deserialize(value, dialect)
        return {key: _deserialize_value(val, dialect) for key, val in value.items()}
    if isinstance(value, list):
        return [_deserialize_value(item, dialect) for item in value]
    if isinstance(value, tuple):
        return tuple(_deserialize_value(item, dialect) for item in value)
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

        Nested BaseExpression values in params are passed through as-is.
        If the type is not found in the registry, attempts to load from
        the 'module' parameter if provided.

        Args:
            type_name: The class name of the expression (e.g., "Column", "Literal").
            **params: Constructor parameters for the expression class.
                      Optionally include 'module' to specify the module path.

        Returns:
            A BaseExpression instance.
        """
        module_name = params.pop("module", None)
        try:
            return _reconstruct_by_name(type_name, self._dialect, params)
        except ExpressionDeserializationError:
            if module_name:
                try:
                    expr_class = ExpressionRegistry.lookup(type_name, module_name)
                    return _reconstruct(expr_class, self._dialect, params)
                except ExpressionDeserializationError:
                    pass
            raise

    def _create_from_spec(self, spec: Dict[str, Any]) -> BaseExpression:
        """Reconstruct an expression from an ExpressionSpec dict using the bound dialect."""
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

        deserialized_params = _deserialize_value(params, self._dialect)
        return _reconstruct(expr_class, self._dialect, deserialized_params)


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
    return _reconstruct(expr_class, dialect, params)


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

        If module is provided, first tries to import from module.
        Otherwise, looks up in the registry.

        Args:
            type_name: The class name.
            module: Optional module path.

        Returns:
            The expression class.

        Raises:
            ExpressionDeserializationError: If class not found.
        """
        if type_name in cls._registry:
            return cls._registry[type_name]

        if module:
            try:
                mod = importlib.import_module(module)
                expr_class = getattr(mod, type_name)
                cls.register(expr_class)
                return expr_class
            except (ImportError, AttributeError):
                pass

        raise ExpressionDeserializationError(
            f"Expression class '{type_name}' not found in registry or module '{module}'"
        )

    @classmethod
    def _auto_register_builtins(cls) -> None:
        """Auto-register all built-in expression classes."""
        import pkgutil
        import importlib
        from . import core, predicates, query_parts, aggregates, advanced_functions
        from . import introspection, transaction
        from . import statements as statements_pkg

        modules = [
            core,
            predicates,
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