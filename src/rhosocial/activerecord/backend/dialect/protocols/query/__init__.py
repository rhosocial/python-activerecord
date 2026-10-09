"""Query-side features: expressions, clauses and functions.

Everything a SELECT composes from -- window functions, joins, set operations,
locking, JSON, the graph pattern language, and the scalar functions a dialect
advertises. Grouped by feature rather than by statement, because the grouping
that matters when adding a switch is the neighbouring feature.

``:mod:`data_type`` also lives here: a data type is rendered where an
expression is, not by a DDL statement.
"""

from .collation import CollationSupport
from .column_type import ColumnTypeSupport
from .data_type import DataTypeSupport
from .cte import CTESupport
from .window import WindowFunctionSupport
from .wildcard import WildcardSupport
from .advanced_grouping import AdvancedGroupingSupport
from .returning import ReturningSupport
from .upsert import UpsertSupport
from .lateral_join import LateralJoinSupport
from .join import JoinSupport
from .array import ArraySupport
from .json import JSONSupport
from .uuid import UUIDSupport
from .explain import ExplainSupport
from .graph import GraphSupport
from .graph_table import GraphTableSupport
from .filter_clause import FilterClauseSupport
from .ordered_set_aggregation import OrderedSetAggregationSupport
from .merge import MergeSupport
from .temporal import TemporalTableSupport
from .qualify import QualifyClauseSupport
from .locking import LockingSupport
from .set_operation import SetOperationSupport
from .ilike import ILIKESupport
from .sql_function import SQLFunctionSupport

__all__ = [
    "AdvancedGroupingSupport",
    "ArraySupport",
    "CTESupport",
    "CollationSupport",
    "ColumnTypeSupport",
    "DataTypeSupport",
    "ExplainSupport",
    "FilterClauseSupport",
    "GraphSupport",
    "GraphTableSupport",
    "ILIKESupport",
    "JSONSupport",
    "JoinSupport",
    "LateralJoinSupport",
    "LockingSupport",
    "MergeSupport",
    "OrderedSetAggregationSupport",
    "QualifyClauseSupport",
    "ReturningSupport",
    "SQLFunctionSupport",
    "SetOperationSupport",
    "TemporalTableSupport",
    "UpsertSupport",
    "UUIDSupport",
    "WildcardSupport",
    "WindowFunctionSupport",
]
