# src/rhosocial/activerecord/backend/impl/sqlite/extension/extensions/fts3_4.py
"""
SQLite FTS3/FTS4 (Full-Text Search) extension implementation.

FTS3 and FTS4 are legacy versions of SQLite's full-text search engine.
They are deprecated in favor of FTS5 but still available for compatibility.

FTS3: Available since SQLite 3.5.0 (2007-11-26)
FTS4: Available since SQLite 3.7.4 (2010-12-07)

Note: For new projects, use FTS5 instead.

Reference: https://www.sqlite.org/fts3.html
"""
from typing import Optional

from ..base import ExtensionType, SQLiteExtensionBase


class FTS4Extension(SQLiteExtensionBase):
    """FTS4 (Full-Text Search version 4) extension.
    
    FTS4 is a legacy full-text search engine, superseded by FTS5.
    It provides basic full-text search capabilities with matchinfo(),
    offsets(), and snippet() functions.
    
    Note:
        FTS4 is deprecated. Use FTS5 for new projects.
    
    Features:
        - Full-text search with MATCH operator
        - matchinfo() for result statistics
        - offsets() for match positions
        - snippet() for result formatting
        - Porter and unicode61 tokenizers
    
    Example:
        >>> fts4 = FTS4Extension()
        >>> fts4.is_available((3, 7, 4))
        True
        >>> fts4.deprecated
        True
    """
    
    def __init__(self):
        """Initialize FTS4 extension."""
        super().__init__(
            name='fts4',
            extension_type=ExtensionType.BUILTIN,
            min_version=(3, 7, 4),
            deprecated=True,
            successor='fts5',
            description='Full-Text Search version 4 (legacy) - Predecessor to FTS5',
            features={
                'full_text_search': {'min_version': (3, 7, 4)},
                'matchinfo': {'min_version': (3, 7, 4)},
                'offsets': {'min_version': (3, 7, 4)},
                'snippet': {'min_version': (3, 7, 4)},
                'porter_tokenizer': {'min_version': (3, 7, 4)},
                'unicode61_tokenizer': {'min_version': (3, 7, 4)},
                'ascii_tokenizer': {'min_version': (3, 7, 4)},
            },
            documentation_url='https://www.sqlite.org/fts3.html'
        )


class FTS3Extension(SQLiteExtensionBase):
    """FTS3 (Full-Text Search version 3) extension.
    
    FTS3 is the original full-text search implementation for SQLite.
    It is the oldest version and should be avoided for new projects.
    
    Note:
        FTS3 is deprecated. Use FTS5 for new projects.
    
    Features:
        - Basic full-text search with MATCH operator
        - matchinfo() for result statistics
        - offsets() for match positions
        - snippet() for result formatting
    
    Example:
        >>> fts3 = FTS3Extension()
        >>> fts3.is_available((3, 5, 0))
        True
        >>> fts3.deprecated
        True
    """
    
    def __init__(self):
        """Initialize FTS3 extension."""
        super().__init__(
            name='fts3',
            extension_type=ExtensionType.BUILTIN,
            min_version=(3, 5, 0),
            deprecated=True,
            successor='fts4',
            description='Full-Text Search version 3 (legacy) - Original FTS implementation',
            features={
                'full_text_search': {'min_version': (3, 5, 0)},
                'matchinfo': {'min_version': (3, 5, 0)},
                'offsets': {'min_version': (3, 5, 0)},
                'snippet': {'min_version': (3, 5, 0)},
            },
            documentation_url='https://www.sqlite.org/fts3.html'
        )


# Singleton instances
_fts4_extension: Optional[FTS4Extension] = None
_fts3_extension: Optional[FTS3Extension] = None


def get_fts4_extension() -> FTS4Extension:
    """Get the FTS4 extension singleton.
    
    Returns:
        FTS4Extension instance
    """
    global _fts4_extension
    if _fts4_extension is None:
        _fts4_extension = FTS4Extension()
    return _fts4_extension


def get_fts3_extension() -> FTS3Extension:
    """Get the FTS3 extension singleton.
    
    Returns:
        FTS3Extension instance
    """
    global _fts3_extension
    if _fts3_extension is None:
        _fts3_extension = FTS3Extension()
    return _fts3_extension
