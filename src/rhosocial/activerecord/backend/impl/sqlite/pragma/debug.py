# src/rhosocial/activerecord/backend/impl/sqlite/pragma/debug.py
"""
SQLite debug and diagnostic PRAGMA definitions.

Debug pragmas are used for database integrity checking,
analysis, and debugging purposes.

Reference: https://www.sqlite.org/pragma.html#toc
"""

from typing import Dict, List, Optional

from .base import PragmaCategory, PragmaInfo


# Debug PRAGMA definitions
DEBUG_PRAGMAS: Dict[str, PragmaInfo] = {
    "integrity_check": PragmaInfo(
        name="integrity_check",
        category=PragmaCategory.DEBUG,
        description="Check database integrity and consistency",
        read_only=True,
        min_version=(3, 0, 0),
        value_type=list,
        documentation_url="https://www.sqlite.org/pragma.html#pragma_integrity_check",
    ),
    "quick_check": PragmaInfo(
        name="quick_check",
        category=PragmaCategory.DEBUG,
        description="Quick integrity check (faster but less thorough)",
        read_only=True,
        min_version=(3, 1, 6),
        value_type=list,
        documentation_url="https://www.sqlite.org/pragma.html#pragma_quick_check",
    ),
    "foreign_key_check": PragmaInfo(
        name="foreign_key_check",
        category=PragmaCategory.DEBUG,
        description="Check foreign key constraints",
        read_only=True,
        min_version=(3, 6, 19),
        value_type=list,
        documentation_url="https://www.sqlite.org/pragma.html#pragma_foreign_key_check",
    ),
    "analysis_limit": PragmaInfo(
        name="analysis_limit",
        category=PragmaCategory.DEBUG,
        description="Limit the amount of analysis performed by ANALYZE",
        read_only=False,
        min_version=(3, 32, 0),
        value_type=int,
        default_value=1000,
        documentation_url="https://www.sqlite.org/pragma.html#pragma_analysis_limit",
    ),
    "data_version": PragmaInfo(
        name="data_version",
        category=PragmaCategory.DEBUG,
        description="Return the data version number",
        read_only=True,
        min_version=(3, 7, 9),
        value_type=int,
        documentation_url="https://www.sqlite.org/pragma.html#pragma_data_version",
    ),
    "freelist_count": PragmaInfo(
        name="freelist_count",
        category=PragmaCategory.DEBUG,
        description="Return the number of unused pages in the database file",
        read_only=True,
        min_version=(3, 8, 0),
        value_type=int,
        documentation_url="https://www.sqlite.org/pragma.html#pragma_freelist_count",
    ),
    "page_count": PragmaInfo(
        name="page_count",
        category=PragmaCategory.DEBUG,
        description="Return the total number of pages in the database file",
        read_only=True,
        min_version=(3, 8, 0),
        value_type=int,
        documentation_url="https://www.sqlite.org/pragma.html#pragma_page_count",
    ),
}


def get_debug_pragma(name: str) -> Optional[PragmaInfo]:
    """Get debug PRAGMA information by name.

    Args:
        name: PRAGMA name

    Returns:
        PragmaInfo if found, None otherwise
    """
    return DEBUG_PRAGMAS.get(name.lower())


def get_all_debug_pragmas() -> Dict[str, PragmaInfo]:
    """Get all debug PRAGMA definitions.

    Returns:
        Dictionary of PRAGMA name to PragmaInfo
    """
    return DEBUG_PRAGMAS.copy()


def get_debug_pragma_names() -> List[str]:
    """Get list of all debug PRAGMA names.

    Returns:
        List of PRAGMA names
    """
    return list(DEBUG_PRAGMAS.keys())
