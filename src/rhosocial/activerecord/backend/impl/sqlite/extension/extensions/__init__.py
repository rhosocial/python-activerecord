# src/rhosocial/activerecord/backend/impl/sqlite/extension/extensions/__init__.py
"""
SQLite extension implementations.

This module provides concrete implementations for various SQLite extensions.
"""

from .fts5 import FTS5Extension, get_fts5_extension
from .fts3_4 import FTS3Extension, FTS4Extension, get_fts3_extension, get_fts4_extension
from .json1 import JSON1Extension, get_json1_extension
from .rtree import RTreeExtension, get_rtree_extension
from .geopoly import GeopolyExtension, get_geopoly_extension


__all__ = [
    # FTS5
    "FTS5Extension",
    "get_fts5_extension",
    # FTS3/FTS4
    "FTS3Extension",
    "FTS4Extension",
    "get_fts3_extension",
    "get_fts4_extension",
    # JSON1
    "JSON1Extension",
    "get_json1_extension",
    # R-Tree
    "RTreeExtension",
    "get_rtree_extension",
    # Geopoly
    "GeopolyExtension",
    "get_geopoly_extension",
]
