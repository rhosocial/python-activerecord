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

from typing import Tuple

from rhosocial.activerecord.backend.expression.types import (
    BlobType,
    DataType,
    IntegerType,
    PRECISION_PARAMETERS,
    RealType,
    TextType,
)

#: The token the SQLite type classes keep whole when their kind is derived.
#:
#: ``SQLite`` is a compound word and the general capital-run rule would split
#: it into ``sq_lite_...``, so the classes whose names begin with it name the
#: token here and keep it whole. The package's own ``__init__`` loop applies
#: the same token to the rest of the package's expressions, and both places
#: read this one value: a derived kind is part of the wire contract, so two
#: spellings of the token would be two places that have to stay in step with
#: nothing keeping them in step. Per ``.claude/rules/constants.md`` a value
#: read from more than one place, where the readings must agree, takes a
#: module-level constant and a test that pins it -- see
#: ``tests/rhosocial/activerecord_test/feature/rules/test_shared_defaults.py``.
SQLITE_KIND_RESERVED: Tuple[str, ...] = ("SQLite",)


class SQLiteIntegerType(IntegerType):
    """SQLite INTEGER — rowid alias when used as PRIMARY KEY.

    In SQLite ``INTEGER PRIMARY KEY`` makes the column an alias for the
    internal rowid.  ``INTEGER PRIMARY KEY AUTOINCREMENT`` prevents rowid
    reuse.
    """

    KIND_RESERVED = SQLITE_KIND_RESERVED

    name = "sqlite_integer"


class SQLiteTextType(TextType):
    """SQLite TEXT — the only string affinity.

    SQLite does not distinguish CHAR/VARCHAR/TEXT at the storage level;
    all string-like types have TEXT affinity.  This class exists so the
    dialect can map ``VARCHAR`` / ``CHAR`` etc. to a canonical type during
    introspection round-trips.
    """

    KIND_RESERVED = SQLITE_KIND_RESERVED

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

    KIND_RESERVED = SQLITE_KIND_RESERVED

    name = "sqlite_real"

    precision: int | None = None

    def __init__(self, dialect=None, precision: int | None = None,
                 ):
        super().__init__(dialect)
        self.precision = precision

    PARAMETERS = PRECISION_PARAMETERS

class SQLiteNumericType(DataType):
    """SQLite NUMERIC — the affinity that spans three type families.

    SQLite's documented affinity rules map ``DECIMAL``, ``NUMERIC``,
    ``BOOLEAN``, ``DATE``, ``DATETIME``, ``TIMESTAMP`` and ``TIME`` all to
    NUMERIC affinity.  A ``BOOLEAN`` column introspects as this class but is
    not a decimal, and a ``DATE`` column introspects as this class but is not
    a date either, so this class is deliberately **not** derived from any
    single core type.
    """

    KIND_RESERVED = SQLITE_KIND_RESERVED

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

    KIND_RESERVED = SQLITE_KIND_RESERVED

    name = "sqlite_blob"
