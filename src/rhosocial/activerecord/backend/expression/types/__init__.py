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

__all__ = [
    'DataType',
    'ArrayType',
    'CustomType',
    'LENGTH_PARAMETERS',
    'PRECISION_PARAMETERS',
    'UNSIGNED_PARAMETERS',
    'TinyIntType',
    'SmallIntType',
    'IntegerType',
    'BigIntType',
    'FloatType',
    'RealType',
    'DoubleType',
    'DecimalType',
    'InvalidTypeNameError',
    'CharType',
    'VarCharType',
    'TextType',
    'BooleanType',
    'BlobType',
    'BinaryType',
    'VarBinaryType',
    'EnumType',
    'DateType',
    'TimeType',
    'TimeTzType',
    'DateTimeType',
    'TimestampType',
    'TimestampTzType',
    'IntervalType',
    'INTERVAL_QUALIFIERS',
    'InvalidIntervalQualifierError',
    'IntervalQualifier',
    'is_valid_interval_qualifier',
    'validate_interval_qualifier',
    'JsonType',
    'JsonBType',
    'XmlType',
    'UUIDType',
]

import importlib

_MODULES = ('_base', 'array', 'binary', 'boolean', 'custom', 'datetime_', 'enum_', 'integer', 'json_', 'numeric', 'string', 'uuid_', 'xml_')

# ``InvalidTypeNameError`` used to be re-exported from the former top-level
# ``type_name`` module. That helper now lives under ``bases/``; keep it visible
# here so ``from ...expression.types import InvalidTypeNameError`` still works.
_EXTRA_MODULES = ('rhosocial.activerecord.backend.expression.bases.type_name',)


def __getattr__(name):
    """Resolve a public name from this namespace lazily (no import cycles)."""
    for module_name in _MODULES:
        module = importlib.import_module(f'.{module_name}', __name__)
        if name in vars(module):
            value = vars(module)[name]
            globals()[name] = value  # cache so vars()/inspect see the name
            return value
    for dotted in _EXTRA_MODULES:
        module = importlib.import_module(dotted)
        if name in vars(module):
            value = vars(module)[name]
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
