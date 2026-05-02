# src/rhosocial/activerecord/backend/named_query/procedure_graph.py
"""
ProcedureGraph data model for declarative DAG-based procedures.

This module provides a data-driven approach to defining procedures as
directed acyclic graphs (DAGs) of steps. Unlike the imperative Procedure
class which mixes logic with execution in run(), ProcedureGraph separates
the "what" (graph structure) from the "how" (execution).

Key Design Principles:
    1. Pure data: ProcedureGraph and StepNode are pure Python data,
       no I/O in their methods
    2. Single definition, dual execution: Same graph can be run by either
       sync or async runner
    3. Auto-parallelism: Runner automatically identifies steps that can run in parallel
    4. Named体系 consistency: Maps to NamedQuery/NamedConnection naming

Usage:
    >>> from rhosocial.activerecord.backend.named_query import (
    ...     ProcedureGraph,
    ...     StepNode,
    ...     TransactionMode,
    ... )
    >>>
    >>> graph = (
    ...     ProcedureGraph(transaction_mode=TransactionMode.STEP)
    ...     | StepNode.query("fetch_users", "myapp.q.active_users", params={"limit": 100})
    ...     | StepNode.query("fetch_orders", "myapp.q.recent_orders", depends_on=["fetch_users"])
    ... )
"""
import re
import importlib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    TYPE_CHECKING,
)

from rhosocial.activerecord.backend.expression.bases import BaseExpression


if TYPE_CHECKING:
    from rhosocial.activerecord.backend.dialect.base import SQLDialectBase


class TransactionMode(Enum):
    """Transaction mode for procedure graph execution."""

    AUTO = "auto"
    STEP = "step"
    NONE = "none"


class StepKind(Enum):
    """Kind of procedure step."""

    NAMED_QUERY = auto()
    EXPRESSION = auto()
    SUBGRAPH = auto()


class CyclicDependencyError(Exception):
    """Raised when a cyclic dependency is detected in the graph."""

    def __init__(self, nodes: List[str]):
        self.nodes = nodes
        super().__init__(f"Cyclic dependency detected: {nodes}")


def _kahn_topological_waves(
    nodes: Dict[str, "StepNode"],
) -> List[List["StepNode"]]:
    """Compute topological waves using Kahn's algorithm.

    Returns steps grouped by wave (parallel execution group).
    Steps in the same wave have no dependencies on each other
    and can be executed in parallel.

    Args:
        nodes: Dict mapping step name to StepNode.

    Returns:
        List of waves, each wave is a list of StepNodes.

    Raises:
        CyclicDependencyError: If a cycle is detected.
    """
    in_degree: Dict[str, int] = {name: 0 for name in nodes}
    dependents: Dict[str, List[str]] = {name: [] for name in nodes}

    for node in nodes.values():
        for dep in node.depends_on:
            if dep not in nodes:
                raise ValueError(f"Unknown dependency: {dep!r}")
            in_degree[node.name] += 1
            dependents[dep].append(node.name)

    waves: List[List[StepNode]] = []
    queue = [name for name, deg in in_degree.items() if deg == 0]

    while queue:
        wave = [nodes[name] for name in queue]
        waves.append(wave)
        next_queue = []
        for name in queue:
            for child in dependents[name]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    next_queue.append(child)
        queue = next_queue

    remaining = [n for n, d in in_degree.items() if d > 0]
    if remaining:
        raise CyclicDependencyError(remaining)

    return waves


class StepNode:
    """Single step in a ProcedureGraph.

    A step represents a single unit of work that can be executed.
    Steps can reference NamedQueries, inline Expressions, or
    nested Subgraphs.

    Attributes:
        name: Unique identifier within the graph.
        label: Human-readable description.
        kind: Type of step (NAMED_QUERY, EXPRESSION, SUBGRAPH).
        named_query: Qualified name for NAMED_QUERY kind.
        expression: BaseExpression for EXPRESSION kind.
        subgraph: ProcedureGraph for SUBGRAPH kind.
        params: Parameters passed to NamedQuery.
        bind: Additional bindings (overrides params).
        depends_on: List of step names this step depends on.
        condition: Condition expression for conditional execution.
        skip_for: List of backends to skip this step for.
        bind_output: Map result paths to variable names.

    Example:
        >>> StepNode.query("fetch_users", "myapp.q.active_users", params={"limit": 100})
        >>> StepNode.expr("create_tbl", CreateTableExpression(...))
    """

    __slots__ = (
        "name",
        "label",
        "kind",
        "named_query",
        "expression",
        "subgraph",
        "params",
        "bind",
        "depends_on",
        "condition",
        "skip_for",
        "bind_output",
        "timeout_ms",
        "retry",
    )

    def __init__(
        self,
        name: str,
        label: str = "",
        kind: StepKind = StepKind.NAMED_QUERY,
        named_query: str = "",
        expression: Optional[BaseExpression] = None,
        subgraph: Optional["ProcedureGraph"] = None,
        params: Optional[Dict[str, Any]] = None,
        bind: Optional[Dict[str, Any]] = None,
        depends_on: Optional[List[str]] = None,
        condition: str = "",
        skip_for: Optional[List[str]] = None,
        bind_output: Optional[Dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
        retry: int = 0,
    ):
        self.name = name
        self.label = label or name
        self.kind = kind
        self.named_query = named_query
        self.expression = expression
        self.subgraph = subgraph
        self.params = params or {}
        self.bind = bind or {}
        self.depends_on = depends_on or []
        self.condition = condition
        self.skip_for = skip_for or []
        self.bind_output = bind_output or {}
        self.timeout_ms = timeout_ms
        self.retry = retry

    @classmethod
    def query(
        cls,
        name: str,
        named_query: str,
        params: Optional[Dict[str, Any]] = None,
        label: str = "",
        depends_on: Optional[List[str]] = None,
        condition: str = "",
        skip_for: Optional[List[str]] = None,
        bind_output: Optional[Dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
        retry: int = 0,
    ) -> "StepNode":
        """Create a NAMED_QUERY step."""
        return cls(
            name=name,
            label=label,
            kind=StepKind.NAMED_QUERY,
            named_query=named_query,
            params=params or {},
            depends_on=depends_on or [],
            condition=condition,
            skip_for=skip_for or [],
            bind_output=bind_output or {},
            timeout_ms=timeout_ms,
            retry=retry,
        )

    @classmethod
    def expr(
        cls,
        name: str,
        expression: BaseExpression,
        label: str = "",
        depends_on: Optional[List[str]] = None,
        condition: str = "",
        skip_for: Optional[List[str]] = None,
        bind_output: Optional[Dict[str, str]] = None,
        timeout_ms: Optional[int] = None,
        retry: int = 0,
    ) -> "StepNode":
        """Create an EXPRESSION step (for migrations)."""
        return cls(
            name=name,
            label=label,
            kind=StepKind.EXPRESSION,
            expression=expression,
            depends_on=depends_on or [],
            condition=condition,
            skip_for=skip_for or [],
            bind_output=bind_output or {},
            timeout_ms=timeout_ms,
            retry=retry,
        )

    @classmethod
    def sub(
        cls,
        name: str,
        subgraph: "ProcedureGraph",
        label: str = "",
        depends_on: Optional[List[str]] = None,
        condition: str = "",
        skip_for: Optional[List[str]] = None,
    ) -> "StepNode":
        """Create a SUBGRAPH step (nested graph)."""
        return cls(
            name=name,
            label=label,
            kind=StepKind.SUBGRAPH,
            subgraph=subgraph,
            depends_on=depends_on or [],
            condition=condition,
            skip_for=skip_for or [],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for diagram/CLI."""
        result = {
            "name": self.name,
            "label": self.label,
            "kind": self.kind.name,
            "depends_on": self.depends_on,
        }
        if self.kind == StepKind.NAMED_QUERY:
            result["named_query"] = self.named_query
            result["params"] = self.params
        elif self.kind == StepKind.EXPRESSION:
            result["expression_type"] = (
                type(self.expression).__name__ if self.expression else None
            )
        elif self.kind == StepKind.SUBGRAPH:
            result["subgraph_steps"] = list(self.subgraph._nodes.keys())
        if self.condition:
            result["condition"] = self.condition
        if self.skip_for:
            result["skip_for"] = self.skip_for
        return result


class ProcedureGraph:
    """Directed Acyclic Graph (DAG) of procedure steps.

    A ProcedureGraph is a pure data structure that describes a set
    of steps and their dependencies. It contains no I/O - all
    execution is done by runners.

    Attributes:
        transaction_mode: Transaction mode for execution.
        strict: Whether to reject RawSQLExpression.
        description: Human-readable description.

    Example:
        >>> graph = (
        ...     ProcedureGraph(transaction_mode=TransactionMode.AUTO)
        ...     | StepNode.query("fetch", "myapp.q.get_data")
        ...     | StepNode.query("process", "myapp.q.process",
        ...                   depends_on=["fetch"])
        ... )
        >>> waves = graph.waves()
    """

    __slots__ = (
        "_nodes",
        "_waves",
        "transaction_mode",
        "strict",
        "description",
    )

    def __init__(
        self,
        transaction_mode: TransactionMode = TransactionMode.AUTO,
        strict: bool = True,
        description: str = "",
    ):
        self._nodes: Dict[str, StepNode] = {}
        self._waves: Optional[List[List[StepNode]]] = None
        self.transaction_mode = transaction_mode
        self.strict = strict
        self.description = description

    def add(self, node: StepNode) -> "ProcedureGraph":
        """Add a step node to the graph."""
        if node.name in self._nodes:
            raise ValueError(f"Duplicate step name: {node.name!r}")
        self._nodes[node.name] = node
        self._waves = None
        return self

    def __or__(self, node: StepNode) -> "ProcedureGraph":
        """Support graph | StepNode syntax."""
        return self.add(node)

    def __getitem__(self, name: str) -> StepNode:
        """Get step by name."""
        return self._nodes[name]

    def __contains__(self, name: str) -> bool:
        """Check if step exists."""
        return name in self._nodes

    def __iter__(self):
        """Iterate over nodes."""
        return iter(self._nodes.values())

    def waves(self) -> List[List[StepNode]]:
        """Get topological waves for parallel execution.

        Returns steps grouped by wave (parallel group).
        Steps in the same wave have no interdependencies
        and can be executed in parallel.
        """
        if self._waves is None:
            self._waves = _kahn_topological_waves(self._nodes)
        return self._waves

    def validate(self) -> List[str]:
        """Validate the graph and return errors/warnings."""
        errors = []

        if not self._nodes:
            errors.append("Empty graph has no steps")
            return errors

        try:
            self.waves()
        except CyclicDependencyError as e:
            errors.append(f"Cyclic dependency: {e}")
        except ValueError as e:
            errors.append(str(e))

        for node in self._nodes.values():
            for dep in node.depends_on:
                if dep not in self._nodes:
                    errors.append(f"Step {node.name!r} depends on unknown {dep!r}")

            if self.strict and node.kind == StepKind.EXPRESSION:
                from rhosocial.activerecord.backend.expression.operators import (
                    RawSQLExpression,
                )

                if isinstance(node.expression, RawSQLExpression):
                    errors.append(
                        f"Step {node.name!r} uses RawSQLExpression (strict=True)"
                    )

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for diagram/CLI."""
        return {
            "transaction_mode": self.transaction_mode.name,
            "strict": self.strict,
            "description": self.description,
            "waves": [
                [{"name": n.name, "label": n.label, "depends_on": n.depends_on}
                 for n in wave]
                for wave in self.waves()
            ],
        }


def _interpolate_template(
    template: str,
    context: Dict[str, Any],
) -> str:
    """Interpolate ${var} placeholders in a template string."""
    pattern = r"\$\{([^}]+)\}"

    def replacer(match):
        var_name = match.group(1)
        if var_name in context:
            return str(context[var_name])
        return match.group(0)

    return re.sub(pattern, replacer, template)


def _safe_eval_condition(
    condition: str,
    context: Dict[str, Any],
) -> bool:
    """Safely evaluate a condition expression.

    Only supports:
        - ${var} template substitution
        - Comparison operators: < > <= >= == !=
        - Logical operators: and, or, not
        - Integer/float/bool literals

    Note: String comparisons are not directly supported. Use numeric/boolean
    values in conditions (e.g., version numbers, counts, flags).

    Args:
        condition: The condition expression.
        context: Variables for substitution.

    Returns:
        Boolean result of the condition.

    Raises:
        ValueError: If the expression is invalid or unsafe.
    """
    # Extract ${var} names from original condition
    pattern = r"\$\{([^}]+)\}"
    template_vars = set(re.findall(pattern, condition))

    # Check for unsafe variables in original condition
    for name in template_vars:
        if name not in context:
            raise ValueError(f"Unknown variable in condition: {name}")

    # Build local_vars for eval - include only numeric and bool values
    local_vars = {}
    for k, v in context.items():
        if isinstance(v, (int, float, bool)):
            local_vars[k] = v

    # Interpolate the condition with values
    interpolated = _interpolate_template(condition, context)

    try:
        result = eval(interpolated, {"__builtins__": {}}, local_vars)
        return bool(result)
    except Exception as e:
        raise ValueError(f"Invalid condition: {condition!r}: {e}") from e


def _extract_path(data: Any, path: str) -> Any:
    """Extract a value from nested data using path notation.

    Supports paths like:
        - "rows[0].version"
        - "data[0].items[1].name"

    Args:
        data: The data to extract from.
        path: Path notation string.

    Returns:
        The extracted value, or None if not found.
    """
    current = data
    parts = re.split(r"[\.\[\]]" + r"+", path)
    parts = [p for p in parts if p]

    for part in parts:
        if not part:
            continue
        if part.isdigit():
            idx = int(part)
            if isinstance(current, (list, tuple)) and idx < len(current):
                current = current[idx]
            else:
                return None
        elif isinstance(current, dict):
            current = current.get(part)
        else:
            attr = getattr(current, part, None)
            if attr is not None:
                current = attr
            else:
                return None

    return current


class GraphContext:
    """Runtime context for graph execution.

    Provides variable bindings, condition evaluation,
    and result binding for ProcedureGraph steps.

    Attributes:
        dialect: The SQL dialect.
        params: Initial parameters.
    """

    __slots__ = ("_dialect", "_params", "_bindings", "_trace")

    def __init__(
        self,
        dialect: "SQLDialectBase",
        params: Optional[Dict[str, Any]] = None,
    ):
        self._dialect = dialect
        self._params = params or {}
        self._bindings: Dict[str, Any] = {}
        self._trace: List[Any] = []

    @property
    def dialect(self) -> "SQLDialectBase":
        return self._dialect

    def get(self, key: str, default: Any = None) -> Any:
        """Get a variable by name."""
        return self._bindings.get(key, self._params.get(key, default))

    def bind(self, output_map: Dict[str, str], result: Any) -> None:
        """Bind result fields to variables per bind_output map."""
        for result_path, var_name in output_map.items():
            value = _extract_path(result, result_path)
            self._bindings[var_name] = value

    def eval_condition(self, condition: str) -> bool:
        """Evaluate a condition expression."""
        if not condition:
            return True
        return _safe_eval_condition(condition, {**self._params, **self._bindings})

    def interpolate(self, template: str) -> str:
        """Interpolate ${var} in a template string."""
        return _interpolate_template(template, {**self._params, **self._bindings})