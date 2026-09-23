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
from .introspection import IntrospectionMixin, AsyncIntrospectionMixin
from .predicate import PredicateMixin
from .expression import ExpressionMixin
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
    "IntrospectionMixin",
    "AsyncIntrospectionMixin",
    "PredicateMixin",
    "ExpressionMixin",
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
