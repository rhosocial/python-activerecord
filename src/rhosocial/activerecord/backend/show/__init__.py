# src/rhosocial/activerecord/backend/show/__init__.py
"""
Backend SHOW functionality support.

This module provides the base classes and mixins for implementing
database-specific SHOW functionality. SHOW commands are MySQL-specific,
but the architecture allows for similar functionality in other databases.

The module provides:
- ShowMixin: Backend mixin for show() method
- AsyncShowMixin: Async version of the mixin
- ShowFunctionality: Base class for SHOW functionality
- AsyncShowFunctionality: Async version of ShowFunctionality
"""

from .mixins import ShowMixin, AsyncShowMixin
from .functionality import ShowFunctionality, AsyncShowFunctionality

__all__ = [
    "ShowMixin",
    "AsyncShowMixin",
    "ShowFunctionality",
    "AsyncShowFunctionality",
]
