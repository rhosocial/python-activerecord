# src/rhosocial/activerecord/backend/impl/sqlite/pragma/config.py
"""
SQLite configuration PRAGMA definitions.

Configuration pragmas control database behavior and can be
modified at runtime. They affect how SQLite operates.

Reference: https://www.sqlite.org/pragma.html#toc
"""
from typing import Dict, List, Optional

from .base import PragmaCategory, PragmaInfo


# Configuration PRAGMA definitions
CONFIGURATION_PRAGMAS: Dict[str, PragmaInfo] = {
    'foreign_keys': PragmaInfo(
        name='foreign_keys',
        category=PragmaCategory.CONFIGURATION,
        description='Enable/disable foreign key constraint checking',
        read_only=False,
        min_version=(3, 6, 19),
        value_type=bool,
        allowed_values=[0, 1, True, False],
        default_value=False,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_foreign_keys'
    ),
    'journal_mode': PragmaInfo(
        name='journal_mode',
        category=PragmaCategory.CONFIGURATION,
        description='Control the journaling mode for database connections',
        read_only=False,
        min_version=(3, 0, 0),
        value_type=str,
        allowed_values=['DELETE', 'TRUNCATE', 'PERSIST', 'MEMORY', 'WAL', 'OFF'],
        default_value='DELETE',
        documentation_url='https://www.sqlite.org/pragma.html#pragma_journal_mode'
    ),
    'synchronous': PragmaInfo(
        name='synchronous',
        category=PragmaCategory.CONFIGURATION,
        description='Control how aggressively SQLite syncs data to disk',
        read_only=False,
        min_version=(3, 0, 0),
        value_type=str,
        allowed_values=['OFF', 'NORMAL', 'FULL', 'EXTRA'],
        default_value='FULL',
        documentation_url='https://www.sqlite.org/pragma.html#pragma_synchronous'
    ),
    'locking_mode': PragmaInfo(
        name='locking_mode',
        category=PragmaCategory.CONFIGURATION,
        description='Control the database connection locking mode',
        read_only=False,
        min_version=(3, 7, 0),
        value_type=str,
        allowed_values=['NORMAL', 'EXCLUSIVE'],
        default_value='NORMAL',
        documentation_url='https://www.sqlite.org/pragma.html#pragma_locking_mode'
    ),
    'temp_store': PragmaInfo(
        name='temp_store',
        category=PragmaCategory.CONFIGURATION,
        description='Control where temporary tables and indices are stored',
        read_only=False,
        min_version=(3, 0, 0),
        value_type=str,
        allowed_values=['DEFAULT', 'FILE', 'MEMORY'],
        default_value='DEFAULT',
        documentation_url='https://www.sqlite.org/pragma.html#pragma_temp_store'
    ),
    'auto_vacuum': PragmaInfo(
        name='auto_vacuum',
        category=PragmaCategory.CONFIGURATION,
        description='Control automatic vacuuming of the database',
        read_only=False,
        min_version=(3, 1, 0),
        value_type=str,
        allowed_values=['NONE', 'FULL', 'INCREMENTAL'],
        default_value='NONE',
        documentation_url='https://www.sqlite.org/pragma.html#pragma_auto_vacuum'
    ),
    'busy_timeout': PragmaInfo(
        name='busy_timeout',
        category=PragmaCategory.CONFIGURATION,
        description='Set the busy timeout in milliseconds',
        read_only=False,
        min_version=(3, 0, 0),
        value_type=int,
        default_value=0,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_busy_timeout'
    ),
    'cache_size': PragmaInfo(
        name='cache_size',
        category=PragmaCategory.CONFIGURATION,
        description='Change the suggested maximum number of database disk pages',
        read_only=False,
        min_version=(3, 0, 0),
        value_type=int,
        default_value=-2000,  # Negative means in KiB
        documentation_url='https://www.sqlite.org/pragma.html#pragma_cache_size'
    ),
    'recursive_triggers': PragmaInfo(
        name='recursive_triggers',
        category=PragmaCategory.CONFIGURATION,
        description='Enable/disable recursive trigger firing',
        read_only=False,
        min_version=(3, 6, 18),
        value_type=bool,
        allowed_values=[0, 1, True, False],
        default_value=False,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_recursive_triggers'
    ),
    'secure_delete': PragmaInfo(
        name='secure_delete',
        category=PragmaCategory.CONFIGURATION,
        description='Control whether deleted content is zeroed out',
        read_only=False,
        min_version=(3, 6, 18),
        value_type=bool,
        allowed_values=[0, 1, True, False, 'FAST'],
        default_value=False,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_secure_delete'
    ),
    'ignore_check_constraints': PragmaInfo(
        name='ignore_check_constraints',
        category=PragmaCategory.CONFIGURATION,
        description='Enable/disable CHECK constraint enforcement',
        read_only=False,
        min_version=(3, 7, 13),
        value_type=bool,
        allowed_values=[0, 1, True, False],
        default_value=False,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_ignore_check_constraints'
    ),
    'defer_foreign_keys': PragmaInfo(
        name='defer_foreign_keys',
        category=PragmaCategory.CONFIGURATION,
        description='Defer foreign key constraints until the transaction ends',
        read_only=False,
        min_version=(3, 8, 0),
        value_type=bool,
        allowed_values=[0, 1, True, False],
        default_value=False,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_defer_foreign_keys'
    ),
    'case_sensitive_like': PragmaInfo(
        name='case_sensitive_like',
        category=PragmaCategory.CONFIGURATION,
        description='Control case sensitivity of LIKE operator',
        read_only=False,
        min_version=(3, 2, 0),
        value_type=bool,
        allowed_values=[0, 1, True, False],
        default_value=False,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_case_sensitive_like'
    ),
    'count_changes': PragmaInfo(
        name='count_changes',
        category=PragmaCategory.CONFIGURATION,
        description='Return number of changed rows (deprecated)',
        read_only=False,
        min_version=(3, 0, 0),
        value_type=bool,
        allowed_values=[0, 1, True, False],
        default_value=False,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_count_changes'
    ),
    'default_cache_size': PragmaInfo(
        name='default_cache_size',
        category=PragmaCategory.CONFIGURATION,
        description='Set the default persistent cache size',
        read_only=False,
        min_version=(3, 0, 0),
        value_type=int,
        default_value=-2000,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_default_cache_size'
    ),
}


def get_configuration_pragma(name: str) -> Optional[PragmaInfo]:
    """Get configuration PRAGMA information by name.
    
    Args:
        name: PRAGMA name
        
    Returns:
        PragmaInfo if found, None otherwise
    """
    return CONFIGURATION_PRAGMAS.get(name.lower())


def get_all_configuration_pragmas() -> Dict[str, PragmaInfo]:
    """Get all configuration PRAGMA definitions.
    
    Returns:
        Dictionary of PRAGMA name to PragmaInfo
    """
    return CONFIGURATION_PRAGMAS.copy()


def get_configuration_pragma_names() -> List[str]:
    """Get list of all configuration PRAGMA names.
    
    Returns:
        List of PRAGMA names
    """
    return list(CONFIGURATION_PRAGMAS.keys())
