# src/rhosocial/activerecord/backend/named_query/__init__.py
"""
Named query support for the backend.

This module provides functionality to resolve and execute named queries
defined as Python callables (functions or classes) with fully qualified names.
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
    guess_statement_type,
)
from .cli import (
    create_named_query_parser,
    handle_named_query,
    parse_params,
    guess_statement_type as cli_guess_statement_type,
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
    "guess_statement_type",
    "create_named_query_parser",
    "handle_named_query",
    "parse_params",
]