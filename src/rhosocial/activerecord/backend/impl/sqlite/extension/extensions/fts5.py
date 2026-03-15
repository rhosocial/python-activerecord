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
- highlight() and snippet() functions

Reference: https://www.sqlite.org/fts5.html
"""
from typing import Any, Dict, List, Optional, Tuple

from ..base import ExtensionType, SQLiteExtensionBase, SQLiteExtensionInfo


class FTS5Extension(SQLiteExtensionBase):
    """FTS5 (Full-Text Search version 5) extension.
    
    FTS5 is the latest version of SQLite's full-text search engine,
    providing advanced search capabilities with customizable tokenizers
    and the BM25 ranking algorithm.
    
    Features:
        - Full-text search with MATCH operator
        - BM25 ranking for relevance scoring
        - Multiple tokenizer options (unicode61, ascii, porter, trigram)
        - highlight() and snippet() functions for result formatting
        - Phrase queries, NEAR queries, AND/OR/NOT operators
        - Column-specific searches
        - Prefix searches
    
    Tokenizers:
        - unicode61: Default Unicode tokenizer (since 3.9.0)
        - ascii: Simple ASCII tokenizer (since 3.9.0)
        - porter: Porter stemmer wrapper (since 3.9.0)
        - trigram: Trigram tokenizer (since 3.34.0)
    
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
            name='fts5',
            extension_type=ExtensionType.BUILTIN,
            min_version=(3, 9, 0),
            deprecated=False,
            description='Full-Text Search version 5 - Advanced full-text search with customizable tokenizers',
            features={
                'full_text_search': {'min_version': (3, 9, 0)},
                'bm25_ranking': {'min_version': (3, 9, 0)},
                'highlight': {'min_version': (3, 9, 0)},
                'snippet': {'min_version': (3, 9, 0)},
                'offset': {'min_version': (3, 9, 0)},
                'porter_tokenizer': {'min_version': (3, 9, 0)},
                'unicode61_tokenizer': {'min_version': (3, 9, 0)},
                'ascii_tokenizer': {'min_version': (3, 9, 0)},
                'trigram_tokenizer': {'min_version': (3, 34, 0)},
                'column_filters': {'min_version': (3, 9, 0)},
                'phrase_queries': {'min_version': (3, 9, 0)},
                'near_queries': {'min_version': (3, 9, 0)},
            },
            documentation_url='https://www.sqlite.org/fts5.html'
        )
    
    def get_supported_tokenizers(self, version: Tuple[int, int, int]) -> List[str]:
        """Get list of supported tokenizers for given SQLite version.
        
        Args:
            version: SQLite version tuple (major, minor, patch)
            
        Returns:
            List of supported tokenizer names
        """
        tokenizers = ['unicode61', 'ascii', 'porter']
        if self.check_feature('trigram_tokenizer', version):
            tokenizers.append('trigram')
        return tokenizers
    
    def format_create_virtual_table(
        self,
        table_name: str,
        columns: List[str],
        tokenizer: Optional[str] = None,
        tokenizer_options: Optional[Dict[str, Any]] = None,
        prefix: Optional[List[int]] = None,
        content: Optional[str] = None,
        content_rowid: Optional[str] = None,
        tokenize: Optional[str] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE statement for FTS5.
        
        Args:
            table_name: Name of the FTS5 virtual table
            columns: List of column names to be indexed
            tokenizer: Tokenizer name (e.g., 'unicode61', 'porter')
            tokenizer_options: Tokenizer options (e.g., {'remove_diacritics': 1})
            prefix: List of prefix lengths for prefix indexing
            content: Content table name (for external content FTS5)
            content_rowid: Column name for rowid in content table
            tokenize: Full tokenize specification string (alternative to tokenizer)
            
        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        options = []
        
        if tokenize:
            options.append(f"tokenize='{tokenize}'")
        elif tokenizer:
            if tokenizer_options:
                opt_parts = []
                for k, v in tokenizer_options.items():
                    opt_parts.append(f"{k} {v}")
                opts_str = " ".join(opt_parts)
                options.append(f"tokenize='{tokenizer} {opts_str}'")
            else:
                options.append(f"tokenize='{tokenizer}'")
        
        if prefix:
            prefix_str = " ".join(str(p) for p in prefix)
            options.append(f"prefix='{prefix_str}'")
        
        if content:
            options.append(f"content='{content}'")
        
        if content_rowid:
            options.append(f"content_rowid='{content_rowid}'")
        
        cols_str = ", ".join(f'"{c}"' for c in columns)
        
        if options:
            opts_str = ", ".join(options)
            sql = f'CREATE VIRTUAL TABLE "{table_name}" USING fts5({cols_str}, {opts_str})'
        else:
            sql = f'CREATE VIRTUAL TABLE "{table_name}" USING fts5({cols_str})'
        
        return sql, ()
    
    def format_match_expression(
        self,
        table_name: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ) -> Tuple[str, tuple]:
        """Format FTS5 MATCH expression for use in WHERE clause.
        
        Args:
            table_name: Name of the FTS5 virtual table
            query: Full-text search query string
            columns: Specific columns to search (None for all columns)
            negate: If True, negate the match (NOT MATCH)
            
        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if columns:
            col_prefix = " OR ".join(f"{c}:" for c in columns)
            match_query = f"{{{col_prefix}}} {query}"
        else:
            match_query = query
        
        if negate:
            sql = f'"{table_name}" NOT MATCH ?'
        else:
            sql = f'"{table_name}" MATCH ?'
        
        return sql, (match_query,)
    
    def format_rank_expression(
        self,
        table_name: str,
        weights: Optional[List[float]] = None,
        bm25_params: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, tuple]:
        """Format FTS5 ranking expression using bm25().
        
        BM25 is the default ranking algorithm for FTS5. It calculates
        relevance scores based on term frequency and document length.
        
        Args:
            table_name: Name of the FTS5 virtual table
            weights: Column weights for ranking (order matches column order)
            bm25_params: BM25 parameters (k1, b) for ranking customization
            
        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        params = []
        
        if weights and bm25_params:
            weight_str = ", ".join(str(w) for w in weights)
            param_parts = []
            for k, v in bm25_params.items():
                param_parts.extend([f"'{k}'", str(v)])
            param_str = ", ".join(param_parts)
            sql = f'bm25("{table_name}", {weight_str}, {param_str})'
        elif weights:
            weight_str = ", ".join(str(w) for w in weights)
            sql = f'bm25("{table_name}", {weight_str})'
        elif bm25_params:
            param_parts = []
            for k, v in bm25_params.items():
                param_parts.extend([f"'{k}'", str(v)])
            param_str = ", ".join(param_parts)
            sql = f'bm25("{table_name}", {param_str})'
        else:
            sql = f'bm25("{table_name}")'
        
        return sql, tuple(params)
    
    def format_highlight_expression(
        self,
        table_name: str,
        column: str,
        query: str,
        prefix_marker: str = "<b>",
        suffix_marker: str = "</b>",
    ) -> Tuple[str, tuple]:
        """Format highlight() function expression.
        
        The highlight() function returns a copy of the text with all
        instances of the search terms surrounded by the specified markers.
        
        Args:
            table_name: Name of the FTS5 virtual table
            column: Column name to highlight
            query: Search query (for ranking)
            prefix_marker: HTML/text to prepend to matches
            suffix_marker: HTML/text to append to matches
            
        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        sql = f'highlight("{table_name}", "{column}", ?, ?)'
        return sql, (prefix_marker, suffix_marker)
    
    def format_snippet_expression(
        self,
        table_name: str,
        column: str,
        query: str,
        prefix_marker: str = "<b>",
        suffix_marker: str = "</b>",
        context_tokens: int = 10,
        ellipsis: str = "...",
    ) -> Tuple[str, tuple]:
        """Format snippet() function expression.
        
        The snippet() function returns a fragment of text with the
        first occurrence of each search term highlighted.
        
        Args:
            table_name: Name of the FTS5 virtual table
            column: Column name to snippet
            query: Search query (for ranking)
            prefix_marker: HTML/text to prepend to matches
            suffix_marker: HTML/text to append to matches
            context_tokens: Number of context tokens around match
            ellipsis: String to use as ellipsis marker
            
        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        sql = f'snippet("{table_name}", "{column}", ?, ?, ?, ?)'
        return sql, (prefix_marker, suffix_marker, ellipsis, context_tokens)
    
    def format_drop_virtual_table(
        self,
        table_name: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """Format DROP TABLE statement for FTS5 virtual table.
        
        Args:
            table_name: Name of the FTS5 virtual table to drop
            if_exists: If True, add IF EXISTS clause
            
        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if if_exists:
            sql = f'DROP TABLE IF EXISTS "{table_name}"'
        else:
            sql = f'DROP TABLE "{table_name}"'
        return sql, ()


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
