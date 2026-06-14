# src/rhosocial/activerecord/backend/impl/sqlite/extension/extensions/geopoly.py
"""
SQLite Geopoly extension implementation.

The Geopoly extension provides a virtual table for polygon geometry
operations. This class provides metadata and version detection only.
SQL generation has been moved to SQLiteGeopolyMixin.

Reference: https://www.sqlite.org/geopoly.html
"""

from ..base import ExtensionType, SQLiteExtensionBase


class GeopolyExtension(SQLiteExtensionBase):
    """Geopoly (polygon geometry) extension.

    Provides metadata and version detection for Geopoly.
    SQL generation is handled by SQLiteGeopolyMixin.

    Example:
        >>> geopoly = GeopolyExtension()
        >>> geopoly.is_available((3, 26, 0))
        True
    """

    def __init__(self):
        """Initialize Geopoly extension."""
        super().__init__(
            name="geopoly",
            extension_type=ExtensionType.VTABLE,
            min_version=(3, 26, 0),
            deprecated=False,
            description="Geopoly - 2D polygon geometry operations",
            features={
                "polygon_operations": {"min_version": (3, 26, 0)},
                "polygon_contains": {"min_version": (3, 26, 0)},
                "polygon_within": {"min_version": (3, 26, 0)},
                "polygon_overlap": {"min_version": (3, 26, 0)},
                "polygon_area": {"min_version": (3, 26, 0)},
                "polygon_json": {"min_version": (3, 26, 0)},
            },
            documentation_url="https://www.sqlite.org/geopoly.html",
        )


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
