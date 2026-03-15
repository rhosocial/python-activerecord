# src/rhosocial/activerecord/backend/impl/sqlite/pragma/wal.py
"""
SQLite WAL (Write-Ahead Logging) PRAGMA definitions.

WAL pragmas control the Write-Ahead Logging mode and
checkpointing behavior.

Reference: https://www.sqlite.org/pragma.html#toc
"""
from typing import Any, Dict, List, Optional

from .base import PragmaCategory, PragmaInfo


# WAL PRAGMA definitions
WAL_PRAGMAS: Dict[str, PragmaInfo] = {
    'wal_checkpoint': PragmaInfo(
        name='wal_checkpoint',
        category=PragmaCategory.WAL,
        description='Checkpoint the database in WAL mode',
        read_only=True,
        min_version=(3, 7, 0),
        value_type=list,
        requires_argument=True,
        argument_type=str,
        allowed_values=[None, 'PASSIVE', 'FULL', 'RESTART', 'TRUNCATE'],
        documentation_url='https://www.sqlite.org/pragma.html#pragma_wal_checkpoint'
    ),
    'wal_autocheckpoint': PragmaInfo(
        name='wal_autocheckpoint',
        category=PragmaCategory.WAL,
        description='Set the auto-checkpoint interval in pages',
        read_only=False,
        min_version=(3, 7, 0),
        value_type=int,
        default_value=1000,
        documentation_url='https://www.sqlite.org/pragma.html#pragma_wal_autocheckpoint'
    ),
}


def get_wal_pragma(name: str) -> Optional[PragmaInfo]:
    """Get WAL PRAGMA information by name.
    
    Args:
        name: PRAGMA name
        
    Returns:
        PragmaInfo if found, None otherwise
    """
    return WAL_PRAGMAS.get(name.lower())


def get_all_wal_pragmas() -> Dict[str, PragmaInfo]:
    """Get all WAL PRAGMA definitions.
    
    Returns:
        Dictionary of PRAGMA name to PragmaInfo
    """
    return WAL_PRAGMAS.copy()


def get_wal_pragma_names() -> List[str]:
    """Get list of all WAL PRAGMA names.
    
    Returns:
        List of PRAGMA names
    """
    return list(WAL_PRAGMAS.keys())
