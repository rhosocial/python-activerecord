# src/rhosocial/activerecord/backend/expression/query_parts/__init__.py
"""Expression namespace: query_parts.

Every public name from the modules in this namespace is re-exported so
callers can keep importing it from this package."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'AliasableMixin': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'Any': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'BaseExpression': 'rhosocial.activerecord.backend.expression.query_parts.pivot',
    'DEFAULT_JOIN_TYPE': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'Enum': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'ForUpdateClause': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'GroupByHavingClause': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'GroupingClause': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'JoinClause': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'JoinType': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'LimitOffsetClause': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'List': 'rhosocial.activerecord.backend.expression.query_parts.pivot',
    'LockStrength': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'NamedRelationRef': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'NullsOrder': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'Optional': 'rhosocial.activerecord.backend.expression.query_parts.pivot',
    'OrderByClause': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'OrderByItem': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'Pivot': 'rhosocial.activerecord.backend.expression.query_parts.pivot',
    'QualifyClause': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'SQLPredicate': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'SortDirection': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'Subquery': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.expression.query_parts.pivot',
    'Table': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'TableSource': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'Tuple': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'Union': 'rhosocial.activerecord.backend.expression.query_parts.pivot',
    'Unpivot': 'rhosocial.activerecord.backend.expression.query_parts.pivot',
    'WhereClause': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    '_JOIN_PHRASES': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    '_JOIN_PHRASE_TO_TYPE': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    '_LOCK_PHRASES': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    '_LOCK_PHRASE_TO_STRENGTH': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'normalize_join_type': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
    'normalize_lock_strength': 'rhosocial.activerecord.backend.expression.query_parts.query_parts',
}

__all__ = [
    'ForUpdateClause',
    'GroupByHavingClause',
    'GroupingClause',
    'JoinClause',
    'JoinType',
    'LimitOffsetClause',
    'LockStrength',
    'NullsOrder',
    'OrderByClause',
    'OrderByItem',
    'Pivot',
    'QualifyClause',
    'SortDirection',
    'Unpivot',
    'WhereClause',
    'normalize_join_type',
    'normalize_lock_strength',
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
