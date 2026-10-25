# src/rhosocial/activerecord/backend/impl/sqlite/mixins/pragma_mixin.py
"""
SQLite-specific Pragma Mixin implementation.

This module provides the SQLitePragmaMixin class.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..pragma import PragmaCategory, PragmaInfo, get_pragma_info, get_all_pragma_infos, get_pragmas_by_category

if TYPE_CHECKING:
    from ..expression.introspection import SQLitePragmaQueryStatement, SQLitePragmaSetStatement


class SQLitePragmaMixin:
    """Mixin for SQLite PRAGMA support.

    Provides methods for pragma query and manipulation.
    """

    def get_pragma_info(self, name: str) -> Optional[PragmaInfo]:
        """Get information about a specific PRAGMA.

        Args:
            name: PRAGMA name

        Returns:
            PragmaInfo, or None if not found in the registry or not available
            in this SQLite version.

        Note:
            A dialect that has not been adapted has no version to compare
            against, so the registry answer stands. Adaptation
            (``backend.introspect_and_adapt()``) is what makes the version
            gate bite, and an un-adapted dialect keeps its old permissiveness.
        """
        info = get_pragma_info(name)
        if info is None:
            return None

        from rhosocial.activerecord.backend.dialect.exceptions import DialectNotAdaptedException

        try:
            version = self.version
        except DialectNotAdaptedException:
            return info

        if version < info.min_version:
            return None

        return info

    def pragma_query_statement(
        self,
        name: str,
        argument: Any = None,
        schema: Optional[str] = None,
    ) -> "SQLitePragmaQueryStatement":
        """The statement that reads a PRAGMA.

        This is where the registry is consulted. A name SQLite does not have,
        or that this version does not have, is rejected before any SQL exists,
        so an unknown name never reaches the engine as statement text.

        Args:
            name: PRAGMA name
            argument: Optional argument, already spelled for the engine
            schema: Optional attached-database name

        Returns:
            The PRAGMA question, ready for ``to_sql()``.

        Raises:
            ValueError: If the PRAGMA is not in the known whitelist or is not
                available in this SQLite version.
        """
        info = self.get_pragma_info(name)
        if info is None:
            raise ValueError(f"Unknown PRAGMA: {name}")

        from ..expression.introspection import SQLitePragmaQueryStatement

        return SQLitePragmaQueryStatement(self, info.name, argument, schema)

    def pragma_set_statement(
        self,
        name: str,
        value: Any,
        argument: Any = None,
        schema: Optional[str] = None,
    ) -> "SQLitePragmaSetStatement":
        """The statement that assigns a PRAGMA.

        The registry is consulted here for the same reason as in
        :meth:`pragma_query_statement`, and additionally decides whether the
        pragma may be written at all and which values it accepts.

        Args:
            name: PRAGMA name
            value: Value to set
            argument: Optional argument, already spelled for the engine
            schema: Optional attached-database name

        Returns:
            The PRAGMA assignment, ready for ``to_sql()``.

        Raises:
            ValueError: If the PRAGMA is unknown, read-only, or the value is
                not among its allowed values.
        """
        info = self.get_pragma_info(name)
        if info is None:
            raise ValueError(f"Unknown PRAGMA: {name}")

        if info.read_only:
            raise ValueError(f"PRAGMA {name} is read-only and cannot be set")

        if info.allowed_values and value not in info.allowed_values:
            raise ValueError(f"Invalid value '{value}' for PRAGMA {name}. Allowed values: {info.allowed_values}")

        from ..expression.introspection import SQLitePragmaSetStatement

        return SQLitePragmaSetStatement(self, info.name, value, argument, schema)

    def get_pragma_sql(self, name: str, argument: Any = None) -> str:
        """Get SQL for reading a PRAGMA.

        Args:
            name: PRAGMA name
            argument: Optional argument

        Returns:
            SQL string
        """
        return self.pragma_query_statement(name, argument).to_sql()[0]

    def set_pragma_sql(self, name: str, value: Any, argument: Any = None) -> str:
        """Get SQL for setting a PRAGMA.

        Args:
            name: PRAGMA name
            value: Value to set
            argument: Optional argument

        Returns:
            SQL string
        """
        return self.pragma_set_statement(name, value, argument).to_sql()[0]

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
