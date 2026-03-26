# src/rhosocial/activerecord/backend/show/functionality.py
"""
Base classes for SHOW functionality.

This module provides abstract base classes for implementing database-specific
SHOW functionality. SHOW commands are primarily a MySQL feature, but this
architecture allows for similar introspection functionality in other databases.

The ShowFunctionality class:
- Is instantiated by the backend's show() method
- Receives the backend instance and server version
- Provides version-aware functionality
- Uses expression-dialect pattern for SQL generation
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..dialect import SQLDialectBase


class ShowFunctionality(ABC):
    """Abstract base class for SHOW functionality.

    Provides version-aware SHOW functionality interface. Subclasses implement
    database-specific SHOW commands using the expression-dialect pattern.

    The class is instantiated by the backend's show() method, receiving:
    - The backend instance for query execution
    - The server version for feature adaptation

    Usage:
        result = backend.show().create_table("users")
        columns = backend.show().columns("users", full=True)
    """

    def __init__(self, backend: Any, version: Optional[Tuple[int, ...]] = None):
        """Initialize SHOW functionality instance.

        Args:
            backend: Backend instance for executing queries.
            version: Database server version tuple, e.g., (8, 0, 0) for MySQL 8.0.
                    Used for feature adaptation based on server capabilities.
        """
        self._backend = backend
        self._version = version or (0,)

    @property
    def dialect(self) -> "SQLDialectBase":
        """Get the dialect instance from the backend."""
        return self._backend.dialect

    @property
    def version(self) -> Tuple[int, ...]:
        """Get the server version."""
        return self._version

    def _check_version(self, minimum: Tuple[int, ...], feature: str) -> bool:
        """Check if server version supports a feature.

        Args:
            minimum: Minimum required version tuple.
            feature: Feature name for error message.

        Returns:
            True if version is supported.

        Raises:
            NotImplementedError: If version is not sufficient.
        """
        if self._version >= minimum:
            return True
        min_version = ".".join(map(str, minimum))
        raise NotImplementedError(
            f"{feature} requires server version {min_version}+, "
            f"current version is {'.'.join(map(str, self._version))}"
        )

    def supports_feature(self, feature: str) -> bool:
        """Check if a feature is supported by the current server version.

        Subclasses should override this method to provide version-specific
        feature detection.

        Args:
            feature: Feature name to check.

        Returns:
            True if feature is supported.
        """
        return True

    # ========== Abstract Methods (Subclasses Must Implement) ==========

    # Note: We don't define abstract methods here because SHOW functionality
    # is database-specific. MySQL will have show_create_table, show_columns, etc.
    # Other databases may have different introspection methods.
    # Subclasses should implement their specific methods.


class AsyncShowFunctionality(ABC):
    """Abstract base class for async SHOW functionality.

    Async version of ShowFunctionality. Mirrors the same interface
    but with async methods.

    Usage:
        result = await backend.show().create_table("users")
        columns = await backend.show().columns("users", full=True)
    """

    def __init__(self, backend: Any, version: Optional[Tuple[int, ...]] = None):
        """Initialize async SHOW functionality instance.

        Args:
            backend: Async backend instance for executing queries.
            version: Database server version tuple for feature adaptation.
        """
        self._backend = backend
        self._version = version or (0,)

    @property
    def dialect(self) -> "SQLDialectBase":
        """Get the dialect instance from the backend."""
        return self._backend.dialect

    @property
    def version(self) -> Tuple[int, ...]:
        """Get the server version."""
        return self._version

    def _check_version(self, minimum: Tuple[int, ...], feature: str) -> bool:
        """Check if server version supports a feature."""
        if self._version >= minimum:
            return True
        min_version = ".".join(map(str, minimum))
        raise NotImplementedError(
            f"{feature} requires server version {min_version}+, "
            f"current version is {'.'.join(map(str, self._version))}"
        )

    def supports_feature(self, feature: str) -> bool:
        """Check if a feature is supported by the current server version."""
        return True
