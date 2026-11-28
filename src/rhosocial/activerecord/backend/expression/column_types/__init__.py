# src/rhosocial/activerecord/backend/expression/column_types/__init__.py
"""Expression namespace: column_types.

Every public name from the modules in this namespace is re-exported so
callers can keep importing it from this package."""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'ABCMeta': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'AliasableMixin': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'ArrayAnnotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'ArrayColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'ArrayValue': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'BaseExpression': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'BinaryAnnotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'BinaryColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'BitStringColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'BooleanAnnotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'BooleanColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'BooleanValue': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'Column': 'rhosocial.activerecord.backend.expression.column_types.column',
    'ColumnBase': 'rhosocial.activerecord.backend.expression.column_types.column',
    'DeclaredValueType': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'GeometryColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'IPAddressColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'IntegerAnnotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'IntegerColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'IntervalColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'JSONAnnotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'JSONColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'JSONValue': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'MacAddressColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'MultirangeColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'NullTestMixin': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'NumberAnnotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'NumericColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'NumericValue': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'OpaqueValue': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'Optional': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'RangeColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'SQLValue': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'StringColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'SurfaceOnlyAnnotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'SurfaceOnlyValue': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'TemporalAnnotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'TemporalValue': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'TextAnnotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'TextValue': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'TimestampColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'TypeCastingMixin': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'UUIDAnnotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'UUIDColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'VectorColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'XMLAnnotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    'XMLColumn': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'XMLValue': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    '_Annotation': 'rhosocial.activerecord.backend.expression.column_types.declared',
    '_column_annotations': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'abstractmethod': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'annotation_for': 'rhosocial.activerecord.backend.expression.column_types.column_types',
    'lru_cache': 'rhosocial.activerecord.backend.expression.column_types.column_types',
}

__all__ = [
    'ArrayAnnotation',
    'ArrayColumn',
    'BinaryAnnotation',
    'BinaryColumn',
    'BitStringColumn',
    'BooleanAnnotation',
    'BooleanColumn',
    'Column',
    'ColumnBase',
    'GeometryColumn',
    'IPAddressColumn',
    'IntegerAnnotation',
    'IntegerColumn',
    'IntervalColumn',
    'JSONAnnotation',
    'JSONColumn',
    'MacAddressColumn',
    'MultirangeColumn',
    'NumberAnnotation',
    'NumericColumn',
    'RangeColumn',
    'StringColumn',
    'SurfaceOnlyAnnotation',
    'TemporalAnnotation',
    'TextAnnotation',
    'TimestampColumn',
    'UUIDAnnotation',
    'UUIDColumn',
    'VectorColumn',
    'XMLAnnotation',
    'XMLColumn',
    'annotation_for',
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
