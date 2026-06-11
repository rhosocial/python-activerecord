# src/rhosocial/activerecord/backend/dialect/mixins/introspection.py
from typing import List, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...introspection.types import IntrospectionScope
    from ...introspection.expressions import (
        DatabaseInfoExpression,
        TableListExpression,
        TableInfoExpression,
        ColumnInfoExpression,
        IndexInfoExpression,
        ForeignKeyExpression,
        ViewListExpression,
        ViewInfoExpression,
        TriggerListExpression,
        TriggerInfoExpression,
    )


class IntrospectionMixin:
    """
    Mixin for database introspection capability declaration.

    Dialects declare capabilities (supports_* methods) and provide format_*
    methods to generate database-specific SQL for introspection queries.
    The actual introspection implementation (query execution and result parsing)
    is in the backend layer via IntrospectionMixin from backend.introspection.mixins.

    Layer responsibilities:
    - Dialect layer (this mixin): Declares capabilities and formats SQL
    - Backend layer: Executes queries and parses results

    This base implementation returns False for all supports_* methods,
    indicating introspection is not supported by default. The format_*
    methods raise UnsupportedFeatureError when called.
    """

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """Whether introspection is supported."""
        return False

    def supports_database_info(self) -> bool:
        """Whether database information query is supported."""
        return False

    def supports_table_introspection(self) -> bool:
        """Whether table introspection is supported."""
        return False

    def supports_column_introspection(self) -> bool:
        """Whether column introspection is supported."""
        return False

    def supports_index_introspection(self) -> bool:
        """Whether index introspection is supported."""
        return False

    def supports_foreign_key_introspection(self) -> bool:
        """Whether foreign key introspection is supported."""
        return False

    def supports_view_introspection(self) -> bool:
        """Whether view introspection is supported."""
        return False

    def supports_trigger_introspection(self) -> bool:
        """Whether trigger introspection is supported."""
        return False

    # ========== Runtime Statistics ==========

    def supports_runtime_stats(self) -> bool:
        """Whether runtime statistics introspection is supported."""
        return False

    def supports_table_stats(self) -> bool:
        """Whether table statistics introspection is supported."""
        return False

    def supports_index_stats(self) -> bool:
        """Whether index statistics introspection is supported."""
        return False

    def supports_unused_indexes_detection(self) -> bool:
        """Whether unused indexes detection is supported."""
        return False

    # ========== Structure Information ==========

    def supports_partition_info(self) -> bool:
        """Whether partition information introspection is supported."""
        return False

    def supports_object_dependencies(self) -> bool:
        """Whether object dependencies introspection is supported."""
        return False

    def supports_extensions(self) -> bool:
        """Whether installed extensions introspection is supported."""
        return False

    # ========== DDL Extraction ==========

    def supports_ddl_extraction(self) -> bool:
        """Whether DDL extraction is supported."""
        return False

    def supports_ddl_extraction_native(self) -> bool:
        """Whether native DDL extraction is supported (False means assembly required)."""
        return False

    def get_supported_introspection_scopes(self) -> List["IntrospectionScope"]:
        """Get list of supported introspection scopes."""
        return []

    # ========== Query Formatting ==========

    def format_database_info_query(self, expr: "DatabaseInfoExpression") -> Tuple[str, tuple]:
        """
        Format database information query.

        Args:
            expr: Database info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If database info query is not supported.
        """
        if not self.supports_database_info():
            raise UnsupportedFeatureError(self.name, "database info query")
        raise NotImplementedError("Subclass must implement format_database_info_query")

    def format_table_list_query(self, expr: "TableListExpression") -> Tuple[str, tuple]:
        """
        Format table list query.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If table introspection is not supported.
        """
        if not self.supports_table_introspection():
            raise UnsupportedFeatureError(self.name, "table introspection")
        raise NotImplementedError("Subclass must implement format_table_list_query")

    def format_table_info_query(self, expr: "TableInfoExpression") -> Tuple[str, tuple]:
        """
        Format single table information query.

        Args:
            expr: Table info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If table introspection is not supported.
        """
        if not self.supports_table_introspection():
            raise UnsupportedFeatureError(self.name, "table introspection")
        raise NotImplementedError("Subclass must implement format_table_info_query")

    def format_column_info_query(self, expr: "ColumnInfoExpression") -> Tuple[str, tuple]:
        """
        Format column information query.

        Args:
            expr: Column info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If column introspection is not supported.
        """
        if not self.supports_column_introspection():
            raise UnsupportedFeatureError(self.name, "column introspection")
        raise NotImplementedError("Subclass must implement format_column_info_query")

    def format_index_info_query(self, expr: "IndexInfoExpression") -> Tuple[str, tuple]:
        """
        Format index information query.

        Args:
            expr: Index info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If index introspection is not supported.
        """
        if not self.supports_index_introspection():
            raise UnsupportedFeatureError(self.name, "index introspection")
        raise NotImplementedError("Subclass must implement format_index_info_query")

    def format_foreign_key_query(self, expr: "ForeignKeyExpression") -> Tuple[str, tuple]:
        """
        Format foreign key information query.

        Args:
            expr: Foreign key expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If foreign key introspection is not supported.
        """
        if not self.supports_foreign_key_introspection():
            raise UnsupportedFeatureError(self.name, "foreign key introspection")
        raise NotImplementedError("Subclass must implement format_foreign_key_query")

    def format_view_list_query(self, expr: "ViewListExpression") -> Tuple[str, tuple]:
        """
        Format view list query.

        Args:
            expr: View list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If view introspection is not supported.
        """
        if not self.supports_view_introspection():
            raise UnsupportedFeatureError(self.name, "view introspection")
        raise NotImplementedError("Subclass must implement format_view_list_query")

    def format_view_info_query(self, expr: "ViewInfoExpression") -> Tuple[str, tuple]:
        """
        Format single view information query.

        Args:
            expr: View info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If view introspection is not supported.
        """
        if not self.supports_view_introspection():
            raise UnsupportedFeatureError(self.name, "view introspection")
        raise NotImplementedError("Subclass must implement format_view_info_query")

    def format_trigger_list_query(self, expr: "TriggerListExpression") -> Tuple[str, tuple]:
        """
        Format trigger list query.

        Args:
            expr: Trigger list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If trigger introspection is not supported.
        """
        if not self.supports_trigger_introspection():
            raise UnsupportedFeatureError(self.name, "trigger introspection")
        raise NotImplementedError("Subclass must implement format_trigger_list_query")

    def format_trigger_info_query(self, expr: "TriggerInfoExpression") -> Tuple[str, tuple]:
        """
        Format single trigger information query.

        Args:
            expr: Trigger info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If trigger introspection is not supported.
        """
        if not self.supports_trigger_introspection():
            raise UnsupportedFeatureError(self.name, "trigger introspection")
        raise NotImplementedError("Subclass must implement format_trigger_info_query")


class AsyncIntrospectionMixin:
    """
    Mixin for async database introspection capability declaration.

    Async version of IntrospectionMixin with symmetric API.
    Dialects declare capabilities (supports_* methods) and provide format_*
    methods to generate database-specific SQL for introspection queries.

    Note: The format_* methods are synchronous even in async context because
    they only generate SQL strings without database I/O.

    This base implementation returns False for all supports_* methods,
    indicating introspection is not supported by default.
    """

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """Whether introspection is supported."""
        return False

    def supports_database_info(self) -> bool:
        """Whether database information query is supported."""
        return False

    def supports_table_introspection(self) -> bool:
        """Whether table introspection is supported."""
        return False

    def supports_column_introspection(self) -> bool:
        """Whether column introspection is supported."""
        return False

    def supports_index_introspection(self) -> bool:
        """Whether index introspection is supported."""
        return False

    def supports_foreign_key_introspection(self) -> bool:
        """Whether foreign key introspection is supported."""
        return False

    def supports_view_introspection(self) -> bool:
        """Whether view introspection is supported."""
        return False

    def supports_trigger_introspection(self) -> bool:
        """Whether trigger introspection is supported."""
        return False

    # ========== Runtime Statistics ==========

    def supports_runtime_stats(self) -> bool:
        """Whether runtime statistics introspection is supported."""
        return False

    def supports_table_stats(self) -> bool:
        """Whether table statistics introspection is supported."""
        return False

    def supports_index_stats(self) -> bool:
        """Whether index statistics introspection is supported."""
        return False

    def supports_unused_indexes_detection(self) -> bool:
        """Whether unused indexes detection is supported."""
        return False

    # ========== Structure Information ==========

    def supports_partition_info(self) -> bool:
        """Whether partition information introspection is supported."""
        return False

    def supports_object_dependencies(self) -> bool:
        """Whether object dependencies introspection is supported."""
        return False

    def supports_extensions(self) -> bool:
        """Whether installed extensions introspection is supported."""
        return False

    # ========== DDL Extraction ==========

    def supports_ddl_extraction(self) -> bool:
        """Whether DDL extraction is supported."""
        return False

    def supports_ddl_extraction_native(self) -> bool:
        """Whether native DDL extraction is supported (False means assembly required)."""
        return False

    def get_supported_introspection_scopes(self) -> List["IntrospectionScope"]:
        """Get list of supported introspection scopes."""
        return []

    # ========== Query Formatting ==========

    def format_database_info_query(self, expr: "DatabaseInfoExpression") -> Tuple[str, tuple]:
        """
        Format database information query.

        Args:
            expr: Database info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If database info query is not supported.
        """
        if not self.supports_database_info():
            raise UnsupportedFeatureError(self.name, "database info query")
        raise NotImplementedError("Subclass must implement format_database_info_query")

    def format_table_list_query(self, expr: "TableListExpression") -> Tuple[str, tuple]:
        """
        Format table list query.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If table introspection is not supported.
        """
        if not self.supports_table_introspection():
            raise UnsupportedFeatureError(self.name, "table introspection")
        raise NotImplementedError("Subclass must implement format_table_list_query")

    def format_table_info_query(self, expr: "TableInfoExpression") -> Tuple[str, tuple]:
        """
        Format single table information query.

        Args:
            expr: Table info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If table introspection is not supported.
        """
        if not self.supports_table_introspection():
            raise UnsupportedFeatureError(self.name, "table introspection")
        raise NotImplementedError("Subclass must implement format_table_info_query")

    def format_column_info_query(self, expr: "ColumnInfoExpression") -> Tuple[str, tuple]:
        """
        Format column information query.

        Args:
            expr: Column info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If column introspection is not supported.
        """
        if not self.supports_column_introspection():
            raise UnsupportedFeatureError(self.name, "column introspection")
        raise NotImplementedError("Subclass must implement format_column_info_query")

    def format_index_info_query(self, expr: "IndexInfoExpression") -> Tuple[str, tuple]:
        """
        Format index information query.

        Args:
            expr: Index info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If index introspection is not supported.
        """
        if not self.supports_index_introspection():
            raise UnsupportedFeatureError(self.name, "index introspection")
        raise NotImplementedError("Subclass must implement format_index_info_query")

    def format_foreign_key_query(self, expr: "ForeignKeyExpression") -> Tuple[str, tuple]:
        """
        Format foreign key information query.

        Args:
            expr: Foreign key expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If foreign key introspection is not supported.
        """
        if not self.supports_foreign_key_introspection():
            raise UnsupportedFeatureError(self.name, "foreign key introspection")
        raise NotImplementedError("Subclass must implement format_foreign_key_query")

    def format_view_list_query(self, expr: "ViewListExpression") -> Tuple[str, tuple]:
        """
        Format view list query.

        Args:
            expr: View list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If view introspection is not supported.
        """
        if not self.supports_view_introspection():
            raise UnsupportedFeatureError(self.name, "view introspection")
        raise NotImplementedError("Subclass must implement format_view_list_query")

    def format_view_info_query(self, expr: "ViewInfoExpression") -> Tuple[str, tuple]:
        """
        Format single view information query.

        Args:
            expr: View info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If view introspection is not supported.
        """
        if not self.supports_view_introspection():
            raise UnsupportedFeatureError(self.name, "view introspection")
        raise NotImplementedError("Subclass must implement format_view_info_query")

    def format_trigger_list_query(self, expr: "TriggerListExpression") -> Tuple[str, tuple]:
        """
        Format trigger list query.

        Args:
            expr: Trigger list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If trigger introspection is not supported.
        """
        if not self.supports_trigger_introspection():
            raise UnsupportedFeatureError(self.name, "trigger introspection")
        raise NotImplementedError("Subclass must implement format_trigger_list_query")

    def format_trigger_info_query(self, expr: "TriggerInfoExpression") -> Tuple[str, tuple]:
        """
        Format single trigger information query.

        Args:
            expr: Trigger info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: If trigger introspection is not supported.
        """
        if not self.supports_trigger_introspection():
            raise UnsupportedFeatureError(self.name, "trigger introspection")
        raise NotImplementedError("Subclass must implement format_trigger_info_query")
