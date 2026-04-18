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
from rhosocial.activerecord.backend.schema import StatementType

from .exceptions import (
    NamedQueryNotFoundError,
    NamedQueryModuleNotFoundError,
    NamedQueryInvalidReturnTypeError,
    NamedQueryInvalidParameterError,
    NamedQueryMissingParameterError,
    NamedQueryNotCallableError,
)


def guess_statement_type(sql: str) -> StatementType:
    """Guess the statement type from SQL string."""
    sql_stripped = sql.strip().upper()
    if sql_stripped.startswith(("SELECT", "WITH", "EXPLAIN", "PRAGMA")):
        return StatementType.DQL
    elif sql_stripped.startswith(("INSERT", "UPDATE", "DELETE")):
        return StatementType.DML
    elif sql_stripped.startswith(("CREATE", "ALTER", "DROP")):
        return StatementType.DDL
    else:
        return StatementType.OTHER


def _is_explain_statement(sql: str) -> bool:
    """Check if SQL is an EXPLAIN statement."""
    return sql.strip().upper().startswith("EXPLAIN")


def _coerce_param_value(value: str, annotation: Any) -> Any:
    """Coerce string value to the expected type based on annotation.

    Args:
        value: The string value from CLI
        annotation: The type annotation from function signature

    Returns:
        The coerced value

    Raises:
        NamedQueryInvalidParameterError: If coercion fails
    """
    annotation_name = getattr(annotation, "__name__", str(annotation))

    if annotation is inspect.Parameter.empty:
        return value

    try:
        if annotation == int or annotation_name == "int":
            return int(value)
        elif annotation == float or annotation_name == "float":
            return float(value)
        elif annotation == bool or annotation_name == "bool":
            lower_val = value.lower()
            if lower_val in ("1", "true", "yes"):
                return True
            elif lower_val in ("0", "false", "no"):
                return False
            else:
                raise NamedQueryInvalidParameterError(
                    "bool",
                    f"Invalid boolean value: {value}. Use 'true', 'false', '1', '0', 'yes', or 'no'",
                )
        elif annotation == str or annotation_name == "str":
            return value
        else:
            return value
    except (ValueError, TypeError) as e:
        raise NamedQueryInvalidParameterError(
            annotation_name,
            f"Cannot coerce '{value}' to {annotation_name}: {e}",
        )


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

        for name, param in sig.parameters.items():
            if name == "dialect":
                continue
            if name == "self":
                continue

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

        try:
            result = self._target_callable(**resolved_params)
        except TypeError as e:
            raise NamedQueryInvalidParameterError(
                "call",
                f"Failed to call named query: {e}",
            )

        if not isinstance(result, BaseExpression):
            actual_type = type(result).__name__
            raise NamedQueryInvalidReturnTypeError(
                self._qualified_name,
                actual_type,
            )

        return result

    def validate_for_execution(
        self,
        sql: str,
        force: bool = False,
        dry_run: bool = False,
    ) -> Tuple[StatementType, bool]:
        """Validate the SQL for execution.

        Args:
            sql: The generated SQL string
            force: Whether to force execution of non-DQL statements
            dry_run: Whether this is a dry run

        Returns:
            Tuple of (statement_type, is_allowed)

        Raises:
            NamedQueryExplainNotAllowedError: If EXPLAIN not allowed
        """
        stmt_type = guess_statement_type(sql)

        if _is_explain_statement(sql) and not dry_run:
            return stmt_type, False

        if stmt_type != StatementType.DQL and not force:
            return stmt_type, False

        return stmt_type, True


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
            - docstring: The docstring

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

        if inspect.isclass(obj):
            try:
                instance = obj()
                if not callable(instance):
                    continue
                target = instance.__call__
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
                    "docstring": inspect.getdoc(obj) or "",
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
                    "docstring": inspect.getdoc(obj) or "",
                })

    return results