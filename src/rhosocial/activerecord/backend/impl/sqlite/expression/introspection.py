# src/rhosocial/activerecord/backend/impl/sqlite/expression/introspection.py
"""
SQLite-specific column info expression.

This module provides SQLiteColumnInfoExpression which extends the base
ColumnInfoExpression with SQLite-specific parameters.
"""

from typing import Optional, TYPE_CHECKING

from ....expression.introspection import ColumnInfoExpression
from ....expression.bases import SQLQueryAndParams

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase


class SQLiteColumnInfoExpression(ColumnInfoExpression):
    """SQLite column information expression.

    Extends ColumnInfoExpression with SQLite-specific parameters.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        table_name: The name of the table to query columns for.
        schema: Optional schema name. Defaults to None.
        include_hidden: Whether to include hidden columns. Defaults to False.
        use_xinfo_pragma: Whether to use PRAGMA table_xinfo instead of table_info.
            PRAGMA table_xinfo includes hidden columns and is available in SQLite 3.26.0+.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        schema: Optional[str] = None,
        include_hidden: bool = False,
        use_xinfo_pragma: bool = False,
    ):
        super().__init__(dialect, table_name, schema, include_hidden)
        self.use_xinfo_pragma = use_xinfo_pragma

    def get_params(self) -> dict:
        params = super().get_params()
        params["use_xinfo_pragma"] = self.use_xinfo_pragma
        return params