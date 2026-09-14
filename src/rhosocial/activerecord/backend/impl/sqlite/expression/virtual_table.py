# src/rhosocial/activerecord/backend/impl/sqlite/expression/virtual_table.py
"""
SQLite-specific virtual table expression classes.

This module provides expression classes for CREATE/DROP virtual table operations.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ....expression.bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase


class CreateVirtualTableExpression(BaseExpression):
    """Expression for CREATE VIRTUAL TABLE statement."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        module: str,
        table_name: str,
        columns: List[str],
        options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(dialect)
        self.module = module
        self.table_name = table_name
        self.columns = columns
        self.options = options

    @property
    def format_method(self) -> str:
        return "format_create_virtual_table"

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_create_virtual_table(self)


class DropVirtualTableExpression(BaseExpression):
    """Expression for DROP TABLE statement targeting a virtual table."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        if_exists: bool = False,
    ):
        super().__init__(dialect)
        self.table_name = table_name
        self.if_exists = if_exists

    @property
    def format_method(self) -> str:
        return "format_drop_virtual_table"

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_drop_virtual_table(self)
