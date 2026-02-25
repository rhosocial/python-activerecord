# src/rhosocial/activerecord/backend/dialect/__init__.py
"""
SQL dialect system for rhosocial-activerecord.

This package provides a protocol-based dialect system that enables fine-grained
feature detection and graceful handling of database-specific SQL features.

Architecture:
- Base classes define core SQL interfaces
- Protocols declare optional advanced features
- Concrete dialects are implemented in their respective backend packages
- Exceptions provide clear error messages when features aren't available

Usage:
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect
    from rhosocial.activerecord.backend.dialect.protocols import WindowFunctionSupport

    dialect = SQLiteDialect()

    # Check protocol implementation
    if isinstance(dialect, WindowFunctionSupport):
        if dialect.supports_window_functions():
            # Use window functions
            pass

    # Or use helper methods
    try:
        dialect.require_protocol(WindowFunctionSupport, "window functions", "MyQuery")
        dialect.check_feature_support("supports_rollup", "ROLLUP")
    except ProtocolNotImplementedError as e:
        print(f"Protocol not implemented: {e}")
    except UnsupportedFeatureError as e:
        print(f"Feature not supported: {e}")
"""

from .base import SQLDialectBase
from .exceptions import UnsupportedFeatureError, ProtocolNotImplementedError
from .protocols import (
    WindowFunctionSupport,
    CTESupport,
    AdvancedGroupingSupport,
    ReturningSupport,
    UpsertSupport,
    LateralJoinSupport,
    ArraySupport,
    JSONSupport,
    ExplainSupport,
    FilterClauseSupport,
    OrderedSetAggregationSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    LockingSupport,
    GraphSupport,
    WildcardSupport,
    JoinSupport,
)
from .mixins import (
    WindowFunctionMixin,
    CTEMixin,
    AdvancedGroupingMixin,
    ReturningMixin,
    UpsertMixin,
    LateralJoinMixin,
    ArrayMixin,
    JSONMixin,
    ExplainMixin,
    FilterClauseMixin,
    OrderedSetAggregationMixin,
    MergeMixin,
    TemporalTableMixin,
    QualifyClauseMixin,
    LockingMixin,
    GraphMixin,
    JoinMixin,
)

# Import Explain types from expression module to make them available in dialect module
from ..expression import (
    ExplainType,
    ExplainFormat,
    ExplainOptions
)

__all__ = [
    # Base classes
    'SQLDialectBase',

    # Exceptions
    'UnsupportedFeatureError',
    'ProtocolNotImplementedError',

    # Protocols
    'WindowFunctionSupport',
    'CTESupport',
    'AdvancedGroupingSupport',
    'ReturningSupport',
    'UpsertSupport',
    'LateralJoinSupport',
    'ArraySupport',
    'JSONSupport',
    'ExplainSupport',
    'FilterClauseSupport',
    'OrderedSetAggregationSupport',
    'MergeSupport',
    'TemporalTableSupport',
    'QualifyClauseSupport',
    'LockingSupport',
    'GraphSupport',
    'WildcardSupport',
    'JoinSupport',

    # Mixins
    'WindowFunctionMixin',
    'CTEMixin',
    'AdvancedGroupingMixin',
    'ReturningMixin',
    'UpsertMixin',
    'LateralJoinMixin',
    'ArrayMixin',
    'JSONMixin',
    'ExplainMixin',
    'FilterClauseMixin',
    'OrderedSetAggregationMixin',
    'MergeMixin',
    'TemporalTableMixin',
    'QualifyClauseMixin',
    'LockingMixin',
    'GraphMixin',
    'JoinMixin',
]