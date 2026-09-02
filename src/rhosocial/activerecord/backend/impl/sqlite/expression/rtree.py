# src/rhosocial/activerecord/backend/impl/sqlite/expression/rtree.py
"""
SQLite-specific R-Tree expression classes.

This module provides expression classes for R-Tree spatial index operations,
including virtual table creation and range queries.
"""

from typing import List, Optional, Tuple, TYPE_CHECKING

from ....expression.bases import BaseExpression, SQLQueryAndParams

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase


class SQLiteRTreeCreateVirtualTable(BaseExpression):
    """R-Tree CREATE VIRTUAL TABLE statement expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: str,
        dimensions: int = 2,
        content_table: Optional[str] = None,
        content_rowid: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.table = table
        self.dimensions = dimensions
        self.content_table = content_table
        self.content_rowid = content_rowid

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_rtree_create_virtual_table(self)


class SQLiteRTreeRangeQuery(BaseExpression):
    """R-Tree range query expression for spatial filtering in WHERE clauses."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: str,
        ranges: List[Tuple[float, float]],
        column_names: Optional[List[Tuple[str, str]]] = None,
    ):
        super().__init__(dialect)
        self.table = table
        self.ranges = ranges
        self.column_names = column_names

    def to_sql(self) -> SQLQueryAndParams:
        return self.dialect.format_rtree_range_query(self)
