# src/rhosocial/activerecord/backend/impl/sqlite/pragma/base.py
"""
SQLite PRAGMA framework base classes and protocols.

This module provides the foundation for SQLite PRAGMA support,
including pragma categories, information classes, and protocols.

SQLite PRAGMA statements are used to:
- Query and modify database configuration
- Inspect database schema and statistics
- Perform integrity checks
- Control performance-related settings

Reference: https://www.sqlite.org/pragma.html
"""

from abc import ABC
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


class PragmaCategory(Enum):
    """SQLite PRAGMA category enumeration.

    Attributes:
        CONFIGURATION: Configuration pragmas (read-write)
        INFORMATION: Information query pragmas (read-only)
        DEBUG: Debug and diagnostic pragmas
        PERFORMANCE: Performance tuning pragmas
        WAL: WAL-specific pragmas
        COMPILE_TIME: Compile-time information pragmas (read-only)
    """

    CONFIGURATION = "configuration"
    INFORMATION = "information"
    DEBUG = "debug"
    PERFORMANCE = "performance"
    WAL = "wal"
    COMPILE_TIME = "compile_time"


@dataclass
class PragmaInfo:
    """SQLite PRAGMA information dataclass.

    Stores metadata about a SQLite PRAGMA including its category,
    version requirements, and value constraints.

    Attributes:
        name: PRAGMA name (e.g., 'foreign_keys', 'journal_mode')
        category: PRAGMA category
        description: Human-readable description
        read_only: Whether the PRAGMA is read-only
        min_version: Minimum SQLite version required
        value_type: Expected value type
        allowed_values: List of allowed values (if restricted)
        default_value: Default value (if applicable)
        requires_argument: Whether the PRAGMA requires an argument
        argument_type: Expected argument type (if requires_argument)
        documentation_url: URL to SQLite documentation
    """

    name: str
    category: PragmaCategory
    description: str
    read_only: bool = False
    min_version: Tuple[int, int, int] = (3, 0, 0)
    value_type: type = str
    allowed_values: Optional[List[Any]] = None
    default_value: Optional[Any] = None
    requires_argument: bool = False
    argument_type: Optional[type] = None
    documentation_url: Optional[str] = None

    def get_sql(self) -> str:
        """Get PRAGMA SQL statement for reading.

        Returns:
            SQL string for reading the PRAGMA value
        """
        return f"PRAGMA {self.name}"

    def get_set_sql(self, value: Any = None, argument: Any = None) -> str:
        """Get PRAGMA SQL statement for setting.

        Args:
            value: Value to set (for configuration pragmas)
            argument: Argument (for pragmas that require an argument)

        Returns:
            SQL string for setting the PRAGMA value
        """
        if self.requires_argument and argument is not None:
            if value is not None:
                return f"PRAGMA {self.name}({argument}) = {value}"
            return f"PRAGMA {self.name}({argument})"
        elif value is not None:
            return f"PRAGMA {self.name} = {value}"
        return f"PRAGMA {self.name}"


@runtime_checkable
class PragmaProtocol(Protocol):
    """Protocol for SQLite PRAGMA implementations."""

    @property
    def name(self) -> str:
        """Get the PRAGMA name."""
        ...

    @property
    def category(self) -> PragmaCategory:
        """Get the PRAGMA category."""
        ...

    def is_available(self, version: Tuple[int, int, int]) -> bool:
        """Check if PRAGMA is available for given SQLite version.

        Args:
            version: SQLite version tuple (major, minor, patch)

        Returns:
            True if PRAGMA is available
        """
        ...

    def get_info(self) -> PragmaInfo:
        """Get PRAGMA information.

        Returns:
            PragmaInfo instance
        """
        ...

    def get_value_sql(self, argument: Any = None) -> str:
        """Get SQL for reading PRAGMA value.

        Args:
            argument: Optional argument for parameterized pragmas

        Returns:
            SQL string
        """
        ...

    def set_value_sql(self, value: Any, argument: Any = None) -> str:
        """Get SQL for setting PRAGMA value.

        Args:
            value: Value to set
            argument: Optional argument for parameterized pragmas

        Returns:
            SQL string
        """
        ...


class PragmaBase(ABC):
    """Abstract base class for SQLite PRAGMA implementations.

    Provides common implementation for PRAGMA protocol methods.
    """

    def __init__(
        self,
        name: str,
        category: PragmaCategory,
        description: str,
        read_only: bool = False,
        min_version: Tuple[int, int, int] = (3, 0, 0),
        value_type: type = str,
        allowed_values: Optional[List[Any]] = None,
        default_value: Optional[Any] = None,
        requires_argument: bool = False,
        argument_type: Optional[type] = None,
        documentation_url: Optional[str] = None,
    ):
        """Initialize the PRAGMA.

        Args:
            name: PRAGMA name
            category: PRAGMA category
            description: Human-readable description
            read_only: Whether the PRAGMA is read-only
            min_version: Minimum SQLite version required
            value_type: Expected value type
            allowed_values: List of allowed values (if restricted)
            default_value: Default value (if applicable)
            requires_argument: Whether the PRAGMA requires an argument
            argument_type: Expected argument type (if requires_argument)
            documentation_url: URL to SQLite documentation
        """
        self._name = name
        self._category = category
        self._description = description
        self._read_only = read_only
        self._min_version = min_version
        self._value_type = value_type
        self._allowed_values = allowed_values
        self._default_value = default_value
        self._requires_argument = requires_argument
        self._argument_type = argument_type
        self._documentation_url = documentation_url

    @property
    def name(self) -> str:
        """Get the PRAGMA name."""
        return self._name

    @property
    def category(self) -> PragmaCategory:
        """Get the PRAGMA category."""
        return self._category

    @property
    def read_only(self) -> bool:
        """Check if PRAGMA is read-only."""
        return self._read_only

    @property
    def min_version(self) -> Tuple[int, int, int]:
        """Get minimum required SQLite version."""
        return self._min_version

    def is_available(self, version: Tuple[int, int, int]) -> bool:
        """Check if PRAGMA is available for given SQLite version.

        Args:
            version: SQLite version tuple (major, minor, patch)

        Returns:
            True if PRAGMA is available
        """
        return version >= self._min_version

    def get_info(self) -> PragmaInfo:
        """Get PRAGMA information.

        Returns:
            PragmaInfo instance
        """
        return PragmaInfo(
            name=self._name,
            category=self._category,
            description=self._description,
            read_only=self._read_only,
            min_version=self._min_version,
            value_type=self._value_type,
            allowed_values=self._allowed_values.copy() if self._allowed_values else None,
            default_value=self._default_value,
            requires_argument=self._requires_argument,
            argument_type=self._argument_type,
            documentation_url=self._documentation_url,
        )

    def get_value_sql(self, argument: Any = None) -> str:
        """Get SQL for reading PRAGMA value.

        Args:
            argument: Optional argument for parameterized pragmas

        Returns:
            SQL string
        """
        if self._requires_argument and argument is not None:
            return f"PRAGMA {self._name}({argument})"
        return f"PRAGMA {self._name}"

    def set_value_sql(self, value: Any, argument: Any = None) -> str:
        """Get SQL for setting PRAGMA value.

        Args:
            value: Value to set
            argument: Optional argument for parameterized pragmas

        Returns:
            SQL string

        Raises:
            ValueError: If PRAGMA is read-only
        """
        if self._read_only:
            raise ValueError(f"PRAGMA {self._name} is read-only and cannot be set")

        if self._allowed_values and value not in self._allowed_values:
            raise ValueError(f"Invalid value '{value}' for PRAGMA {self._name}. Allowed values: {self._allowed_values}")

        if self._requires_argument and argument is not None:
            return f"PRAGMA {self._name}({argument}) = {value}"
        return f"PRAGMA {self._name} = {value}"

    def validate_value(self, value: Any) -> bool:
        """Validate a value for this PRAGMA.

        Args:
            value: Value to validate

        Returns:
            True if value is valid
        """
        if self._allowed_values:
            return value in self._allowed_values
        return isinstance(value, self._value_type)


@runtime_checkable
class SQLitePragmaSupport(Protocol):
    """Protocol for SQLite PRAGMA support in dialects/backends.

    Defines the interface for PRAGMA operations.
    """

    def get_pragma_info(self, name: str) -> Optional[PragmaInfo]:
        """Get information about a specific PRAGMA.

        Args:
            name: PRAGMA name

        Returns:
            PragmaInfo, or None if not found
        """
        ...

    def get_pragma_sql(self, name: str, argument: Any = None) -> str:
        """Get SQL for reading a PRAGMA.

        Args:
            name: PRAGMA name
            argument: Optional argument

        Returns:
            SQL string
        """
        ...

    def set_pragma_sql(self, name: str, value: Any, argument: Any = None) -> str:
        """Get SQL for setting a PRAGMA.

        Args:
            name: PRAGMA name
            value: Value to set
            argument: Optional argument

        Returns:
            SQL string
        """
        ...

    def is_pragma_available(self, name: str) -> bool:
        """Check if a PRAGMA is available.

        Args:
            name: PRAGMA name

        Returns:
            True if available
        """
        ...

    def get_pragmas_by_category(self, category: PragmaCategory) -> List[PragmaInfo]:
        """Get all pragmas in a category.

        Args:
            category: PRAGMA category

        Returns:
            List of PragmaInfo for pragmas in the category
        """
        ...

    def get_all_pragma_infos(self) -> Dict[str, PragmaInfo]:
        """Get information for all known pragmas.

        Returns:
            Dictionary mapping PRAGMA names to their info
        """
        ...
