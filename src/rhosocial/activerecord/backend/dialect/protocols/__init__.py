"""Every dialect protocol, one module per protocol, grouped by subject.

A dialect declares what it supports by inheriting the protocol for the feature and
implementing its methods. The grouping is by subject rather than by engine, because
the grouping that matters when adding a switch is the neighbouring feature.

Naming a database object and changing one are independent: an engine may name a
table without being able to create one. :mod:`~...object` holds the first,
:mod:`~...ddl` the second.

Two invariants the conformance tests enforce, and which this layout exists to
support:

* A dialect that advertises a feature implements every method its protocol declares.
  ``DummyDialect`` is the reference and must satisfy all of them, so adding a method
  to a protocol obliges the reference dialect to implement it.
* A dialect that lacks a feature lists the protocol as deliberately not implemented.
  Positive and negative lists together must partition every protocol, so a new
  protocol cannot be added without deciding which side it falls on.

Both tests walk this package's attributes, so every protocol is re-exported here
even though it is defined in a submodule.
"""

# --- Named objects ---
from .object.index import IndexObjectSupport
from .object.namespace import NamespaceSupport
from .object.relation import TableObjectSupport
from .object.relation import ViewObjectSupport
from .object.relation import MaterializedViewObjectSupport
from .object.relation import ForeignTableObjectSupport
from .object.routine import RoutineObjectSupport
from .object.sequence import SequenceObjectSupport
from .object.synonym import SynonymObjectSupport
from .object.trigger import TriggerObjectSupport
from .object.type_ import TypeObjectSupport

# --- Data definition ---
from .ddl.alter_table_modifier import AlterTableModifierSupport
from .ddl.auto_increment import AutoIncrementColumnSupport
from .ddl.identity_column import IdentityColumnSupport
from .ddl.column_attribute import ColumnAttributeSupport
from .ddl.comment import CommentSupport
from .ddl.constraint import ConstraintSupport
from .ddl.database.alter_database import AlterDatabaseSupport
from .ddl.database.create_database import CreateDatabaseSupport
from .ddl.database.drop_database import DropDatabaseSupport
from .ddl.domain.alter_domain import AlterDomainSupport
from .ddl.domain.create_domain import CreateDomainSupport
from .ddl.domain.drop_domain import DropDomainSupport
from .ddl.generated_column import GeneratedColumnSupport
from .ddl.index.create_index import CreateIndexSupport
from .ddl.index.drop_index import DropIndexSupport
from .ddl.index.fulltext import FulltextIndexSupport
from .ddl.partition import PartitionSupport
from .ddl.routine.create_function import CreateRoutineSupport
from .ddl.routine.drop_function import DropRoutineSupport
from .ddl.schema.create_schema import CreateSchemaSupport
from .ddl.schema.drop_schema import DropSchemaSupport
from .ddl.sequence.alter_sequence import AlterSequenceSupport
from .ddl.sequence.create_sequence import CreateSequenceSupport
from .ddl.sequence.drop_sequence import DropSequenceSupport
from .ddl.table.alter_table import AlterTableSupport
from .ddl.table.create_table import CreateTableSupport
from .ddl.table.create_table_as import CreateTableAsSupport
from .ddl.table.create_table_clone import CreateTableCloneSupport
from .ddl.table.create_table_like import CreateTableLikeSupport
from .ddl.table.create_table_using_template import CreateTableUsingTemplateSupport
from .ddl.table.drop_table import DropTableSupport
from .ddl.trigger.create_trigger import CreateTriggerSupport
from .ddl.trigger.drop_trigger import DropTriggerSupport
from .ddl.truncate import TruncateSupport
from .ddl.type_.alter_type import AlterTypeSupport
from .ddl.type_.create_type import CreateTypeSupport
from .ddl.type_.drop_type import DropTypeSupport
from .ddl.view.create_view import CreateViewSupport
from .ddl.view.drop_view import DropViewSupport
from .ddl.view.materialized_view import MaterializedViewSupport

# --- Query features ---
from .query.timestamp import TimestampSupport
from .query.pivot import PivotSupport
from .query.dql_order import DqlOrderSupport
from .query.advanced_grouping import AdvancedGroupingSupport
from .query.array import ArraySupport
from .query.collation import CollationSupport
from .query.column_type import ColumnTypeSupport
from .query.cte import CTESupport
from .query.data_type import DataTypeSupport
from .query.explain import ExplainSupport
from .query.filter_clause import FilterClauseSupport
from .query.graph import GraphSupport
from .query.graph_table import GraphTableSupport
from .query.ilike import ILIKESupport
from .query.join import JoinSupport
from .query.json import JSONSupport
from .query.lateral_join import LateralJoinSupport
from .query.locking import LockingSupport
from .query.merge import MergeSupport
from .query.ordered_set_aggregation import OrderedSetAggregationSupport
from .query.qualify import QualifyClauseSupport
from .query.returning import ReturningSupport
from .query.set_operation import SetOperationSupport
from .query.sql_function import SQLFunctionSupport
from .query.temporal import TemporalTableSupport
from .query.upsert import UpsertSupport
from .query.uuid import UUIDSupport
from .query.wildcard import WildcardSupport
from .query.window import WindowFunctionSupport

# --- Introspection and sessions ---
from .introspect.introspection import IntrospectionSupport
from .introspect.transaction import TransactionControlSupport

# --- SQL/XML ---
from .sqlxml.xml_aggregation import SQLXMLAggregationSupport
from .sqlxml.xml_construction import SQLXMLConstructionSupport
from .sqlxml.xml_parsing import SQLXMLParsingSupport
from .sqlxml.xml_querying import SQLXMLQueryingSupport
from .sqlxml.xml_querying import SQLXMLSupport
from .sqlxml.xml_serialization import SQLXMLSerializationSupport

# DDLTypeSupport was the former name of DataTypeSupport. It is kept as an
# alias because backends referenced it; a dialect is typed by its data types,
# not by whether it declares DDL for them.
DDLTypeSupport = DataTypeSupport

__all__ = [
    "AdvancedGroupingSupport",
    "AlterDatabaseSupport",
    "AlterDomainSupport",
    "AlterSequenceSupport",
    "AlterTableModifierSupport",
    "AlterTableSupport",
    "AlterTypeSupport",
    "ArraySupport",
    "AutoIncrementColumnSupport",
    "CTESupport",
    "CollationSupport",
    "ColumnAttributeSupport",
    "CommentSupport",
    "ConstraintSupport",
    "CreateDatabaseSupport",
    "CreateDomainSupport",
    "CreateIndexSupport",
    "CreateRoutineSupport",
    "CreateSchemaSupport",
    "CreateSequenceSupport",
    "CreateTableAsSupport",
    "CreateTableCloneSupport",
    "CreateTableLikeSupport",
    "CreateTableSupport",
    "CreateTableUsingTemplateSupport",
    "CreateTriggerSupport",
    "CreateTypeSupport",
    "CreateViewSupport",
    "DDLTypeSupport",
    "ColumnTypeSupport",
    "DataTypeSupport",
    "TimestampSupport",
    "DqlOrderSupport",
    "DropDatabaseSupport",
    "DropDomainSupport",
    "DropIndexSupport",
    "DropRoutineSupport",
    "DropSchemaSupport",
    "DropSequenceSupport",
    "DropTableSupport",
    "DropTriggerSupport",
    "DropTypeSupport",
    "DropViewSupport",
    "ExplainSupport",
    "FilterClauseSupport",
    "ForeignTableObjectSupport",
    "FulltextIndexSupport",
    "GeneratedColumnSupport",
    "GraphSupport",
    "GraphTableSupport",
    "ILIKESupport",
    "IdentityColumnSupport",
    "IndexObjectSupport",
    "IntrospectionSupport",
    "JSONSupport",
    "JoinSupport",
    "LateralJoinSupport",
    "LockingSupport",
    "MaterializedViewObjectSupport",
    "MaterializedViewSupport",
    "MergeSupport",
    "NamespaceSupport",
    "OrderedSetAggregationSupport",
    "PartitionSupport",
    "PivotSupport",
    "QualifyClauseSupport",
    "ReturningSupport",
    "RoutineObjectSupport",
    "SQLFunctionSupport",
    "SQLXMLAggregationSupport",
    "SQLXMLConstructionSupport",
    "SQLXMLParsingSupport",
    "SQLXMLQueryingSupport",
    "SQLXMLSerializationSupport",
    "SQLXMLSupport",
    "SequenceObjectSupport",
    "SetOperationSupport",
    "SynonymObjectSupport",
    "TableObjectSupport",
    "TemporalTableSupport",
    "TransactionControlSupport",
    "TriggerObjectSupport",
    "TruncateSupport",
    "TypeObjectSupport",
    "UpsertSupport",
    "UUIDSupport",
    "ViewObjectSupport",
    "WildcardSupport",
    "WindowFunctionSupport",
]
