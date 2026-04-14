# src/rhosocial/activerecord/backend/impl/sqlite/expression/table_list.py
"""
SQLite-specific table list expression.

This module provides SQLiteTableListExpression which extends the base
TableListExpression with SQLite-specific parameters.
"""

from dataclasses import dataclass

from ....expression.introspection import TableListExpression


@dataclass
class SQLiteTableListExpression(TableListExpression):
    """SQLite table list expression.

    Extends TableListExpression with SQLite-specific parameters.

    Attributes:
        use_table_list_pragma: Whether to use PRAGMA table_list instead of
        querying sqlite_master. PRAGMA table_list is available in SQLite 3.37.0+.
    """

    use_table_list_pragma: bool = False

    def __post_init__(self):
        """Populate params dictionary after initialization."""
        super().__post_init__()
        self._params["use_table_list_pragma"] = self.use_table_list_pragma