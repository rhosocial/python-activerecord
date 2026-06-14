# src/rhosocial/activerecord/backend/impl/sqlite/mixins/extension.py
"""
SQLite-specific Extension implementation.

This module provides the SQLiteExtensionMixin class for runtime
extension capability detection, using version checks and compile options
instead of a separate extension registry.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ExtensionType(Enum):
    """Type of SQLite extension."""
    BUILTIN = "builtin"
    LOADABLE = "loadable"
    VTABLE = "vtable"


@dataclass
class SQLiteExtensionInfo:
    """Information about a specific SQLite extension."""
    name: str
    extension_type: ExtensionType
    installed: bool
    min_version: Tuple[int, int, int]
    deprecated: bool = False
    successor: Optional[str] = None
    description: str = ""
    features: List[str] = field(default_factory=list)


_EXTENSION_METADATA: Dict[str, Dict[str, Any]] = {
    "fts5": {
        "type": ExtensionType.BUILTIN,
        "min_version": (3, 9, 0),
        "description": "Full-Text Search version 5 - Advanced full-text search with customizable tokenizers",
        "features": {
            "full_text_search": (3, 9, 0),
            "bm25_ranking": (3, 9, 0),
            "highlight": (3, 9, 0),
            "snippet": (3, 9, 0),
            "offset": (3, 9, 0),
            "porter_tokenizer": (3, 9, 0),
            "unicode61_tokenizer": (3, 9, 0),
            "trigram_tokenizer": (3, 34, 0),
            "column_filters": (3, 9, 0),
            "phrase_queries": (3, 9, 0),
            "near_queries": (3, 9, 0),
        },
    },
    "fts4": {
        "type": ExtensionType.BUILTIN,
        "min_version": (3, 7, 4),
        "deprecated": True,
        "successor": "fts5",
        "description": "Full-Text Search version 4 (legacy) - Predecessor to FTS5",
        "features": {
            "full_text_search": (3, 7, 4),
            "matchinfo": (3, 7, 4),
            "offsets": (3, 7, 4),
            "snippet": (3, 7, 4),
            "prefix_queries": (3, 7, 4),
        },
    },
    "fts3": {
        "type": ExtensionType.BUILTIN,
        "min_version": (3, 7, 4),
        "deprecated": True,
        "successor": "fts5",
        "description": "Full-Text Search version 3 (legacy) - Predecessor to FTS5",
        "features": {
            "full_text_search": (3, 7, 4),
            "matchinfo": (3, 7, 4),
            "offsets": (3, 7, 4),
        },
    },
    "json1": {
        "type": ExtensionType.BUILTIN,
        "min_version": (3, 38, 0),
        "description": "JSON SQL functions and operators for managing JSON content",
        "features": {
            "json_functions": (3, 38, 0),
            "json_array": (3, 38, 0),
            "json_object": (3, 38, 0),
            "json_extract": (3, 38, 0),
            "json_set": (3, 38, 0),
            "json_insert": (3, 38, 0),
            "json_replace": (3, 38, 0),
            "json_remove": (3, 38, 0),
            "json_type": (3, 38, 0),
            "json_valid": (3, 38, 0),
            "json_quote": (3, 38, 0),
            "json_each": (3, 38, 0),
            "json_tree": (3, 38, 0),
            "json_array_length": (3, 38, 0),
            "json_array_unpack": (3, 38, 0),
            "json_object_pack": (3, 38, 0),
            "json_object_retrieve": (3, 38, 0),
            "json_object_length": (3, 38, 0),
            "json_object_keys": (3, 38, 0),
            "json_arrow_operators": (3, 38, 0),
        },
    },
    "rtree": {
        "type": ExtensionType.VTABLE,
        "min_version": (3, 6, 0),
        "description": "R-Tree spatial indexing for efficient range queries on multi-dimensional data",
        "features": {
            "rtree_index": (3, 6, 0),
            "rtree_query": (3, 8, 5),
            "rtree_integers": (3, 6, 0),
            "rtree_floats": (3, 6, 0),
        },
    },
    "geopoly": {
        "type": ExtensionType.VTABLE,
        "min_version": (3, 26, 0),
        "description": "Geopoly - Polygon geometry and spatial relationship operations",
        "features": {
            "polygon_operations": (3, 26, 0),
            "geopoly_contains": (3, 26, 0),
            "geopoly_area": (3, 26, 0),
            "geopoly_regular": (3, 26, 0),
            "geojson": (3, 26, 0),
        },
    },
}


class SQLiteExtensionMixin:
    """Mixin for SQLite extension support.

    Provides methods for extension detection and feature checking
    via version-based analysis and compile option inspection.
    """

    _runtime_params: Dict[str, Any] = {}

    def set_runtime_param(self, key: str, value: Any) -> None:
        """Set a runtime parameter (detected after connection)."""
        self._runtime_params[key] = value

    def get_runtime_param(self, key: str, default: Any = None) -> Any:
        """Get a runtime parameter."""
        return self._runtime_params.get(key, default)

    def _is_extension_enabled_in_build(self, ext_name: str) -> bool:
        """Check compile options for extension availability."""
        compile_options = self.get_runtime_param("compile_options", {})
        if not compile_options:
            return True  # no compile options = version check only
        option_map = {
            "fts5": "ENABLE_FTS5",
            "fts4": "ENABLE_FTS4",
            "fts3": "ENABLE_FTS3",
            "json1": "ENABLE_JSON1",
            "rtree": "ENABLE_RTREE",
            "geopoly": "ENABLE_GEOPOLY",
        }
        option = option_map.get(ext_name)
        if option is None:
            return True
        return option in compile_options

    def detect_extensions(self) -> Dict[str, SQLiteExtensionInfo]:
        """Detect all available extensions.

        Returns:
            Dictionary mapping extension names to their info
        """
        result = {}
        for name, meta in _EXTENSION_METADATA.items():
            available = self._is_extension_enabled_in_build(name) and self.version >= meta["min_version"]
            features = [
                fname for fname, fver in meta.get("features", {}).items()
                if self.version >= fver
            ]
            result[name] = SQLiteExtensionInfo(
                name=name,
                extension_type=meta["type"],
                installed=available,
                min_version=meta["min_version"],
                deprecated=meta.get("deprecated", False),
                successor=meta.get("successor"),
                description=meta["description"],
                features=features,
            )
        return result

    def is_extension_available(self, name: str) -> bool:
        """Check if a specific extension is available.

        Args:
            name: Extension name

        Returns:
            True if extension is available
        """
        meta = _EXTENSION_METADATA.get(name)
        if not meta:
            return False
        if not self._is_extension_enabled_in_build(name):
            return False
        return self.version >= meta["min_version"]

    def get_extension_info(self, name: str) -> Optional[SQLiteExtensionInfo]:
        """Get information about a specific extension.

        Args:
            name: Extension name

        Returns:
            Extension info, or None if not found
        """
        meta = _EXTENSION_METADATA.get(name)
        if not meta:
            return None
        available = self._is_extension_enabled_in_build(name) and self.version >= meta["min_version"]
        features = [
            fname for fname, fver in meta.get("features", {}).items()
            if self.version >= fver
        ]
        return SQLiteExtensionInfo(
            name=name,
            extension_type=meta["type"],
            installed=available,
            min_version=meta["min_version"],
            deprecated=meta.get("deprecated", False),
            successor=meta.get("successor"),
            description=meta["description"],
            features=features,
        )

    def check_extension_feature(self, ext_name: str, feature_name: str) -> bool:
        """Check if an extension feature is available.

        Args:
            ext_name: Extension name
            feature_name: Feature name

        Returns:
            True if feature is available
        """
        meta = _EXTENSION_METADATA.get(ext_name)
        if not meta:
            return False
        if not self._is_extension_enabled_in_build(ext_name):
            return False
        feat_version = meta.get("features", {}).get(feature_name)
        if feat_version is None:
            return False
        return self.version >= feat_version

    def get_supported_extension_features(self, ext_name: str) -> List[str]:
        """Get list of supported features for an extension.

        Args:
            ext_name: Extension name

        Returns:
            List of supported feature names
        """
        meta = _EXTENSION_METADATA.get(ext_name)
        if not meta:
            return []
        return [
            fname for fname, fver in meta.get("features", {}).items()
            if self._is_extension_enabled_in_build(ext_name) and self.version >= fver
        ]
