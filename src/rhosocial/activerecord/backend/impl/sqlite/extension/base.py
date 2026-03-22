# src/rhosocial/activerecord/backend/impl/sqlite/extension/base.py
"""
SQLite extension framework base classes and protocols.

This module provides the foundation for SQLite extension support,
including extension types, information classes, and protocols.
"""

from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


class ExtensionType(Enum):
    """SQLite extension type enumeration.

    Attributes:
        BUILTIN: Built-in extension (compiled into SQLite)
        LOADABLE: Loadable extension (.so/.dll files)
        VTABLE: Virtual table module
    """

    BUILTIN = "builtin"
    LOADABLE = "loadable"
    VTABLE = "vtable"


@dataclass
class SQLiteExtensionInfo:
    """SQLite extension information dataclass.

    Stores metadata about a SQLite extension including its type,
    version requirements, and available features.

    Attributes:
        name: Extension name (e.g., 'fts5', 'json1')
        extension_type: Type of extension (BUILTIN, LOADABLE, VTABLE)
        installed: Whether the extension is installed/available
        version: Installed version string (if available)
        min_version: Minimum SQLite version required
        deprecated: Whether this extension is deprecated
        successor: Name of successor extension (if deprecated)
        description: Human-readable description
        features: Dictionary of features with their version requirements
        documentation_url: URL to extension documentation
    """

    name: str
    extension_type: ExtensionType
    installed: bool
    version: Optional[str] = None
    min_version: Tuple[int, int, int] = (3, 0, 0)
    deprecated: bool = False
    successor: Optional[str] = None
    description: Optional[str] = None
    features: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    documentation_url: Optional[str] = None


@runtime_checkable
class SQLiteExtensionProtocol(Protocol):
    """Protocol for SQLite extension implementations.

    Defines the interface that all SQLite extensions must implement
    to be compatible with the extension framework.
    """

    @property
    def name(self) -> str:
        """Get the extension name."""
        ...

    @property
    def extension_type(self) -> ExtensionType:
        """Get the extension type."""
        ...

    def is_available(self, version: Tuple[int, int, int]) -> bool:
        """Check if extension is available for given SQLite version.

        Args:
            version: SQLite version tuple (major, minor, patch)

        Returns:
            True if extension is available
        """
        ...

    def get_info(self, version: Tuple[int, int, int]) -> SQLiteExtensionInfo:
        """Get extension information.

        Args:
            version: SQLite version tuple (major, minor, patch)

        Returns:
            SQLiteExtensionInfo instance
        """
        ...

    def check_feature(self, feature_name: str, version: Tuple[int, int, int]) -> bool:
        """Check if a specific feature is available.

        Args:
            feature_name: Name of the feature to check
            version: SQLite version tuple (major, minor, patch)

        Returns:
            True if feature is available
        """
        ...

    def get_supported_features(self, version: Tuple[int, int, int]) -> List[str]:
        """Get list of supported features for given version.

        Args:
            version: SQLite version tuple (major, minor, patch)

        Returns:
            List of supported feature names
        """
        ...


class SQLiteExtensionBase(ABC):
    """Abstract base class for SQLite extensions.

    Provides common implementation for extension protocol methods.
    Subclasses must implement the abstract methods.
    """

    def __init__(
        self,
        name: str,
        extension_type: ExtensionType,
        min_version: Tuple[int, int, int] = (3, 0, 0),
        deprecated: bool = False,
        successor: Optional[str] = None,
        description: Optional[str] = None,
        features: Optional[Dict[str, Dict[str, Any]]] = None,
        documentation_url: Optional[str] = None,
    ):
        """Initialize the extension.

        Args:
            name: Extension name
            extension_type: Type of extension
            min_version: Minimum SQLite version required
            deprecated: Whether this extension is deprecated
            successor: Name of successor extension (if deprecated)
            description: Human-readable description
            features: Dictionary of features with their version requirements
            documentation_url: URL to extension documentation
        """
        self._name = name
        self._extension_type = extension_type
        self._min_version = min_version
        self._deprecated = deprecated
        self._successor = successor
        self._description = description
        self._features = features or {}
        self._documentation_url = documentation_url

    @property
    def name(self) -> str:
        """Get the extension name."""
        return self._name

    @property
    def extension_type(self) -> ExtensionType:
        """Get the extension type."""
        return self._extension_type

    @property
    def min_version(self) -> Tuple[int, int, int]:
        """Get minimum required SQLite version."""
        return self._min_version

    @property
    def deprecated(self) -> bool:
        """Check if extension is deprecated."""
        return self._deprecated

    @property
    def successor(self) -> Optional[str]:
        """Get successor extension name."""
        return self._successor

    def is_available(self, version: Tuple[int, int, int]) -> bool:
        """Check if extension is available for given SQLite version.

        Args:
            version: SQLite version tuple (major, minor, patch)

        Returns:
            True if extension is available
        """
        return version >= self._min_version

    def get_info(self, version: Tuple[int, int, int]) -> SQLiteExtensionInfo:
        """Get extension information.

        Args:
            version: SQLite version tuple (major, minor, patch)

        Returns:
            SQLiteExtensionInfo instance
        """
        return SQLiteExtensionInfo(
            name=self._name,
            extension_type=self._extension_type,
            installed=self.is_available(version),
            min_version=self._min_version,
            deprecated=self._deprecated,
            successor=self._successor,
            description=self._description,
            features=self._features.copy(),
            documentation_url=self._documentation_url,
        )

    def check_feature(self, feature_name: str, version: Tuple[int, int, int]) -> bool:
        """Check if a specific feature is available.

        Args:
            feature_name: Name of the feature to check
            version: SQLite version tuple (major, minor, patch)

        Returns:
            True if feature is available
        """
        if not self.is_available(version):
            return False

        if feature_name not in self._features:
            return self.is_available(version)

        feature_config = self._features[feature_name]
        min_feature_version = feature_config.get("min_version", self._min_version)
        return version >= min_feature_version

    def get_supported_features(self, version: Tuple[int, int, int]) -> List[str]:
        """Get list of supported features for given version.

        Args:
            version: SQLite version tuple (major, minor, patch)

        Returns:
            List of supported feature names
        """
        if not self.is_available(version):
            return []

        return [name for name in self._features if self.check_feature(name, version)]

    def get_min_version_for_feature(self, feature_name: str) -> Optional[Tuple[int, int, int]]:
        """Get minimum version required for a feature.

        Args:
            feature_name: Name of the feature

        Returns:
            Minimum version tuple, or None if feature not defined
        """
        if feature_name not in self._features:
            return None

        feature_config = self._features[feature_name]
        return feature_config.get("min_version", self._min_version)


@runtime_checkable
class SQLiteExtensionSupport(Protocol):
    """Protocol for SQLite extension support in dialects/backends.

    Defines the interface for extension detection and feature checking.
    """

    def detect_extensions(self) -> Dict[str, SQLiteExtensionInfo]:
        """Detect all available extensions.

        Returns:
            Dictionary mapping extension names to their info
        """
        ...

    def is_extension_available(self, name: str) -> bool:
        """Check if a specific extension is available.

        Args:
            name: Extension name

        Returns:
            True if extension is available
        """
        ...

    def get_extension_info(self, name: str) -> Optional[SQLiteExtensionInfo]:
        """Get information about a specific extension.

        Args:
            name: Extension name

        Returns:
            Extension info, or None if not found
        """
        ...

    def check_extension_feature(self, ext_name: str, feature_name: str) -> bool:
        """Check if an extension feature is available.

        Args:
            ext_name: Extension name
            feature_name: Feature name

        Returns:
            True if feature is available
        """
        ...
