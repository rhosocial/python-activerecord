# src/rhosocial/activerecord/backend/impl/sqlite/extension/registry.py
"""
SQLite extension registry.

This module provides a centralized registry for SQLite extensions,
including known extension definitions and version requirements.
"""

from typing import Dict, List, Optional, Tuple, Any

from .base import (
    ExtensionType,
    SQLiteExtensionInfo,
    SQLiteExtensionBase,
)


# Known SQLite extensions with their metadata
KNOWN_EXTENSIONS: Dict[str, Dict[str, Any]] = {
    "fts5": {
        "type": ExtensionType.BUILTIN,
        "min_version": (3, 9, 0),
        "description": "Full-Text Search version 5 - Advanced full-text search with customizable tokenizers",
        "documentation_url": "https://www.sqlite.org/fts5.html",
        "features": {
            "full_text_search": {"min_version": (3, 9, 0)},
            "bm25_ranking": {"min_version": (3, 9, 0)},
            "highlight": {"min_version": (3, 9, 0)},
            "snippet": {"min_version": (3, 9, 0)},
            "offset": {"min_version": (3, 9, 0)},
            "porter_tokenizer": {"min_version": (3, 9, 0)},
            "unicode61_tokenizer": {"min_version": (3, 9, 0)},
            "trigram_tokenizer": {"min_version": (3, 34, 0)},
            "column_filters": {"min_version": (3, 9, 0)},
            "phrase_queries": {"min_version": (3, 9, 0)},
            "near_queries": {"min_version": (3, 9, 0)},
        },
    },
    "fts4": {
        "type": ExtensionType.BUILTIN,
        "min_version": (3, 7, 4),
        "deprecated": True,
        "successor": "fts5",
        "description": "Full-Text Search version 4 (legacy) - Predecessor to FTS5",
        "documentation_url": "https://www.sqlite.org/fts3.html",
        "features": {
            "full_text_search": {"min_version": (3, 7, 4)},
            "matchinfo": {"min_version": (3, 7, 4)},
            "offsets": {"min_version": (3, 7, 4)},
            "snippet": {"min_version": (3, 7, 4)},
            "porter_tokenizer": {"min_version": (3, 7, 4)},
            "unicode61_tokenizer": {"min_version": (3, 7, 4)},
        },
    },
    "fts3": {
        "type": ExtensionType.BUILTIN,
        "min_version": (3, 5, 0),
        "deprecated": True,
        "successor": "fts4",
        "description": "Full-Text Search version 3 (legacy) - Original FTS implementation",
        "documentation_url": "https://www.sqlite.org/fts3.html",
        "features": {
            "full_text_search": {"min_version": (3, 5, 0)},
            "matchinfo": {"min_version": (3, 5, 0)},
            "offsets": {"min_version": (3, 5, 0)},
            "snippet": {"min_version": (3, 5, 0)},
        },
    },
    "json1": {
        "type": ExtensionType.BUILTIN,
        "min_version": (3, 38, 0),  # Built-in since 3.38.0
        "description": "JSON functions - JSON processing and manipulation",
        "documentation_url": "https://www.sqlite.org/json1.html",
        "features": {
            "json_functions": {"min_version": (3, 38, 0)},
            "json_array": {"min_version": (3, 38, 0)},
            "json_object": {"min_version": (3, 38, 0)},
            "json_extract": {"min_version": (3, 38, 0)},
            "json_arrow_operators": {"min_version": (3, 38, 0)},
            "json_each": {"min_version": (3, 38, 0)},
            "json_tree": {"min_version": (3, 38, 0)},
            "json_patch": {"min_version": (3, 38, 0)},
            "json_type": {"min_version": (3, 38, 0)},
            "json_valid": {"min_version": (3, 38, 0)},
        },
    },
    "rtree": {
        "type": ExtensionType.VTABLE,
        "min_version": (3, 6, 0),
        "description": "R-Tree spatial index - Efficient range queries for multi-dimensional data",
        "documentation_url": "https://www.sqlite.org/rtree.html",
        "features": {
            "rtree_index": {"min_version": (3, 6, 0)},
            "rtree_query": {"min_version": (3, 8, 5)},
            "rtree_integrity_check": {"min_version": (3, 24, 0)},
            "rtree_auxiliary_functions": {"min_version": (3, 25, 0)},
        },
    },
    "geopoly": {
        "type": ExtensionType.VTABLE,
        "min_version": (3, 26, 0),
        "description": "Geopoly - 2D polygon geometry operations",
        "documentation_url": "https://www.sqlite.org/geopoly.html",
        "features": {
            "polygon_operations": {"min_version": (3, 26, 0)},
            "polygon_contains": {"min_version": (3, 26, 0)},
            "polygon_within": {"min_version": (3, 26, 0)},
            "polygon_overlap": {"min_version": (3, 26, 0)},
            "polygon_area": {"min_version": (3, 26, 0)},
            "polygon_json": {"min_version": (3, 26, 0)},
        },
    },
    "dbstat": {
        "type": ExtensionType.VTABLE,
        "min_version": (3, 6, 17),
        "description": "Database statistics virtual table - Schema-level storage statistics",
        "documentation_url": "https://www.sqlite.org/dbstat.html",
        "features": {
            "table_statistics": {"min_version": (3, 6, 17)},
            "aggregate_statistics": {"min_version": (3, 31, 0)},
        },
    },
    "fts5tokenize": {
        "type": ExtensionType.VTABLE,
        "min_version": (3, 12, 0),
        "description": "FTS5 tokenization virtual table - Token inspection for FTS5",
        "documentation_url": "https://www.sqlite.org/fts5.html#the_fts5tokenize_virtual_table",
        "features": {
            "token_inspection": {"min_version": (3, 12, 0)},
        },
    },
}


class SQLiteExtensionRegistry:
    """Registry for SQLite extensions.

    Manages known extensions and provides methods for detection,
    version checking, and feature queries.
    """

    def __init__(self):
        """Initialize the registry."""
        self._extensions: Dict[str, SQLiteExtensionBase] = {}
        self._known_extensions = KNOWN_EXTENSIONS.copy()

    def register(self, extension: SQLiteExtensionBase) -> None:
        """Register an extension.

        Args:
            extension: Extension instance to register
        """
        self._extensions[extension.name] = extension

    def unregister(self, name: str) -> None:
        """Unregister an extension.

        Args:
            name: Extension name to unregister
        """
        self._extensions.pop(name, None)

    def get_extension(self, name: str) -> Optional[SQLiteExtensionBase]:
        """Get a registered extension.

        Args:
            name: Extension name

        Returns:
            Extension instance, or None if not found
        """
        return self._extensions.get(name)

    def get_all_extensions(self) -> Dict[str, SQLiteExtensionBase]:
        """Get all registered extensions.

        Returns:
            Dictionary of extension name to extension instance
        """
        return self._extensions.copy()

    def get_known_extension_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get known extension configuration.

        Args:
            name: Extension name

        Returns:
            Extension configuration dict, or None if not found
        """
        return self._known_extensions.get(name)

    def get_all_known_extension_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all known extension configurations.

        Returns:
            Dictionary of extension name to configuration
        """
        return self._known_extensions.copy()

    def is_extension_available(self, name: str, version: Tuple[int, int, int]) -> bool:
        """Check if an extension is available for given version.

        Args:
            name: Extension name
            version: SQLite version tuple

        Returns:
            True if extension is available
        """
        extension = self._extensions.get(name)
        if extension:
            return extension.is_available(version)

        config = self._known_extensions.get(name)
        if config:
            return version >= config.get("min_version", (3, 0, 0))

        return False

    def check_extension_feature(self, ext_name: str, feature_name: str, version: Tuple[int, int, int]) -> bool:
        """Check if an extension feature is available.

        Args:
            ext_name: Extension name
            feature_name: Feature name
            version: SQLite version tuple

        Returns:
            True if feature is available
        """
        extension = self._extensions.get(ext_name)
        if extension:
            return extension.check_feature(feature_name, version)

        config = self._known_extensions.get(ext_name)
        if config:
            if not self.is_extension_available(ext_name, version):
                return False

            features = config.get("features", {})
            if feature_name not in features:
                return self.is_extension_available(ext_name, version)

            feature_config = features[feature_name]
            return version >= feature_config.get("min_version", config.get("min_version", (3, 0, 0)))

        return False

    def get_extension_info(self, name: str, version: Tuple[int, int, int]) -> Optional[SQLiteExtensionInfo]:
        """Get extension information.

        Args:
            name: Extension name
            version: SQLite version tuple

        Returns:
            Extension info, or None if not found
        """
        extension = self._extensions.get(name)
        if extension:
            return extension.get_info(version)

        config = self._known_extensions.get(name)
        if config:
            return SQLiteExtensionInfo(
                name=name,
                extension_type=config.get("type", ExtensionType.BUILTIN),
                installed=self.is_extension_available(name, version),
                min_version=config.get("min_version", (3, 0, 0)),
                deprecated=config.get("deprecated", False),
                successor=config.get("successor"),
                description=config.get("description"),
                features=config.get("features", {}).copy(),
                documentation_url=config.get("documentation_url"),
            )

        return None

    def detect_extensions(self, version: Tuple[int, int, int]) -> Dict[str, SQLiteExtensionInfo]:
        """Detect all available extensions for given version.

        Args:
            version: SQLite version tuple

        Returns:
            Dictionary mapping extension names to their info
        """
        result = {}

        for name in self._extensions:
            extension = self._extensions[name]
            result[name] = extension.get_info(version)

        for name in self._known_extensions:
            if name not in result:
                result[name] = self.get_extension_info(name, version)

        return result

    def get_supported_features(self, ext_name: str, version: Tuple[int, int, int]) -> List[str]:
        """Get list of supported features for an extension.

        Args:
            ext_name: Extension name
            version: SQLite version tuple

        Returns:
            List of supported feature names
        """
        extension = self._extensions.get(ext_name)
        if extension:
            return extension.get_supported_features(version)

        config = self._known_extensions.get(ext_name)
        if config:
            if not self.is_extension_available(ext_name, version):
                return []

            features = config.get("features", {})
            min_version = config.get("min_version", (3, 0, 0))

            return [
                name for name, feat_config in features.items() if version >= feat_config.get("min_version", min_version)
            ]

        return []

    def get_min_version_for_feature(self, ext_name: str, feature_name: str) -> Optional[Tuple[int, int, int]]:
        """Get minimum version required for an extension feature.

        Args:
            ext_name: Extension name
            feature_name: Feature name

        Returns:
            Minimum version tuple, or None if not defined
        """
        extension = self._extensions.get(ext_name)
        if extension:
            return extension.get_min_version_for_feature(feature_name)

        config = self._known_extensions.get(ext_name)
        if config:
            features = config.get("features", {})
            if feature_name in features:
                return features[feature_name].get("min_version", config.get("min_version"))

        return None


# Global registry instance
_registry: Optional[SQLiteExtensionRegistry] = None


def get_registry() -> SQLiteExtensionRegistry:
    """Get the global extension registry.

    Returns:
        Global SQLiteExtensionRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = SQLiteExtensionRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (mainly for testing)."""
    global _registry
    _registry = None
