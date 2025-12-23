# src/rhosocial/activerecord/backend/impl/dummy/dialect.py
"""
Dummy backend SQL dialect implementation.

This dialect implements all protocols and supports all features.
It is used for to_sql() testing and does not involve actual database connections.
"""
from typing import Tuple, Optional, List, Dict, Any

from rhosocial.activerecord.backend.dialect.base import BaseDialect
from rhosocial.activerecord.backend.dialect.protocols import (
    WindowFunctionSupport, CTESupport, AdvancedGroupingSupport, ReturningSupport,
    UpsertSupport, LateralJoinSupport, ArraySupport, JSONSupport, ExplainSupport,
    FilterClauseSupport, OrderedSetAggregationSupport, MergeSupport,
    TemporalTableSupport, QualifyClauseSupport, LockingSupport, GraphSupport,
)

class DummyDialect(
    BaseDialect,
    WindowFunctionSupport, CTESupport, AdvancedGroupingSupport, ReturningSupport,
    UpsertSupport, LateralJoinSupport, ArraySupport, JSONSupport, ExplainSupport,
    FilterClauseSupport, OrderedSetAggregationSupport, MergeSupport,
    TemporalTableSupport, QualifyClauseSupport, LockingSupport, GraphSupport,
):
    """
    Dummy dialect supporting all features for SQL generation testing.
    """

    def get_placeholder(self) -> str:
        """Use '?' placeholder for consistency."""
        return "?"

    # region Protocol Support Checks
    def supports_window_functions(self) -> bool: return True
    def supports_window_frame_clause(self) -> bool: return True
    def supports_basic_cte(self) -> bool: return True
    def supports_recursive_cte(self) -> bool: return True
    def supports_materialized_cte(self) -> bool: return True
    def supports_rollup(self) -> bool: return True
    def supports_cube(self) -> bool: return True
    def supports_grouping_sets(self) -> bool: return True
    def supports_returning_clause(self) -> bool: return True
    def supports_upsert(self) -> bool: return True
    def get_upsert_syntax_type(self) -> str: return "ON CONFLICT"
    def supports_lateral_join(self) -> bool: return True
    def supports_array_type(self) -> bool: return True
    def supports_array_constructor(self) -> bool: return True
    def supports_array_access(self) -> bool: return True
    def supports_json_type(self) -> bool: return True
    def get_json_access_operator(self) -> str: return "->"
    def supports_json_table(self) -> bool: return True
    def supports_explain_analyze(self) -> bool: return True
    def supports_explain_format(self, format_type: str) -> bool: return True
    def supports_filter_clause(self) -> bool: return True
    def supports_ordered_set_aggregation(self) -> bool: return True
    def supports_merge_statement(self) -> bool: return True
    def supports_temporal_tables(self) -> bool: return True
    def supports_qualify_clause(self) -> bool: return True
    def supports_for_update_skip_locked(self) -> bool: return True
    def supports_graph_match(self) -> bool: return True
    # endregion





