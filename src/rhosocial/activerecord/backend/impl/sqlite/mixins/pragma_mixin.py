# src/rhosocial/activerecord/backend/impl/sqlite/mixins/pragma_mixin.py
"""
SQLite-specific Pragma Mixin implementation.

This module provides the SQLitePragmaMixin class.
"""

from typing import Any, Dict, List, Optional
from ..pragma import PragmaCategory, PragmaInfo, get_pragma_info, get_all_pragma_infos, get_pragmas_by_category


class SQLitePragmaMixin:
    """Mixin for SQLite PRAGMA support.

    Provides methods for pragma query and manipulation.
    """

    def get_pragma_info(self, name: str) -> Optional[PragmaInfo]:
        """Get information about a specific PRAGMA.

        Args:
            name: PRAGMA name

        Returns:
            PragmaInfo, or None if not found
        """
        info = get_pragma_info(name)
        if info is None:
            return None

        version = self.version
        if version < info.min_version:
            return None

        return info

    def get_pragma_sql(self, name: str, argument: Any = None) -> str:
        """Get SQL for reading a PRAGMA.

        Args:
            name: PRAGMA name
            argument: Optional argument

        Returns:
            SQL string
        """
        info = self.get_pragma_info(name)
        if info is None:
            raise ValueError(f"Unknown PRAGMA: {name}")

        if info.requires_argument and argument is not None:
            return f"PRAGMA {info.name}({argument})"
        return f"PRAGMA {info.name}"

    def set_pragma_sql(self, name: str, value: Any, argument: Any = None) -> str:
        """Get SQL for setting a PRAGMA.

        Args:
            name: PRAGMA name
            value: Value to set
            argument: Optional argument

        Returns:
            SQL string
        """
        info = self.get_pragma_info(name)
        if info is None:
            raise ValueError(f"Unknown PRAGMA: {name}")

        if info.read_only:
            raise ValueError(f"PRAGMA {name} is read-only and cannot be set")

        if info.allowed_values and value not in info.allowed_values:
            raise ValueError(f"Invalid value '{value}' for PRAGMA {name}. Allowed values: {info.allowed_values}")

        if info.requires_argument and argument is not None:
            return f"PRAGMA {info.name}({argument}) = {value}"
        return f"PRAGMA {info.name} = {value}"

    def is_pragma_available(self, name: str) -> bool:
        """Check if a PRAGMA is available.

        Args:
            name: PRAGMA name

        Returns:
            True if available
        """
        info = get_pragma_info(name)
        if info is None:
            return False

        version = self.version
        return version >= info.min_version

    def get_pragmas_by_category(self, category: PragmaCategory) -> List[PragmaInfo]:
        """Get all pragmas in a category.

        Args:
            category: PRAGMA category

        Returns:
            List of PragmaInfo for pragmas in the category
        """
        version = self.version
        return [info for info in get_pragmas_by_category(category) if version >= info.min_version]

    def get_all_pragma_infos(self) -> Dict[str, PragmaInfo]:
        """Get information for all known pragmas.

        Returns:
            Dictionary mapping PRAGMA names to their info
        """
        version = self.version
        return {name: info for name, info in get_all_pragma_infos().items() if version >= info.min_version}
