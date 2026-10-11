# src/rhosocial/activerecord/backend/impl/sqlite/mixins/column_type.py
"""SQLite's column-type table: the class each common Python type means here.

This is the SQLite half of the column-type protocol: the answer for each of
the common Python types the framework defines.

Why SQLite answers for itself at all
------------------------------------
SQLite has five storage affinities -- TEXT, INTEGER, REAL, BLOB, NUMERIC --
and no ``BOOLEAN``, no ``DATE``, no ``UUID``, no ``JSON``, no array. It would
be easy to read that as "SQLite cannot host these column classes" and answer
with nothing, and that would be wrong in the direction this protocol exists to
prevent. The probe (``plan/2026-10-08/suggested-pairing-*.md``, SQLite 3.50.4)
shows the opposite: the *storage* is a convention the value layer converts to
and from, while the *operations* are carried by real SQL that runs. ``dict``
is a TEXT column the JSON1 functions read; a date is a TEXT column ``strftime``
and ``julianday`` understand; a boolean is an INTEGER 0/1 column whose
three-valued logic ``IS TRUE`` gets right. Refusing these would throw away a
working pairing because the storage has no native type -- exactly the
conflation the DataType/Column separation forbids.

The evidence, per entry group (all measured on SQLite 3.50.4)
-------------------------------------------------------------
* **bool** -> :class:`~...column_types.BooleanColumn`. Stored INTEGER 0/1; the
  boolean battery passes in full except for rendering-discipline items
  (``= 1`` / ``= 0`` literals, which the framework forbids anyway).
* **int / float / decimal.Decimal** -> :class:`~...column_types.IntegerColumn`
  / :class:`~...column_types.NumericColumn` / ``NumericColumn``. SQLite has
  real INTEGER and REAL, and ``NUMERIC`` is only an *affinity* -- a Decimal
  travels as a float and reads back as one. That is a value-layer conversion,
  not a missing operation.
* **str / enum.Enum** -> :class:`~...column_types.StringColumn`. TEXT storage;
  ``length('Zebra')`` is 5 characters, so the class's ``LENGTH`` is
  character-based. An enum is TEXT + ``CHECK``: the probe confirms an illegal
  member is rejected with ``CHECK failed``, at the price of lexicographic
  rather than declaration-order sorting. ``ilike`` has no SQLite keyword at
  all (``near "ILIKE": syntax error``); how case-insensitive matching is
  offered is the column layer's decision, not this table's.
* **bytes / bytearray** -> :class:`~...column_types.BinaryColumn`. BLOB
  storage; equality, byte length, substring, concatenation and ``hex()`` all
  pass. One value-layer caveat: sqlite3 decodes fetched BLOB as UTF-8 and
  raises on bytes that are not text.
* **date / time / datetime** ->
  :class:`~...column_types.TimestampColumn`. All are TEXT; microseconds survive
  in the text form. The arithmetic domain goes through ``julianday``, whose
  differences carry ~1 ms of floating-point error, and there are no named time
  zones -- documented limits of the backend rather than absent operations.
* **timedelta** -> :class:`~...column_types.NumericColumn`. There is no
  interval type in SQLite, so a duration is a number of seconds; the value
  layer rejects ``timedelta`` at bind time, hence the converter.
* **uuid.UUID** -> :class:`~...column_types.UUIDColumn`. TEXT substitution; the
  class carries no UUID-specific operator anyway, and sqlite3 refuses to bind
  a ``uuid.UUID`` object, so a converter writes the canonical string.
* **dict** -> :class:`~...column_types.JSONColumn` (JSON1). Scalar and nested
  paths, has-key, array length, validity and whole-document equality all pass;
  only binding a ``dict`` fails, and the framework's ``json.dumps`` is the fix.
* **list / tuple / set / frozenset** ->
  :class:`~...column_types.JSONColumn`. SQLite has no array type
  (``ARRAY[...]`` is a syntax error), so the honest class is the document one:
  length, element access via ``$[n]``, containment via ``json_each`` all work.
  ``ArrayColumn`` here would offer ``array_length()`` / ``unnest()`` as if a
  native array existed.

The JSON1 build assumption
--------------------------
Every JSON entry rests on the **JSON1** functions. Since 3.38.0 they are part
of the SQLite build proper; below that they were a compile-time extension, and
the detection already lives on the dialect
(:meth:`~rhosocial.activerecord.backend.impl.sqlite.dialect.SQLiteDialect.supports_json_type`).
This table claims the pairing; the build is the dialect's fact to report when
the JSON operations are consulted.
"""

import datetime
import decimal
import enum
import uuid
from typing import Any, Dict, Type

from rhosocial.activerecord.backend.dialect.mixins.column_type import ColumnTypeMixin
from rhosocial.activerecord.backend.expression.column_types import (
    BinaryColumn,
    BooleanColumn,
    ColumnBase,
    TimestampColumn,
    IntegerColumn,
    JSONColumn,
    NumericColumn,
    StringColumn,
    UUIDColumn,
)

#: SQLite's full table: ``{common Python type: ColumnBase subclass}``.
#:
#: No entry is ``None``: the probe found a working pairing for all eighteen on
#: 3.50.4, and an entry answered with ``None`` would be a claim that this
#: backend has no column for a value it demonstrably carries.
SQLITE_COLUMN_TYPES: Dict[Any, Type[ColumnBase]] = {
    bool: BooleanColumn,
    int: IntegerColumn,
    float: NumericColumn,
    decimal.Decimal: NumericColumn,
    str: StringColumn,
    bytes: BinaryColumn,
    bytearray: BinaryColumn,
    datetime.date: TimestampColumn,
    datetime.time: TimestampColumn,
    datetime.datetime: TimestampColumn,
    datetime.timedelta: NumericColumn,
    uuid.UUID: UUIDColumn,
    dict: JSONColumn,
    # No array type exists in SQLite, so the four sequence entries take the
    # document column class rather than `ArrayColumn`.
    list: JSONColumn,
    tuple: JSONColumn,
    set: JSONColumn,
    frozenset: JSONColumn,
    enum.Enum: StringColumn,
}


class SQLiteColumnTypeMixin(ColumnTypeMixin):
    """SQLite's answer to "which column class does this annotation mean here"."""

    def suggested_column_types(self) -> Dict[Any, Type[ColumnBase]]:
        return dict(SQLITE_COLUMN_TYPES)


__all__ = ["SQLITE_COLUMN_TYPES", "SQLiteColumnTypeMixin"]
