# src/rhosocial/activerecord/backend/dialect/protocols/introspect/async_introspection.py
"""Protocol mirroring AsyncIntrospectionMixin (async introspection capability)."""

from typing import List, Tuple, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from typing import runtime_checkable, Protocol

@runtime_checkable
class AsyncIntrospectionSupport(Protocol):
    def supports_introspection(self) -> bool:
        ...  # pragma: no cover

    def supports_database_info(self) -> bool:
        ...  # pragma: no cover

    def supports_table_introspection(self) -> bool:
        ...  # pragma: no cover

    def supports_column_introspection(self) -> bool:
        ...  # pragma: no cover

    def supports_index_introspection(self) -> bool:
        ...  # pragma: no cover

    def supports_foreign_key_introspection(self) -> bool:
        ...  # pragma: no cover

    def supports_view_introspection(self) -> bool:
        ...  # pragma: no cover

    def supports_trigger_introspection(self) -> bool:
        ...  # pragma: no cover

    def supports_runtime_stats(self) -> bool:
        ...  # pragma: no cover

    def supports_table_stats(self) -> bool:
        ...  # pragma: no cover

    def supports_index_stats(self) -> bool:
        ...  # pragma: no cover

    def supports_unused_indexes_detection(self) -> bool:
        ...  # pragma: no cover

    def supports_partition_info(self) -> bool:
        ...  # pragma: no cover

    def supports_object_dependencies(self) -> bool:
        ...  # pragma: no cover

    def supports_extensions(self) -> bool:
        ...  # pragma: no cover

    def supports_table_storage_introspection(self) -> bool:
        ...  # pragma: no cover

    def supports_column_data_profile(self) -> bool:
        ...  # pragma: no cover

    def supports_column_value_sample(self) -> bool:
        ...  # pragma: no cover

    def supports_join_coverage(self) -> bool:
        ...  # pragma: no cover

    def supports_ddl_extraction(self) -> bool:
        ...  # pragma: no cover

    def supports_ddl_extraction_native(self) -> bool:
        ...  # pragma: no cover

    def format_database_info_query_statement(self, expr: "DatabaseInfoQueryStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_table_list_query_statement(self, expr: "TableListQueryStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_table_info_query_statement(self, expr: "TableInfoQueryStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_column_info_query_statement(self, expr: "ColumnInfoQueryStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_index_info_query_statement(self, expr: "IndexInfoQueryStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_foreign_key_query_statement(self, expr: "ForeignKeyQueryStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_view_list_query_statement(self, expr: "ViewListQueryStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_view_info_query_statement(self, expr: "ViewInfoQueryStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_trigger_list_query_statement(self, expr: "TriggerListQueryStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_trigger_info_query_statement(self, expr: "TriggerInfoQueryStatement") -> Tuple[str, tuple]:
        ...  # pragma: no cover
