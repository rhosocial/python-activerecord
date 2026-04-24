# src/rhosocial/activerecord/backend/named_connection/__init__.py
"""
Named connection support for the backend.

This module provides functionality to resolve and execute named connections
defined as Python callables (functions or classes) with fully qualified names.

What is Named Connection:
    Named connection is a callable (function, class instance with __call__) that:
    - Lives in a Python module
    - Returns a ConnectionConfig (BaseConfig subclass) object

    Example function:
        >>> def production_db(pool_size: int = 10):
        ...     '''Get production database configuration.'''
        ...     return MySQLConnectionConfig(host="prod.example.com", pool_size=pool_size)

    Example class:
        >>> class ConnectionFactory:
        ...     def __call__(self, pool_size: int = 10):
        ...         '''Get production database configuration.'''
        ...         return MySQLConnectionConfig(host="prod.example.com", pool_size=pool_size)

Important Notes:
    This is a BACKEND FEATURE, independent of ActiveRecord or ActiveQuery.

    - Named connections are used to externalize database connection configuration
    - They allow configuration to be defined in Python modules with full IDE support
    - Configuration can be versioned and tracked alongside code
    - Sensitive fields (password, secret, etc.) are filtered in describe() output

Components:
    - resolver: Main resolver class and functions
    - exceptions: All custom exception types
    - validators: Validation functions for config objects

Usage:
    >>> from rhosocial.activerecord.backend.named_connection import NamedConnectionResolver
    >>> resolver = NamedConnectionResolver("myapp.connections.prod_db").load()
    >>> config = resolver.resolve({"pool_size": 20})

    >>> # List all connections in a module
    >>> from rhosocial.activerecord.backend.named_connection import list_named_connections_in_module
    >>> connections = list_named_connections_in_module("myapp.connections")

    >>> # Convenience function
    >>> from rhosocial.activerecord.backend.named_connection import resolve_named_connection
    >>> config = resolve_named_connection("myapp.connections.prod_db", {"pool_size": 20})
"""
from .exceptions import (
    NamedConnectionError,
    NamedConnectionNotFoundError,
    NamedConnectionModuleNotFoundError,
    NamedConnectionInvalidReturnTypeError,
    NamedConnectionInvalidParameterError,
    NamedConnectionMissingParameterError,
    NamedConnectionNotCallableError,
)
from .validators import (
    validate_connection_config,
    filter_sensitive_fields,
)
from .resolver import (
    NamedConnectionResolver,
    resolve_named_connection,
    list_named_connections_in_module,
)
from .cli import (
    create_named_connection_parser,
    handle_named_connection,
    resolve_connection_config,
    parse_params,
)

__all__ = [
    "NamedConnectionError",
    "NamedConnectionNotFoundError",
    "NamedConnectionModuleNotFoundError",
    "NamedConnectionInvalidReturnTypeError",
    "NamedConnectionInvalidParameterError",
    "NamedConnectionMissingParameterError",
    "NamedConnectionNotCallableError",
    "NamedConnectionResolver",
    "resolve_named_connection",
    "list_named_connections_in_module",
    "validate_connection_config",
    "filter_sensitive_fields",
    "create_named_connection_parser",
    "handle_named_connection",
    "resolve_connection_config",
    "parse_params",
]
