# src/rhosocial/activerecord/backend/named_query/__init__.py
"""
Named query support for the backend.

This module provides functionality to resolve and execute named queries
defined as Python callables (functions or classes) with fully qualified names.

What is Named Query:
    Named query is a callable (function, class instance with __call__) that:
    - Lives in a Python module
    - Has 'dialect' as its first parameter (after 'self' for classes)
    - Returns a BaseExpression object implementing Executable protocol

    Example function:
        >>> def active_users(dialect, limit: int = 100):
        ...     '''Get active users with optional limit.'''
        ...     return Select(...)

    Example class:
        >>> class UserQueries:
        ...     def __call__(self, dialect, status: str = 'active'):
        ...         '''Get users by status.'''
        ...         return Select(...)

Important Notes:
    This is a BACKEND FEATURE, independent of ActiveRecord or ActiveQuery.

    - This module is for CLI and script-based query execution
    - It is NOT part of the ActiveRecord pattern
    - It provides a way to organize reusable queries in Python modules
    - The queries return type-safe expressions, not raw SQL strings

    This design ensures:
    - SQL injection prevention through expression-based approach
    - Type safety through BaseExpression and Executable protocol
    - Query reusability across different backends via dialect abstraction

Components:
    - resolver: Main resolver class and functions
    - exceptions: All custom exception types
    - cli: CLI utilities for backend command-line tools

Usage:
    >>> from rhosocial.activerecord.backend.named_query import NamedQueryResolver
    >>> resolver = NamedQueryResolver("myapp.queries.active_users").load()
    >>> expression = resolver.execute(dialect, {"limit": 50})

    >>> # List all queries in a module
    >>> from rhosocial.activerecord.backend.named_query import list_named_queries_in_module
    >>> queries = list_named_queries_in_module("myapp.queries")
"""
from .exceptions import (
    NamedQueryError,
    NamedQueryNotFoundError,
    NamedQueryModuleNotFoundError,
    NamedQueryInvalidReturnTypeError,
    NamedQueryInvalidParameterError,
    NamedQueryMissingParameterError,
    NamedQueryNotCallableError,
    NamedQueryExplainNotAllowedError,
)
from .resolver import (
    NamedQueryResolver,
    resolve_named_query,
    list_named_queries_in_module,
    validate_expression,
)
from .cli import (
    create_named_query_parser,
    handle_named_query,
    parse_params,
)

__all__ = [
    "NamedQueryError",
    "NamedQueryNotFoundError",
    "NamedQueryModuleNotFoundError",
    "NamedQueryInvalidReturnTypeError",
    "NamedQueryInvalidParameterError",
    "NamedQueryMissingParameterError",
    "NamedQueryNotCallableError",
    "NamedQueryExplainNotAllowedError",
    "NamedQueryResolver",
    "resolve_named_query",
    "list_named_queries_in_module",
    "validate_expression",
    "create_named_query_parser",
    "handle_named_query",
    "parse_params",
]