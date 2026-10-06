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
        ColumnInfoExpression,
        DatabaseInfoExpression,
        ForeignKeyExpression,
        IndexInfoExpression,
        TableInfoExpression,
        TableListExpression,
        TriggerInfoExpression,
        TriggerListExpression,
        ViewInfoExpression,
        ViewListExpression,
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
        """Whether unused indexes detection is supported."""
        ...  # pragma: no cover

    # ========== Structure Information ==========

    def supports_partition_info(self) -> bool:
        """Whether partition information introspection is supported."""
        ...  # pragma: no cover

    def supports_object_dependencies(self) -> bool:
        """Whether object dependencies introspection is supported."""
        ...  # pragma: no cover

    def supports_extensions(self) -> bool:
        """Whether installed extensions introspection is supported."""
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

    def format_database_info_query(self, expr: "DatabaseInfoExpression") -> Tuple[str, tuple]:
        """
        Format database information query.

        Args:
            expr: Database info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_table_list_query(self, expr: "TableListExpression") -> Tuple[str, tuple]:
        """
        Format table list query.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_table_info_query(self, expr: "TableInfoExpression") -> Tuple[str, tuple]:
        """
        Format single table information query.

        Args:
            expr: Table info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_column_info_query(self, expr: "ColumnInfoExpression") -> Tuple[str, tuple]:
        """
        Format column information query.

        Args:
            expr: Column info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_index_info_query(self, expr: "IndexInfoExpression") -> Tuple[str, tuple]:
        """
        Format index information query.

        Args:
            expr: Index info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_foreign_key_query(self, expr: "ForeignKeyExpression") -> Tuple[str, tuple]:
        """
        Format foreign key information query.

        Args:
            expr: Foreign key expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_view_list_query(self, expr: "ViewListExpression") -> Tuple[str, tuple]:
        """
        Format view list query.

        Args:
            expr: View list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_view_info_query(self, expr: "ViewInfoExpression") -> Tuple[str, tuple]:
        """
        Format single view information query.

        Args:
            expr: View info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_trigger_list_query(self, expr: "TriggerListExpression") -> Tuple[str, tuple]:
        """
        Format trigger list query.

        Args:
            expr: Trigger list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_trigger_info_query(self, expr: "TriggerInfoExpression") -> Tuple[str, tuple]:
        """
        Format single trigger information query.

        Args:
            expr: Trigger info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover
