# src/rhosocial/activerecord/backend/impl/sqlite/expressions.py
"""
SQLite-specific introspection expressions.

This module defines SQLite-specific expression classes that extend the
base introspection expressions with SQLite-specific parameters.
"""

from dataclasses import dataclass

from ...introspection.expressions import (
    ColumnInfoExpression,
    TableListExpression,
)


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
        super().__post_init__()
        self._params["use_xinfo_pragma"] = self.use_xinfo_pragma


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
