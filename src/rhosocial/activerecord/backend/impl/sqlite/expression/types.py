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

Each class carries ``backend="sqlite"`` so the ``DataType.__init__`` guard
does not reject them.
"""

from __future__ import annotations

from typing import Set

from rhosocial.activerecord.backend.expression.types import (
    BlobType,
    DataType,
    IntegerType,
    TextType,
)


class SQLiteIntegerType(IntegerType, backend="sqlite"):
    """SQLite INTEGER — rowid alias when used as PRIMARY KEY.

    In SQLite ``INTEGER PRIMARY KEY`` makes the column an alias for the
    internal rowid.  ``INTEGER PRIMARY KEY AUTOINCREMENT`` prevents rowid
    reuse.
    """

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'IntegerType', 'IntType'}


class SQLiteTextType(TextType, backend="sqlite"):
    """SQLite TEXT — the only string affinity.

    SQLite does not distinguish CHAR/VARCHAR/TEXT at the storage level;
    all string-like types have TEXT affinity.  This class exists so the
    dialect can map ``VARCHAR`` / ``CHAR`` etc. to a canonical type during
    introspection round-trips.
    """

    length: int | None = None

    def __init__(self, length: int | None = None, dialect=None):
        super().__init__(dialect)
        self.length = length

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'TextType', 'VarCharType', 'CharType'}


class SQLiteRealType(DataType, backend="sqlite"):
    """SQLite REAL — affinity for floating-point types.

    Matches REAL, FLOAT, DOUBLE, and DOUBLE PRECISION in SQLite's
    type affinity mapping.
    """

    precision: int | None = None

    def __init__(self, precision: int | None = None, dialect=None):
        super().__init__(dialect)
        self.precision = precision

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision

    def __hash__(self) -> int:
        return hash((type(self), self.precision))

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'RealType', 'FloatType', 'DoubleType'}


class SQLiteNumericType(DataType, backend="sqlite"):
    """SQLite NUMERIC — affinity for DECIMAL / BOOLEAN / DATE / etc.

    SQLite maps ``DECIMAL``, ``NUMERIC``, ``BOOLEAN``, ``DATE``,
    ``DATETIME``, ``TIMESTAMP`` and ``TIME`` to this affinity.
    """

    precision: int | None = None
    scale: int | None = None

    def __init__(self, precision: int | None = None, scale: int | None = None,
                 dialect=None):
        super().__init__(dialect)
        self.precision = precision
        self.scale = scale

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision and self.scale == other.scale

    def __hash__(self) -> int:
        return hash((type(self), self.precision, self.scale))

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'DecimalType', 'NumericType', 'BooleanType',
                'DateType', 'DateTimeType', 'TimestampType',
                'TimestampTzType', 'TimeType', 'TimeTzType'}


class SQLiteBlobType(BlobType, backend="sqlite"):
    """SQLite BLOB — affinity for binary data.

    SQLite maps ``BLOB``, ``BYTEA``, ``BINARY`` and ``VARBINARY`` to
    this affinity.
    """

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'BlobType'}
