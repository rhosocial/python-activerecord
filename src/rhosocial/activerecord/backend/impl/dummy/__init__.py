# src/rhosocial/activerecord/backend/impl/dummy/__init__.py
"""
Dummy backend implementation for SQL generation testing.

This module provides a dummy backend and dialect that can generate SQL
without connecting to a real database. It's primarily used for testing
the expression building and SQL generation capabilities of the ActiveRecord system.
"""

from .backend import DummyBackend, AsyncDummyBackend
from .dialect import DummyDialect

__all__ = [
    'DummyBackend',
    'AsyncDummyBackend',
    'DummyDialect',
]