# src/rhosocial/activerecord/backend/impl/sqlite/mixins.py
"""
SQLite-specific mixin implementations.

This module provides mixin classes that implement SQLite-specific features
defined in the protocols module, including extension, pragma, and introspection
capability declaration.
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.introspection.types import IntrospectionScope
    from rhosocial.activerecord.backend.expression.introspection import (
        DatabaseInfoExpression,
        TableListExpression,
        TableInfoExpression,
        ColumnInfoExpression,
        IndexInfoExpression,
        ForeignKeyExpression,
    )

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

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
    _runtime_params: Dict[str, Any] = {}

    def _ensure_extension_registry(self) -> SQLiteExtensionRegistry:
        """Ensure extension registry is initialized."""
        if self._extension_registry is None:
            self._extension_registry = get_registry()
            self._extension_registry.register(get_fts5_extension())
        return self._extension_registry

    def set_runtime_param(self, key: str, value: Any) -> None:
        """Set a runtime parameter (detected after connection)."""
        self._runtime_params[key] = value

    def get_runtime_param(self, key: str, default: Any = None) -> Any:
        """Get a runtime parameter."""
        return self._runtime_params.get(key, default)

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


class SQLiteVirtualTableMixin(SQLiteExtensionMixin):
    """Mixin for SQLite virtual table support.

    Provides methods for creating and managing virtual tables
    including R-Tree, FTS5, Geopoly, and other virtual table modules.

    Version requirements:
    - Virtual tables (CREATE VIRTUAL TABLE): SQLite 3.8.8+
    - R-Tree: SQLite 3.6.0+
    - FTS5: SQLite 3.9.0+
    - Geopoly: SQLite 3.26.0+
    """

    # ========== Capability Detection ==========

    def supports_virtual_table(self) -> bool:
        """Whether virtual tables are supported."""
        version = getattr(self, "version", (3, 35, 0))
        return version >= (3, 8, 8)

    def supports_rtree(self) -> bool:
        """Whether R-Tree virtual table is supported.

        Requires SQLITE_ENABLE_RTREE compile option.
        Falls back to version-based check if compile options not available.
        """
        compile_options = self.get_runtime_param("compile_options", {})
        if compile_options:
            return "ENABLE_RTREE" in compile_options
        version = getattr(self, "version", (3, 35, 0))
        return version >= (3, 6, 0)

    def supports_fts5(self) -> bool:
        """Whether FTS5 virtual table is supported.

        Requires SQLITE_ENABLE_FTS5 compile option.
        Falls back to version-based check if compile options not available.
        """
        compile_options = self.get_runtime_param("compile_options", {})
        if compile_options:
            return "ENABLE_FTS5" in compile_options
        version = getattr(self, "version", (3, 35, 0))
        return version >= (3, 9, 0)

    def supports_geopoly(self) -> bool:
        """Whether Geopoly virtual table is supported.

        Requires SQLITE_ENABLE_GEOPOLY compile option.
        Falls back to version-based check if compile options not available.
        """
        compile_options = self.get_runtime_param("compile_options", {})
        if compile_options:
            return "ENABLE_GEOPOLY" in compile_options
        version = getattr(self, "version", (3, 35, 0))
        return version >= (3, 26, 0)

    def supports_math_functions(self) -> bool:
        """Whether built-in math functions are supported.

        SQLite 3.35.0+ includes built-in math functions, but they must be
        enabled at compile time. Runtime detection is needed for older versions.

        Returns:
            True if math functions are supported
        """
        version = getattr(self, "version", (3, 35, 0))
        if version >= (3, 35, 0):
            return self.get_runtime_param("math_functions_available", True)
        return False

    def supports_json1_extension(self) -> bool:
        """Whether json1 extension is available.

        The json1 extension provides JSON functions. It was an optional
        extension in older SQLite versions. Starting from 3.38.0,
        it's built-in by default. Runtime detection is needed for
        older versions.

        Returns:
            True if json1 extension is available
        """
        version = getattr(self, "version", (3, 35, 0))
        if version >= (3, 38, 0):
            return True
        return self.get_runtime_param("json1_available", False)

    # ========== FTS5 Capability Detection ==========

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

    # ========== Virtual Table SQL Formatting ==========

    def format_create_virtual_table(
        self,
        module: str,
        table_name: str,
        columns: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE statement.

        Args:
            module: Virtual table module (rtree, fts5, geopoly, etc.)
            table_name: Name of the virtual table
            columns: List of column names
            options: Optional module-specific options

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if module.lower() == "rtree":
            return self._format_rtree_create(table_name, columns, options)
        elif module.lower() == "fts5":
            return self._format_fts5_create(table_name, columns, options)
        elif module.lower() == "geopoly":
            return self._format_geopoly_create(table_name, columns, options)
        else:
            raise ValueError(f"Unknown virtual table module: {module}")

    def _format_rtree_create(
        self,
        table_name: str,
        columns: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE for R-Tree."""
        from .extension.extensions.rtree import get_rtree_extension

        version = getattr(self, "version", (3, 35, 0))
        if version < (3, 6, 0):
            raise UnsupportedFeatureError(
                getattr(self, "name", "sqlite"), "R-Tree", "R-Tree requires SQLite 3.6.0 or later."
            )

        rtree = get_rtree_extension()
        dimensions = options.get("dimensions", 2) if options else 2
        return rtree.format_create_virtual_table(
            table_name=table_name,
            dimensions=dimensions,
        )

    def _format_fts5_create(
        self,
        table_name: str,
        columns: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE for FTS5."""
        return self.format_fts5_create_virtual_table(
            table_name=table_name,
            columns=columns,
            **(options or {}),
        )

    def _format_geopoly_create(
        self,
        table_name: str,
        columns: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, tuple]:
        """Format CREATE VIRTUAL TABLE for Geopoly."""
        from .extension.extensions.geopoly import get_geopoly_extension

        version = getattr(self, "version", (3, 35, 0))
        if version < (3, 26, 0):
            raise UnsupportedFeatureError(
                getattr(self, "name", "sqlite"), "Geopoly", "Geopoly requires SQLite 3.26.0 or later."
            )

        geopoly = get_geopoly_extension()
        extra_cols = []
        for c in columns:
            if c != '_shape':
                extra_cols.append(c)
        extra_columns = extra_cols if extra_cols else None
        return geopoly.format_create_virtual_table(
            table_name=table_name,
            content_table=options.get("content") if options else None,
            extra_columns=extra_columns,
        )

    def format_drop_virtual_table(
        self,
        table_name: str,
        if_exists: bool = False,
    ) -> Tuple[str, tuple]:
        """Format DROP TABLE statement for virtual table.

        Args:
            table_name: Name of the virtual table
            if_exists: Add IF EXISTS clause

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        if if_exists:
            return f'DROP TABLE IF EXISTS "{table_name}"', ()
        return f'DROP TABLE "{table_name}"', ()

    # ========== FTS5 SQL Formatting ==========

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

    def format_match_predicate(
        self,
        table: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ) -> Tuple[str, tuple]:
        """Format full-text search MATCH predicate for FTS.

        This method delegates to format_fts5_match_expression for
        the actual formatting logic.

        Args:
            table: Name of the FTS table
            query: Full-text search query string
            columns: Specific columns to search (None for all columns)
            negate: If True, negate the match (NOT MATCH)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return self.format_fts5_match_expression(
            table_name=table,
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

    def format_fts5_offset_expression(
        self,
        table_name: str,
        column: str,
    ) -> Tuple[str, tuple]:
        """Format offset() function expression.

        The offset() function returns the byte offset of the current
        match within the column content.

        Args:
            table_name: Name of the FTS5 virtual table
            column: Column name to get offsets for

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        fts5 = get_fts5_extension()
        return fts5.format_offset_expression(
            table_name=table_name,
            column=column,
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


class SQLiteIntrospectionCapabilityMixin:
    """SQLite introspection capability declaration.

    This mixin implements the IntrospectionSupport protocol by declaring
    which introspection features SQLite supports based on version.
    The actual introspection implementation is in the backend layer
    via SQLiteIntrospectionMixin from the introspection module.

    Dialects only declare capabilities (supports_* methods), they do not
    implement the actual introspection methods.

    Version requirements for SQLite introspection features:
    - PRAGMA table_list: SQLite 3.37.0+ (fallback to sqlite_master query)
    - PRAGMA table_xinfo: SQLite 3.26.0+ (includes hidden columns)
    - PRAGMA table_info: All versions
    - PRAGMA index_list/index_info: All versions
    - PRAGMA foreign_key_list: SQLite 3.6.19+
    """

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """SQLite supports introspection."""
        return True

    def supports_database_info(self) -> bool:
        """SQLite supports database info."""
        return True

    def supports_table_introspection(self) -> bool:
        """SQLite supports table introspection."""
        return True

    def supports_column_introspection(self) -> bool:
        """SQLite supports column introspection.

        PRAGMA table_info is available in all versions.
        PRAGMA table_xinfo (with hidden column support) needs 3.26.0+.
        """
        return True

    def supports_index_introspection(self) -> bool:
        """SQLite supports index introspection."""
        return True

    def supports_foreign_key_introspection(self) -> bool:
        """SQLite supports foreign key introspection.

        PRAGMA foreign_key_list was added in SQLite 3.6.19 (2009-10-14).
        Note: Foreign key constraints are disabled by default and must be
        enabled via 'PRAGMA foreign_keys = ON'.
        """
        version = getattr(self, "version", (3, 35, 0))
        return version >= (3, 6, 19)

    def supports_view_introspection(self) -> bool:
        """SQLite supports view introspection."""
        return True

    def supports_trigger_introspection(self) -> bool:
        """SQLite supports trigger introspection."""
        return True

    # ========== Runtime Statistics ==========

    def supports_runtime_stats(self) -> bool:
        """SQLite does not support runtime statistics introspection."""
        return False

    def supports_table_stats(self) -> bool:
        """SQLite does not support table statistics introspection."""
        return False

    def supports_index_stats(self) -> bool:
        """SQLite does not support index statistics introspection."""
        return False

    def supports_unused_indexes_detection(self) -> bool:
        """SQLite does not support unused indexes detection."""
        return False

    # ========== Structure Information ==========

    def supports_partition_info(self) -> bool:
        """SQLite does not support partition information (no partitions in SQLite)."""
        return False

    def supports_object_dependencies(self) -> bool:
        """SQLite does not support object dependencies introspection."""
        return False

    def supports_extensions(self) -> bool:
        """SQLite supports extension introspection via pragma_module_list."""
        return True

    # ========== DDL Extraction ==========

    def supports_ddl_extraction(self) -> bool:
        """SQLite supports DDL extraction via sqlite_master."""
        return True

    def supports_ddl_extraction_native(self) -> bool:
        """SQLite does not have native DDL extraction (requires assembly)."""
        return False

    # ========== Fine-grained Capability Detection ==========

    def supports_table_list_pragma(self) -> bool:
        """PRAGMA table_list requires SQLite 3.37.0+.

        Returns:
            True if PRAGMA table_list is available.
            If False, fallback to sqlite_master query.
        """
        return self.version >= (3, 37, 0)

    def supports_table_xinfo_pragma(self) -> bool:
        """PRAGMA table_xinfo (includes hidden columns) requires SQLite 3.26.0+.

        Returns:
            True if PRAGMA table_xinfo is available.
            If False, use PRAGMA table_info instead.
        """
        return self.version >= (3, 26, 0)

    def get_supported_introspection_scopes(self) -> List["IntrospectionScope"]:
        """Get list of supported introspection scopes."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        scopes = [
            IntrospectionScope.DATABASE,
            IntrospectionScope.TABLE,
            IntrospectionScope.COLUMN,
            IntrospectionScope.INDEX,
            IntrospectionScope.VIEW,
            IntrospectionScope.TRIGGER,
        ]
        # Foreign key introspection requires SQLite 3.6.19+
        if self.supports_foreign_key_introspection():
            scopes.append(IntrospectionScope.FOREIGN_KEY)
        return scopes

    # ========== Query Formatting ==========

    def _quote_identifier(self, name: str) -> str:
        """Quote an identifier for SQLite.

        SQLite uses double quotes for identifiers.

        Args:
            name: The identifier name to quote.

        Returns:
            The quoted identifier.
        """
        return f'"{name}"'

    def format_database_info_query(self, expr: "DatabaseInfoExpression") -> Tuple[str, tuple]:
        """Format database information query.

        SQLite doesn't have a specific query for database info, so we use
        sqlite_version() and count tables in sqlite_master.

        Args:
            expr: Database info expression with parameters.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        sql = "SELECT sqlite_version() AS version"
        return (sql, ())

    def format_table_list_query(self, expr: "TableListExpression") -> Tuple[str, tuple]:
        """Format table list query.

        For SQLite 3.37.0+, use PRAGMA table_list.
        For older versions, query sqlite_master table.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        schema = params.get("schema") or "main"
        include_views = params.get("include_views", True)
        include_system = params.get("include_system", False)
        table_type = params.get("table_type")

        # Use PRAGMA table_list for SQLite 3.37.0+
        if self.supports_table_list_pragma():
            sql = f"PRAGMA {schema}.table_list"
            return (sql, ())

        # Fallback to sqlite_master query for older versions
        sql = "SELECT name, type FROM sqlite_master WHERE type IN ('table'"
        if include_views:
            sql += ", 'view'"
        sql += ")"

        # Exclude system tables unless requested
        if not include_system:
            sql += " AND name NOT LIKE 'sqlite_%'"

        # Filter by table type if specified
        if table_type:
            if table_type == "BASE TABLE":
                sql += " AND type = 'table'"
            elif table_type == "VIEW":
                sql += " AND type = 'view'"

        sql += " ORDER BY name"
        return (sql, ())

    def format_table_info_query(self, expr: "TableInfoExpression") -> Tuple[str, tuple]:
        """Format single table information query.

        Query sqlite_master for table details.

        Args:
            expr: Table info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema") or "main"

        sql = f"SELECT name, type, sql FROM {schema}.sqlite_master WHERE name = ?"
        return (sql, (table_name,))

    def format_column_info_query(self, expr: "ColumnInfoExpression") -> Tuple[str, tuple]:
        """Format column information query.

        For SQLite 3.26.0+, can use PRAGMA table_xinfo to include hidden columns.
        Otherwise, use PRAGMA table_info.

        Args:
            expr: Column info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        include_hidden = params.get("include_hidden", False)
        schema = params.get("schema") or "main"

        # Use table_xinfo for hidden columns if supported and requested
        if include_hidden and self.supports_table_xinfo_pragma():
            sql = f"PRAGMA {schema}.table_xinfo({self._quote_identifier(table_name)})"
        else:
            sql = f"PRAGMA {schema}.table_info({self._quote_identifier(table_name)})"

        return (sql, ())

    def format_index_info_query(self, expr: "IndexInfoExpression") -> Tuple[str, tuple]:
        """Format index information query.

        Use PRAGMA index_list to get indexes for a table.

        Args:
            expr: Index info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema") or "main"

        sql = f"PRAGMA {schema}.index_list({self._quote_identifier(table_name)})"
        return (sql, ())

    def format_foreign_key_query(self, expr: "ForeignKeyExpression") -> Tuple[str, tuple]:
        """Format foreign key information query.

        Use PRAGMA foreign_key_list to get foreign keys for a table.

        Args:
            expr: Foreign key expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema") or "main"

        sql = f"PRAGMA {schema}.foreign_key_list({self._quote_identifier(table_name)})"
        return (sql, ())

    def format_view_list_query(self, expr: "ViewListExpression") -> Tuple[str, tuple]:
        """Format view list query.

        Query sqlite_master for views.

        Args:
            expr: View list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        schema = params.get("schema") or "main"
        include_system = params.get("include_system", False)

        sql = f"SELECT name FROM {schema}.sqlite_master WHERE type = 'view'"

        # Exclude system views unless requested
        if not include_system:
            sql += " AND name NOT LIKE 'sqlite_%'"

        sql += " ORDER BY name"
        return (sql, ())

    def format_view_info_query(self, expr: "ViewInfoExpression") -> Tuple[str, tuple]:
        """Format single view information query.

        Query sqlite_master for view details.

        Args:
            expr: View info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        view_name = params.get("view_name", "")
        schema = params.get("schema") or "main"

        sql = f"SELECT name, sql FROM {schema}.sqlite_master WHERE type = 'view' AND name = ?"
        return (sql, (view_name,))

    def format_trigger_list_query(self, expr: "TriggerListExpression") -> Tuple[str, tuple]:
        """Format trigger list query.

        Query sqlite_master for triggers, optionally filtered by table.

        Args:
            expr: Trigger list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name")
        schema = params.get("schema") or "main"

        sql = f"SELECT name, tbl_name, sql FROM {schema}.sqlite_master WHERE type = 'trigger'"
        if table_name:
            sql += " AND tbl_name = ?"
            return (sql, (table_name,))

        sql += " ORDER BY name"
        return (sql, ())

    def format_trigger_info_query(self, expr: "TriggerInfoExpression") -> Tuple[str, tuple]:
        """Format single trigger information query.

        Query sqlite_master for trigger details.

        Args:
            expr: Trigger info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        trigger_name = params.get("trigger_name", "")
        schema = params.get("schema") or "main"

        sql = f"SELECT name, tbl_name, sql FROM {schema}.sqlite_master WHERE type = 'trigger' AND name = ?"
        return (sql, (trigger_name,))
