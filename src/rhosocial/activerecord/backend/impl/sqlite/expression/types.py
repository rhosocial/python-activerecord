# src/rhosocial/activerecord/backend/impl/sqlite/expression/types.py
"""SQLite-specific DataType subclasses for the five type affinities.

SQLite uses type affinity rather than strict types.  These five classes
correspond to the five affinity families documented at
https://www.sqlite.org/datatype3.html:

* ``SQLiteIntegerType``  — INTEGER affinity (INT, BIGINT, SMALLINT, …)
* ``SQLiteTextType``     — TEXT affinity (CHAR, VARCHAR, CLOB, …)
* ``SQLiteRealType``     — REAL affinity (FLOAT, DOUBLE, REAL, …)
* ``SQLiteNumericType``  — NUMERIC affinity (DECIMAL, BOOLEAN, DATE, …)
* ``SQLiteBlobType``     — BLOB affinity (BLOB, BYTEA, …)

Each class carries a ``sqlite_``-prefixed generic ``name`` (the protocol
dispatch key), so the backend's concrete type family is distinguishable
from the core type family by name alone.
"""

from __future__ import annotations

from typing import Set

from rhosocial.activerecord.backend.expression.types import (
    BlobType,
    DataType,
    IntegerType,
    TextType,
)


class SQLiteIntegerType(IntegerType):
    """SQLite INTEGER — rowid alias when used as PRIMARY KEY.

    In SQLite ``INTEGER PRIMARY KEY`` makes the column an alias for the
    internal rowid.  ``INTEGER PRIMARY KEY AUTOINCREMENT`` prevents rowid
    reuse.
    """

    name = "sqlite_integer"

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'IntegerType', 'IntType'}


class SQLiteTextType(TextType):
    """SQLite TEXT — the only string affinity.

    SQLite does not distinguish CHAR/VARCHAR/TEXT at the storage level;
    all string-like types have TEXT affinity.  This class exists so the
    dialect can map ``VARCHAR`` / ``CHAR`` etc. to a canonical type during
    introspection round-trips.
    """

    name = "sqlite_text"

    length: int | None = None

    def __init__(self, dialect=None, length: int | None = None,
                 dialect_options: Dict[str, Any] | None = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.length = length

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'TextType', 'VarCharType', 'CharType'}


class SQLiteRealType(DataType):
    """SQLite REAL — affinity for floating-point types.

    Matches REAL, FLOAT, DOUBLE, and DOUBLE PRECISION in SQLite's
    type affinity mapping.
    """

    name = "sqlite_real"

    precision: int | None = None

    def __init__(self, dialect=None, precision: int | None = None,
                 dialect_options: Dict[str, Any] | None = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.precision = precision

    def _type_params(self) -> tuple:
        return (self.precision,)

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'RealType', 'FloatType', 'DoubleType'}


class SQLiteNumericType(DataType):
    """SQLite NUMERIC — affinity for DECIMAL / BOOLEAN / DATE / etc.

    SQLite maps ``DECIMAL``, ``NUMERIC``, ``BOOLEAN``, ``DATE``,
    ``DATETIME``, ``TIMESTAMP`` and ``TIME`` to this affinity.
    """

    name = "sqlite_numeric"

    precision: int | None = None
    scale: int | None = None

    def __init__(self, dialect=None, precision: int | None = None,
                 scale: int | None = None,
                 dialect_options: Dict[str, Any] | None = None):
        super().__init__(dialect, dialect_options=dialect_options)
        self.precision = precision
        self.scale = scale

    def _type_params(self) -> tuple:
        return (self.precision, self.scale)

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'DecimalType', 'NumericType', 'BooleanType',
                'DateType', 'DateTimeType', 'TimestampType',
                'TimestampTzType', 'TimeType', 'TimeTzType'}


class SQLiteBlobType(BlobType):
    """SQLite BLOB — affinity for binary data.

    SQLite maps ``BLOB``, ``BYTEA``, ``BINARY`` and ``VARBINARY`` to
    this affinity.
    """

    name = "sqlite_blob"

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'BlobType'}
