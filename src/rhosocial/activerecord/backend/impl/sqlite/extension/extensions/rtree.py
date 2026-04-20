# src/rhosocial/activerecord/backend/impl/sqlite/extension/extensions/rtree.py
"""
SQLite R-Tree extension implementation.

The R-Tree extension provides a virtual table implementation for
spatial indexing, enabling efficient range queries on multi-dimensional
data such as geographic coordinates.

Available since SQLite 3.6.0 (2008-07-16).

Reference: https://www.sqlite.org/rtree.html
"""

from typing import List, Optional, Tuple

from ..base import ExtensionType, SQLiteExtensionBase


class RTreeExtension(SQLiteExtensionBase):
    """R-Tree (spatial index) extension.

    The R-Tree extension provides efficient spatial indexing for
    multi-dimensional data. It is commonly used for:
        - Geographic data (latitude/longitude)
        - Range queries
        - Nearest neighbor searches
        - Spatial joins

    Features:
        - R-Tree virtual tables for spatial indexing
        - Range queries for multi-dimensional data
        - Auxiliary functions (distance, area)
        - Integrity check functionality

    Example:
        >>> rtree = RTreeExtension()
        >>> rtree.is_available((3, 6, 0))
        True
    """

    def __init__(self):
        """Initialize R-Tree extension."""
        super().__init__(
            name="rtree",
            extension_type=ExtensionType.VTABLE,
            min_version=(3, 6, 0),
            deprecated=False,
            description="R-Tree spatial index - Efficient range queries for multi-dimensional data",
            features={
                "rtree_index": {"min_version": (3, 6, 0)},
                "rtree_query": {"min_version": (3, 8, 5)},
                "rtree_integrity_check": {"min_version": (3, 24, 0)},
                "rtree_auxiliary_functions": {"min_version": (3, 25, 0)},
            },
            documentation_url="https://www.sqlite.org/rtree.html",
        )

    def format_create_virtual_table(
        self,
        table_name: str,
        dimensions: int = 2,
        content_table: Optional[str] = None,
        content_rowid: Optional[str] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE statement for R-Tree.

        Args:
            table_name: Name of the R-Tree virtual table
            dimensions: Number of dimensions (default 2)
            content_table: Optional content table for data storage
            content_rowid: Optional column name for rowid in content table

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        cols = ["id"]  # R-Tree requires id as first column
        for i in range(dimensions):
            cols.extend([f"min{i}", f"max{i}"])

        if content_table:
            if content_rowid:
                sql = (
                    f'CREATE VIRTUAL TABLE "{table_name}" USING rtree'
                    f'({", ".join(cols)}, content="{content_table}", content_rowid="{content_rowid}")'
                )
            else:
                sql = f'CREATE VIRTUAL TABLE "{table_name}" USING rtree({", ".join(cols)}, content="{content_table}")'
        else:
            sql = f'CREATE VIRTUAL TABLE "{table_name}" USING rtree({", ".join(cols)})'

        return sql, ()

    def format_range_query(
        self,
        table_name: str,
        ranges: List[Tuple[float, float]],
        column_names: Optional[List[str]] = None,
    ) -> Tuple[str, tuple]:
        """Format range query for R-Tree table.

        Args:
            table_name: Name of the R-Tree virtual table
            ranges: List of (min, max) tuples for each dimension
            column_names: Optional column names (default: min0, max0, min1, max1, ...)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if column_names is None:
            conditions = []
            params = []
            for i, (min_val, max_val) in enumerate(ranges):
                conditions.append(f'"{table_name}".min{i} >= ? AND "{table_name}".max{i} <= ?')
                params.extend([min_val, max_val])
        else:
            conditions = []
            params = []
            for (min_val, max_val), col in zip(ranges, column_names):
                conditions.append(f'"{col}" >= ? AND "{col}" <= ?')
                params.extend([min_val, max_val])

        sql = f'SELECT * FROM "{table_name}" WHERE {" AND ".join(conditions)}'
        return sql, tuple(params)

    def format_drop_virtual_table(
        self,
        table_name: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """Format DROP TABLE statement for R-Tree virtual table.

        Args:
            table_name: Name of the R-Tree virtual table to drop
            if_exists: If True, add IF EXISTS clause

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if if_exists:
            sql = f'DROP TABLE IF EXISTS "{table_name}"'
        else:
            sql = f'DROP TABLE "{table_name}"'
        return sql, ()


# Singleton instance
_rtree_extension: Optional[RTreeExtension] = None


def get_rtree_extension() -> RTreeExtension:
    """Get the R-Tree extension singleton.

    Returns:
        RTreeExtension instance
    """
    global _rtree_extension
    if _rtree_extension is None:
        _rtree_extension = RTreeExtension()
    return _rtree_extension
