# src/rhosocial/activerecord/backend/named_query/procedure.py
"""
Named procedure support for the backend.

This module provides functionality to define and execute named procedures
that can orchestrate multiple named queries with transaction support.

What is Named Procedure:
    Named procedure is a class that:
    - Inherits from the Procedure base class
    - Defines parameters as class attributes with type annotations
    - Implements a run(ctx) method that orchestrates named queries

    Example:
        >>> from rhosocial.activerecord.backend.named_query import Procedure, ProcedureContext
        >>>
        >>> class MonthlyReportProcedure(Procedure):
        ...     month: str  # Required parameter
        ...     threshold: int = 100  # Optional with default
        ...
        ...     def run(self, ctx: ProcedureContext) -> None:
        ...         # Execute a named query and bind result
        ...         ctx.execute(
        ...             "myapp.queries.orders.monthly_summary",
        ...             params={"month": self.month},
        ...             bind="summary",
        ...         )
        ...         # Get scalar value from result
        ...         total = ctx.scalar("summary", "total_count")
        ...         if total < self.threshold:
        ...             ctx.log(f"Total {total} below threshold")
        ...             return
        ...         # Iterate rows
        ...         for row in ctx.rows("summary"):
        ...             ctx.execute(
        ...                 "myapp.queries.archive.insert_record",
        ...                 params={"order_id": row["id"], "month": self.month},
        ...             )

Components:
    - Procedure: Base class for named procedures
    - ProcedureContext: Runtime context for procedure execution
    - ProcedureRunner: Executes procedures with transaction management
    - ProcedureResult: Result object returned by procedure execution

Usage:
    >>> from rhosocial.activerecord.backend.named_query import ProcedureRunner
    >>> runner = ProcedureRunner("myapp.procedures.monthly_report")
    >>> result = runner.run(dialect, {"month": "2026-03"})
"""
import inspect
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Type

from .resolver import resolve_named_query


class TransactionMode(Enum):
    """Transaction mode for procedure execution."""

    AUTO = "auto"
    STEP = "step"
    NONE = "none"


@dataclass
class LogEntry:
    """Represents a log entry from procedure execution."""

    level: str
    message: str


@dataclass
class ProcedureResult:
    """Result of procedure execution."""

    outputs: List[Dict[str, Any]] = field(default_factory=list)
    logs: List[LogEntry] = field(default_factory=list)
    aborted: bool = False
    abort_reason: Optional[str] = None


class ProcedureContext:
    """Runtime context for procedure execution.

    This class provides the interface for procedures to interact with
    the execution environment, including executing named queries,
    binding results, and logging.

    Attributes:
        dialect: The dialect instance for query execution.
        bindings: Dictionary of bound result sets.

    Example:
        >>> class MyProcedure(Procedure):
        ...     def run(self, ctx: ProcedureContext) -> None:
        ...         ctx.execute("myapp.queries.get_users", bind="users")
        ...         for user in ctx.rows("users"):
        ...             print(user["name"])
    """

    def __init__(
        self,
        dialect: Any,
        execute_callback: Any,
        transaction_mode: TransactionMode = TransactionMode.AUTO,
    ):
        self._dialect = dialect
        self._execute_callback = execute_callback
        self._transaction_mode = transaction_mode
        self._bindings: Dict[str, Dict[str, Any]] = {}
        self._logs: List[LogEntry] = []

    @property
    def dialect(self) -> Any:
        """Get the dialect instance."""
        return self._dialect

    @property
    def bindings(self) -> Dict[str, Dict[str, Any]]:
        """Get all bindings."""
        return self._bindings

    def execute(
        self,
        qualified_name: str,
        params: Optional[Dict[str, Any]] = None,
        bind: Optional[str] = None,
        output: bool = False,
    ) -> Dict[str, Any]:
        """Execute a named query and optionally bind the result.

        Args:
            qualified_name: Fully qualified name of the named query.
            params: Parameters to pass to the named query.
            bind: Optional variable name to bind the result to.
            output: Mark this result as an output to be returned.

        Returns:
            Dict containing:
                - data: List ofrow dictionaries
                - affected_rows: Number of rows affected
                - sql: The generated SQL
                - params: The SQL parameters

        Example:
            >>> ctx.execute(
            ...     "myapp.queries.active_users",
            ...     params={"limit": 50},
            ...     bind="users",
            ... )
        """
        params = params or {}
        result = self._execute_callback(qualified_name, self._dialect, params)

        result_data = {
            "qualified_name": qualified_name,
            "params": params,
            "bind": bind,
            "output": output,
            "sql": result.get("sql", ""),
            "params_sql": result.get("params_sql", ()),
            "data": result.get("data", []),
            "affected_rows": result.get("affected_rows", 0),
        }

        if bind:
            self._bindings[bind] = result_data

        return result_data

    def scalar(self, var_name: str, column: str) -> Any:
        """Extract a scalar value from a bound result set.

        Args:
            var_name: The variable name the result was bound to.
            column: The column name to extract.

        Returns:
            The value from the first row's column, or None if not found.

        Example:
            >>> total = ctx.scalar("summary", "total_count")
        """
        if var_name not in self._bindings:
            raise ValueError(f"Variable '{var_name}' not found in bindings")

        data = self._bindings[var_name].get("data", [])
        if not data:
            return None

        first_row = data[0]
        return first_row.get(column)

    def rows(self, var_name: str) -> Iterator[Dict[str, Any]]:
        """Iterate over all rows in a bound result set.

        Args:
            var_name: The variable name the result was bound to.

        Yields:
            Row dictionaries from the result set.

        Example:
            >>> for user in ctx.rows("users"):
            ...     print(user["name"])
        """
        if var_name not in self._bindings:
            raise ValueError(f"Variable '{var_name}' not found in bindings")

        data = self._bindings[var_name].get("data", [])
        yield from data

    def bind(self, name: str, data: Any) -> None:
        """Bind arbitrary data to a variable.

        Args:
            name: Variable name to bind to.
            data: Data to bind. Can be a single item, dict, or list of items.

        Example:
            >>> ctx.bind("config", {"threshold": 100})
            >>> ctx.bind("items", [{"id": 1}, {"id": 2}])
        """
        if data is None:
            self._bindings[name] = {"data": []}
        elif isinstance(data, list):
            self._bindings[name] = {"data": data}
        elif isinstance(data, dict):
            self._bindings[name] = {"data": [data]}
        else:
            self._bindings[name] = {"data": [data]}

    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message from the procedure.

        Args:
            message: The log message.
            level: Log level (DEBUG, INFO, WARNING, ERROR).

        Example:
            >>> ctx.log("Processing started", "DEBUG")
        """
        self._logs.append(LogEntry(level=level, message=message))

    def abort(self, reason: str) -> None:
        """Abort the procedure execution.

        This triggers a transaction rollback and stops further execution.

        Args:
            reason: The reason for aborting.

        Example:
        >>> if total < threshold:
        ...     ctx.abort(f"Total {total} below threshold {threshold}")
        """
        from .exceptions import NamedQueryError

        raise NamedQueryError(f"Procedure aborted: {reason}")


class Procedure:
    """Base class for named procedures.

    Subclasses must:
    - Define parameters as class attributes with type annotations
    - Implement a run(ctx: ProcedureContext) method

    Attributes:
        Parameters are defined as class attributes with type annotations.
        Required parameters have no default, optional parameters have defaults.

    Example:
        >>> class MyProcedure(Procedure):
        ...     month: str
        ...     threshold: int = 100
        ...
        ...     def run(self, ctx: ProcedureContext) -> None:
        ...         ctx.execute("myapp.queries.get_data", bind="data")
    """

    def run(self, ctx: ProcedureContext) -> None:
        """Execute the procedure logic.

        This method must be implemented by subclasses to define
        the procedure's logic.

        Args:
            ctx: The procedure context for execution.

        Raises:
            Any exception will cause transaction rollback.
        """
        raise NotImplementedError("Subclasses must implement run()")

    @classmethod
    def get_parameters(cls) -> Dict[str, Any]:
        """Get parameter information from class attributes.

        Returns:
            Dict mapping parameter names to type annotations and defaults.
        """
        params = {}
        for name, annotation in cls.__annotations__.items():
            if name == "run":
                continue
            default = getattr(cls, name, inspect.Parameter.empty)
            params[name] = {
                "annotation": annotation,
                "default": default,
                "has_default": default is not inspect.Parameter.empty,
            }
        return params


class ProcedureRunner:
    """Runner for executing named procedures.

    This class handles the complete lifecycle of executing a named procedure,
    including transaction management and result collection.

    Example:
        >>> runner = ProcedureRunner("myapp.procedures.monthly_report")
        >>> runner.load()
        >>> result = runner.run(dialect, {"month": "2026-03"})
    """

    def __init__(self, qualified_name: str):
        """Initialize runner with a qualified name.

        Args:
            qualified_name: Fully qualified name of the procedure class.
        """
        self._qualified_name = qualified_name
        self._procedure_class: Optional[Type[Procedure]] = None
        self._params_info: Dict[str, Any] = {}
        self._parse_qualified_name()

    def _parse_qualified_name(self) -> None:
        """Parse the qualified name."""
        parts = self._qualified_name.rsplit(".", 1)
        if len(parts) != 2:
            from .exceptions import NamedQueryError

            raise NamedQueryError(
                f"Invalid qualified name '{self._qualified_name}'. "
                "Must be in format 'module.path.ClassName'"
            )
        self._module_name = parts[0]
        self._class_name = parts[1]

    @property
    def qualified_name(self) -> str:
        """Get the qualified name."""
        return self._qualified_name

    def load(self) -> "ProcedureRunner":
        """Load the procedure class.

        Returns:
            self for chaining.

        Raises:
            NamedQueryModuleNotFoundError: If module cannot be imported.
            NamedQueryNotFoundError: If class doesn't exist or inherit Procedure.
        """
        import importlib

        from .exceptions import NamedQueryError, NamedQueryModuleNotFoundError

        try:
            module = importlib.import_module(self._module_name)
        except ModuleNotFoundError as e:
            raise NamedQueryModuleNotFoundError(
                self._module_name,
                f"Module not found: {e}",
            ) from None

        if not hasattr(module, self._class_name):
            raise NamedQueryError(
                f"Procedure '{self._class_name}' not found in module '{self._module_name}'"
            )

        cls = getattr(module, self._class_name)

        if not isinstance(cls, type) or not issubclass(cls, Procedure):
            raise NamedQueryError(
                f"'{self._class_name}' must inherit from Procedure base class"
            )

        self._procedure_class = cls
        self._params_info = cls.get_parameters()
        return self

    def describe(self) -> Dict[str, Any]:
        """Get procedure description.

        Returns:
            Dict with procedure info.
        """
        if not self._procedure_class:
            raise NamedQueryError("Procedure not loaded. Call load() first.")

        return {
            "qualified_name": self._qualified_name,
            "class_name": self._class_name,
            "docstring": inspect.getdoc(self._procedure_class) or "",
            "parameters": self._params_info,
        }

    def run(
        self,
        dialect: Any,
        user_params: Optional[Dict[str, Any]] = None,
        transaction_mode: TransactionMode = TransactionMode.AUTO,
    ) -> ProcedureResult:
        """Execute the procedure.

        Args:
            dialect: The dialect instance.
            user_params: User-provided parameters.
            transaction_mode: Transaction mode (auto, step, none).

        Returns:
            ProcedureResult with outputs and logs.
        """
        if not self._procedure_class:
            raise NamedQueryError("Procedure not loaded. Call load() first.")

        user_params = user_params or {}
        procedure = self._procedure_class()

        for param_name, param_value in user_params.items():
            if param_name in self._params_info:
                setattr(procedure, param_name, param_value)

        def execute_callback(fqn: str, dial: Any, params: Dict[str, Any]) -> Dict[str, Any]:
            _, sql, params_sql = resolve_named_query(fqn, dial, params)
            return {
                "sql": sql,
                "params_sql": params_sql,
                "data": [],
                "affected_rows": 0,
            }

        ctx = ProcedureContext(dialect, execute_callback, transaction_mode)

        result = ProcedureResult()

        try:
            procedure.run(ctx)
        except Exception as e:
            result.aborted = True
            result.abort_reason = str(e)

        result.logs = ctx._logs

        for name, bound_data in ctx.bindings.items():
            if bound_data.get("output"):
                result.outputs.append(bound_data)

        return result