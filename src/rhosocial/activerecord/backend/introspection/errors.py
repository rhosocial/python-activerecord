# src/rhosocial/activerecord/backend/introspection/errors.py
"""
Introspection-related exceptions.

This module defines exceptions specific to database introspection operations.
"""

from typing import Optional
from rhosocial.activerecord.backend.errors import DatabaseError


class IntrospectionError(DatabaseError):
    """Base exception for introspection operations."""

    def __init__(self, message: str, backend: Optional[str] = None):
        self.backend = backend
        super().__init__(message)


class IntrospectionNotSupportedError(IntrospectionError):
    """Raised when the backend does not support the specified introspection operation."""

    def __init__(self, backend: str, scope: str):
        message = f"'{backend}' does not support introspection scope: {scope}"
        super().__init__(message, backend)
        self.scope = scope


class IntrospectionQueryError(IntrospectionError):
    """Raised when an introspection query fails to execute."""

    def __init__(self, message: str, query: Optional[str] = None,
                 backend: Optional[str] = None):
        self.query = query
        super().__init__(message, backend)


class ObjectNotFoundError(IntrospectionError):
    """Raised when an introspection target object is not found."""

    def __init__(self, object_type: str, object_name: str,
                 schema: Optional[str] = None):
        self.object_type = object_type
        self.object_name = object_name
        self.schema = schema

        full_name = f"{schema}.{object_name}" if schema else object_name
        message = f"{object_type} '{full_name}' not found"
        super().__init__(message)


class IntrospectionCacheError(IntrospectionError):
    """Raised when there is an issue with the introspection cache."""

    def __init__(self, message: str, operation: str):
        self.operation = operation
        super().__init__(message)
