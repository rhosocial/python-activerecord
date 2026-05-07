# src/rhosocial/activerecord/backend/impl/sqlite/expression/table_list.py
"""
SQLite-specific table list expression.

This module provides SQLiteTableListExpression which extends the base
TableListExpression with SQLite-specific parameters.
"""

from typing import Optional, TYPE_CHECKING

from ....expression.introspection import TableListExpression

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase


class SQLiteTableListExpression(TableListExpression):
    """SQLite table list expression.

    Extends TableListExpression with SQLite-specific parameters.

    Args:
        dialect: The SQL dialect to use for SQL generation.
        schema: Optional schema name. Defaults to None.
        include_views: Whether to include views in the result. Defaults to True.
        include_system: Whether to include system tables. Defaults to False.
        table_type: Optional table type filter. Defaults to None.
        use_table_list_pragma: Whether to use PRAGMA table_list instead of
            querying sqlite_master. PRAGMA table_list is available in SQLite 3.37.0+.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        schema: Optional[str] = None,
        include_views: bool = True,
        include_system: bool = False,
        table_type: Optional[str] = None,
        use_table_list_pragma: bool = False,
    ):
        super().__init__(dialect, schema, include_views, include_system, table_type)
        self.use_table_list_pragma = use_table_list_pragma

    def get_params(self) -> dict:
        params = super().get_params()
        params["use_table_list_pragma"] = self.use_table_list_pragma
        return params