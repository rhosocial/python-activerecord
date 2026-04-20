# src/rhosocial/activerecord/backend/impl/sqlite/protocols.py
"""
SQLite-specific protocol definitions.

This module defines protocol interfaces for SQLite-specific features
that are not part of the standard SQL dialect protocols.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable


@runtime_checkable
class SQLiteExtensionSupport(Protocol):
    """Protocol for SQLite extension support in dialects/backends.

    Defines the interface for extension detection and feature checking.
    """

    def detect_extensions(self) -> Dict[str, Any]:
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

    def get_extension_info(self, name: str) -> Optional[Any]:
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


@runtime_checkable
class SQLitePragmaSupport(Protocol):
    """Protocol for SQLite PRAGMA support in dialects/backends.

    Defines the interface for PRAGMA operations.
    """

    def get_pragma_info(self, name: str) -> Optional[Any]:
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

    def get_pragmas_by_category(self, category: Any) -> List[Any]:
        """Get all pragmas in a category.

        Args:
            category: PRAGMA category

        Returns:
            List of PragmaInfo for pragmas in the category
        """
        ...

    def get_all_pragma_infos(self) -> Dict[str, Any]:
        """Get information for all known pragmas.

        Returns:
            Dictionary mapping PRAGMA names to their info
        """
        ...


@runtime_checkable
class VirtualTableSupport(Protocol):
    """Protocol for SQLite virtual table support.

    Defines the interface for virtual table operations including
    R-Tree, FTS5, Geopoly, and other virtual table modules.

    Reference: https://www.sqlite.org/vtab.html
    """

    def supports_virtual_table(self) -> bool:
        """Whether virtual tables are supported (SQLite 3.8.8+)."""
        ...

    def supports_rtree(self) -> bool:
        """Whether R-Tree virtual table is supported (SQLite 3.6.0+)."""
        ...

    def supports_fts5(self) -> bool:
        """Whether FTS5 virtual table is supported (SQLite 3.9.0+)."""
        ...

    def supports_geopoly(self) -> bool:
        """Whether Geopoly virtual table is supported (SQLite 3.26.0+)."""
        ...

    def format_create_virtual_table(
        self,
        module: str,
        table_name: str,
        columns: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE statement.

        Args:
            module: Virtual table module (rtree, fts5, geopoly, etc.)
            table_name: Name of the virtual table
            columns: List of column names
            options: Optional module-specific options

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...

    def format_drop_virtual_table(
        self,
        table_name: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """Format DROP TABLE statement for virtual table.

        Args:
            table_name: Name of the virtual table
            if_exists: Add IF EXISTS clause

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...
