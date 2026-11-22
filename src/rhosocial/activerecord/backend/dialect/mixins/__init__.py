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
from .trim import TrimMixin
from .string_ops import LpadMixin, RepeatMixin, RpadMixin
from .json import JSONMixin
from .uuid import UUIDMixin
from .explain import ExplainMixin
from .graph import GraphMixin, GraphTableMixin
from .merge import MergeMixin
from .temporal import TemporalTableMixin
from .pivot import PivotMixin
from .set_operation import SetOperationMixin
from .partition import PartitionMixin
from .ddl_table import TableMixin, ConstraintMixin
from .ddl_comment import CommentMixin
from .ddl_view import ViewMixin, TruncateMixin
from .ddl_schema import SchemaMixin
from .ddl_index import IndexMixin
from .ddl_sequence import SequenceMixin
from .ilike import ILIKEMixin
from .trigger import TriggerMixin
from .function import FunctionMixin, FunctionCallMixin
from .generated_column import GeneratedColumnMixin
from .auto_increment import AutoIncrementColumnMixin
from .identity_column import IdentityColumnMixin
from .introspection import IntrospectionMixin, AsyncIntrospectionMixin
from .predicate import PredicateMixin
from .expression import ExpressionMixin
from .relation_source import RelationSourceMixin
from .schema_namespace import NamespaceMixin
from .object_table_name import TableObjectMixin
from .object_view_name import ViewObjectMixin
from .object_materialized_view_name import MaterializedViewObjectMixin
from .object_foreign_table_name import ForeignTableObjectMixin
from .object_index_name import IndexObjectMixin
from .object_database_name import DatabaseNameMixin
from .object_property_graph_name import PropertyGraphNameMixin
from .object_schema_name import SchemaNameMixin
from .object_sequence_name import SequenceObjectMixin
from .object_trigger_name import TriggerObjectMixin
from .object_synonym_name import SynonymObjectMixin
from .datetime import DateTimeMixin
from .dql import DQLMixin
from .dml import DMLMixin
from .ddl_column import DDLColumnMixin
from .data_type import DataTypeMixin
from .column_type import ColumnTypeMixin
from .ddl_type import DataTypeMixin
from .user_defined_type import UserDefinedTypeMixin
from .ddl_domain import DomainMixin
from .ddl_database import DatabaseMixin
from .transaction import TransactionControlMixin

from .create_database_mixin import CreateDatabaseMixin
from .alter_database_mixin import AlterDatabaseMixin
from .drop_database_mixin import DropDatabaseMixin
from .create_domain_mixin import CreateDomainMixin
from .alter_domain_mixin import AlterDomainMixin
from .drop_domain_mixin import DropDomainMixin
from .create_sequence_mixin import CreateSequenceMixin
from .alter_sequence_mixin import AlterSequenceMixin
from .drop_sequence_mixin import DropSequenceMixin
from .create_view_mixin import CreateViewMixin
from .drop_view_mixin import DropViewMixin
from .materialized_view_mixin import MaterializedViewMixin
from .create_trigger_mixin import CreateTriggerMixin
from .drop_trigger_mixin import DropTriggerMixin
from .create_schema_mixin import CreateSchemaMixin
from .drop_schema_mixin import DropSchemaMixin
from .create_routine_mixin import CreateRoutineMixin
from .drop_routine_mixin import DropRoutineMixin
from .sql_function_mixin import SQLFunctionMixin

from .drop_type_mixin import DropTypeMixin
from .alter_type_mixin import AlterTypeMixin
from .create_type_mixin import CreateTypeMixin
from .fulltext_index_mixin import FulltextIndexMixin
from .drop_index_mixin import DropIndexMixin
from .create_index_mixin import CreateIndexMixin
from .type_object_mixin import TypeObjectMixin
from .routine_object_mixin import RoutineObjectMixin

from .create_table_using_template_mixin import CreateTableUsingTemplateMixin
from .create_table_clone_mixin import CreateTableCloneMixin
from .create_table_like_mixin import CreateTableLikeMixin
from .create_table_as_mixin import CreateTableAsMixin
from .alter_table_mixin import AlterTableMixin
from .drop_table_mixin import DropTableMixin
from .create_table_mixin import CreateTableMixin
from .qualify_clause_mixin import QualifyClauseMixin
from .locking_mixin import LockingMixin
from .advanced_grouping_mixin import AdvancedGroupingMixin
from .dql_order_mixin import DqlOrderMixin
from .wildcard_mixin import WildcardMixin
from .ordered_set_aggregation_mixin import OrderedSetAggregationMixin
from .filter_clause_mixin import FilterClauseMixin
from .transactional_d_d_l_mixin import TransactionalDDLMixin
from .timestamp_mixin import TimestampMixin
from .database_assigned_column_mixin import DatabaseAssignedColumnMixin
from .returning_mixin import ReturningMixin
from .column_attribute_mixin import ColumnAttributeMixin
from .alter_table_modifier_mixin import AlterTableModifierMixin
__all__ = [
    "SQLXMLParsingMixin",
    "SQLXMLSerializationMixin",
    "SQLXMLConstructionMixin",
    "SQLXMLAggregationMixin",    "SQLXMLQueryingMixin",
    "SQLXMLMixin",
    "CollationMixin",
    "WindowFunctionMixin",
    "CTEMixin",
    "UpsertMixin",
    "LateralJoinMixin",
    "JoinMixin",
    "ArrayMixin",
    "JSONMixin",
    "UUIDMixin",
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
    "CommentMixin",
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
    "AutoIncrementColumnMixin",
    "IdentityColumnMixin",
    "IntrospectionMixin",
    "AsyncIntrospectionMixin",
    "PredicateMixin",
    "ExpressionMixin",
    "NamespaceMixin",
    "RelationSourceMixin",
    "TableObjectMixin",
    "ViewObjectMixin",
    "MaterializedViewObjectMixin",
    "ForeignTableObjectMixin",
    "IndexObjectMixin",
    "PropertyGraphNameMixin",
    "SchemaNameMixin",
    "DatabaseNameMixin",
    "SequenceObjectMixin",
    "TriggerObjectMixin",
    "RoutineObjectMixin",
    "TypeObjectMixin",
    "SynonymObjectMixin",
    "DateTimeMixin",
    "DQLMixin",
    "DMLMixin",
    "DDLColumnMixin",
    "DataTypeMixin",
    "ColumnTypeMixin",
    "UserDefinedTypeMixin",
    "DomainMixin",
    "DatabaseMixin",
    "TransactionControlMixin",
    "TrimMixin",
    "LpadMixin",
    "RepeatMixin",
    "RpadMixin",
    "SQLFunctionMixin",
    "DropRoutineMixin",
    "CreateRoutineMixin",
    "DropSchemaMixin",
    "CreateSchemaMixin",
    "DropTriggerMixin",
    "CreateTriggerMixin",
    "MaterializedViewMixin",
    "DropViewMixin",
    "CreateViewMixin",
    "DropSequenceMixin",
    "AlterSequenceMixin",
    "CreateSequenceMixin",
    "DropDomainMixin",
    "AlterDomainMixin",
    "CreateDomainMixin",
    "DropDatabaseMixin",
    "AlterDatabaseMixin",
    "CreateDatabaseMixin",
    "DropTypeMixin",
    "AlterTypeMixin",
    "CreateTypeMixin",
    "FulltextIndexMixin",
    "DropIndexMixin",
    "CreateIndexMixin",
    "CreateTableUsingTemplateMixin",
    "CreateTableCloneMixin",
    "CreateTableLikeMixin",
    "CreateTableAsMixin",
    "AlterTableMixin",
    "DropTableMixin",
    "CreateTableMixin",
    "QualifyClauseMixin",
    "LockingMixin",
    "AdvancedGroupingMixin",
    "DqlOrderMixin",
    "WildcardMixin",
    "OrderedSetAggregationMixin",
    "FilterClauseMixin",
    "TransactionalDDLMixin",
    "TimestampMixin",
    "DatabaseAssignedColumnMixin",
    "ReturningMixin",
    "ColumnAttributeMixin",
    "AlterTableModifierMixin",
]
