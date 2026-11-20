# src/rhosocial/activerecord/backend/impl/sqlite/adapters/__init__.py
"""SQLite-specific type adapters.

This package keeps the historical import path stable:

    from rhosocial.activerecord.backend.impl.sqlite.adapters import SQLiteJSONAdapter

All public adapter classes are re-exported here; the submodules are internal
implementation details and are not a stable API.

Design rationale
----------------
SQLite has dynamic typing / type affinity, so a column's declared type only
influences affinity and any value can be stored in any column. The adapters in
this package therefore implement *application-level conventions*: they decide
which textual or binary representation a Python value is bound and read as.

Adapters provided:

- :class:`SQLiteBlobAdapter` -- bytes vs BLOB (no standard adapter exists).
- :class:`SQLiteJSONAdapter` -- dict/list vs TEXT, with the extended serializer
  SQLite users expect (datetime, UUID, Decimal, set), plus optional
  ``default``/``object_hook`` hooks for neutral-type codecs.
- :class:`SQLiteUUIDAdapter` -- UUID vs TEXT or BLOB.
- :class:`SQLiteGeometryAdapter` -- neutral geometry vs TEXT WKT, optionally
  prefixed with ``SRID=...;`` (EWKT prefix).
- :class:`SQLiteVectorAdapter` -- neutral dense vector vs a JSON array in TEXT.
- :class:`SQLiteBitStringAdapter` -- neutral bit string vs a ``0``/``1`` text.
- :class:`SQLiteRangeAdapter` -- neutral ``Range``/``Multirange`` vs TEXT JSON.
- :class:`SQLiteMacAddressAdapter` -- neutral ``MacAddress`` vs canonical text.

The neutral family adapters derive from the bases in
``rhosocial.activerecord.backend.adapters``; they only add a concrete SQLite
storage shape (TEXT). Conversion failures are reported as
:class:`~rhosocial.activerecord.backend.errors.TypeConversionError` by those
bases, so callers get one error type regardless of family.
"""

from .binary import SQLiteBlobAdapter
from .bitstring import SQLiteBitStringAdapter
from .document import SQLiteJSONAdapter
from .identifiers import SQLiteUUIDAdapter
from .network import SQLiteMacAddressAdapter
from .range import SQLiteRangeAdapter
from .spatial import SQLiteGeometryAdapter
from .vector import SQLiteVectorAdapter

__all__ = [
    "SQLiteBitStringAdapter",
    "SQLiteBlobAdapter",
    "SQLiteGeometryAdapter",
    "SQLiteJSONAdapter",
    "SQLiteMacAddressAdapter",
    "SQLiteRangeAdapter",
    "SQLiteUUIDAdapter",
    "SQLiteVectorAdapter",
]
