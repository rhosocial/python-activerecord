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

Why four of the five derive from a core type and one does not
-------------------------------------------------------------
``INTEGER``, ``TEXT``, ``REAL`` and ``BLOB`` each name one core concept, so
those classes derive from it.  ``NUMERIC`` does not: SQLite's own affinity
rules map ``DECIMAL``, ``NUMERIC``, ``BOOLEAN``, ``DATE``, ``DATETIME``,
``TIMESTAMP`` *and* ``TIME`` onto it, so the affinity spans the numeric,
boolean and temporal families at once and there is no single core type it
could honestly be.  That is a deliberate placement, not an omission — the
schema differ compares two introspected columns and both arrive as this
class, so the collapse is where it belongs.
"""

from __future__ import annotations

from rhosocial.activerecord.backend.expression.types import (
    BlobType,
    DataType,
    IntegerType,
    RealType,
    TextType,
)


class SQLiteIntegerType(IntegerType):
    """SQLite INTEGER — rowid alias when used as PRIMARY KEY.

    In SQLite ``INTEGER PRIMARY KEY`` makes the column an alias for the
    internal rowid.  ``INTEGER PRIMARY KEY AUTOINCREMENT`` prevents rowid
    reuse.
    """

    name = "sqlite_integer"


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
                 ):
        super().__init__(dialect)
        self.length = length


class SQLiteRealType(RealType):
    """SQLite REAL — affinity for floating-point types.

    Matches REAL, FLOAT, DOUBLE, and DOUBLE PRECISION in SQLite's
    type affinity mapping.
    """

    name = "sqlite_real"

    precision: int | None = None

    def __init__(self, dialect=None, precision: int | None = None,
                 ):
        super().__init__(dialect)
        self.precision = precision

    PARAMETERS = ("precision",)

class SQLiteNumericType(DataType):
    """SQLite NUMERIC — the affinity that spans three type families.

    SQLite's documented affinity rules map ``DECIMAL``, ``NUMERIC``,
    ``BOOLEAN``, ``DATE``, ``DATETIME``, ``TIMESTAMP`` and ``TIME`` all to
    NUMERIC affinity.  A ``BOOLEAN`` column introspects as this class but is
    not a decimal, and a ``DATE`` column introspects as this class but is not
    a date either, so this class is deliberately **not** derived from any
    single core type.
    """

    name = "sqlite_numeric"

    precision: int | None = None
    scale: int | None = None

    def __init__(self, dialect=None, precision: int | None = None,
                 scale: int | None = None,
                 ):
        super().__init__(dialect)
        self.precision = precision
        self.scale = scale

    PARAMETERS = ("precision", "scale",)

class SQLiteBlobType(BlobType):
    """SQLite BLOB — affinity for binary data.

    SQLite maps ``BLOB``, ``BYTEA``, ``BINARY`` and ``VARBINARY`` to
    this affinity.
    """

    name = "sqlite_blob"
