# src/rhosocial/activerecord/backend/introspection/errors.py
"""
Database introspection error definitions.

This module provides exception classes for database introspection operations.
"""

from typing import Optional, Any


class IntrospectionError(Exception):
    """Base exception for introspection errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class IntrospectionNotSupportedError(IntrospectionError):
    """Raised when an introspection feature is not supported by the backend."""

    def __init__(self, feature: str, backend: Optional[str] = None):
        self.feature = feature
        self.backend = backend
        message = f"Introspection feature '{feature}' is not supported"
        if backend:
            message += f" by backend '{backend}'"
        super().__init__(message, {"feature": feature, "backend": backend})


class IntrospectionQueryError(IntrospectionError):
    """Raised when an introspection query fails."""

    def __init__(self, query: str, original_error: Optional[Exception] = None):
        self.query = query
        self.original_error = original_error
        message = f"Introspection query failed: {query}"
        if original_error:
            message += f" - {str(original_error)}"
        super().__init__(message, {"query": query, "original_error": str(original_error) if original_error else None})


class ObjectNotFoundError(IntrospectionError):
    """Raised when a database object is not found during introspection."""

    def __init__(self, object_type: str, object_name: str, schema: Optional[str] = None):
        self.object_type = object_type
        self.object_name = object_name
        self.schema = schema
        message = f"{object_type} '{object_name}' not found"
        if schema:
            message += f" in schema '{schema}'"
        super().__init__(message, {
            "object_type": object_type,
            "object_name": object_name,
            "schema": schema
        })


class IntrospectionCacheError(IntrospectionError):
    """Raised when there's an issue with the introspection cache."""

    def __init__(self, operation: str, details: Optional[str] = None):
        self.operation = operation
        message = f"Introspection cache error during {operation}"
        if details:
            message += f": {details}"
        super().__init__(message, {"operation": operation, "details": details})
