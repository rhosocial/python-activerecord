# src/rhosocial/activerecord/backend/expression/introspection/__init__.py
"""Expression namespace: introspection.

Every public name from the modules in this namespace is re-exported so
callers can keep importing it from this package."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'BaseExpression': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'ColumnDataProfileQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'ColumnInfoQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'ColumnValueSampleQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'DDLStatementQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'DatabaseInfoQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'ForeignKeyQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'IndexInfoQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'IndexUsageStatsQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'IntrospectionExpression': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'JoinCoverageQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'ObjectDependencyQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'Optional': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'RuntimeMetricsQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'Sequence': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'TableInfoQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'TableListQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'TableUsageStatsQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'TriggerInfoQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'TriggerListQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'UnusedIndexesQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'VALUE_SAMPLE_LIMIT': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'ViewInfoQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
    'ViewListQueryStatement': 'rhosocial.activerecord.backend.expression.introspection.introspection',
}

__all__ = [
    'ColumnDataProfileQueryStatement',
    'ColumnInfoQueryStatement',
    'ColumnValueSampleQueryStatement',
    'DDLStatementQueryStatement',
    'DatabaseInfoQueryStatement',
    'ForeignKeyQueryStatement',
    'IndexInfoQueryStatement',
    'IndexUsageStatsQueryStatement',
    'IntrospectionExpression',
    'JoinCoverageQueryStatement',
    'ObjectDependencyQueryStatement',
    'RuntimeMetricsQueryStatement',
    'TableInfoQueryStatement',
    'TableListQueryStatement',
    'TableUsageStatsQueryStatement',
    'TriggerInfoQueryStatement',
    'TriggerListQueryStatement',
    'UnusedIndexesQueryStatement',
    'ViewInfoQueryStatement',
    'ViewListQueryStatement',
]


def __getattr__(name):
    """Resolve a public name from this namespace lazily (no import cycles)."""
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_name)
    value = vars(module)[name]
    globals()[name] = value
    return value
