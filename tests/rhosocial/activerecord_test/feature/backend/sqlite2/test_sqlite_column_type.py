# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_column_type.py
"""SQLite's own column-type table.

The protocol tests assert that the *rules* hold; this file asserts SQLite's
*answers*, so that a change to them has to be a deliberate edit with its reason
written down rather than a drift nobody notices:

1. all eighteen common entries resolve, and to SQLite's classes;
2. the table differs from the portable dummy baseline in exactly the places the
   evidence says it does -- the four sequence entries -- and nowhere else;
3. the dummy dialect is *not* this table: it states the portable baseline.

No database is needed: every assertion is on the table or on a never-connected
dialect.
"""

import datetime
import decimal
import enum
import uuid

import pytest

from rhosocial.activerecord.backend.expression.column_types import (
    ArrayColumn,
    BinaryColumn,
    BooleanColumn,
    ColumnBase,
    DateTimeColumn,
    IntegerColumn,
    JSONColumn,
    NumericColumn,
    StringColumn,
    UUIDColumn,
)
from rhosocial.activerecord.backend.impl.dummy.column_type import DUMMY_COLUMN_TYPES
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.mixins.column_type import (
    SQLITE_COLUMN_TYPES,
)

from column_helpers import COMMON_TYPES, resolve_column_class


def sqlite_dialect(version=(3, 46, 1)):
    """A version-adapted SQLite dialect; 3.46 is well past the JSON1 line."""
    return SQLiteDialect(version=version)


def dummy_dialect():
    """An adapted dummy dialect: the dialect-less baseline, not a server."""
    dialect = DummyDialect()
    dialect._version = (3, 46, 1)
    return dialect


#: ``{entry: column class}`` as SQLite states it. Written out in full rather
#: than derived, because a derived table would restate the code's own answer
#: back at itself and could not catch a change to it.
_SQLITE_ANSWERS = [
    (bool, BooleanColumn),
    (int, IntegerColumn),
    (float, NumericColumn),
    (decimal.Decimal, NumericColumn),
    (str, StringColumn),
    (bytes, BinaryColumn),
    (bytearray, BinaryColumn),
    (datetime.date, DateTimeColumn),
    (datetime.time, DateTimeColumn),
    (datetime.datetime, DateTimeColumn),
    (datetime.timedelta, NumericColumn),
    (uuid.UUID, UUIDColumn),
    (dict, JSONColumn),
    (list, JSONColumn),
    (tuple, JSONColumn),
    (set, JSONColumn),
    (frozenset, JSONColumn),
    (enum.Enum, StringColumn),
]

_ENTRY_IDS = [getattr(entry, "__name__", str(entry)) for entry, _ in _SQLITE_ANSWERS]


def test_the_table_answers_every_entry_of_the_contract():
    """Completeness is the contract; a hole is a test failure, not a silent gap.

    SQLite is not special here -- every backend owes the same eighteen answers,
    and the ten backends are held to it in their own CI. Core can enforce it
    for the backend it ships, so it does.
    """
    missing = [entry for entry in COMMON_TYPES if entry not in SQLITE_COLUMN_TYPES]
    assert missing == []


def test_the_table_has_no_entry_beyond_the_contract():
    """A backend may extend the list with a type of its own; SQLite has none.

    Asserted so that an extension added later is a deliberate act with its own
    entry in this file, rather than a key that appears in the table and is never
    checked by anything.
    """
    assert set(SQLITE_COLUMN_TYPES) == set(COMMON_TYPES)


def test_no_entry_is_answered_with_none():
    """The probe found a working pairing for all eighteen, so none is refused.

    ``None`` would mean "this backend has no column for this value", and SQLite
    demonstrably does: a date is a TEXT column ``strftime`` reads, a dict is a
    TEXT column JSON1 reads. Refusing them would be reading the *storage* (no
    native type) as a statement about the *operations* -- the exact conflation
    the DataType/Column split exists to prevent.
    """
    assert None not in SQLITE_COLUMN_TYPES.values()


@pytest.mark.parametrize("entry, expected", _SQLITE_ANSWERS, ids=_ENTRY_IDS)
def test_every_entry_selects_the_class_sqlite_states(entry, expected):
    """Through the selection, not by reading the dict."""
    assert resolve_column_class(sqlite_dialect(), entry) is expected


@pytest.mark.parametrize("entry", COMMON_TYPES, ids=_ENTRY_IDS)
def test_every_answer_is_a_column_class(entry):
    assert issubclass(resolve_column_class(sqlite_dialect(), entry), ColumnBase)


def test_the_sequences_are_documents_because_sqlite_has_no_array_type():
    """``ArrayColumn`` would offer ``array_length()`` / ``unnest()`` as if one existed.

    SQLite has no array type at all -- ``supports_array_type()`` is False and
    ``ARRAY[...]`` is a syntax error -- so suggesting ``ArrayColumn`` would hand
    the caller operations the engine cannot execute. The array probe shows the
    document route carries the same intent: length through ``json_array_length``,
    elements through ``$[n]``, containment and unnest through ``json_each``.
    """
    dialect = sqlite_dialect()
    assert dialect.supports_array_type() is False
    for entry in (list, tuple, set, frozenset):
        assert resolve_column_class(dialect, entry) is JSONColumn
        assert resolve_column_class(dialect, entry) is not ArrayColumn


def test_the_numeric_entries_take_the_one_numeric_class():
    """float / Decimal / timedelta all answer NumericColumn.

    The numeric family is one class by decision: the operations are the same
    whatever the value was declared as, and the difference between a
    ``NUMERIC(18,4)`` and a ``DOUBLE PRECISION`` belongs to the DDL layer's
    ``DataType``. A duration is a number of seconds here, so it answers the
    same class as the other numbers.
    """
    dialect = sqlite_dialect()
    assert resolve_column_class(dialect, float) is NumericColumn
    assert resolve_column_class(dialect, decimal.Decimal) is NumericColumn
    assert resolve_column_class(dialect, datetime.timedelta) is NumericColumn


def test_the_dummy_dialect_states_the_portable_baseline():
    """It stands for no server, so it states no backend's answers.

    SQLite is built into core and the dummy is the other dialect core ships, so
    the two are easy to conflate. They are deliberately different: the dummy is
    the dialect-less default a unit test reads, and copying a real backend's
    table into it would make "what does the portable baseline say" unanswerable.
    """
    dummy = dummy_dialect()
    assert dummy.suggested_column_types() == DUMMY_COLUMN_TYPES
    for entry in COMMON_TYPES:
        assert resolve_column_class(dummy, entry) is DUMMY_COLUMN_TYPES[entry]


def test_the_two_dialects_really_do_differ_where_stated():
    """The distinction above is load-bearing, so it is checked rather than described."""
    sqlite, dummy = sqlite_dialect(), dummy_dialect()
    assert resolve_column_class(sqlite, list) is JSONColumn
    assert resolve_column_class(dummy, list) is ArrayColumn
    # The numeric merge is shared by both tables.
    assert resolve_column_class(sqlite, decimal.Decimal) is NumericColumn
    assert resolve_column_class(dummy, decimal.Decimal) is NumericColumn


@pytest.mark.parametrize("entry", COMMON_TYPES, ids=_ENTRY_IDS)
def test_every_entry_builds_a_column_that_renders(entry):
    """A table answer is only real if the column it names can be constructed.

    The selection answering correctly and the object refusing to build would
    leave the failure at query time with a message about a column rather than
    about the annotation, which is the outcome the narrow column classes were
    introduced to remove.
    """
    dialect = sqlite_dialect()
    column = resolve_column_class(dialect, entry)(dialect, "c")
    assert isinstance(column, ColumnBase)
    assert column.to_sql() == ('"c"', ())
