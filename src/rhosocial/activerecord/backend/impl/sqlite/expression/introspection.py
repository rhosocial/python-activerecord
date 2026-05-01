# src/rhosocial/activerecord/backend/impl/sqlite/expression/introspection.py
"""
SQLite-specific column info expression.

This module provides SQLiteColumnInfoExpression which extends the base
ColumnInfoExpression with SQLite-specific parameters.
"""

from dataclasses import dataclass

from ....expression.introspection import ColumnInfoExpression


@dataclass
class SQLiteColumnInfoExpression(ColumnInfoExpression):
    """SQLite column information expression.

    Extends ColumnInfoExpression with SQLite-specific parameters.

    Attributes:
        use_xinfo_pragma: Whether to use PRAGMA table_xinfo instead of table_info.
        PRAGMA table_xinfo includes hidden columns and is available in SQLite 3.26.0+.
    """

    use_xinfo_pragma: bool = False

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        if not hasattr(self, '_params'):
            self._params = {}
        self._params["use_xinfo_pragma"] = self.use_xinfo_pragma