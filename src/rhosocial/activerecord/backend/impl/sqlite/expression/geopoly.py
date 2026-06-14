# src/rhosocial/activerecord/backend/impl/sqlite/expression/geopoly.py
"""
SQLite-specific Geopoly expression classes.

This module provides expression classes for Geopoly polygon geometry operations,
including virtual table creation, point-in-polygon queries, and area calculations.
"""

from typing import List, Optional, TYPE_CHECKING

from ....expression.bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase


class SQLiteGeopolyCreateVirtualTable(BaseExpression):
    """Geopoly CREATE VIRTUAL TABLE statement expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        content_table: Optional[str] = None,
        extra_columns: Optional[List[str]] = None,
    ):
        super().__init__(dialect)
        self.table_name = table_name
        self.content_table = content_table
        self.extra_columns = extra_columns or []

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_geopoly_create_virtual_table(self)


class SQLiteGeopolyContainsExpression(BaseExpression):
    """Geopoly point-in-polygon query expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
        longitude: float,
        latitude: float,
    ):
        super().__init__(dialect)
        self.table_name = table_name
        self.longitude = longitude
        self.latitude = latitude

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_geopoly_contains_query(self)


class SQLiteGeopolyAreaExpression(BaseExpression):
    """Geopoly area calculation expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table_name: str,
    ):
        super().__init__(dialect)
        self.table_name = table_name

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_geopoly_area_expression(self)
