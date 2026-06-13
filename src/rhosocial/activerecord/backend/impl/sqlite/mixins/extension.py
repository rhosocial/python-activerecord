# src/rhosocial/activerecord/backend/impl/sqlite/mixins/extension.py
"""
SQLite-specific Extension implementation.

This module provides the SQLiteExtensionMixin class.
"""

from typing import Any, Dict, List, Optional
from ..extension import SQLiteExtensionRegistry, get_registry, SQLiteExtensionInfo
from ..extension.extensions import get_fts5_extension


class SQLiteExtensionMixin:
    """Mixin for SQLite extension support.

    Provides methods for extension detection, version management,
    and feature checking.
    """

    _extension_registry: SQLiteExtensionRegistry = None
    _runtime_params: Dict[str, Any] = {}

    def _ensure_extension_registry(self) -> SQLiteExtensionRegistry:
        """Ensure extension registry is initialized."""
        if self._extension_registry is None:
            self._extension_registry = get_registry()
            self._extension_registry.register(get_fts5_extension())
        return self._extension_registry

    def set_runtime_param(self, key: str, value: Any) -> None:
        """Set a runtime parameter (detected after connection)."""
        self._runtime_params[key] = value

    def get_runtime_param(self, key: str, default: Any = None) -> Any:
        """Get a runtime parameter."""
        return self._runtime_params.get(key, default)

    def detect_extensions(self) -> Dict[str, SQLiteExtensionInfo]:
        """Detect all available extensions.

        Returns:
            Dictionary mapping extension names to their info
        """
        registry = self._ensure_extension_registry()
        version = self.version
        return registry.detect_extensions(version)

    def is_extension_available(self, name: str) -> bool:
        """Check if a specific extension is available.

        Args:
            name: Extension name

        Returns:
            True if extension is available
        """
        registry = self._ensure_extension_registry()
        version = self.version
        return registry.is_extension_available(name, version)

    def get_extension_info(self, name: str) -> Optional[SQLiteExtensionInfo]:
        """Get information about a specific extension.

        Args:
            name: Extension name

        Returns:
            Extension info, or None if not found
        """
        registry = self._ensure_extension_registry()
        version = self.version
        return registry.get_extension_info(name, version)

    def check_extension_feature(self, ext_name: str, feature_name: str) -> bool:
        """Check if an extension feature is available.

        Args:
            ext_name: Extension name
            feature_name: Feature name

        Returns:
            True if feature is available
        """
        registry = self._ensure_extension_registry()
        version = self.version
        return registry.check_extension_feature(ext_name, feature_name, version)

    def get_supported_extension_features(self, ext_name: str) -> List[str]:
        """Get list of supported features for an extension.

        Args:
            ext_name: Extension name

        Returns:
            List of supported feature names
        """
        registry = self._ensure_extension_registry()
        version = self.version
        return registry.get_supported_features(ext_name, version)

