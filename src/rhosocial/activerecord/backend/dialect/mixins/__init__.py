# src/rhosocial/activerecord/backend/dialect/mixins/__init__.py
"""
SQL dialect mixins package.

All mixin classes are re-exported here to maintain backward compatibility.
Existing code using `from .mixins import XxxMixin` will continue to work.
"""

from .xml import (
    SQLXMLParsingMixin,
    SQLXMLSerializationMixin,
    SQLXMLConstructionMixin,
    SQLXMLAggregationMixin,
    SQLXMLQueryingMixin,
    SQLXMLMixin,
)
from .collation import CollationMixin
from .window import WindowFunctionMixin
from .cte import CTEMixin
from .upsert import UpsertMixin
from .join import LateralJoinMixin, JoinMixin
from .array import ArrayMixin
from .json import JSONMixin
from .explain import ExplainMixin
from .graph import GraphMixin, GraphTableMixin
from .merge import MergeMixin
from .temporal import TemporalTableMixin
from .pivot import PivotMixin
from .set_operation import SetOperationMixin
from .partition import PartitionMixin
from .ddl_table import TableMixin, ConstraintMixin
from .ddl_comment import CommentOnMixin
from .ddl_view import ViewMixin, TruncateMixin
from .ddl_schema import SchemaMixin
from .ddl_index import IndexMixin
from .ddl_sequence import SequenceMixin
from .ilike import ILIKEMixin
from .trigger import TriggerMixin
from .function import FunctionMixin, FunctionCallMixin
from .generated_column import GeneratedColumnMixin
from .auto_increment import AutoIncrementMixin
from .identity_column import IdentityColumnMixin
from .introspection import IntrospectionMixin, AsyncIntrospectionMixin
from .predicate import PredicateMixin
from .expression import ExpressionMixin
from .relation_source import RelationSourceMixin
from .schema_namespace import NamespaceMixin
from .object_table_name import TableNameMixin
from .object_view_name import ViewNameMixin
from .object_materialized_view_name import MaterializedViewNameMixin
from .object_foreign_table_name import ForeignTableNameMixin
from .object_index_name import IndexNameMixin
from .object_database_name import DatabaseNameMixin
from .object_property_graph_name import PropertyGraphNameMixin
from .object_schema_name import SchemaNameMixin
from .object_sequence_name import SequenceNameMixin
from .object_trigger_name import TriggerNameMixin
from .object_function_name import FunctionNameMixin
from .object_procedure_name import ProcedureNameMixin
from .object_type_name import TypeNameMixin
from .object_domain_name import DomainNameMixin
from .object_synonym_name import SynonymNameMixin
from .datetime import DateTimeMixin
from .dql import DQLMixin
from .dml import DMLMixin
from .ddl_column import DDLColumnMixin
from .data_type import DataTypeMixin
from .ddl_type import DDLTypeMixin
from .user_defined_type import UserDefinedTypeMixin
from .ddl_domain import DomainMixin
from .ddl_database import DatabaseMixin
from .transaction import TransactionControlMixin

__all__ = [
    "SQLXMLParsingMixin",
    "SQLXMLSerializationMixin",
    "SQLXMLConstructionMixin",
    "SQLXMLAggregationMixin",
    "SQLXMLQueryingMixin",
    "SQLXMLMixin",
    "CollationMixin",
    "WindowFunctionMixin",
    "CTEMixin",
    "UpsertMixin",
    "LateralJoinMixin",
    "JoinMixin",
    "ArrayMixin",
    "JSONMixin",
    "ExplainMixin",
    "GraphMixin",
    "GraphTableMixin",
    "MergeMixin",
    "TemporalTableMixin",
    "PivotMixin",
    "SetOperationMixin",
    "PartitionMixin",
    "TableMixin",
    "ConstraintMixin",
    "CommentOnMixin",
    "ViewMixin",
    "TruncateMixin",
    "SchemaMixin",
    "IndexMixin",
    "SequenceMixin",
    "ILIKEMixin",
    "TriggerMixin",
    "FunctionMixin",
    "FunctionCallMixin",
    "GeneratedColumnMixin",
    "AutoIncrementMixin",
    "IdentityColumnMixin",
    "IntrospectionMixin",
    "AsyncIntrospectionMixin",
    "PredicateMixin",
    "ExpressionMixin",
    "NamespaceMixin",
    "RelationSourceMixin",
    "TableNameMixin",
    "ViewNameMixin",
    "MaterializedViewNameMixin",
    "ForeignTableNameMixin",
    "IndexNameMixin",
    "PropertyGraphNameMixin",
    "SchemaNameMixin",
    "DatabaseNameMixin",
    "SequenceNameMixin",
    "TriggerNameMixin",
    "FunctionNameMixin",
    "ProcedureNameMixin",
    "TypeNameMixin",
    "DomainNameMixin",
    "SynonymNameMixin",
    "DateTimeMixin",
    "DQLMixin",
    "DMLMixin",
    "DDLColumnMixin",
    "DataTypeMixin",
    "DDLTypeMixin",
    "UserDefinedTypeMixin",
    "DomainMixin",
    "DatabaseMixin",
    "TransactionControlMixin",
]
