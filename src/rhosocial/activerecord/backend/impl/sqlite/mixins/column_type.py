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
* **timedelta** -> :class:`~...column_types.IntervalColumn`. There is no
  interval type in SQLite, so a duration is a number of seconds; the value
  layer rejects ``timedelta`` at bind time, hence the converter. The class
  names the value -- a span -- rather than the numeric storage, and it
  promises no arithmetic.
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
* **Geometry / Vector / BitString / Range / Multirange / MacAddress** -> their
  core column classes. SQLite has no spatial, vector, range or bit operation,
  but those classes promise none: they carry only alias, null tests, casting
  and collation, which SQLite does execute on a value it stores as text or
  JSON. The family operations belong to a backend that has them, and such a
  backend declares its own class deriving from the core one.

The JSON1 build assumption
--------------------------
Every JSON entry rests on the **JSON1** functions. Since 3.38.0 they are part
of the SQLite build proper; below that they were a compile-time extension, and
the detection already lives on the dialect
(:meth:`~rhosocial.activerecord.backend.impl.sqlite.dialect.SQLiteDialect.supports_json_type`).
This table claims the pairing; the build is the dialect's fact to report when
the JSON operations are consulted.
"""
from rhosocial.activerecord.backend.suggestion.definitions import ColumnTypeSuggestion, ExtraColumnTypeSuggestion


import datetime
import decimal
import enum
import uuid
from typing import Any, Dict, Optional, Type

from rhosocial.activerecord.backend.adapters import (
    BitString,
    Geometry,
    MacAddress,
    Multirange,
    Range,
    Vector,
)
from rhosocial.activerecord.backend.expression.column_types import (
    BinaryColumn,
    BitStringColumn,
    BooleanColumn,
    ColumnBase,
    GeometryColumn,
    IntegerColumn,
    IntervalColumn,
    JSONColumn,
    MacAddressColumn,
    MultirangeColumn,
    NumericColumn,
    RangeColumn,
    StringColumn,
    TimestampColumn,
    UUIDColumn,
    VectorColumn,
)

#: SQLite's full table: ``{framework-modelled Python type: ColumnBase subclass}``.
#:
#: No common scalar is ``None``: the probe found a working pairing for all
#: eighteen on 3.50.4, and an entry answered with ``None`` would be a claim that
#: this backend has no column for a value it demonstrably carries.
#:
#: The six complex families name the matching core column class. Those classes
#: (``GeometryColumn`` and siblings) carry only alias, null tests, casting and
#: collation -- exactly what SQLite can do with a value it stores as text or
#: JSON -- so naming one promises nothing SQLite cannot execute. The family
#: operations stay in a backend that actually has them.
SQLITE_COLUMN_TYPES: Dict[Any, Optional[Type[ColumnBase]]] = {
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
    # A duration is a duration even when the storage is a number of units: the
    # class names the value, and ``IntervalColumn`` promises no arithmetic.
    datetime.timedelta: IntervalColumn,
    uuid.UUID: UUIDColumn,
    dict: JSONColumn,
    # No array type exists in SQLite, so the four sequence entries take the
    # document column class rather than `ArrayColumn`.
    list: JSONColumn,
    tuple: JSONColumn,
    set: JSONColumn,
    frozenset: JSONColumn,
    enum.Enum: StringColumn,
    # Carried as text/JSON; the class names the value, not an operation.
    Geometry: GeometryColumn,
    Vector: VectorColumn,
    BitString: BitStringColumn,
    Range: RangeColumn,
    Multirange: MultirangeColumn,
    MacAddress: MacAddressColumn,
}


class SQLiteColumnTypeMixin:
    """SQLite's answer to "which column class does this annotation mean here"."""

    def suggest_column_types(self) -> Dict[Any, Type[ColumnBase]]:
        return ColumnTypeSuggestion(table=dict(SQLITE_COLUMN_TYPES))


    def suggest_extra_column_types(self):
        """No backend-owned extra column types."""
        return ExtraColumnTypeSuggestion(table={})


__all__ = ["SQLITE_COLUMN_TYPES", "SQLiteColumnTypeMixin"]
