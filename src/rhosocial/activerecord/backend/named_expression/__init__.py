# src/rhosocial/activerecord/backend/named_expression/__init__.py
"""
Named expression support for the backend.

This module provides functionality to resolve and execute named expressions
defined as Python callables (functions or classes) with fully qualified names.

What is Named Expression:
    Named expression is a callable (function, class instance with __call__) that:
    - Lives in a Python module
    - Has 'dialect' as its first parameter (after 'self' for classes)
    - Returns a BaseExpression object

    Example function:
        >>> def active_users(dialect, limit: int = 100):
        ...     '''Get active users with optional limit.'''
        ...     return QueryExpression(...)

    Example class:
        >>> class UserQueries:
        ...     def __call__(self, dialect, status: str = 'active'):
        ...         '''Get users by status.'''
        ...         return QueryExpression(...)

Important Notes:
    This is a BACKEND FEATURE, independent of ActiveRecord or ActiveQuery.

    - This module is for CLI and script-based expression execution
    - It is NOT part of the ActiveRecord pattern
    - It provides a way to organize reusable expressions in Python modules
    - The expressions return type-safe expressions, not raw SQL strings

    This design ensures:
    - SQL injection prevention through expression-based approach
    - Type safety through BaseExpression
    - Expression reusability across different backends via dialect abstraction

Components:
    - resolver: Main resolver class and functions
    - exceptions: All custom exception types
    - cli: CLI utilities for backend command-line tools

Usage:
    >>> from rhosocial.activerecord.backend.named_expression import NamedExpressionResolver
    >>> resolver = NamedExpressionResolver("myapp.queries.active_users").load()
    >>> expression = resolver.execute(dialect, {"limit": 50})

    >>> # List all expressions in a module
    >>> from rhosocial.activerecord.backend.named_expression import list_named_expressions_in_module
    >>> expressions = list_named_expressions_in_module("myapp.queries")
"""
from .exceptions import (
    NamedExpressionError,
    NamedExpressionNotFoundError,
    NamedExpressionModuleNotFoundError,
    NamedExpressionInvalidReturnTypeError,
    NamedExpressionInvalidParameterError,
    NamedExpressionMissingParameterError,
    NamedExpressionNotCallableError,
    NamedExpressionExplainNotAllowedError,
    ProcedureError,
    ProcedureAbortedError,
    ProcedureStepError,
    ProcedureGraphError,
    ProcedureGraphValidationError,
)
from .resolver import (
    NamedExpressionResolver,
    resolve_named_expression,
    list_named_expressions_in_module,
)
from .cli import (
    create_named_expression_parser,
    handle_named_expression,
    parse_params,
)
from .cli_procedure import (
    create_named_procedure_parser,
    handle_named_procedure,
    list_named_procedures_in_module,
)
from .procedure import (
    Procedure,
    ProcedureContext,
    ProcedureRunner,
    ProcedureResult,
    ParallelStep,
    TransactionMode,
    LogEntry,
    AsyncProcedure,
    AsyncProcedureContext,
    AsyncProcedureRunner,
    StepKind,
    TraceEntry,
)
from .diagram import ProcedureDiagram
from .procedure_graph import (
    ProcedureGraph,
    StepNode,
    StepKind as GraphStepKind,
    TransactionMode as GraphTransactionMode,
    GraphContext,
    CyclicDependencyError,
)
from .graph_result import (
    ProcedureGraphResult,
    StepTraceEntry,
    StepStatus,
)
from .graph_runner import (
    ProcedureGraphRunner,
    AsyncProcedureGraphRunner,
    ProcedureGraphValidationError as GraphValidationError,
)
from .graph_resolver import (
    NamedProcedureGraphResolver,
    NamedProcedureGraphError,
    NamedProcedureGraphInvalidReturnTypeError,
    resolve_named_procedure_graph,
    list_procedure_graphs_in_module,
)

__all__ = [
    "NamedExpressionError",
    "NamedExpressionNotFoundError",
    "NamedExpressionModuleNotFoundError",
    "NamedExpressionInvalidReturnTypeError",
    "NamedExpressionInvalidParameterError",
    "NamedExpressionMissingParameterError",
    "NamedExpressionNotCallableError",
    "NamedExpressionExplainNotAllowedError",
    "NamedExpressionResolver",
    "resolve_named_expression",
    "list_named_expressions_in_module",
    "create_named_expression_parser",
    "handle_named_expression",
    "parse_params",
    "create_named_procedure_parser",
    "handle_named_procedure",
    "list_named_procedures_in_module",
    "Procedure",
    "ProcedureContext",
    "ProcedureRunner",
    "ProcedureResult",
    "ParallelStep",
    "TransactionMode",
    "LogEntry",
    "AsyncProcedure",
    "AsyncProcedureContext",
    "AsyncProcedureRunner",
    "StepKind",
    "TraceEntry",
    "ProcedureDiagram",
    "ProcedureError",
    "ProcedureAbortedError",
    "ProcedureStepError",
    "ProcedureGraph",
    "StepNode",
    "GraphStepKind",
    "GraphTransactionMode",
    "GraphContext",
    "CyclicDependencyError",
    "ProcedureGraphResult",
    "StepTraceEntry",
    "StepStatus",
    "ProcedureGraphRunner",
    "AsyncProcedureGraphRunner",
    "NamedProcedureGraphResolver",
    "NamedProcedureGraphError",
    "NamedProcedureGraphInvalidReturnTypeError",
    "resolve_named_procedure_graph",
    "list_procedure_graphs_in_module",
    "ProcedureGraphValidationError",
]
