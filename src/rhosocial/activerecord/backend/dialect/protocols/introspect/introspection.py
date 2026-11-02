# src/rhosocial/activerecord/backend/dialect/protocols/introspectionsupport.py
"""IntrospectionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import List, Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...mixins.introspection import IntrospectionScope
    from ....expression.introspection import (
        ColumnInfoQueryStatement,
        DatabaseInfoQueryStatement,
        ForeignKeyQueryStatement,
        IndexInfoQueryStatement,
        TableInfoQueryStatement,
        TableListQueryStatement,
        TriggerInfoQueryStatement,
        TriggerListQueryStatement,
        UnusedIndexesQueryStatement,
        ViewInfoQueryStatement,
        ViewListQueryStatement,
    )


@runtime_checkable
class IntrospectionSupport(Protocol):
    """
    Protocol for database introspection capability declaration.

    This protocol defines methods that dialects implement to declare which
    introspection features they support. Dialects also provide format_*
    methods to generate database-specific SQL for introspection queries.

    Layer responsibilities:
    - Dialect layer: Declares capabilities (supports_*) and formats SQL (format_*)
    - Backend layer: Executes queries and parses results

    Expression pattern:
    - Expressions collect parameters (table_name, schema, options, etc.)
    - Dialects generate SQL from expression parameters
    - Backends execute SQL and parse results
    """

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """Whether introspection is supported."""
        ...  # pragma: no cover

    def supports_database_info(self) -> bool:
        """Whether database information query is supported."""
        ...  # pragma: no cover

    def supports_table_introspection(self) -> bool:
        """Whether table introspection is supported."""
        ...  # pragma: no cover

    def supports_column_introspection(self) -> bool:
        """Whether column introspection is supported."""
        ...  # pragma: no cover

    def supports_index_introspection(self) -> bool:
        """Whether index introspection is supported."""
        ...  # pragma: no cover

    def supports_foreign_key_introspection(self) -> bool:
        """Whether foreign key introspection is supported."""
        ...  # pragma: no cover

    def supports_view_introspection(self) -> bool:
        """Whether view introspection is supported."""
        ...  # pragma: no cover

    def supports_trigger_introspection(self) -> bool:
        """Whether trigger introspection is supported."""
        ...  # pragma: no cover

    # ========== Runtime Statistics ==========

    def supports_runtime_stats(self) -> bool:
        """Whether runtime statistics introspection is supported."""
        ...  # pragma: no cover

    def supports_table_stats(self) -> bool:
        """Whether table statistics introspection is supported."""
        ...  # pragma: no cover

    def supports_index_stats(self) -> bool:
        """Whether index statistics introspection is supported."""
        ...  # pragma: no cover

    def supports_unused_indexes_detection(self) -> bool:
        """Whether unused indexes detection is supported.

        Answering ``True`` means :meth:`format_unused_indexes_query_statement`
        renders for this dialect. What "unused" *means* is the backend's to
        state -- counters reset, views cover only the statistics they can see,
        and an index missing from the answer is absence of evidence, never
        proof of use. The common minimum returned is an address; the engine's
        own numbers ride on its subclass or in ``extra``.
        """
        ...  # pragma: no cover

    # ========== Structure Information ==========

    def supports_partition_info(self) -> bool:
        """Whether partition information introspection is supported."""
        ...  # pragma: no cover

    def supports_object_dependencies(self) -> bool:
        """Whether object dependencies introspection is supported."""
        ...  # pragma: no cover

    def supports_extensions(self) -> bool:
        """Whether this engine exposes a catalogue of installed add-on components.

        The question is uniform across engines; the answer is not.
        ``extension`` is not SQL-standard vocabulary -- each engine calls its
        loadable, inspectable add-ons something different, and the concept
        differs materially: PostgreSQL's are ``CREATE EXTENSION`` packages
        carrying a version and a schema (``pg_extension``), SQLite's are
        registered virtual table modules (``PRAGMA module_list``), MySQL's are
        plugins (``information_schema.plugins``). A ``True`` therefore promises
        that this engine *will answer*, never *what shape the answer takes*.

        This is the same situation as ``supports_fulltext_search``, where the
        mechanism differs completely (``MATCH ... AGAINST`` versus ``CONTAINS``)
        while the question stays worth asking through one name. What the probe
        buys is discoverability, not semantics -- so the field set of the
        answer lives in the backend's own result type, and reading that type
        (and the backend's docs) is required before relying on any field.
        """
        ...  # pragma: no cover

    def supports_table_storage_introspection(self) -> bool:
        """Whether per-table storage metrics introspection is supported.

        Declaring it means the dialect can answer the storage slots of
        ``IntrospectionTableInfo`` -- ``size_bytes``, ``row_count``, and
        where the engine's storage is row-plus-index shaped,
        ``data_size_bytes`` / ``index_size_bytes``. An engine whose storage
        answers no part of that (Firebird) answers False, and its CLI offers
        the family as "not supported here" rather than an empty list.
        """
        ...  # pragma: no cover

    # ========== DDL Extraction ==========

    def supports_ddl_extraction(self) -> bool:
        """Whether DDL extraction is supported."""
        ...  # pragma: no cover

    def supports_ddl_extraction_native(self) -> bool:
        """Whether native DDL extraction is supported (False means assembly required)."""
        ...  # pragma: no cover

    def get_supported_introspection_scopes(self) -> List["IntrospectionScope"]:
        """Get list of supported introspection scopes."""
        ...  # pragma: no cover

    # ========== Query Formatting ==========

    def format_database_info_query_statement(self, expr: "DatabaseInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format database information query.

        Args:
            expr: Database info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_table_list_query_statement(self, expr: "TableListQueryStatement") -> Tuple[str, tuple]:
        """
        Format table list query.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_table_info_query_statement(self, expr: "TableInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format single table information query.

        Args:
            expr: Table info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_column_info_query_statement(self, expr: "ColumnInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format column information query.

        Args:
            expr: Column info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_index_info_query_statement(self, expr: "IndexInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format index information query.

        Args:
            expr: Index info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_foreign_key_query_statement(self, expr: "ForeignKeyQueryStatement") -> Tuple[str, tuple]:
        """
        Format foreign key information query.

        Args:
            expr: Foreign key expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_view_list_query_statement(self, expr: "ViewListQueryStatement") -> Tuple[str, tuple]:
        """
        Format view list query.

        Args:
            expr: View list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_view_info_query_statement(self, expr: "ViewInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format single view information query.

        Args:
            expr: View info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_trigger_list_query_statement(self, expr: "TriggerListQueryStatement") -> Tuple[str, tuple]:
        """
        Format trigger list query.

        Args:
            expr: Trigger list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_trigger_info_query_statement(self, expr: "TriggerInfoQueryStatement") -> Tuple[str, tuple]:
        """
        Format single trigger information query.

        Args:
            expr: Trigger info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_unused_indexes_query_statement(
        self, expr: "UnusedIndexesQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format an unused-indexes listing.

        The one place the family's meaning is fixed: whatever an engine
        counts, the rendered query must return at least the three address
        columns -- schema, table, index -- because the caller receives
        ``UnusedIndexInfo`` and nothing downstream can rebuild an address out
        of a statistic. What the numbers *mean* is the backend's to state.

        Args:
            expr: Unused indexes expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover