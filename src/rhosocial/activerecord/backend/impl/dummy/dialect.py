# src/rhosocial/activerecord/backend/impl/dummy/dialect.py
"""
Dummy backend SQL dialect implementation.

This dialect implements all protocols and supports all features.
It is used for to_sql() testing and does not involve actual database connections.
"""

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




