# src/rhosocial/activerecord/backend/named_query/graph_resolver.py
"""
NamedProcedureGraphResolver for resolving callable ProcedureGraphs.

This module provides functionality to resolve and execute named procedure
graphs defined as Python callables with fully qualified names.
"""
import inspect
import importlib
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

from .exceptions import NamedQueryError, NamedQueryModuleNotFoundError
from .procedure_graph import ProcedureGraph


if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect.base import SQLDialectBase


class NamedProcedureGraphError(NamedQueryError):
    """Base error for NamedProcedureGraph operations."""

    pass


class NamedProcedureGraphInvalidReturnTypeError(NamedProcedureGraphError):
    """Raised when a named procedure graph returns invalid type."""

    def __init__(self, qualified_name: str, actual_type: str):
        self.qualified_name = qualified_name
        self.actual_type = actual_type
        super().__init__(
            f"Named procedure graph '{qualified_name}' must return "
            f"ProcedureGraph, got {actual_type}"
        )


class NamedProcedureGraphResolver:
    """Resolver for named procedure graphs.

    A named procedure graph is a callable (function or class with __call__)
    that:
    - Has 'dialect' as its first parameter
    - Returns a ProcedureGraph

    Example function:
        >>> def monthly_report_graph(dialect, params=None):
        ...     month = (params or {}).get("month", "")
        ...     return (
        ...         ProcedureGraph()
        ...         | StepNode.query("sales", "myapp.q.agg_sales", {"month": month})
        ...         | StepNode.query("refunds", "myapp.q.agg_refunds", {"month": month})
        ...     )

    Example class:
        >>> class MonthlyReportGraph:
        ...     def __call__(self, dialect, params=None):
        ...         return ProcedureGraph() | ...

    Usage:
        >>> from rhosocial.activerecord.backend.named_query import (
        ...     NamedProcedureGraphResolver,
        ... )
        >>> resolver = NamedProcedureGraphResolver("myapp.procedures.monthly")
        >>> resolver.load()
        >>> graph = resolver.build(dialect, {"month": "2026-04"})
    """

    def __init__(self, qualified_name: str):
        """Initialize resolver with qualified name.

        Args:
            qualified_name: Fully qualified Python name (module.path.callable).
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
        """Parse the qualified name."""
        parts = self._qualified_name.rsplit(".", 1)
        if len(parts) != 2:
            raise NamedProcedureGraphError(
                f"Invalid qualified name '{self._qualified_name}'. "
                "Must be in format 'module.path.callable'"
            )
        self._module_name = parts[0]
        self._attr_name = parts[1]

    @property
    def qualified_name(self) -> str:
        return self._qualified_name

    @property
    def module_name(self) -> str:
        return self._module_name

    @property
    def attr_name(self) -> str:
        return self._attr_name

    def load(self) -> "NamedProcedureGraphResolver":
        """Load the callable from the module.

        Returns:
            self for chaining.

        Raises:
            NamedQueryModuleNotFoundError: If module cannot be imported.
            NamedProcedureGraphError: If callable not found or not callable.
        """
        try:
            module = importlib.import_module(self._module_name)
        except ModuleNotFoundError as e:
            raise NamedQueryModuleNotFoundError(
                self._module_name,
                f"Module not found: {e}",
            ) from None

        if not hasattr(module, self._attr_name):
            raise NamedProcedureGraphError(
                f"Procedure graph '{self._attr_name}' not found "
                f"in module '{self._module_name}'"
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
            raise NamedProcedureGraphError(
                f"'{self._attr_name}' must be a function, method, "
                f"or class with __call__"
            )

        self._validate_signature()
        return self

    def _validate_signature(self) -> None:
        """Validate that the callable has 'dialect' as first parameter."""
        sig = inspect.signature(self._target_callable)
        params = list(sig.parameters.keys())
        if not params:
            raise NamedProcedureGraphError(
                f"'{self._attr_name}' has no parameters"
            )
        first_param = params[0]
        if first_param not in ("dialect", "self"):
            raise NamedProcedureGraphError(
                f"'{self._attr_name}' first parameter must be 'dialect', "
                f"got '{first_param}'"
            )

    def build(
        self,
        dialect: "SQLDialectBase",
        params: Optional[Dict[str, Any]] = None,
    ) -> ProcedureGraph:
        """Build the ProcedureGraph by calling the callable.

        Args:
            dialect: The SQL dialect instance.
            params: Optional parameters.

        Returns:
            The constructed ProcedureGraph.

        Raises:
            NamedProcedureGraphInvalidReturnTypeError: If callable returns non-ProcedureGraph.
            NamedProcedureGraphError: If callable not loaded.
        """
        if self._target_callable is None:
            raise NamedProcedureGraphError(
                "Callable not loaded. Call load() first."
            )

        resolved_params = {"dialect": dialect}
        if params:
            resolved_params["params"] = params

        try:
            result = self._target_callable(**resolved_params)
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                raise NamedProcedureGraphError(
                    f"Failed to call '{self._attr_name}': {e}. "
                    f"Expected parameters: dialect, optionally params"
                ) from None
            raise NamedProcedureGraphError(
                f"Failed to call '{self._attr_name}': {e}"
            ) from None

        if not isinstance(result, ProcedureGraph):
            raise NamedProcedureGraphInvalidReturnTypeError(
                self._qualified_name,
                type(result).__name__,
            )

        errors = result.validate()
        if errors:
            from .graph_runner import ProcedureGraphValidationError
            raise ProcedureGraphValidationError(errors)

        return result

    def describe(self) -> Dict[str, Any]:
        """Get description of the procedure graph."""
        if self._callable is None:
            raise NamedProcedureGraphError(
                "Callable not loaded. Call load() first."
            )

        sig = inspect.signature(self._target_callable)
        docstring = inspect.getdoc(self._callable) or ""

        return {
            "qualified_name": self._qualified_name,
            "is_class": self._is_class,
            "docstring": docstring,
            "signature": str(sig),
        }


def resolve_named_procedure_graph(
    qualified_name: str,
    dialect: "SQLDialectBase",
    params: Optional[Dict[str, Any]] = None,
) -> Tuple[ProcedureGraph, NamedProcedureGraphResolver]:
    """Resolve and build a named procedure graph in one step.

    This is a convenience function that combines resolver creation,
    loading, and building in a single call.

    Args:
        qualified_name: Fully qualified Python name.
        dialect: The SQL dialect instance.
        params: Optional parameters.

    Returns:
        Tuple of (ProcedureGraph, resolver).

    Example:
        >>> graph, resolver = resolve_named_procedure_graph(
        ...     "myapp.procedures.monthly",
        ...     dialect,
        ...     {"month": "2026-04"}
        ... )
        >>> waves = graph.waves()
    """
    resolver = NamedProcedureGraphResolver(qualified_name).load()
    graph = resolver.build(dialect, params)
    return graph, resolver


def list_procedure_graphs_in_module(module_name: str) -> List[Dict[str, Any]]:
    """List all callable objects in a module that could be procedure graphs.

    Scans a module for callables with 'dialect' as first parameter
    that might return ProcedureGraph.

    Args:
        module_name: The module name to scan.

    Returns:
        List of dicts with procedure graph info.

    Raises:
        NamedQueryModuleNotFoundError: If module cannot be imported.
    """
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        raise NamedQueryModuleNotFoundError(
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
            if first_param and first_param == "dialect":
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
            if first_param and first_param == "dialect":
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