# src/rhosocial/activerecord/backend/expression/operators/__init__.py
"""Expression namespace: operators.

Every public name from the modules in this namespace is re-exported so
callers can keep importing it from this package."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'AliasableMixin': 'rhosocial.activerecord.backend.expression.operators.operators',
    'ArithmeticMixin': 'rhosocial.activerecord.backend.expression.operators.operators',
    'ArithmeticOperation': 'rhosocial.activerecord.backend.expression.operators.operators',
    'ArithmeticOperator': 'rhosocial.activerecord.backend.expression.operators.operators',
    'BaseExpression': 'rhosocial.activerecord.backend.expression.operators.operators',
    'BinaryExpression': 'rhosocial.activerecord.backend.expression.operators.operators',
    'ComparisonMixin': 'rhosocial.activerecord.backend.expression.operators.operators',
    'ConcatenationOperation': 'rhosocial.activerecord.backend.expression.operators.operators',
    'Enum': 'rhosocial.activerecord.backend.expression.operators.operators',
    'NumericValueMixin': 'rhosocial.activerecord.backend.expression.operators.operators',
    'Parameter': 'rhosocial.activerecord.backend.expression.operators.operators',
    'RawSQL': 'rhosocial.activerecord.backend.expression.operators.operators',
    'RawSQLPredicate': 'rhosocial.activerecord.backend.expression.operators.operators',
    'SQLOperation': 'rhosocial.activerecord.backend.expression.operators.operators',
    'SQLPredicate': 'rhosocial.activerecord.backend.expression.operators.operators',
    'SQLValue': 'rhosocial.activerecord.backend.expression.operators.operators',
    'StringPatternPredicateMixin': 'rhosocial.activerecord.backend.expression.operators.operators',
    'StringValueMixin': 'rhosocial.activerecord.backend.expression.operators.operators',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.expression.operators.operators',
    'TypeCastingMixin': 'rhosocial.activerecord.backend.expression.operators.operators',
    'UnaryExpression': 'rhosocial.activerecord.backend.expression.operators.operators',
    '_ARITHMETIC_SYMBOLS': 'rhosocial.activerecord.backend.expression.operators.operators',
    '_bind_values': 'rhosocial.activerecord.backend.expression.operators.operators',
}

__all__ = [
    'ArithmeticOperation',
    'ArithmeticOperator',
    'BinaryExpression',
    'ConcatenationOperation',
    'RawSQL',
    'RawSQLPredicate',
    'SQLOperation',
    'UnaryExpression',
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
