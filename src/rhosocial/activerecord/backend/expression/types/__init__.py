# src/rhosocial/activerecord/backend/expression/types/__init__.py
"""SQL DataType expression system — core types (DDL only).

All types are ``BaseExpression`` subclasses and behave as *value objects*:
they are comparable and hashable by logical content, ignoring any
attached dialect reference.

Usage scope
-----------
These types are used **only** for DDL column definition expressions
(``ColumnDefinition.data_type``).  They are **not** intended for, and
should **not** be used in, introspection result handling, query building,
or any other context.  Each database backend defines its own type subclasses
(see backend ``impl/*/expression/types.py``) for backend-specific behaviour.

In practice, application code rarely imports from this package directly.
Instead, choose types from the target backend's own ``types.py``
(e.g. ``SQLiteIntegerType`` from the SQLite backend).  Backend-specific tests
should likewise prefer the backend's types to ensure the correct dialect
behaviour is exercised.

Naming convention
-----------------
+---------------------------+------------------+------------------------+
| Layer                    | Prefix           | Example                |
+===========================+==================+========================+
| Core (this package)      | *(none)*         | ``IntegerType``        |
+---------------------------+------------------+------------------------+
| SQLite backend           | ``SQLite``       | ``SQLiteIntegerType``  |
+---------------------------+------------------+------------------------+
| MySQL backend            | ``MySql``        | ``MySqlVarCharType``   |
+---------------------------+------------------+------------------------+
| PostgreSQL backend       | ``Postgres``     | ``PostgresArrayType``  |
+---------------------------+------------------+------------------------+

Usage::

    >>> from rhosocial.activerecord.backend.expression.types import (
    ...     IntegerType, VarCharType, DecimalType, BooleanType
    ... )
    >>> col_def = ColumnDefinition(dialect, "id", IntegerType())
    >>> col_def.data_type.to_sql(dialect)
    ('INTEGER', ())"""

import importlib

# Public name -> defining module. Private names here stay reachable
# through this package but are not part of __all__.
_EXPORTS = {
    'ABC': 'rhosocial.activerecord.backend.expression.types._base',
    'Any': 'rhosocial.activerecord.backend.expression.types._base',
    'ArrayType': 'rhosocial.activerecord.backend.expression.types.array',
    'BaseExpression': 'rhosocial.activerecord.backend.expression.types._base',
    'BigIntType': 'rhosocial.activerecord.backend.expression.types.integer',
    'BinaryType': 'rhosocial.activerecord.backend.expression.types.binary',
    'BlobType': 'rhosocial.activerecord.backend.expression.types.binary',
    'BooleanType': 'rhosocial.activerecord.backend.expression.types.boolean',
    'CharType': 'rhosocial.activerecord.backend.expression.types.string',
    'CustomType': 'rhosocial.activerecord.backend.expression.types.custom',
    'DataType': 'rhosocial.activerecord.backend.expression.types._base',
    'DateTimeType': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'DateType': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'DecimalType': 'rhosocial.activerecord.backend.expression.types.numeric',
    'DoubleType': 'rhosocial.activerecord.backend.expression.types.numeric',
    'EnumType': 'rhosocial.activerecord.backend.expression.types.enum_',
    'FloatType': 'rhosocial.activerecord.backend.expression.types.numeric',
    'INTERVAL_FIELDS': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'INTERVAL_QUALIFIERS': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'IntegerType': 'rhosocial.activerecord.backend.expression.types.integer',
    'IntervalQualifier': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'IntervalType': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'InvalidIntervalQualifierError': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'InvalidTypeNameError': 'rhosocial.activerecord.backend.expression.bases.type_name',
    'JsonBType': 'rhosocial.activerecord.backend.expression.types.json_',
    'JsonType': 'rhosocial.activerecord.backend.expression.types.json_',
    'LENGTH_PARAMETERS': 'rhosocial.activerecord.backend.expression.types._base',
    'List': 'rhosocial.activerecord.backend.expression.types.enum_',
    'Optional': 'rhosocial.activerecord.backend.expression.types._base',
    'PRECISION_PARAMETERS': 'rhosocial.activerecord.backend.expression.types._base',
    'RealType': 'rhosocial.activerecord.backend.expression.types.numeric',
    'SmallIntType': 'rhosocial.activerecord.backend.expression.types.integer',
    'TYPE_CHECKING': 'rhosocial.activerecord.backend.expression.types._base',
    'TextType': 'rhosocial.activerecord.backend.expression.types.string',
    'TimeType': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'TimeTzType': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'TimestampType': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'TimestampTzType': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'TinyIntType': 'rhosocial.activerecord.backend.expression.types.integer',
    'Tuple': 'rhosocial.activerecord.backend.expression.types._base',
    'UNSIGNED_PARAMETERS': 'rhosocial.activerecord.backend.expression.types._base',
    'UUIDType': 'rhosocial.activerecord.backend.expression.types.uuid_',
    'VarBinaryType': 'rhosocial.activerecord.backend.expression.types.binary',
    'VarCharType': 'rhosocial.activerecord.backend.expression.types.string',
    'XmlType': 'rhosocial.activerecord.backend.expression.types.xml_',
    '_ASCII_SPACE': 'rhosocial.activerecord.backend.expression.types.datetime_',
    '_backend_slug': 'rhosocial.activerecord.backend.expression.types._base',
    '_consume_field': 'rhosocial.activerecord.backend.expression.types.datetime_',
    '_consume_precision': 'rhosocial.activerecord.backend.expression.types.datetime_',
    '_interval_qualifier_shape': 'rhosocial.activerecord.backend.expression.types.datetime_',
    '_is_dispatch_name': 'rhosocial.activerecord.backend.expression.types._base',
    '_skip_ascii_space': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'annotations': 'rhosocial.activerecord.backend.expression.types._base',
    'is_identifier': 'rhosocial.activerecord.backend.expression.types._base',
    'is_simple_name': 'rhosocial.activerecord.backend.expression.types._base',
    'is_valid_interval_qualifier': 'rhosocial.activerecord.backend.expression.types.datetime_',
    'split_dotted': 'rhosocial.activerecord.backend.expression.types._base',
    'validate_interval_qualifier': 'rhosocial.activerecord.backend.expression.types.datetime_',
}

__all__ = [
    'ArrayType',
    'BigIntType',
    'BinaryType',
    'BlobType',
    'BooleanType',
    'CharType',
    'CustomType',
    'DataType',
    'DateTimeType',
    'DateType',
    'DecimalType',
    'DoubleType',
    'EnumType',
    'FloatType',
    'INTERVAL_QUALIFIERS',
    'IntegerType',
    'IntervalQualifier',
    'IntervalType',
    'InvalidIntervalQualifierError',
    'InvalidTypeNameError',
    'JsonBType',
    'JsonType',
    'LENGTH_PARAMETERS',
    'PRECISION_PARAMETERS',
    'RealType',
    'SmallIntType',
    'TextType',
    'TimeType',
    'TimeTzType',
    'TimestampType',
    'TimestampTzType',
    'TinyIntType',
    'UNSIGNED_PARAMETERS',
    'UUIDType',
    'VarBinaryType',
    'VarCharType',
    'XmlType',
    'is_valid_interval_qualifier',
    'validate_interval_qualifier',
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
