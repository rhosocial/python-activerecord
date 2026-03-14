# src/rhosocial/activerecord/backend/impl/sqlite/extension/__init__.py
"""
SQLite extension framework.

This module provides a comprehensive framework for SQLite extension support,
including extension detection, version management, and feature queries.
"""
from .base import (
    ExtensionType,
    SQLiteExtensionInfo,
    SQLiteExtensionProtocol,
    SQLiteExtensionBase,
    SQLiteExtensionSupport,
)
from .registry import (
    KNOWN_EXTENSIONS,
    SQLiteExtensionRegistry,
    get_registry,
    reset_registry,
)


__all__ = [
    # Base classes and types
    'ExtensionType',
    'SQLiteExtensionInfo',
    'SQLiteExtensionProtocol',
    'SQLiteExtensionBase',
    'SQLiteExtensionSupport',
    # Registry
    'KNOWN_EXTENSIONS',
    'SQLiteExtensionRegistry',
    'get_registry',
    'reset_registry',
]
