# src/rhosocial/activerecord/backend/expression/bases/__init__.py
"""Expression namespace: bases.

Every public name from the modules in this namespace is re-exported so
callers can keep importing it from this package."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'AliasableMixin': 'rhosocial.activerecord.backend.expression.bases.bases',
    'Any': 'rhosocial.activerecord.backend.expression.bases.bases',
    'ArithmeticMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'ArrayMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'BaseExpression': 'rhosocial.activerecord.backend.expression.bases.bases',
    'BooleanLogicMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'ColumnBase': 'rhosocial.activerecord.backend.expression.bases.collect_columns',
    'ComparisonMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'ContextVar': 'rhosocial.activerecord.backend.expression.bases.bases',
    'DateTimeMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'Dict': 'rhosocial.activerecord.backend.expression.bases.bases',
    'Enum': 'rhosocial.activerecord.backend.expression.bases.bases',
    'IntervalMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'InvalidTypeNameError': 'rhosocial.activerecord.backend.expression.bases.type_name',
    'Iterator': 'rhosocial.activerecord.backend.expression.bases.collect_columns',
    'JSONAccessorMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'List': 'rhosocial.activerecord.backend.expression.bases.bases',
    'LogicalMixin': 'rhosocial.activerecord.backend.expression.bases.bases',
    'MULTI_WORD_TYPE_NAMES': 'rhosocial.activerecord.backend.expression.bases.type_name',
    'NotANumberMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'NotComparableMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'NullTestMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'NumericValueMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'Optional': 'rhosocial.activerecord.backend.expression.bases.bases',
    'Protocol': 'rhosocial.activerecord.backend.expression.bases.bases',
    'QueryWithParams': 'rhosocial.activerecord.backend.expression.bases.bases',
    'ResultTypeMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'SQLLiteral': 'rhosocial.activerecord.backend.expression.bases.bases',
    'SQLPredicate': 'rhosocial.activerecord.backend.expression.bases.bases',
    'SQLQueryAndParams': 'rhosocial.activerecord.backend.expression.bases.bases',
    'SQLValue': 'rhosocial.activerecord.backend.expression.bases.bases',
    'Set': 'rhosocial.activerecord.backend.expression.bases.collect_columns',
    'StringPatternPredicateMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'StringToIntegerMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'StringValueMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'T': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'TRIM_DEFAULT_DIRECTION': 'rhosocial.activerecord.backend.expression.bases.defaults',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.expression.bases.bases',
    'TemporalArithmeticMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'ToSQLProtocol': 'rhosocial.activerecord.backend.expression.bases.bases',
    'TranscendentalMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'Tuple': 'rhosocial.activerecord.backend.expression.bases.bases',
    'TypeCastingMixin': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'TypeVar': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'Union': 'rhosocial.activerecord.backend.expression.bases.bases',
    '_ASCII_SPACE': 'rhosocial.activerecord.backend.expression.bases.type_name',
    '_LogicalOperators': 'rhosocial.activerecord.backend.expression.bases.mixins',
    '_RENDER_DIALECT': 'rhosocial.activerecord.backend.expression.bases.bases',
    '_ResultT': 'rhosocial.activerecord.backend.expression.bases.mixins',
    '_as_interval': 'rhosocial.activerecord.backend.expression.bases.mixins',
    '_bare_word': 'rhosocial.activerecord.backend.expression.bases.type_name',
    '_camel_to_words': 'rhosocial.activerecord.backend.expression.bases.bases',
    '_consume_digits': 'rhosocial.activerecord.backend.expression.bases.type_name',
    '_consume_identifier': 'rhosocial.activerecord.backend.expression.bases.type_name',
    '_is_type_name': 'rhosocial.activerecord.backend.expression.bases.type_name',
    '_skip_ascii_space': 'rhosocial.activerecord.backend.expression.bases.type_name',
    '_skip_space': 'rhosocial.activerecord.backend.expression.bases.type_name',
    'annotations': 'rhosocial.activerecord.backend.expression.bases.collect_columns',
    'build_json_path': 'rhosocial.activerecord.backend.expression.bases.mixins',
    'current_dialect': 'rhosocial.activerecord.backend.expression.bases.bases',
    'is_valid_type_name': 'rhosocial.activerecord.backend.expression.bases.type_name',
    'iter_columns': 'rhosocial.activerecord.backend.expression.bases.collect_columns',
    'referenced_columns': 'rhosocial.activerecord.backend.expression.bases.collect_columns',
    'runtime_checkable': 'rhosocial.activerecord.backend.expression.bases.bases',
    'validate_type_name': 'rhosocial.activerecord.backend.expression.bases.type_name',
    'value_expression': 'rhosocial.activerecord.backend.expression.bases.coerce',
    'value_sequence': 'rhosocial.activerecord.backend.expression.bases.coerce',
}

__all__ = [
    'AliasableMixin',
    'ArithmeticMixin',
    'ArrayMixin',
    'BaseExpression',
    'BooleanLogicMixin',
    'ComparisonMixin',
    'DateTimeMixin',
    'IntervalMixin',
    'InvalidTypeNameError',
    'JSONAccessorMixin',
    'LogicalMixin',
    'MULTI_WORD_TYPE_NAMES',
    'NotANumberMixin',
    'NotComparableMixin',
    'NullTestMixin',
    'NumericValueMixin',
    'QueryWithParams',
    'ResultTypeMixin',
    'SQLLiteral',
    'SQLPredicate',
    'SQLValue',
    'StringPatternPredicateMixin',
    'StringToIntegerMixin',
    'StringValueMixin',
    'T',
    'TemporalArithmeticMixin',
    'ToSQLProtocol',
    'TranscendentalMixin',
    'TypeCastingMixin',
    'build_json_path',
    'current_dialect',
    'is_valid_type_name',
    'iter_columns',
    'referenced_columns',
    'validate_type_name',
    'value_expression',
    'value_sequence',
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
