# src/rhosocial/activerecord/backend/impl/sqlite/extension/extensions/rtree.py
"""
SQLite R-Tree extension implementation.

The R-Tree extension provides a virtual table implementation for
spatial indexing. This class provides metadata and version detection only.
SQL generation has been moved to SQLiteRTreeMixin.

Reference: https://www.sqlite.org/rtree.html
"""

from ..base import ExtensionType, SQLiteExtensionBase


class RTreeExtension(SQLiteExtensionBase):
    """R-Tree (spatial index) extension.

    Provides metadata and version detection for R-Tree.
    SQL generation is handled by SQLiteRTreeMixin.

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
