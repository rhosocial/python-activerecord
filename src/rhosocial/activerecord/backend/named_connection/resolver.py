# src/rhosocial/activerecord/backend/named_connection/resolver.py
"""
Named connection resolver module.

This module provides functionality to resolve named connections defined as
Python callables (functions or classes) with fully qualified names.

A named connection is a callable (function, class instance with __call__, or method) that:
- Resides in a Python module
- Has 'backend_cls' as its first parameter (after 'self' for classes)
- Returns a ConnectionConfig (BaseConfig subclass) object

Named Connection Discovery:
    Named connections are discovered by scanning modules for callables with 'backend_cls'
    as the first parameter. Both functions and class instances are supported.

    Example function:
        >>> def production_db(backend_cls, pool_size: int = 10):
        ...     '''Get production database configuration.'''
        ...     return MySQLConnectionConfig(host="prod.example.com", pool_size=pool_size)

    Example class:
        >>> class ConnectionFactory:
        ...     def __call__(self, backend_cls, pool_size: int = 10):
        ...         '''Get production database configuration.'''
        ...         return MySQLConnectionConfig(host="prod.example.com", pool_size=pool_size)

Usage:
    Resolving a named connection:
        >>> from rhosocial.activerecord.backend.named_connection import NamedConnectionResolver
        >>> resolver = NamedConnectionResolver("myapp.connections.prod_db").load()
        >>> info = resolver.describe()
        >>> config = resolver.resolve(SQLiteBackend)

    Listing all connections in a module:
        >>> from rhosocial.activerecord.backend.named_connection import list_named_connections_in_module
        >>> connections = list_named_connections_in_module("myapp.connections")
"""
import inspect
import importlib
import re
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TYPE_CHECKING

from rhosocial.activerecord.backend.config import BaseConfig

from .exceptions import (
    NamedConnectionInvalidReturnTypeError,
    NamedConnectionInvalidParameterError,
    NamedConnectionMissingParameterError,
    NamedConnectionModuleNotFoundError,
    NamedConnectionNotCallableError,
    NamedConnectionNotFoundError,
)
from .validators import validate_connection_config, filter_sensitive_fields

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.base.base import StorageBackend


class NamedConnectionResolver:
    """Resolver for named connections defined as Python callables.

    This class provides a complete interface for resolving and executing
    named connections. It handles loading callables from modules,
    introspecting their signatures, and executing them with proper
    parameter handling.

    Lifecycle:
        1. Create resolver with qualified name
        2. Call load() to import the callable
        3. Optionally call describe() to get signature info
        4. Call resolve() to get ConnectionConfig

    Attributes:
        qualified_name: The fully qualified name of the named connection.
        module_name: The module name (parsed from qualified name).
        attr_name: The attribute name (parsed from qualified name).

    Example:
        >>> from rhosocial.activerecord.backend.named_connection import NamedConnectionResolver
        >>> resolver = NamedConnectionResolver("myapp.connections.prod_db")
        >>> resolver.load()
        >>> info = resolver.describe()
        >>> print(f"Parameters: {info['parameters']}")
        >>> config = resolver.resolve(SQLiteBackend, {"pool_size": 20})
    """

    def __init__(self, qualified_name: str):
        """Initialize resolver with a fully qualified name.

        Args:
            qualified_name: Fully qualified Python name in format 'module.path.callable'.
                Must contain exactly one dot separating module from callable name.

        Raises:
            NamedConnectionNotFoundError: If qualified_name format is invalid.
        """
        self._qualified_name = qualified_name
        self._module_name: str = ""
        self._attr_name: str = ""
        self._callable: Optional[Callable] = None
        self._target_callable: Optional[Callable] = None
        self._is_class: bool = False
        self._instance: Optional[Any] = None
        self._parse_qualified_name()

    def _parse_qualified_name(self) -> None:
        """Parse the qualified name into module and attribute names."""
        parts = self._qualified_name.rsplit(".", 1)
        if len(parts) != 2:
            raise NamedConnectionNotFoundError(
                self._qualified_name,
                "Qualified name must be in the format 'module.path.callable'",
            )
        self._module_name = parts[0]
        self._attr_name = parts[1]

    @property
    def qualified_name(self) -> str:
        """Get the qualified name of the named connection."""
        return self._qualified_name

    @property
    def module_name(self) -> str:
        """Get the module name."""
        return self._module_name

    @property
    def attr_name(self) -> str:
        """Get the attribute name."""
        return self._attr_name

    @property
    def is_class(self) -> bool:
        """Check if the callable is a class instance."""
        if self._target_callable is None:
            raise NamedConnectionNotCallableError(
                self._qualified_name,
                "Callable not loaded yet. Call load() first.",
            )
        return self._is_class

    def load(self) -> "NamedConnectionResolver":
        """Load the callable from the module.

        Returns:
            self: Returns self for method chaining.

        Raises:
            NamedConnectionModuleNotFoundError: If the module cannot be imported.
            NamedConnectionNotFoundError: If the attribute doesn't exist.
            NamedConnectionNotCallableError: If the attribute is not callable.
        """
        try:
            module = importlib.import_module(self._module_name)
        except ModuleNotFoundError as e:
            raise NamedConnectionModuleNotFoundError(
                self._module_name,
                f"Module not found. Ensure the module is installed or in PYTHONPATH: {e}",
            ) from None

        if not hasattr(module, self._attr_name):
            raise NamedConnectionNotFoundError(
                self._qualified_name,
                f"Attribute '{self._attr_name}' not found in module '{self._module_name}'",
            )

        self._callable = getattr(module, self._attr_name)

        if inspect.isclass(self._callable):
            self._is_class = True
            self._instance = self._callable()
            self._target_callable = self._instance.__call__
        elif inspect.isfunction(self._callable) or inspect.ismethod(self._callable):
            self._is_class = False
            self._target_callable = self._callable
        else:
            raise NamedConnectionNotCallableError(
                self._qualified_name,
                "Named connection must be a function, method, or class with __call__",
            )

        return self

    def get_signature(self) -> inspect.Signature:
        """Get the signature of the target callable."""
        if self._target_callable is None:
            raise NamedConnectionNotCallableError(
                self._qualified_name,
                "Callable not loaded yet. Call load() first.",
            )
        return inspect.signature(self._target_callable)

    def get_user_params(self) -> List[str]:
        """Get parameter names excluding 'backend_cls' and 'self'.

        Returns:
            List[str]: List of user-facing parameter names.
        """
        sig = self.get_signature()
        params = []
        for name, _param in sig.parameters.items():
            if name in ("backend_cls", "self"):
                continue
            params.append(name)
        return params

    def describe(self) -> Dict[str, Any]:
        """Get detailed description of the named connection (without sensitive data).

        This method provides comprehensive information about the named connection,
        including its signature, docstring, and parameter details.
        Sensitive fields (password, secret, etc.) are filtered out.

        Returns:
            Dict containing:
                - qualified_name (str): The fully qualified name.
                - is_class (bool): Whether it's a class instance.
                - docstring (str): The full docstring.
                - signature (str): The full signature string.
                - parameters (Dict): Dict of parameter info.
                - config_preview (dict): Non-sensitive config fields.

        Raises:
            NamedConnectionNotCallableError: If callable not loaded yet.
        """
        sig = self.get_signature()
        docstring = inspect.getdoc(self._callable) or ""

        params_info = {}
        for name, param in sig.parameters.items():
            if name in ("backend_cls", "self"):
                continue
            param_info = {
                "name": name,
                "type": (
                    str(param.annotation)
                    if param.annotation != inspect.Parameter.empty
                    else "Any"
                ),
                "has_default": param.default != inspect.Parameter.empty,
            }
            if param.default != inspect.Parameter.empty:
                param_info["default"] = repr(param.default)
            params_info[name] = param_info

        # Execute to get config preview (without sensitive fields)
        config_preview = {}
        try:
            config = self._target_callable(
                backend_cls=None,  # type: ignore
            )
            if isinstance(config, BaseConfig):
                raw_dict = config.to_dict()
                config_preview = filter_sensitive_fields(raw_dict)
        except Exception:
            pass

        return {
            "qualified_name": self._qualified_name,
            "is_class": self._is_class,
            "docstring": docstring,
            "signature": str(sig),
            "parameters": params_info,
            "config_preview": config_preview,
        }

    def resolve(
        self,
        backend_cls: Optional[Type["StorageBackend"]],
        user_params: Optional[Dict[str, Any]] = None,
    ) -> BaseConfig:
        """Resolve and return the ConnectionConfig from the named connection.

        Args:
            backend_cls: The backend class to pass as first parameter.
                Can be None if the callable doesn't use it.
            user_params: User-provided parameters (excluding backend_cls and self).

        Returns:
            BaseConfig: The ConnectionConfig instance returned by the callable.

        Raises:
            NamedConnectionNotCallableError: If callable not loaded yet.
            NamedConnectionMissingParameterError: If a required parameter is missing.
            NamedConnectionInvalidParameterError: If an unknown parameter is provided.
            NamedConnectionInvalidReturnTypeError: If the callable doesn't return
                a ConnectionConfig (BaseConfig subclass).
        """
        if self._target_callable is None:
            raise NamedConnectionNotCallableError(
                self._qualified_name,
                "Callable not loaded yet. Call load() first.",
            )

        user_params = user_params or {}
        sig = self.get_signature()

        resolved_params: Dict[str, Any] = {"backend_cls": backend_cls}

        param_names = set()
        for name, param in sig.parameters.items():
            if name == "backend_cls":
                continue
            if name == "self":
                continue
            param_names.add(name)

            if name in user_params:
                resolved_params[name] = user_params[name]
            elif param.default != inspect.Parameter.empty:
                resolved_params[name] = param.default
            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                continue
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                continue
            else:
                raise NamedConnectionMissingParameterError(
                    name,
                    f"Required parameter '{name}' not provided",
                )

        extra_params = set(user_params.keys()) - param_names
        if extra_params:
            raise NamedConnectionInvalidParameterError(
                list(extra_params)[0],
                f"Unknown parameter(s): {', '.join(extra_params)}. "
                f"Available parameters: {list(param_names)}",
            )

        try:
            result = self._target_callable(**resolved_params)
        except TypeError as e:
            error_msg = str(e)
            if "unexpected keyword argument" in error_msg:
                match = re.search(r"unexpected keyword argument '(\w+)'", error_msg)
                if match:
                    unknown_param = match.group(1)
                    raise NamedConnectionInvalidParameterError(
                        unknown_param,
                        f"Unknown parameter '{unknown_param}'. "
                        f"Available parameters: {list(resolved_params.keys())}",
                    ) from None
            raise NamedConnectionInvalidParameterError(
                "call",
                f"Failed to call named connection: {e}. "
                f"Check that all parameters are valid.",
            ) from None

        # Validate return type
        validate_connection_config(result, self._qualified_name)

        return result


def resolve_named_connection(
    qualified_name: str,
    backend_cls: Optional[Type["StorageBackend"]],
    user_params: Optional[Dict[str, Any]] = None,
) -> BaseConfig:
    """Resolve and execute a named connection in one step.

    This is a convenience function that combines resolver creation,
    loading, and execution in a single call.

    Args:
        qualified_name: Fully qualified Python name (module.path.callable).
        backend_cls: The backend class (automatically injected as first param).
        user_params: User-provided parameters (excluding backend_cls).

    Returns:
        BaseConfig: The ConnectionConfig instance.

    Example:
        >>> from rhosocial.activerecord.backend.named_connection import resolve_named_connection
        >>> config = resolve_named_connection(
        ...     "myapp.connections.prod_db",
        ...     SQLiteBackend,
        ...     {"pool_size": 20}
        ... )
    """
    resolver = NamedConnectionResolver(qualified_name).load()
    return resolver.resolve(backend_cls, user_params)


def list_named_connections_in_module(module_name: str) -> List[Dict[str, Any]]:
    """List all callable objects in a module that could be named connections.

    Args:
        module_name: The module name to scan.

    Returns:
        List[Dict[str, Any]]: List of dicts with connection info.

    Raises:
        NamedConnectionModuleNotFoundError: If the module cannot be imported.
    """
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        raise NamedConnectionModuleNotFoundError(
            module_name,
            f"Module not found: {e}",
        ) from None

    results = []
    for name in dir(module):
        if name.startswith("_"):
            continue

        obj = getattr(module, name, None)
        if obj is None:
            continue

        full_doc = inspect.getdoc(obj) or ""
        brief = full_doc.split("\n")[0].strip() if full_doc else ""

        if inspect.isclass(obj):
            try:
                instance = obj()
                if not callable(instance):
                    continue
                target = instance.__call__
                method_doc = inspect.getdoc(target)
                if method_doc and not full_doc:
                    full_doc = method_doc
                    brief = method_doc.split("\n")[0].strip()
            except Exception:
                continue

            try:
                sig = inspect.signature(target)
            except (ValueError, TypeError):
                continue

            first_param = next(iter(sig.parameters), None)
            if first_param and first_param == "backend_cls":
                results.append(
                    {
                        "name": name,
                        "is_class": True,
                        "signature": str(sig),
                        "docstring": full_doc,
                        "brief": brief,
                    }
                )

        elif inspect.isfunction(obj):
            try:
                sig = inspect.signature(obj)
            except (ValueError, TypeError):
                continue

            first_param = next(iter(sig.parameters), None)
            if first_param and first_param == "backend_cls":
                results.append(
                    {
                        "name": name,
                        "is_class": False,
                        "signature": str(sig),
                        "docstring": full_doc,
                        "brief": brief,
                    }
                )

    return results
