# src/rhosocial/activerecord/backend/expression/value_types/__init__.py
"""Expression namespace: value_types.

Every public name from the modules in this namespace is re-exported so
callers can keep importing it from this package."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'ABC': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'AliasableMixin': 'rhosocial.activerecord.backend.expression.value_types.logical',
    'AllColumnsWildcard': 'rhosocial.activerecord.backend.expression.value_types.wildcards',
    'Any': 'rhosocial.activerecord.backend.expression.value_types.logical',
    'ArithmeticMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'ArrayMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'ArrayValue': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'BaseExpression': 'rhosocial.activerecord.backend.expression.value_types.parameter',
    'BooleanLogicMixin': 'rhosocial.activerecord.backend.expression.value_types.logical',
    'BooleanValue': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'ComparisonMixin': 'rhosocial.activerecord.backend.expression.value_types.literals',
    'DateTimeMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'Identifier': 'rhosocial.activerecord.backend.expression.value_types.literals',
    'JSONAccessorMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'JSONValue': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'LogicalValue': 'rhosocial.activerecord.backend.expression.value_types.logical',
    'NotANumberMixin': 'rhosocial.activerecord.backend.expression.value_types.logical',
    'NotComparableMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'NullTestMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'NumericValue': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'NumericValueMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'OpaqueValue': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'Optional': 'rhosocial.activerecord.backend.expression.value_types.wildcards',
    'Parameter': 'rhosocial.activerecord.backend.expression.value_types.parameter',
    'RowCountWildcard': 'rhosocial.activerecord.backend.expression.value_types.wildcards',
    'SQLValue': 'rhosocial.activerecord.backend.expression.value_types.literals',
    'StringPatternPredicateMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'StringToIntegerMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'StringValueMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'SurfaceOnlyValue': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.expression.value_types.literals',
    'TemporalArithmeticMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'TemporalValue': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'TextValue': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'TranscendentalMixin': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'TypeCastingMixin': 'rhosocial.activerecord.backend.expression.value_types.logical',
    'XMLValue': 'rhosocial.activerecord.backend.expression.value_types.value_types',
    'abstractmethod': 'rhosocial.activerecord.backend.expression.value_types.value_types',
}

__all__ = [
    'AllColumnsWildcard',
    'ArrayValue',
    'BooleanValue',
    'Identifier',
    'JSONValue',
    'LogicalValue',
    'NumericValue',
    'OpaqueValue',
    'Parameter',
    'RowCountWildcard',
    'SurfaceOnlyValue',
    'TemporalValue',
    'TextValue',
    'XMLValue',
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
