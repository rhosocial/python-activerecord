# src/rhosocial/activerecord/backend/expression/types/__init__.py
"""
SQL DataType expression system — core types (DDL only).

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
    >>> col_def = ColumnDefinition("id", IntegerType())
    >>> col_def.data_type.to_sql(dialect)
    ('INTEGER', ())
"""

from ._base import DataType
from .custom import CustomType
from .integer import TinyIntType, SmallIntType, IntType, IntegerType, BigIntType
from .numeric import FloatType, RealType, DoubleType, DecimalType
from .string import CharType, VarCharType, CharacterVaryingType, TextType
from .boolean import BooleanType
from .binary import BlobType
from .datetime_ import (
    DateType,
    TimeType,
    TimeTzType,
    DateTimeType,
    TimestampType,
    TimestampTzType,
    IntervalType,
)
from .json_ import JsonType, JsonBType

__all__ = [
    "DataType",
    "CustomType",
    # integer
    "TinyIntType",
    "SmallIntType",
    "IntType",
    "IntegerType",
    "BigIntType",
    # numeric
    "FloatType",
    "RealType",
    "DoubleType",
    "DecimalType",
    # string
    "CharType",
    "VarCharType",
    "CharacterVaryingType",
    "TextType",
    # boolean
    "BooleanType",
    # binary
    "BlobType",
    # datetime
    "DateType",
    "TimeType",
    "TimeTzType",
    "DateTimeType",
    "TimestampType",
    "TimestampTzType",
    "IntervalType",
    # json
    "JsonType",
    "JsonBType",
]
