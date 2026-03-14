# src/rhosocial/activerecord/backend/impl/sqlite/extension/extensions/geopoly.py
"""
SQLite Geopoly extension implementation.

The Geopoly extension provides a virtual table for polygon geometry
operations, built on top of the R-Tree extension. It supports
operations like point-in-polygon tests and polygon overlap checks.

Available since SQLite 3.26.0 (2018-12-01).

Reference: https://www.sqlite.org/geopoly.html
"""
from typing import Optional, Tuple, List

from ..base import ExtensionType, SQLiteExtensionBase


class GeopolyExtension(SQLiteExtensionBase):
    """Geopoly (polygon geometry) extension.
    
    The Geopoly extension provides polygon-based geometry operations
    for SQLite. It is particularly useful for:
        - Point-in-polygon tests
        - Polygon containment checks
        - Polygon overlap detection
        - Area calculations
    
    Features:
        - Polygon operations with JSON representation
        - geopoly_contains() for point-in-polygon
        - geopoly_within() for polygon containment
        - geopoly_overlap() for overlap detection
        - geopoly_area() for area calculation
    
    Note:
        Requires R-Tree extension to be available.
    
    Example:
        >>> geopoly = GeopolyExtension()
        >>> geopoly.is_available((3, 26, 0))
        True
    """
    
    def __init__(self):
        """Initialize Geopoly extension."""
        super().__init__(
            name='geopoly',
            extension_type=ExtensionType.VTABLE,
            min_version=(3, 26, 0),
            deprecated=False,
            description='Geopoly - 2D polygon geometry operations',
            features={
                'polygon_operations': {'min_version': (3, 26, 0)},
                'polygon_contains': {'min_version': (3, 26, 0)},
                'polygon_within': {'min_version': (3, 26, 0)},
                'polygon_overlap': {'min_version': (3, 26, 0)},
                'polygon_area': {'min_version': (3, 26, 0)},
                'polygon_json': {'min_version': (3, 26, 0)},
            },
            documentation_url='https://www.sqlite.org/geopoly.html'
        )
    
    def format_create_virtual_table(
        self,
        table_name: str,
        content_table: Optional[str] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE statement for Geopoly.
        
        Args:
            table_name: Name of the Geopoly virtual table
            content_table: Optional content table for data storage
            
        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if content_table:
            sql = f'CREATE VIRTUAL TABLE "{table_name}" USING geopoly(content="{content_table}")'
        else:
            sql = f'CREATE VIRTUAL TABLE "{table_name}" USING geopoly()'
        
        return sql, ()
    
    def format_contains_query(
        self,
        table_name: str,
        longitude: float,
        latitude: float,
    ) -> Tuple[str, tuple]:
        """Format point-in-polygon query.
        
        Args:
            table_name: Name of the Geopoly virtual table
            longitude: Longitude coordinate
            latitude: Latitude coordinate
            
        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        sql = f'SELECT * FROM "{table_name}" WHERE geopoly_contains(_shape, ?)'
        return sql, (f'[{longitude}, {latitude}]',)
    
    def format_area_query(
        self,
        table_name: str,
    ) -> Tuple[str, tuple]:
        """Format area calculation query.
        
        Args:
            table_name: Name of the Geopoly virtual table
            
        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        sql = f'SELECT *, geopoly_area(_shape) as area FROM "{table_name}"'
        return sql, ()
    
    def format_drop_virtual_table(
        self,
        table_name: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """Format DROP TABLE statement for Geopoly virtual table.
        
        Args:
            table_name: Name of the Geopoly virtual table to drop
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
_geopoly_extension: Optional[GeopolyExtension] = None


def get_geopoly_extension() -> GeopolyExtension:
    """Get the Geopoly extension singleton.
    
    Returns:
        GeopolyExtension instance
    """
    global _geopoly_extension
    if _geopoly_extension is None:
        _geopoly_extension = GeopolyExtension()
    return _geopoly_extension
