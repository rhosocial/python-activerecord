# src/rhosocial/activerecord/backend/impl/sqlite/pragma/info.py
"""
SQLite information query PRAGMA definitions.

Information pragmas are read-only queries that return metadata
about the database schema, structure, and state.

Reference: https://www.sqlite.org/pragma.html#toc
"""
from typing import Dict, List, Optional

from .base import PragmaCategory, PragmaInfo


# Information PRAGMA definitions
INFORMATION_PRAGMAS: Dict[str, PragmaInfo] = {
    'table_info': PragmaInfo(
        name='table_info',
        category=PragmaCategory.INFORMATION,
        description='Return information about the columns in a table',
        read_only=True,
        min_version=(3, 0, 0),
        value_type=list,
        requires_argument=True,
        argument_type=str,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_table_info'
    ),
    'table_xinfo': PragmaInfo(
        name='table_xinfo',
        category=PragmaCategory.INFORMATION,
        description='Return extended information about table columns (includes hidden columns)',
        read_only=True,
        min_version=(3, 26, 0),
        value_type=list,
        requires_argument=True,
        argument_type=str,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_table_xinfo'
    ),
    'index_info': PragmaInfo(
        name='index_info',
        category=PragmaCategory.INFORMATION,
        description='Return information about the columns in an index',
        read_only=True,
        min_version=(3, 0, 0),
        value_type=list,
        requires_argument=True,
        argument_type=str,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_index_info'
    ),
    'index_xinfo': PragmaInfo(
        name='index_xinfo',
        category=PragmaCategory.INFORMATION,
        description='Return extended information about index columns',
        read_only=True,
        min_version=(3, 9, 0),
        value_type=list,
        requires_argument=True,
        argument_type=str,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_index_xinfo'
    ),
    'index_list': PragmaInfo(
        name='index_list',
        category=PragmaCategory.INFORMATION,
        description='Return list of indexes for a table',
        read_only=True,
        min_version=(3, 0, 0),
        value_type=list,
        requires_argument=True,
        argument_type=str,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_index_list'
    ),
    'foreign_key_list': PragmaInfo(
        name='foreign_key_list',
        category=PragmaCategory.INFORMATION,
        description='Return list of foreign keys for a table',
        read_only=True,
        min_version=(3, 0, 0),
        value_type=list,
        requires_argument=True,
        argument_type=str,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_foreign_key_list'
    ),
    'database_list': PragmaInfo(
        name='database_list',
        category=PragmaCategory.INFORMATION,
        description='Return list of all database connections',
        read_only=True,
        min_version=(3, 0, 0),
        value_type=list,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_database_list'
    ),
    'collation_list': PragmaInfo(
        name='collation_list',
        category=PragmaCategory.INFORMATION,
        description='Return list of all collation sequences',
        read_only=True,
        min_version=(3, 0, 0),
        value_type=list,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_collation_list'
    ),
    'function_list': PragmaInfo(
        name='function_list',
        category=PragmaCategory.INFORMATION,
        description='Return list of all SQL functions',
        read_only=True,
        min_version=(3, 11, 0),
        value_type=list,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_function_list'
    ),
    'module_list': PragmaInfo(
        name='module_list',
        category=PragmaCategory.INFORMATION,
        description='Return list of all virtual table modules',
        read_only=True,
        min_version=(3, 11, 0),
        value_type=list,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_module_list'
    ),
    'pragma_list': PragmaInfo(
        name='pragma_list',
        category=PragmaCategory.INFORMATION,
        description='Return list of all PRAGMA commands',
        read_only=True,
        min_version=(3, 11, 0),
        value_type=list,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_pragma_list'
    ),
    'table_list': PragmaInfo(
        name='table_list',
        category=PragmaCategory.INFORMATION,
        description='Return list of all tables in the database',
        read_only=True,
        min_version=(3, 37, 0),
        value_type=list,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_table_list'
    ),
    'stats': PragmaInfo(
        name='stats',
        category=PragmaCategory.INFORMATION,
        description='Return information about tables and indices',
        read_only=True,
        min_version=(3, 22, 0),
        value_type=list,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_stats'
    ),
}


def get_information_pragma(name: str) -> Optional[PragmaInfo]:
    """Get information PRAGMA by name.
    
    Args:
        name: PRAGMA name
        
    Returns:
        PragmaInfo if found, None otherwise
    """
    return INFORMATION_PRAGMAS.get(name.lower())


def get_all_information_pragmas() -> Dict[str, PragmaInfo]:
    """Get all information PRAGMA definitions.
    
    Returns:
        Dictionary of PRAGMA name to PragmaInfo
    """
    return INFORMATION_PRAGMAS.copy()


def get_information_pragma_names() -> List[str]:
    """Get list of all information PRAGMA names.
    
    Returns:
        List of PRAGMA names
    """
    return list(INFORMATION_PRAGMAS.keys())
