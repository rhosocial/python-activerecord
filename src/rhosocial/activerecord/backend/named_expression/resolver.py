# src/rhosocial/activerecord/backend/named_expression/resolver.py
"""
Named expression resolver module.

This module provides functionality to resolve and execute named expressions
defined as Python callables (functions or classes) with fully qualified names.

A named expression is a callable (function, class instance with __call__, or method) that:
- Resides in a Python module
- Has 'dialect' as its first parameter (after 'self' for classes)
- Returns a BaseExpression object

Named Expression Discovery:
    Named expressions are discovered by scanning modules for callables with 'dialect'
    as the first parameter. Both functions and class instances are supported.

    Example function:
        >>> def active_users(dialect, limit: int = 100):
        ...     '''Get active users.'''
        ...     return QueryExpression(...)

    Example class:
        >>> class UserQueries:
        ...     def __call__(self, dialect, status: str = 'active'):
        ...         '''Get users by status.'''
        ...         return QueryExpression(...)

Usage:
    Resolving a named expression:
        >>> from rhosocial.activerecord.backend.named_expression import NamedExpressionResolver
        >>> resolver = NamedExpressionResolver("myapp.queries.active_users").load()
        >>> info = resolver.describe()
        >>> expression = resolver.execute(dialect, {"limit": 50})

    Listing all expressions in a module:
        >>> from rhosocial.activerecord.backend.named_expression import list_named_expressions_in_module
        >>> expressions = list_named_expressions_in_module("myapp.queries")

Note:
    This is a backend feature. It is independent of ActiveRecord or ActiveQuery
    and is designed for CLI and script-based query execution.
"""
import inspect
import importlib
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from rhosocial.activerecord.backend.expression.bases import BaseExpression

from .exceptions import (
    NamedExpressionInvalidReturnTypeError,
    NamedExpressionInvalidParameterError,
    NamedExpressionMissingParameterError,
    NamedExpressionModuleNotFoundError,
    NamedExpressionNotCallableError,
    NamedExpressionNotFoundError,
)


def _resolve_annotation(ann: Any, ns: dict) -> Any:
    """Resolve string (forward reference) annotations via eval in module namespace."""
    if isinstance(ann, str):
        try:
            return eval(ann, ns)
        except Exception:
            return ann
    return ann


def _ann_str(param: inspect.Parameter) -> str:
    if param.annotation is inspect.Parameter.empty:
        return "<untyped>"
    return str(param.annotation)


def _classify_param(param: inspect.Parameter, ns: dict) -> tuple:
    """Returns (kind, annotated).

    kind: "scalar" | "expression"
    annotated: False triggers warning
    """
    ann = param.annotation
    if ann is inspect.Parameter.empty:
        return "scalar", False
    ann = _resolve_annotation(ann, ns)
    if isinstance(ann, type) and issubclass(ann, BaseExpression):
        return "expression", True
    return "scalar", True


def _classify(expr: BaseExpression) -> List[str]:
    """Classify an expression into tag categories."""
    from rhosocial.activerecord.backend.expression.executable import Executable
    from rhosocial.activerecord.backend.schema import StatementType

    if not isinstance(expr, Executable):
        return ["CLAUSE"]
    st = expr.statement_type
    tag_map = [
        ({StatementType.DQL, StatementType.SELECT}, "DQL"),
        ({StatementType.DML, StatementType.INSERT, StatementType.UPDATE,
          StatementType.DELETE, StatementType.MERGE, StatementType.TRUNCATE}, "DML"),
        ({StatementType.DDL}, "DDL"),
        ({StatementType.TCL}, "TCL"),
        ({StatementType.CALL, StatementType.EXECUTE}, "CALL"),
        ({StatementType.EXPLAIN}, "EXPLAIN"),
    ]
    return [next((lbl for types, lbl in tag_map if st in types), "OTHER")]


def _probe_tags(
    target_callable: Callable,
    dialect: Any = None,
) -> List[str]:
    """Probe a callable to determine its expression tags."""
    try:
        sig = inspect.signature(target_callable)
    except (ValueError, TypeError):
        return ["?"]

    for name, param in sig.parameters.items():
        if name in ("dialect", "self"):
            continue
        if param.default is inspect.Parameter.empty:
            return ["?"]

    if dialect is None:
        return ["?"]

    try:
        result = target_callable(dialect=dialect)
    except Exception:
        return ["?"]

    if not isinstance(result, BaseExpression):
        return ["?"]

    return _classify(result)


class NamedExpressionResolver:
    """Resolver for named expressions defined as Python callables.

    This class provides a complete interface for resolving and executing
    named expressions. It handles loading callables from modules,
    introspecting their signatures, and executing them with
    proper parameter handling.

    Lifecycle:
        1. Create resolver with qualified name
        2. Call load() to import the callable
        3. Optionally call describe() to get signature info
        4. Call execute() to run the expression

    Attributes:
        qualified_name: The fully qualified name of the named expression.
        module_name: The module name (parsed from qualified name).
        attr_name: The attribute name (parsed from qualified name).

    Example:
        >>> from rhosocial.activerecord.backend.named_expression import NamedExpressionResolver
        >>> resolver = NamedExpressionResolver("myapp.queries.active_users")
        >>> resolver.load()
        >>> info = resolver.describe()
        >>> print(f"Parameters: {info['parameters']}")
        >>> expression = resolver.execute(dialect, {"limit": 100})
    """

    def __init__(self, qualified_name: str):
        """Initialize resolver with a fully qualified name.

        Args:
            qualified_name: Fully qualified Python name in format 'module.path.callable'.
                Must contain exactly one dot separating module from callable name.

        Raises:
            NamedExpressionNotFoundError: If qualified_name format is invalid
                (must be 'module.path.callable' with exactly one dot).

        Example:
            >>> resolver = NamedExpressionResolver("myapp.queries.user_active")
            >>> resolver = NamedExpressionResolver("project.models.queries.orders_pending")
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
        """Parse the qualified name into module and attribute names.

        This internal method splits the qualified name on the last dot
        to separate the module path from the callable name.

        Raises:
            NamedExpressionNotFoundError: If format is invalid.
                Valid format: 'module.path.callable' (exactly one dot).
        """
        parts = self._qualified_name.rsplit(".", 1)
        if len(parts) != 2:
            raise NamedExpressionNotFoundError(
                self._qualified_name,
                "Qualified name must be in the format 'module.path.callable'",
            )
        self._module_name = parts[0]
        self._attr_name = parts[1]

    @property
    def qualified_name(self) -> str:
        """Get the qualified name of the named expression.

        Returns:
            str: The fully qualified name (module.path.callable).
        """
        return self._qualified_name

    @property
    def module_name(self) -> str:
        """Get the module name.

        Returns:
            str: The module name (may be empty if not loaded).
        """
        return self._module_name

    @property
    def attr_name(self) -> str:
        """Get the attribute name.

        Returns:
            str: The attribute name (may be empty if not loaded).
        """
        return self._attr_name

    @property
    def is_class(self) -> bool:
        """Check if the callable is a class instance.

        Returns:
            bool: True if the callable is a class with __call__, False otherwise.

        Raises:
            NamedExpressionNotCallableError: If callable not loaded yet.
        """
        if self._target_callable is None:
            raise NamedExpressionNotCallableError(
                self._qualified_name,
                "Callable not loaded yet. Call load() first.",
            )
        return self._is_class

    def load(self) -> "NamedExpressionResolver":
        """Load the callable from the module.

        This method imports the module and retrieves the callable attribute.
        For classes, it also instantiates the class and prepares for calling.

        Returns:
            self: Returns self for method chaining.

        Raises:
            NamedExpressionModuleNotFoundError: If the module cannot be imported.
                Check that:
                - Module is installed in the environment
                - Module path is in PYTHONPATH
                - Module name is spelled correctly

            NamedExpressionNotFoundError: If the attribute doesn't exist in the module.
                Check that:
                - The function/class is defined in the module
                - The function/class is exported in __all__ (if used)

            NamedExpressionNotCallableError: If the attribute exists but is not callable.
                Only functions, methods, and classes with __call__ are valid.

        Example:
            >>> resolver = NamedExpressionResolver("myapp.queries.user_active")
            >>> resolver.load()  # loads and prepares the callable
            >>> # or chain it
            >>> info = NamedExpressionResolver("myapp.queries.user_active").load().describe()
        """
        try:
            module = importlib.import_module(self._module_name)
        except ModuleNotFoundError as e:
            raise NamedExpressionModuleNotFoundError(
                self._module_name,
                f"Module not found. Ensure the module is installed or in PYTHONPATH: {e}",
            ) from None

        if not hasattr(module, self._attr_name):
            raise NamedExpressionNotFoundError(
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
            raise NamedExpressionNotCallableError(
                self._qualified_name,
                "Named expression must be a function, method, or class with __call__",
            )

        return self

    def get_signature(self) -> inspect.Signature:
        """Get the signature of the target callable.

        This method provides access to the callable's parameter information,
        including parameter names, types, defaults, and kinds (positional,
        keyword, VAR_POSITIONAL, VAR_KEYWORD).

        Returns:
            inspect.Signature: The signature of the callable.

        Raises:
            NamedExpressionNotCallableError: If callable not loaded yet.
                Call load() before getting signature.

        Example:
            >>> resolver.load()
            >>> sig = resolver.get_signature()
            >>> for name, param in sig.parameters.items():
            ...     print(f"{name}: {param.annotation} = {param.default}")
        """
        if self._target_callable is None:
            raise NamedExpressionNotCallableError(
                self._qualified_name,
                "Callable not loaded yet. Call load() first.",
            )
        return inspect.signature(self._target_callable)

    def get_user_params(self) -> List[str]:
        """Get parameter names excluding 'dialect' and 'self'.

        This method returns only the user-facing parameters that should
        be provided by the CLI or caller. Parameters named 'dialect'
        and 'self' are automatically handled by the resolver.

        Returns:
            List[str]: List of user-facing parameter names.

        Raises:
            NamedExpressionNotCallableError: If callable not loaded yet.

        Example:
            >>> resolver.load()
            >>> params = resolver.get_user_params()
            >>> print(f"User params: {params}")  # ['limit', 'status']
        """
        sig = self.get_signature()
        params = []
        for name, _param in sig.parameters.items():
            if name in ("dialect", "self"):
                continue
            params.append(name)
        return params

    def get_param_specs(self) -> List[Dict[str, Any]]:
        """Get parameter specifications with type classification.

        Returns:
            List of dicts with keys: name, kind (scalar|expression),
            annotated (bool), annotation (str), has_default (bool), default (optional).
        """
        sig = self.get_signature()
        ns = vars(importlib.import_module(self._module_name))
        result = []
        for name, param in sig.parameters.items():
            if name in ("dialect", "self"):
                continue
            kind, annotated = _classify_param(param, ns)
            entry: Dict[str, Any] = {
                "name": name,
                "kind": kind,
                "annotated": annotated,
                "annotation": _ann_str(param),
                "has_default": param.default is not inspect.Parameter.empty,
            }
            if entry["has_default"]:
                entry["default"] = repr(param.default)
            result.append(entry)
        return result

    def describe(self) -> Dict[str, Any]:
        """Get detailed description of the named expression.

        This method provides comprehensive information about the named expression,
        including its signature, docstring, and parameter details.
        It is useful for generating help text and documentation.

        Returns:
            Dict containing:
                - qualified_name (str): The fully qualified name.
                - is_class (bool): Whether it's a class instance.
                - docstring (str): The full docstring.
                - signature (str): The full signature string.
                - parameters (Dict): Dict of parameter info with keys:
                    - name (str): Parameter name.
                    - type (str): Type annotation as string.
                    - has_default (bool): Whether parameter has default.
                    - default (str, optional): Default value repr.

        Raises:
            NamedExpressionNotCallableError: If callable not loaded yet.

        Example:
            >>> resolver.load()
            >>> info = resolver.describe()
            >>> print(info['signature'])
            >>> print(info['docstring'])
            >>> for name, param in info['parameters'].items():
            ...     print(f"  {name}: {param['type']}")
        """
        sig = self.get_signature()
        docstring = inspect.getdoc(self._callable) or ""

        params_info = {}
        for name, param in sig.parameters.items():
            if name in ("dialect", "self"):
                continue
            param_info: Dict[str, Any] = {
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
        """Execute the named expression with the given dialect and parameters.

        This method resolves parameters, calls the callable, and validates
        the return type. It handles all parameter injection including
        the required 'dialect' parameter.

        Args:
            dialect: The dialect instance. This is automatically injected
                and required as the first parameter.
            user_params: User-provided parameters (excluding dialect and self).
                These map to the callable's parameters.

        Returns:
            BaseExpression: The expression object returned by the callable.

        Raises:
            NamedExpressionNotCallableError: If callable not loaded yet.
                Call load() before execute().

            NamedExpressionMissingParameterError: If a required parameter
                (without default) is not provided.

            NamedExpressionInvalidParameterError: If an unknown parameter is provided
                or parameter type conversion fails.

            NamedExpressionInvalidReturnTypeError: If the callable doesn't return a
                BaseExpression. This is a security check - only type-safe expressions
                are allowed. Use 'query' subcommand for raw SQL.

        Example:
            >>> resolver.load()
            >>> expression = resolver.execute(dialect, {"limit": 50, "status": "active"})
        """
        if self._target_callable is None:
            raise NamedExpressionNotCallableError(
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
                raise NamedExpressionMissingParameterError(
                    name,
                    f"Required parameter '{name}' not provided",
                )

        extra_params = set(user_params.keys()) - param_names
        if extra_params:
            raise NamedExpressionInvalidParameterError(
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
                    raise NamedExpressionInvalidParameterError(
                        unknown_param,
                        f"Unknown parameter '{unknown_param}'. "
                        f"Available parameters: {list(resolved_params.keys())}",
                    ) from None
            raise NamedExpressionInvalidParameterError(
                "call",
                f"Failed to call named expression: {e}. "
                f"Check that all parameters are valid.",
            ) from None
        except ValueError as e:
            param_with_issue = None
            for name, value in resolved_params.items():
                if name in ("dialect", "self"):
                    continue
                try:
                    if isinstance(value, str):
                        if (
                            name in param_names
                            and sig.parameters[name].annotation in (int,)
                        ):
                            int(value)
                except ValueError:
                    param_with_issue = name
                    break
            if param_with_issue:
                raise NamedExpressionInvalidParameterError(
                    param_with_issue,
                    str(e),
                ) from None
            raise NamedExpressionInvalidParameterError(
                "parameter",
                f"Parameter conversion error: {e}",
            ) from None

        if not isinstance(result, BaseExpression):
            actual_type = type(result).__name__
            raise NamedExpressionInvalidReturnTypeError(
                self._qualified_name,
                actual_type,
            )

        return result


def resolve_named_expression(
    qualified_name: str,
    dialect: Any,
    user_params: Optional[Dict[str, Any]] = None,
) -> BaseExpression:
    """Resolve and execute a named expression in one step.

    This is a convenience function that combines resolver creation,
    loading, and execution in a single call. It is useful for
    simple use cases where detailed control is not needed.

    Args:
        qualified_name: Fully qualified Python name (module.path.callable).
        dialect: The dialect instance (automatically injected as first param).
        user_params: User-provided parameters (excluding dialect).

    Returns:
        BaseExpression: The expression object returned by the callable.

    Raises:
        NamedExpressionError: Various named expression errors including:
            - NamedExpressionModuleNotFoundError
            - NamedExpressionNotFoundError
            - NamedExpressionNotCallableError
            - NamedExpressionMissingParameterError
            - NamedExpressionInvalidParameterError
            - NamedExpressionInvalidReturnTypeError

    Example:
        >>> from rhosocial.activerecord.backend.named_expression import resolve_named_expression
        >>> expression = resolve_named_expression(
        ...     "myapp.queries.active_users",
        ...     dialect,
        ...     {"limit": 50}
        ... )
    """
    resolver = NamedExpressionResolver(qualified_name).load()
    return resolver.execute(dialect, user_params)


def list_named_expressions_in_module(
    module_name: str,
    dialect: Any = None,
) -> List[Dict[str, Any]]:
    """List all callable objects in a module that could be named expressions.

    This function scans a module for callable objects that meet the
    named expression criteria. A callable is considered a potential
    named expression if:
    - It is a function or class (with __call__)
    - Its first parameter (after 'self' for classes) is named 'dialect'

    This is useful for discovering available expressions and generating
    help/listing output.

    Args:
        module_name: The module name to scan. Can be a top-level module
            or a nested module path.
        dialect: Optional dialect instance for dry-probing expression tags.
            When provided, the function attempts to call each expression with
            default parameters to determine its tags (DQL, DML, DDL, CLAUSE, etc.).

    Returns:
        List[Dict[str, Any]]: List of dicts with expression info:
            - name (str): The attribute name.
            - is_class (bool): Whether it's a class instance.
            - signature (str): The signature string.
            - docstring (str): The full docstring.
            - brief (str): First line of docstring (one-line summary).
            - tags (List[str]): Classification tags (DQL, DML, DDL, CLAUSE, ?, etc.).
            - param_specs (List[Dict]): Parameter specifications.

    Raises:
        NamedExpressionModuleNotFoundError: If the module cannot be imported.

    Example:
        >>> from rhosocial.activerecord.backend.named_expression import list_named_expressions_in_module
        >>> expressions = list_named_expressions_in_module("myapp.queries")
        >>> for q in expressions:
        ...     print(f"{q['name']}: {q['brief']} [{','.join(q['tags'])}]")
    """
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        raise NamedExpressionModuleNotFoundError(
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
        ns = vars(module)

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
                # Build param_specs from class __call__ signature
                param_specs = []
                for pname, pparam in sig.parameters.items():
                    if pname in ("dialect", "self"):
                        continue
                    kind, annotated = _classify_param(pparam, ns)
                    entry: Dict[str, Any] = {
                        "name": pname,
                        "kind": kind,
                        "annotated": annotated,
                        "annotation": _ann_str(pparam),
                        "has_default": pparam.default is not inspect.Parameter.empty,
                    }
                    if entry["has_default"]:
                        entry["default"] = repr(pparam.default)
                    param_specs.append(entry)

                results.append(
                    {
                        "name": name,
                        "is_class": True,
                        "signature": str(sig),
                        "docstring": full_doc,
                        "brief": brief,
                        "tags": _probe_tags(target, dialect),
                        "param_specs": param_specs,
                    }
                )

        elif inspect.isfunction(obj):
            try:
                sig = inspect.signature(obj)
            except (ValueError, TypeError):
                continue

            first_param = next(iter(sig.parameters), None)
            if first_param and first_param == "dialect":
                # Build param_specs from function signature
                param_specs = []
                for pname, pparam in sig.parameters.items():
                    if pname in ("dialect", "self"):
                        continue
                    kind, annotated = _classify_param(pparam, ns)
                    entry: Dict[str, Any] = {
                        "name": pname,
                        "kind": kind,
                        "annotated": annotated,
                        "annotation": _ann_str(pparam),
                        "has_default": pparam.default is not inspect.Parameter.empty,
                    }
                    if entry["has_default"]:
                        entry["default"] = repr(pparam.default)
                    param_specs.append(entry)

                results.append(
                    {
                        "name": name,
                        "is_class": False,
                        "signature": str(sig),
                        "docstring": full_doc,
                        "brief": brief,
                        "tags": _probe_tags(obj, dialect),
                        "param_specs": param_specs,
                    }
                )

    return results
