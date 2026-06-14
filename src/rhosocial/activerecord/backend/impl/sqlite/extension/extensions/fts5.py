# src/rhosocial/activerecord/backend/impl/sqlite/extension/extensions/fts5.py
"""
SQLite FTS5 (Full-Text Search) extension implementation.

FTS5 is a virtual table module that provides full-text search capabilities
for SQLite databases. It is available since SQLite 3.9.0 (2015-11-02).

Key features:
- Full-text search with customizable tokenizers
- BM25 ranking function for relevance scoring
- Phrase queries, NEAR queries, AND/OR/NOT operators
- Column filters and prefix queries
- highlight() and snippet() functions (NOTE: offset/offsets are FTS3/FTS4 only)

Reference: https://www.sqlite.org/fts5.html
"""

from typing import List, Tuple

from ..base import ExtensionType, SQLiteExtensionBase


class FTS5Extension(SQLiteExtensionBase):
    """FTS5 (Full-Text Search version 5) extension.

    FTS5 is the latest version of SQLite's full-text search engine.
    This class provides metadata and version detection only.
    SQL generation has been moved to SQLiteFTS5Mixin.

    Example:
        >>> fts5 = FTS5Extension()
        >>> fts5.is_available((3, 35, 0))
        True
        >>> fts5.check_feature('trigram_tokenizer', (3, 34, 0))
        True
    """

    def __init__(self):
        """Initialize FTS5 extension."""
        super().__init__(
            name="fts5",
            extension_type=ExtensionType.BUILTIN,
            min_version=(3, 9, 0),
            deprecated=False,
            description="Full-Text Search version 5 - Advanced full-text search with customizable tokenizers",
            features={
                "full_text_search": {"min_version": (3, 9, 0)},
                "bm25_ranking": {"min_version": (3, 9, 0)},
                "highlight": {"min_version": (3, 9, 0)},
                "snippet": {"min_version": (3, 9, 0)},
                "porter_tokenizer": {"min_version": (3, 9, 0)},
                "unicode61_tokenizer": {"min_version": (3, 9, 0)},
                "ascii_tokenizer": {"min_version": (3, 9, 0)},
                "trigram_tokenizer": {"min_version": (3, 34, 0)},
                "column_filters": {"min_version": (3, 9, 0)},
                "phrase_queries": {"min_version": (3, 9, 0)},
                "near_queries": {"min_version": (3, 9, 0)},
            },
            documentation_url="https://www.sqlite.org/fts5.html",
        )

    def get_supported_tokenizers(self, version: Tuple[int, int, int]) -> List[str]:
        """Get list of supported tokenizers for given SQLite version."""
        tokenizers = ["unicode61", "ascii", "porter"]
        if self.check_feature("trigram_tokenizer", version):
            tokenizers.append("trigram")
        return tokenizers


# Singleton instance
_fts5_extension: Optional[FTS5Extension] = None


def get_fts5_extension() -> FTS5Extension:
    """Get the FTS5 extension singleton.

    Returns:
        FTS5Extension instance
    """
    global _fts5_extension
    if _fts5_extension is None:
        _fts5_extension = FTS5Extension()
    return _fts5_extension
