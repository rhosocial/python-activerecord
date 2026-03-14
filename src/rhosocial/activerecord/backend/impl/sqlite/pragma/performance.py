# src/rhosocial/activerecord/backend/impl/sqlite/pragma/performance.py
"""
SQLite performance tuning PRAGMA definitions.

Performance pragmas control database performance-related settings
such as cache size, memory mapping, and page size.

Reference: https://www.sqlite.org/pragma.html#toc
"""
from typing import Any, Dict, List, Optional

from .base import PragmaCategory, PragmaInfo


# Performance PRAGMA definitions
PERFORMANCE_PRAGMAS: Dict[str, PragmaInfo] = {
    'cache_size': PragmaInfo(
        name='cache_size',
        category=PragmaCategory.PERFORMANCE,
        description='Change the suggested maximum number of database disk pages',
        read_only=False,
        min_version=(3, 0, 0),
        value_type=int,
        default_value=-2000,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_cache_size'
    ),
    'cache_spill': PragmaInfo(
        name='cache_spill',
        category=PragmaCategory.PERFORMANCE,
        description='Enable/disable spilling of cache pages to disk',
        read_only=False,
        min_version=(3, 8, 0),
        value_type=bool,
        allowed_values=[0, 1, True, False],
        default_value=True,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_cache_spill'
    ),
    'mmap_size': PragmaInfo(
        name='mmap_size',
        category=PragmaCategory.PERFORMANCE,
        description='Set the maximum size of memory-mapped I/O',
        read_only=False,
        min_version=(3, 7, 17),
        value_type=int,
        default_value=0,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_mmap_size'
    ),
    'page_size': PragmaInfo(
        name='page_size',
        category=PragmaCategory.PERFORMANCE,
        description='Set the database page size (must be set before first use)',
        read_only=False,
        min_version=(3, 0, 0),
        value_type=int,
        allowed_values=[512, 1024, 2048, 4096, 8192, 16384, 32768, 65536],
        default_value=4096,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_page_size'
    ),
    'max_page_count': PragmaInfo(
        name='max_page_count',
        category=PragmaCategory.PERFORMANCE,
        description='Set the maximum number of pages in the database',
        read_only=False,
        min_version=(3, 5, 0),
        value_type=int,
        default_value=1073741823,  # Maximum possible
        documentation_url='https://www.sqlite.org/pragma.html#pragma_max_page_count'
    ),
    'soft_heap_limit': PragmaInfo(
        name='soft_heap_limit',
        category=PragmaCategory.PERFORMANCE,
        description='Set the soft heap limit for the database connection',
        read_only=False,
        min_version=(3, 6, 7),
        value_type=int,
        default_value=0,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_soft_heap_limit'
    ),
    'hard_heap_limit': PragmaInfo(
        name='hard_heap_limit',
        category=PragmaCategory.PERFORMANCE,
        description='Set the hard heap limit for the database connection',
        read_only=False,
        min_version=(3, 30, 0),
        value_type=int,
        default_value=0,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_hard_heap_limit'
    ),
    'threads': PragmaInfo(
        name='threads',
        category=PragmaCategory.PERFORMANCE,
        description='Set the maximum number of worker threads',
        read_only=False,
        min_version=(3, 8, 11),
        value_type=int,
        default_value=0,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_threads'
    ),
}


def get_performance_pragma(name: str) -> Optional[PragmaInfo]:
    """Get performance PRAGMA information by name.
    
    Args:
        name: PRAGMA name
        
    Returns:
        PragmaInfo if found, None otherwise
    """
    return PERFORMANCE_PRAGMAS.get(name.lower())


def get_all_performance_pragmas() -> Dict[str, PragmaInfo]:
    """Get all performance PRAGMA definitions.
    
    Returns:
        Dictionary of PRAGMA name to PragmaInfo
    """
    return PERFORMANCE_PRAGMAS.copy()


def get_performance_pragma_names() -> List[str]:
    """Get list of all performance PRAGMA names.
    
    Returns:
        List of PRAGMA names
    """
    return list(PERFORMANCE_PRAGMAS.keys())
