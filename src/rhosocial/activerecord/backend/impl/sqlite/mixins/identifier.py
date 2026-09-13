# src/rhosocial/activerecord/backend/impl/sqlite/mixins/identifier.py
"""
SQLite-specific Identifier implementation.

This module provides the SQLiteIdentifierMixin class.
"""


class SQLiteIdentifierMixin:
    """SQLite-specific identifier and column formatting."""

    def get_parameter_placeholder(self, _position: int = 0) -> str:
        """SQLite uses '?' for placeholders."""
        return "?"


# =============================================================================
# SQLiteDateTimeMixin — datetime expression formatting
# =============================================================================

