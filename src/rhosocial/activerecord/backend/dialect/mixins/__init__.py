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
from .grouping import AdvancedGroupingMixin
from .returning import ReturningMixin
from .upsert import UpsertMixin
from .join import LateralJoinMixin, JoinMixin
from .array import ArrayMixin
from .json import JSONMixin
from .explain import ExplainMixin
from .graph import GraphMixin, GraphTableMixin
from .filter_clause import FilterClauseMixin
from .aggregation import OrderedSetAggregationMixin
from .merge import MergeMixin
from .temporal import TemporalTableMixin, QualifyClauseMixin
from .locking import LockingMixin
from .set_operation import SetOperationMixin
from .partition import PartitionMixin
from .ddl_table import TableMixin, ConstraintMixin
from .ddl_view import ViewMixin, TruncateMixin
from .ddl_schema import SchemaMixin
from .ddl_index import IndexMixin
from .ddl_sequence import SequenceMixin
from .ilike import ILIKEMixin
from .trigger import TriggerMixin
from .function import FunctionMixin
from .generated_column import GeneratedColumnMixin
from .introspection import IntrospectionMixin, AsyncIntrospectionMixin
from .identifier import IdentifierMixin
from .predicate import PredicateMixin
from .expression import ExpressionMixin
from .datetime import DateTimeMixin
from .dql import DQLMixin
from .dml import DMLMixin
from .ddl_column import DDLColumnMixin
from .ddl_type import DDLTypeMixin
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
    "AdvancedGroupingMixin",
    "ReturningMixin",
    "UpsertMixin",
    "LateralJoinMixin",
    "JoinMixin",
    "ArrayMixin",
    "JSONMixin",
    "ExplainMixin",
    "GraphMixin",
    "GraphTableMixin",
    "FilterClauseMixin",
    "OrderedSetAggregationMixin",
    "MergeMixin",
    "TemporalTableMixin",
    "QualifyClauseMixin",
    "LockingMixin",
    "SetOperationMixin",
    "PartitionMixin",
    "TableMixin",
    "ConstraintMixin",
    "ViewMixin",
    "TruncateMixin",
    "SchemaMixin",
    "IndexMixin",
    "SequenceMixin",
    "ILIKEMixin",
    "TriggerMixin",
    "FunctionMixin",
    "GeneratedColumnMixin",
    "IntrospectionMixin",
    "AsyncIntrospectionMixin",
    "IdentifierMixin",
    "PredicateMixin",
    "ExpressionMixin",
    "DateTimeMixin",
    "DQLMixin",
    "DMLMixin",
    "DDLColumnMixin",
    "DDLTypeMixin",
    "TransactionControlMixin",
]
