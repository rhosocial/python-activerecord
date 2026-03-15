# src/rhosocial/activerecord/backend/impl/sqlite/pragma/compile_time.py
"""
SQLite compile-time PRAGMA definitions.

Compile-time pragmas provide information about how SQLite was compiled,
including available compile options and encoding settings.

Reference: https://www.sqlite.org/pragma.html#toc
"""
from typing import Any, Dict, List, Optional

from .base import PragmaCategory, PragmaInfo


# Compile-time PRAGMA definitions
COMPILE_TIME_PRAGMAS: Dict[str, PragmaInfo] = {
    'compile_options': PragmaInfo(
        name='compile_options',
        category=PragmaCategory.COMPILE_TIME,
        description='Return the compile-time options used to build SQLite',
        read_only=True,
        min_version=(3, 6, 23),
        value_type=list,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_compile_options'
    ),
    'encoding': PragmaInfo(
        name='encoding',
        category=PragmaCategory.COMPILE_TIME,
        description='Return the database encoding (UTF-8, UTF-16le, UTF-16be)',
        read_only=True,
        min_version=(3, 0, 0),
        value_type=str,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_encoding'
    ),
    'schema_version': PragmaInfo(
        name='schema_version',
        category=PragmaCategory.COMPILE_TIME,
        description='Return the schema version number',
        read_only=True,
        min_version=(3, 0, 0),
        value_type=int,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_schema_version'
    ),
    'user_version': PragmaInfo(
        name='user_version',
        category=PragmaCategory.COMPILE_TIME,
        description='Return or set the user version number',
        read_only=False,
        min_version=(3, 0, 0),
        value_type=int,
        default_value=0,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_user_version'
    ),
    'application_id': PragmaInfo(
        name='application_id',
        category=PragmaCategory.COMPILE_TIME,
        description='Return or set the application ID',
        read_only=False,
        min_version=(3, 7, 17),
        value_type=int,
        default_value=0,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_application_id'
    ),
}


def get_compile_time_pragma(name: str) -> Optional[PragmaInfo]:
    """Get compile-time PRAGMA information by name.
    
    Args:
        name: PRAGMA name
        
    Returns:
        PragmaInfo if found, None otherwise
    """
    return COMPILE_TIME_PRAGMAS.get(name.lower())


def get_all_compile_time_pragmas() -> Dict[str, PragmaInfo]:
    """Get all compile-time PRAGMA definitions.
    
    Returns:
        Dictionary of PRAGMA name to PragmaInfo
    """
    return COMPILE_TIME_PRAGMAS.copy()


def get_compile_time_pragma_names() -> List[str]:
    """Get list of all compile-time PRAGMA names.
    
    Returns:
        List of PRAGMA names
    """
    return list(COMPILE_TIME_PRAGMAS.keys())
