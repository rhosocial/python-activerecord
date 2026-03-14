# src/rhosocial/activerecord/backend/impl/sqlite/pragma/__init__.py
"""
SQLite PRAGMA framework.

This module provides a comprehensive framework for SQLite PRAGMA support,
including pragma categories, information classes, and utilities.

SQLite PRAGMA statements are used to:
- Query and modify database configuration
- Inspect database schema and statistics
- Perform integrity checks
- Control performance-related settings
"""
from typing import Dict, List, Optional

from .base import (
    PragmaCategory,
    PragmaInfo,
    PragmaProtocol,
    PragmaBase,
    SQLitePragmaSupport,
)
from .config import (
    CONFIGURATION_PRAGMAS,
    get_configuration_pragma,
    get_all_configuration_pragmas,
    get_configuration_pragma_names,
)
from .info import (
    INFORMATION_PRAGMAS,
    get_information_pragma,
    get_all_information_pragmas,
    get_information_pragma_names,
)
from .debug import (
    DEBUG_PRAGMAS,
    get_debug_pragma,
    get_all_debug_pragmas,
    get_debug_pragma_names,
)
from .performance import (
    PERFORMANCE_PRAGMAS,
    get_performance_pragma,
    get_all_performance_pragmas,
    get_performance_pragma_names,
)
from .wal import (
    WAL_PRAGMAS,
    get_wal_pragma,
    get_all_wal_pragmas,
    get_wal_pragma_names,
)
from .compile_time import (
    COMPILE_TIME_PRAGMAS,
    get_compile_time_pragma,
    get_all_compile_time_pragmas,
    get_compile_time_pragma_names,
)


# Aggregate all pragmas
ALL_PRAGMAS = {}
ALL_PRAGMAS.update(CONFIGURATION_PRAGMAS)
ALL_PRAGMAS.update(INFORMATION_PRAGMAS)
ALL_PRAGMAS.update(DEBUG_PRAGMAS)
ALL_PRAGMAS.update(PERFORMANCE_PRAGMAS)
ALL_PRAGMAS.update(WAL_PRAGMAS)
ALL_PRAGMAS.update(COMPILE_TIME_PRAGMAS)


def get_pragma_info(name: str) -> Optional[PragmaInfo]:
    """Get PRAGMA information by name.
    
    Args:
        name: PRAGMA name
        
    Returns:
        PragmaInfo if found, None otherwise
    """
    return ALL_PRAGMAS.get(name.lower())


def get_all_pragma_infos() -> Dict[str, PragmaInfo]:
    """Get all PRAGMA definitions.
    
    Returns:
        Dictionary of PRAGMA name to PragmaInfo
    """
    return ALL_PRAGMAS.copy()


def get_pragma_names() -> List[str]:
    """Get list of all PRAGMA names.
    
    Returns:
        List of PRAGMA names
    """
    return list(ALL_PRAGMAS.keys())


def get_pragmas_by_category(category: PragmaCategory) -> List[PragmaInfo]:
    """Get all pragmas in a category.
    
    Args:
        category: PRAGMA category
        
    Returns:
        List of PragmaInfo for pragmas in the category
    """
    return [info for info in ALL_PRAGMAS.values() if info.category == category]


__all__ = [
    # Base
    'PragmaCategory',
    'PragmaInfo',
    'PragmaProtocol',
    'PragmaBase',
    'SQLitePragmaSupport',
    # Configuration pragmas
    'CONFIGURATION_PRAGMAS',
    'get_configuration_pragma',
    'get_all_configuration_pragmas',
    'get_configuration_pragma_names',
    # Information pragmas
    'INFORMATION_PRAGMAS',
    'get_information_pragma',
    'get_all_information_pragmas',
    'get_information_pragma_names',
    # Debug pragmas
    'DEBUG_PRAGMAS',
    'get_debug_pragma',
    'get_all_debug_pragmas',
    'get_debug_pragma_names',
    # Performance pragmas
    'PERFORMANCE_PRAGMAS',
    'get_performance_pragma',
    'get_all_performance_pragmas',
    'get_performance_pragma_names',
    # WAL pragmas
    'WAL_PRAGMAS',
    'get_wal_pragma',
    'get_all_wal_pragmas',
    'get_wal_pragma_names',
    # Compile-time pragmas
    'COMPILE_TIME_PRAGMAS',
    'get_compile_time_pragma',
    'get_all_compile_time_pragmas',
    'get_compile_time_pragma_names',
    # Aggregate
    'ALL_PRAGMAS',
    'get_pragma_info',
    'get_all_pragma_infos',
    'get_pragma_names',
    'get_pragmas_by_category',
]
