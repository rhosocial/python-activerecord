# src/rhosocial/activerecord/backend/dialect/protocols/family/RelationSourceSupport.py
"""Protocol mirror of RelationSourceMixin (family-level feature group). Members/order/signatures identical."""

from typing import Any, List, Tuple, Union, TYPE_CHECKING
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.objects import RelationObject
from rhosocial.activerecord.backend.expression.sources import JSONTableColumn
from typing import runtime_checkable, Protocol


@runtime_checkable
class RelationSourceSupport(Protocol):
    def supports_derived_table(self) -> bool:
        ...  # pragma: no cover

    def supports_values_table_constructor(self) -> bool:
        ...  # pragma: no cover

    def supports_table_function(self) -> bool:
        ...  # pragma: no cover

    def format_named_relation(self, expr: "NamedRelationRef") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def source_alias_separator(self) -> str:
        ...  # pragma: no cover

    def append_source_alias(self, sql: str, source: "TableSource") -> str:
        ...  # pragma: no cover

    def format_source_document(self, expr: Union[BaseExpression, str]) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_derived_table(self, expr: "DerivedTableSource") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_values_table(self, expr: "ValuesTableSource") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_table_function(self, expr: "TableFunctionSource") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_graph_table(self, expr: "GraphTableSource") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_json_table(self, expr: "JsonTableSource") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def join_source_columns(self, columns: List[Any], render_column: Any) -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_json_table_column(self, expr: "JSONTableColumn") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_source_column_type(self, expr: "JSONTableColumn | XMLTableColumn") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_xml_table(self, expr: "XmlTableSource") -> Tuple[str, tuple]:
        ...  # pragma: no cover

    def format_xml_table_column(self, expr: "XMLTableColumn") -> Tuple[str, tuple]:
        ...  # pragma: no cover
