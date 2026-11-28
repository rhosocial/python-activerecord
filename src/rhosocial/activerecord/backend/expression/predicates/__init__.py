# src/rhosocial/activerecord/backend/expression/predicates/__init__.py
"""Expression namespace: predicates.

Every public name from the modules in this namespace is re-exported so
callers can keep importing it from this package."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'Any': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'BaseExpression': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'BetweenPredicate': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'ComparisonOperator': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'ComparisonPredicate': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'DistinctFromPredicate': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'Enum': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'ILikePredicate': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'InPredicate': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'IsBooleanPredicate': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'IsNullPredicate': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'LikeOperator': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'LikePredicate': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'LogicalPredicate': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'SQLPredicate': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'value_expression': 'rhosocial.activerecord.backend.expression.predicates.predicates',
    'value_sequence': 'rhosocial.activerecord.backend.expression.predicates.predicates',
}

__all__ = [
    'BetweenPredicate',
    'ComparisonOperator',
    'ComparisonPredicate',
    'DistinctFromPredicate',
    'ILikePredicate',
    'InPredicate',
    'IsBooleanPredicate',
    'IsNullPredicate',
    'LikeOperator',
    'LikePredicate',
    'LogicalPredicate',
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
