# src/rhosocial/activerecord/backend/named_query/resolver.py
"""
Named query resolver module.

Provides functionality to resolve and execute named queries defined as
Python callables (functions or classes) with fully qualified names.
"""
import inspect
import importlib
import sys
from typing import Any, Dict, List, Optional, Tuple, Callable

from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.executable import Executable
from rhosocial.activerecord.backend.schema import StatementType

from .exceptions import (
    NamedQueryNotFoundError,
    NamedQueryModuleNotFoundError,
    NamedQueryInvalidReturnTypeError,
    NamedQueryInvalidParameterError,
    NamedQueryMissingParameterError,
    NamedQueryNotCallableError,
)


def validate_expression(expression: BaseExpression, qualified_name: str) -> StatementType:
    """Validate that an expression is executable and return its statement type.

    Args:
        expression: The expression to validate
        qualified_name: The qualified name of the named query (for error messages)

    Returns:
        StatementType: The statement type of the expression

    Raises:
        NamedQueryInvalidReturnTypeError: If expression doesn't implement Executable
    """
    if not isinstance(expression, Executable):
        raise NamedQueryInvalidReturnTypeError(
            qualified_name,
            type(expression).__name__,
            "Expression must implement Executable protocol for named-query execution",
        )
    return expression.statement_type


class NamedQueryResolver:
    """Resolver for named queries defined as Python callables."""

    def __init__(self, qualified_name: str):
        """Initialize resolver with a fully qualified name.

        Args:
            qualified_name: Fully qualified Python name (module.path.callable)
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
            raise NamedQueryNotFoundError(
                self._qualified_name,
                "Qualified name must be in the format 'module.path.callable'",
            )
        self._module_name = parts[0]
        self._attr_name = parts[1]

    def load(self) -> "NamedQueryResolver":
        """Load the callable from the module.

        Returns:
            self for method chaining

        Raises:
            NamedQueryModuleNotFoundError: If module cannot be imported
            NamedQueryNotCallableError: If the target is not callable
        """
        try:
            module = importlib.import_module(self._module_name)
        except ModuleNotFoundError as e:
            raise NamedQueryModuleNotFoundError(
                self._module_name,
                f"Module not found. Ensure the module is installed or in PYTHONPATH: {e}",
            )

        if not hasattr(module, self._attr_name):
            raise NamedQueryNotFoundError(
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
            raise NamedQueryNotCallableError(
                self._qualified_name,
                "Named query must be a function, method, or class with __call__",
            )

        return self

    def get_signature(self) -> inspect.Signature:
        """Get the signature of the target callable.

        Returns:
            inspect.Signature: The signature of the callable

        Raises:
            NamedQueryNotCallableError: If callable not loaded
        """
        if self._target_callable is None:
            raise NamedQueryNotCallableError(
                self._qualified_name,
                "Callabl not loaded yet. Call load() first.",
            )
        return inspect.signature(self._target_callable)

    def get_user_params(self) -> List[str]:
        """Get parameter names excluding 'dialect' and 'self'.

        Returns:
            List of user-facing parameter names
        """
        sig = self.get_signature()
        params = []
        for name, param in sig.parameters.items():
            if name in ("dialect", "self"):
                continue
            params.append(name)
        return params

    def describe(self) -> Dict[str, Any]:
        """Get description of the named query including signature and docstring.

        Returns:
            Dict containing:
                - qualified_name: The fully qualified name
                - is_class: Whether it's a class
                - docstring: The docstring
                - signature: The full signature string
                - parameters: Dict of parameter info (name, type, default)

        Raises:
            NamedQueryNotCallableError: If callable not loaded
        """
        sig = self.get_signature()
        docstring = inspect.getdoc(self._callable) or ""

        params_info = {}
        for name, param in sig.parameters.items():
            if name in ("dialect", "self"):
                continue
            param_info = {
                "name": name,
                "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                "has_default": param.default != inspect.Parameter.empty,
            }
            if param.default != inspect.Parameter.empty:
                param_info["default"] = repr(param.default)
            params_info[name] = param_info

        return {
            "qualified_name": self._qualified_name,
            "is_class": self._is_class,
            "docstring": docstring,
            "signature": str(sig),
            "parameters": params_info,
        }

    def execute(
        self,
        dialect: Any,
        user_params: Optional[Dict[str, Any]] = None,
    ) -> BaseExpression:
        """Execute the named query with the given dialect and parameters.

        Args:
            dialect: The dialect instance (injected by CLI)
            user_params: User-provided parameters (excluding dialect)

        Returns:
            BaseExpression: The expression object

        Raises:
            NamedQueryMissingParameterError: If required parameter is missing
            NamedQueryInvalidParameterError: If parameter is invalid
            NamedQueryInvalidReturnTypeError: If return type is not BaseExpression
        """
        if self._target_callable is None:
            raise NamedQueryNotCallableError(
                self._qualified_name,
                "Callable not loaded yet. Call load() first.",
            )

        user_params = user_params or {}
        sig = self.get_signature()

        resolved_params: Dict[str, Any] = {"dialect": dialect}

        param_names = set()
        for name, param in sig.parameters.items():
            if name == "dialect":
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
                raise NamedQueryMissingParameterError(
                    name,
                    f"Required parameter '{name}' not provided",
                )

        extra_params = set(user_params.keys()) - param_names
        if extra_params:
            raise NamedQueryInvalidParameterError(
                list(extra_params)[0],
                f"Unknown parameter(s): {', '.join(extra_params)}. "
                f"Available parameters: {list(param_names)}",
            )

        try:
            result = self._target_callable(**resolved_params)
        except TypeError as e:
            error_msg = str(e)
            if "unexpected keyword argument" in error_msg:
                import re
                match = re.search(r"unexpected keyword argument '(\w+)'", error_msg)
                if match:
                    unknown_param = match.group(1)
                    raise NamedQueryInvalidParameterError(
                        unknown_param,
                        f"Unknown parameter '{unknown_param}'. "
                        f"Available parameters: {list(resolved_params.keys())}",
                    )
            raise NamedQueryInvalidParameterError(
                "call",
                f"Failed to call named query: {e}. "
                f"Check that all parameters are valid.",
            )
        except ValueError as e:
            param_with_issue = None
            for name, value in resolved_params.items():
                if name in ("dialect", "self"):
                    continue
                try:
                    if isinstance(value, str):
                        int(value) if name in param_names and sig.parameters[name].annotation in (int,) else str(value)
                except ValueError:
                    param_with_issue = name
                    break
            if param_with_issue:
                raise NamedQueryInvalidParameterError(
                    param_with_issue,
                    str(e),
                )
            raise NamedQueryInvalidParameterError(
                "parameter",
                f"Parameter conversion error: {e}",
            )

        if not isinstance(result, BaseExpression):
            actual_type = type(result).__name__
            raise NamedQueryInvalidReturnTypeError(
                self._qualified_name,
                actual_type,
            )

        if not isinstance(result, Executable):
            raise NamedQueryInvalidReturnTypeError(
                self._qualified_name,
                type(result).__name__,
                "Expression must implement Executable protocol",
            )

        return result


def resolve_named_query(
    qualified_name: str,
    dialect: Any,
    user_params: Optional[Dict[str, Any]] = None,
) -> Tuple[BaseExpression, str, tuple]:
    """Resolve and execute a named query in one step.

    Args:
        qualified_name: Fully qualified Python name
        dialect: The dialect instance
        user_params: User-provided parameters

    Returns:
        Tuple of (expression, sql, params)

    Raises:
        NamedQueryError: Various named query errors
    """
    resolver = NamedQueryResolver(qualified_name).load()
    expression = resolver.execute(dialect, user_params)
    sql, params = expression.to_sql()
    return expression, sql, params


def list_named_queries_in_module(module_name: str) -> List[Dict[str, Any]]:
    """List all callable objects in a module that could be named queries.

    A callable is considered a potential named query if:
    - It is a function or class
    - Its first parameter (after 'self' for classes) is named 'dialect'

    Args:
        module_name: The module name to scan

    Returns:
        List of dicts with query info:
            - name: The attribute name
            - is_class: Whether it's a class
            - signature: The signature string
            - docstring: The full docstring
            - brief: First line of docstring (one-line summary)

    Raises:
        NamedQueryModuleNotFoundError: If module cannot be imported
    """
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        raise NamedQueryModuleNotFoundError(
            module_name,
            f"Module not found: {e}",
        )

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
            if first_param and first_param == "dialect":
                results.append({
                    "name": name,
                    "is_class": True,
                    "signature": str(sig),
                    "docstring": full_doc,
                    "brief": brief,
                })

        elif inspect.isfunction(obj):
            try:
                sig = inspect.signature(obj)
            except (ValueError, TypeError):
                continue

            first_param = next(iter(sig.parameters), None)
            if first_param and first_param == "dialect":
                results.append({
                    "name": name,
                    "is_class": False,
                    "signature": str(sig),
                    "docstring": full_doc,
                    "brief": brief,
                })

    return results