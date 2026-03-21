# src/rhosocial/activerecord/backend/impl/sqlite/mixins.py
"""
SQLite-specific mixin implementations.

This module provides mixin classes that implement SQLite-specific features
defined in the protocols module, including extension and pragma support.
"""

from typing import Any, Dict, List, Optional, Tuple

from .extension import (
    SQLiteExtensionRegistry,
    get_registry,
    SQLiteExtensionInfo,
)
from .extension.extensions import (
    get_fts5_extension,
)
from .pragma import (
    PragmaCategory,
    PragmaInfo,
    get_pragma_info,
    get_all_pragma_infos,
    get_pragmas_by_category,
)


class SQLiteExtensionMixin:
    """Mixin for SQLite extension support.

    Provides methods for extension detection, version management,
    and feature checking.
    """

    _extension_registry: SQLiteExtensionRegistry = None

    def _ensure_extension_registry(self) -> SQLiteExtensionRegistry:
        """Ensure extension registry is initialized."""
        if self._extension_registry is None:
            self._extension_registry = get_registry()
            self._extension_registry.register(get_fts5_extension())
        return self._extension_registry

    def detect_extensions(self) -> Dict[str, SQLiteExtensionInfo]:
        """Detect all available extensions.

        Returns:
            Dictionary mapping extension names to their info
        """
        registry = self._ensure_extension_registry()
        version = getattr(self, "version", (3, 35, 0))
        return registry.detect_extensions(version)

    def is_extension_available(self, name: str) -> bool:
        """Check if a specific extension is available.

        Args:
            name: Extension name

        Returns:
            True if extension is available
        """
        registry = self._ensure_extension_registry()
        version = getattr(self, "version", (3, 35, 0))
        return registry.is_extension_available(name, version)

    def get_extension_info(self, name: str) -> Optional[SQLiteExtensionInfo]:
        """Get information about a specific extension.

        Args:
            name: Extension name

        Returns:
            Extension info, or None if not found
        """
        registry = self._ensure_extension_registry()
        version = getattr(self, "version", (3, 35, 0))
        return registry.get_extension_info(name, version)

    def check_extension_feature(self, ext_name: str, feature_name: str) -> bool:
        """Check if an extension feature is available.

        Args:
            ext_name: Extension name
            feature_name: Feature name

        Returns:
            True if feature is available
        """
        registry = self._ensure_extension_registry()
        version = getattr(self, "version", (3, 35, 0))
        return registry.check_extension_feature(ext_name, feature_name, version)

    def get_supported_extension_features(self, ext_name: str) -> List[str]:
        """Get list of supported features for an extension.

        Args:
            ext_name: Extension name

        Returns:
            List of supported feature names
        """
        registry = self._ensure_extension_registry()
        version = getattr(self, "version", (3, 35, 0))
        return registry.get_supported_features(ext_name, version)


class SQLitePragmaMixin:
    """Mixin for SQLite PRAGMA support.

    Provides methods for pragma query and manipulation.
    """

    def get_pragma_info(self, name: str) -> Optional[PragmaInfo]:
        """Get information about a specific PRAGMA.

        Args:
            name: PRAGMA name

        Returns:
            PragmaInfo, or None if not found
        """
        info = get_pragma_info(name)
        if info is None:
            return None

        version = getattr(self, "version", (3, 35, 0))
        if version < info.min_version:
            return None

        return info

    def get_pragma_sql(self, name: str, argument: Any = None) -> str:
        """Get SQL for reading a PRAGMA.

        Args:
            name: PRAGMA name
            argument: Optional argument

        Returns:
            SQL string
        """
        info = self.get_pragma_info(name)
        if info is None:
            raise ValueError(f"Unknown PRAGMA: {name}")

        if info.requires_argument and argument is not None:
            return f"PRAGMA {info.name}({argument})"
        return f"PRAGMA {info.name}"

    def set_pragma_sql(self, name: str, value: Any, argument: Any = None) -> str:
        """Get SQL for setting a PRAGMA.

        Args:
            name: PRAGMA name
            value: Value to set
            argument: Optional argument

        Returns:
            SQL string
        """
        info = self.get_pragma_info(name)
        if info is None:
            raise ValueError(f"Unknown PRAGMA: {name}")

        if info.read_only:
            raise ValueError(f"PRAGMA {name} is read-only and cannot be set")

        if info.allowed_values and value not in info.allowed_values:
            raise ValueError(f"Invalid value '{value}' for PRAGMA {name}. Allowed values: {info.allowed_values}")

        if info.requires_argument and argument is not None:
            return f"PRAGMA {info.name}({argument}) = {value}"
        return f"PRAGMA {info.name} = {value}"

    def is_pragma_available(self, name: str) -> bool:
        """Check if a PRAGMA is available.

        Args:
            name: PRAGMA name

        Returns:
            True if available
        """
        info = get_pragma_info(name)
        if info is None:
            return False

        version = getattr(self, "version", (3, 35, 0))
        return version >= info.min_version

    def get_pragmas_by_category(self, category: PragmaCategory) -> List[PragmaInfo]:
        """Get all pragmas in a category.

        Args:
            category: PRAGMA category

        Returns:
            List of PragmaInfo for pragmas in the category
        """
        version = getattr(self, "version", (3, 35, 0))
        return [info for info in get_pragmas_by_category(category) if version >= info.min_version]

    def get_all_pragma_infos(self) -> Dict[str, PragmaInfo]:
        """Get information for all known pragmas.

        Returns:
            Dictionary mapping PRAGMA names to their info
        """
        version = getattr(self, "version", (3, 35, 0))
        return {name: info for name, info in get_all_pragma_infos().items() if version >= info.min_version}


class FTS5Mixin(SQLiteExtensionMixin):
    """Mixin for FTS5 (Full-Text Search) support in SQLite.

    FTS5 is a virtual table module that provides full-text search capabilities.
    It is available since SQLite 3.9.0 (2015-11-02).

    This mixin provides methods for:
    - Creating and dropping FTS5 virtual tables
    - Formatting MATCH expressions for full-text queries
    - Ranking results using bm25()
    - Highlighting and snippet extraction
    """

    def supports_fts5(self) -> bool:
        """Whether FTS5 full-text search is supported.

        FTS5 is available since SQLite 3.9.0.

        Returns:
            True if FTS5 is supported
        """
        return self.check_extension_feature("fts5", "full_text_search")

    def supports_fts5_bm25(self) -> bool:
        """Whether BM25 ranking function is supported.

        BM25 is the default ranking function in FTS5, available
        since SQLite 3.9.0.

        Returns:
            True if BM25 is supported
        """
        return self.check_extension_feature("fts5", "bm25_ranking")

    def supports_fts5_highlight(self) -> bool:
        """Whether highlight() function is supported.

        The highlight() function returns a copy of the text with
        search terms surrounded by specified markers.

        Returns:
            True if highlight() is supported
        """
        return self.check_extension_feature("fts5", "highlight")

    def supports_fts5_snippet(self) -> bool:
        """Whether snippet() function is supported.

        The snippet() function returns a fragment of text with
        search terms highlighted.

        Returns:
            True if snippet() is supported
        """
        return self.check_extension_feature("fts5", "snippet")

    def supports_fts5_offset(self) -> bool:
        """Whether offset() function is supported.

        Returns the byte offset of the match within the original text.

        Returns:
            True if offset() is supported
        """
        return self.check_extension_feature("fts5", "offset")

    def get_supported_fts5_tokenizers(self) -> List[str]:
        """Get list of supported FTS5 tokenizers.

        Standard tokenizers:
        - 'unicode61': Default tokenizer, supports Unicode (since 3.9.0)
        - 'ascii': Simple ASCII tokenizer (since 3.9.0)
        - 'porter': Porter stemmer wrapper (since 3.9.0)
        - 'trigram': Trigram tokenizer (since 3.34.0)

        Returns:
            List of supported tokenizer names
        """
        tokenizers = ["unicode61", "ascii", "porter"]
        if self.check_extension_feature("fts5", "trigram_tokenizer"):
            tokenizers.append("trigram")
        return tokenizers

    def format_fts5_create_virtual_table(
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
        if not self.supports_fts5():
            from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

            raise UnsupportedFeatureError(
                getattr(self, "name", "sqlite"), "FTS5", "FTS5 full-text search requires SQLite 3.9.0 or later."
            )

        fts5 = get_fts5_extension()
        return fts5.format_create_virtual_table(
            table_name=table_name,
            columns=columns,
            tokenizer=tokenizer,
            tokenizer_options=tokenizer_options,
            prefix=prefix,
            content=content,
            content_rowid=content_rowid,
            tokenize=tokenize,
        )

    def format_fts5_match_expression(
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
        fts5 = get_fts5_extension()
        return fts5.format_match_expression(
            table_name=table_name,
            query=query,
            columns=columns,
            negate=negate,
        )

    def format_fts5_rank_expression(
        self,
        table_name: str,
        weights: Optional[List[float]] = None,
        bm25_params: Optional[Dict[str, float]] = None,
    ) -> Tuple[str, tuple]:
        """Format FTS5 ranking expression using bm25().

        Args:
            table_name: Name of the FTS5 virtual table
            weights: Column weights for ranking (order matches column order)
            bm25_params: BM25 parameters (k1, b) for ranking customization

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        fts5 = get_fts5_extension()
        return fts5.format_rank_expression(
            table_name=table_name,
            weights=weights,
            bm25_params=bm25_params,
        )

    def format_fts5_highlight_expression(
        self,
        table_name: str,
        column: str,
        query: str,
        prefix_marker: str = "<b>",
        suffix_marker: str = "</b>",
    ) -> Tuple[str, tuple]:
        """Format highlight() function expression.

        Args:
            table_name: Name of the FTS5 virtual table
            column: Column name to highlight
            query: Search query (for ranking)
            prefix_marker: HTML/text to prepend to matches
            suffix_marker: HTML/text to append to matches

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        fts5 = get_fts5_extension()
        return fts5.format_highlight_expression(
            table_name=table_name,
            column=column,
            query=query,
            prefix_marker=prefix_marker,
            suffix_marker=suffix_marker,
        )

    def format_fts5_snippet_expression(
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
        fts5 = get_fts5_extension()
        return fts5.format_snippet_expression(
            table_name=table_name,
            column=column,
            query=query,
            prefix_marker=prefix_marker,
            suffix_marker=suffix_marker,
            context_tokens=context_tokens,
            ellipsis=ellipsis,
        )

    def format_fts5_drop_virtual_table(
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
        fts5 = get_fts5_extension()
        return fts5.format_drop_virtual_table(
            table_name=table_name,
            if_exists=if_exists,
        )
