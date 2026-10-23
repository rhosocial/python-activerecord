# src/rhosocial/activerecord/backend/impl/sqlite/expression/geopoly.py
"""
SQLite-specific Geopoly expression classes.

This module provides expression classes for Geopoly polygon geometry operations,
including virtual table creation, point-in-polygon queries, and area calculations.
"""

from typing import List, Optional, TYPE_CHECKING

from ....expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import Table

if TYPE_CHECKING:
    from ....dialect import SQLDialectBase


class SQLiteGeopolyCreateVirtualTable(BaseExpression):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression."""
        return "format_geopoly_create_virtual_table"
    """Geopoly CREATE VIRTUAL TABLE statement expression.

    Geopoly has no external content table: the polygons are the rows of the
    table itself, and ``extra_columns`` hold the caller's own auxiliary
    data. So there is no content table to name, and no parameter for one.
    """

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        extra_columns: Optional[List[str]] = None,
    ):
        super().__init__(dialect)
        if not isinstance(table, Table):
            raise TypeError(
                f"table must be a Table, "
                f"got {type(table).__name__}"
            )
        self.table = table
        self.extra_columns = extra_columns or []
class SQLiteGeopolyContainsExpression(BaseExpression):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression."""
        return "format_geopoly_contains_expression"
    """Geopoly point-in-polygon query expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
        longitude: float,
        latitude: float,
    ):
        super().__init__(dialect)
        if not isinstance(table, Table):
            raise TypeError(
                f"table must be a Table, "
                f"got {type(table).__name__}"
            )
        self.table = table
        self.longitude = longitude
        self.latitude = latitude
class SQLiteGeopolyAreaExpression(BaseExpression):

    @property
    def format_method(self) -> str:
        """The dialect method that renders this expression."""
        return "format_geopoly_area_expression"
    """Geopoly area calculation expression."""

    def __init__(
        self,
        dialect: "SQLDialectBase",
        table: "Table",
    ):
        super().__init__(dialect)
        if not isinstance(table, Table):
            raise TypeError(
                f"table must be a Table, "
                f"got {type(table).__name__}"
            )
        self.table = table
