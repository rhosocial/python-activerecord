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

These are value objects: they carry only logical type parameters.
The SQLite dialect binds itself as the rendering dialect when it
instantiates them (see ``parse_type()`` in ``mixins/types.py``);
``bind()`` or ``to_sql(dialect=...)`` may be used at any other time.
"""

from __future__ import annotations

from typing import Set

from rhosocial.activerecord.backend.expression.types import (
    BlobType,
    DataType,
    IntegerType,
    TextType,
)
from rhosocial.activerecord.backend.expression.types._validation import (
    FLOAT_PRECISION_MAX,
    FLOAT_PRECISION_MIN,
    require_optional_range,
)


class SQLiteIntegerType(IntegerType):
    """SQLite INTEGER — rowid alias when used as PRIMARY KEY.

    In SQLite ``INTEGER PRIMARY KEY`` makes the column an alias for the
    internal rowid.  ``INTEGER PRIMARY KEY AUTOINCREMENT`` prevents rowid
    reuse.
    """

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

    length: int | None = None

    # SQLite has no length limit for TEXT; mirror the core string types' floor.
    LENGTH_MIN = 1
    LENGTH_MAX = None

    def __init__(self, dialect=None, *, length: int | None = None):
        super().__init__(dialect)
        self.length = require_optional_range(
            length, type(self).__name__, "length", self.LENGTH_MIN, self.LENGTH_MAX
        )

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'TextType', 'VarCharType', 'CharType'}


class SQLiteRealType(DataType):
    """SQLite REAL — affinity for floating-point types.

    Matches REAL, FLOAT, DOUBLE, and DOUBLE PRECISION in SQLite's
    type affinity mapping.
    """

    precision: int | None = None

    def __init__(self, dialect=None, *, precision: int | None = None):
        super().__init__(dialect)
        self.precision = require_optional_range(
            precision, type(self).__name__, "precision", FLOAT_PRECISION_MIN, FLOAT_PRECISION_MAX
        )

    def __eq__(self, other: object) -> bool:
        if type(self) is not type(other):
            return False
        return self.precision == other.precision

    def __hash__(self) -> int:
        return hash((type(self), self.precision))

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'RealType', 'FloatType', 'DoubleType'}


class SQLiteNumericType(DataType):
    """SQLite NUMERIC — affinity for DECIMAL / BOOLEAN / DATE / etc.

    SQLite maps ``DECIMAL``, ``NUMERIC``, ``BOOLEAN``, ``DATE``,
    ``DATETIME``, ``TIMESTAMP`` and ``TIME`` to this affinity.
    """

    precision: int | None = None
    scale: int | None = None

    def __init__(self, dialect=None, *,
                 precision: int | None = None, scale: int | None = None):
        super().__init__(dialect)
        self.precision = require_optional_range(
            precision, type(self).__name__, "precision", 1, None
        )
        self.scale = require_optional_range(
            scale, type(self).__name__, "scale", 0, self.precision if self.precision is not None else None
        )

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


class SQLiteBlobType(BlobType):
    """SQLite BLOB — affinity for binary data.

    SQLite maps ``BLOB``, ``BYTEA``, ``BINARY`` and ``VARBINARY`` to
    this affinity.
    """

    @classmethod
    def synonyms(cls) -> Set[str]:
        return {'BlobType'}
