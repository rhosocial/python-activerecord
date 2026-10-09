# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_column_suggestion.py
"""SQLite's own column-type table, and the narrowing it declares.

The protocol tests assert that the *rules* hold; this file asserts SQLite's
*answers*, so that a change to them has to be a deliberate edit with its reason
written down rather than a drift nobody notices:

1. all eighteen entries resolve, and to the classes §12 of the protocol assigns
   SQLite;
2. the table differs from core's dialect-less baseline in exactly the places
   the plan says it does -- the sequences and the numeric split -- and nowhere
   else;
3. ``ilike`` is narrowed while ``like`` is not, and the JSON operations are
   narrowed by whether this build actually has JSON1;
4. the dummy dialect is *not* this table. It keeps the neutral baseline on
   purpose, because it stands for no server.

No database is needed: every assertion is on the table or on the dialect, which
is never connected.
"""

import datetime
import decimal
import enum
import uuid

import pytest

from rhosocial.activerecord.backend.expression.column_suggestions import (
    COLUMN_TYPE_ENTRIES,
    NEUTRAL_COLUMN_TYPE_SUGGESTIONS,
)
from rhosocial.activerecord.backend.expression.column_types import (
    ArrayColumn,
    BinaryColumn,
    BooleanColumn,
    ColumnBase,
    DateTimeColumn,
    DecimalColumn,
    FloatColumn,
    IntegerColumn,
    JSONColumn,
    NumericColumn,
    StringColumn,
    UUIDColumn,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.mixins.column_suggestion import (
    SQLITE_COLUMN_TYPE_SUGGESTIONS,
)


def sqlite_dialect(version=(3, 46, 1)):
    """A version-adapted SQLite dialect.

    ``supports_json_type`` reads ``self.version``, and an unadapted dialect
    raises rather than answering -- so every test that touches the JSON gate
    needs a version. 3.46 is a real release well past the 3.38.0 line where the
    JSON functions became part of SQLite proper.
    """
    return SQLiteDialect(version=version)


def dummy_dialect():
    """An adapted dummy dialect: the dialect-less baseline, not a server."""
    dialect = DummyDialect()
    dialect._version = (3, 46, 1)
    return dialect


# ---------------------------------------------------------------------------
# 1. The table: eighteen answers, all of them SQLite's own
# ---------------------------------------------------------------------------

#: ``{entry: column class}`` as §12's SQLite row specifies it. Written out in
#: full rather than derived, because a derived table would restate the code's own
#: answer back at itself and could not catch a change to it.
_SQLITE_ANSWERS = [
    (bool, BooleanColumn),
    (int, IntegerColumn),
    (float, FloatColumn),
    (decimal.Decimal, DecimalColumn),
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


def test_the_table_answers_every_entry_of_the_protocol():
    """Completeness is the contract; a hole is a test failure, not a silent gap.

    SQLite is not special here -- every backend owes the same eighteen answers,
    and the ten backends are held to it in Phase 3. Core can enforce it for the
    backend it ships, so it does.
    """
    missing = [
        entry for entry in COLUMN_TYPE_ENTRIES if entry not in SQLITE_COLUMN_TYPE_SUGGESTIONS
    ]
    assert missing == []


def test_the_table_has_no_entry_beyond_the_protocols():
    """A backend may extend the list with a type of its own; SQLite has none.

    Asserted so that an extension added later is a deliberate act with its own
    entry in this file, rather than a key that appears in the table and is never
    checked by anything.
    """
    assert set(SQLITE_COLUMN_TYPE_SUGGESTIONS) == set(COLUMN_TYPE_ENTRIES)


def test_no_entry_is_answered_unsupported():
    """The probe found a working pairing for all eighteen, so none is refused.

    ``UNSUPPORTED`` would mean "this backend has no column for this value", and
    SQLite demonstrably does: a date is a TEXT column ``strftime`` reads, a dict
    is a TEXT column JSON1 reads. Refusing them would be reading the *storage*
    (no native type) as a statement about the *operations* -- the exact
    conflation the DataType/Column split exists to prevent.
    """
    from rhosocial.activerecord.backend.expression.column_suggestions import UNSUPPORTED

    assert UNSUPPORTED not in list(SQLITE_COLUMN_TYPE_SUGGESTIONS.values())


@pytest.mark.parametrize("entry, expected", _SQLITE_ANSWERS, ids=_ENTRY_IDS)
def test_every_entry_resolves_to_the_class_sqlite_states(entry, expected):
    """Through the public entry point, not by reading the dict."""
    assert sqlite_dialect().column_class_for(entry) is expected


@pytest.mark.parametrize("entry", COLUMN_TYPE_ENTRIES, ids=_ENTRY_IDS)
def test_every_answer_is_a_column_class(entry):
    assert issubclass(sqlite_dialect().column_class_for(entry), ColumnBase)


# ---------------------------------------------------------------------------
# 2. Where SQLite differs from the neutral baseline, and only there
# ---------------------------------------------------------------------------


def test_the_table_differs_from_the_neutral_baseline_exactly_where_the_plan_says():
    """The deviation set is pinned, so a change to it is a deliberate edit.

    §12 gives SQLite three cells of its own -- ``dict``, ``list`` and
    ``timedelta`` -- and two of those are what the neutral table already said,
    so the entries that actually move are the four sequences (SQLite has no array
    type, so a ``list`` field is a JSON document) plus ``float`` and
    ``Decimal``, which the common baseline splits out of ``NumericColumn``.

    Asserting the whole deviation set rather than spot-checking one entry is the
    point: a table that quietly started answering something else for, say,
    ``datetime.time`` would still pass a test that only looked at ``list``.
    """
    deviating = {
        entry
        for entry in COLUMN_TYPE_ENTRIES
        if SQLITE_COLUMN_TYPE_SUGGESTIONS[entry] is not NEUTRAL_COLUMN_TYPE_SUGGESTIONS[entry]
    }
    assert deviating == {list, tuple, set, frozenset, float, decimal.Decimal}


def test_the_sequences_are_documents_because_sqlite_has_no_array_type():
    """``ArrayColumn`` would offer ``array_length()`` and ``unnest()`` as if one existed.

    SQLite has no array type at all -- ``supports_array_type()`` is False and
    ``ARRAY[...]`` is a syntax error -- so suggesting ``ArrayColumn`` would hand
    the caller operations the engine cannot execute. The array probe shows the
    document route carries the same intent: length through ``json_array_length``,
    elements through ``$[n]``, containment and unnest through ``json_each``.
    """
    dialect = sqlite_dialect()
    assert dialect.supports_array_type() is False
    for entry in (list, tuple, set, frozenset):
        assert dialect.column_class_for(entry) is JSONColumn
        assert dialect.column_class_for(entry) is not ArrayColumn


def test_float_and_decimal_split_out_of_the_numeric_baseline():
    """Same operations, different names -- and a reader is meant to see which.

    ``FloatColumn`` and ``DecimalColumn`` offer exactly what ``NumericColumn``
    does, so this is not a functional change; it is the answer no longer hiding
    which of the two a field holds. ``timedelta`` stays ``NumericColumn``
    because a duration has no column class of its own yet.
    """
    dialect = sqlite_dialect()
    assert dialect.column_class_for(float) is FloatColumn
    assert dialect.column_class_for(decimal.Decimal) is DecimalColumn
    assert dialect.column_class_for(datetime.timedelta) is NumericColumn


# ---------------------------------------------------------------------------
# 3. Narrowing: ilike, and the JSON1 build assumption
# ---------------------------------------------------------------------------


def test_ilike_is_unavailable_because_sqlite_has_no_such_keyword():
    """A parse error, not a semantic difference.

    The probe on 3.50.4 returns ``near "ILIKE": syntax error`` -- there is no
    spelling to render -- which is why this is a refusal rather than a documented
    degradation. PostgreSQL and ClickHouse have the keyword; SQLite does not.
    """
    assert sqlite_dialect().supports_column_operation("StringColumn", "ilike") is False


def test_like_stays_available_and_is_not_the_same_operation():
    """The narrowing is on the pair, so ``like`` is untouched on the same column.

    Worth stating because SQLite's ``LIKE`` is *already* case-insensitive for
    ASCII -- the probe matches both ``'aXc'`` and ``'ABC'`` against ``'a%c'`` --
    which is why a caller who wanted case-insensitive matching can reach for it.
    It is a narrower guarantee than ``ILIKE``'s, not an equivalent one: non-ASCII
    stays case-sensitive. Over-narrowing here would refuse a query that works.
    """
    dialect = sqlite_dialect()
    assert dialect.supports_column_operation("StringColumn", "like") is True


def test_the_narrowing_is_on_the_pair_and_not_the_operation():
    """A backend that cannot ``ilike`` a string can still add two integers.

    Answering at the wider grain -- "no ``ilike`` on this backend" -- would
    refuse operations that are perfectly available, so the granularity is the
    ``(column class, operation)`` pair.
    """
    dialect = sqlite_dialect()
    assert dialect.supports_column_operation("IntegerColumn", "ilike") is True
    assert dialect.supports_column_operation("IntegerColumn", "like") is True


def test_json_path_is_available_when_the_build_has_json1():
    """The normal case: JSON1 is part of SQLite itself from 3.38.0."""
    assert sqlite_dialect().supports_column_operation("JSONColumn", "json_path") is True
    assert sqlite_dialect().supports_column_operation("JSONColumn", "json_value") is True


def test_json_path_is_narrowed_on_a_build_without_json1():
    """The JSON1 assumption is asked of the dialect, not assumed by the table.

    JSON1 is a compile-time extension below 3.38.0 and part of SQLite proper
    from 3.38.0 on, so this is a *build* property rather than a version gate --
    which is exactly why the answer cannot come from a version comparison in this
    mixin. It is delegated to
    :meth:`~rhosocial.activerecord.backend.impl.sqlite.dialect.SQLiteDialect.supports_json_type`,
    the detection the backend already runs, so a build compiled without the
    functions answers False for the JSON operations instead of the table quietly
    claiming a capability the server does not have.

    The column *class* is unaffected: ``dict`` still suggests ``JSONColumn``, so
    the model builds and the pairing is refused at the operation, which is the
    place a build-level limitation belongs.
    """
    without_json1 = SQLiteDialect(version=(3, 37, 0))
    without_json1.set_runtime_param("json1_available", False)
    assert without_json1.supports_column_operation("JSONColumn", "json_path") is False
    assert without_json1.supports_column_operation("JSONColumn", "json_value") is False
    # Everything else keeps its answer: one missing extension is not a backend
    # with no columns.
    assert without_json1.column_class_for(dict) is JSONColumn
    assert without_json1.supports_column_operation("StringColumn", "like") is True


def test_the_json_gate_follows_the_runtime_probe_on_an_old_version():
    """Below 3.38.0 the backend's own probe decides, and it is honoured."""
    probed_present = SQLiteDialect(version=(3, 37, 0))
    probed_present.set_runtime_param("json1_available", True)
    assert probed_present.supports_column_operation("JSONColumn", "json_path") is True


def test_the_json_gate_answers_before_the_dialect_is_adapted():
    """Reading a capability must not require a connection.

    ``supports_column_operation`` is consulted while a model is being built,
    which can precede ``introspect_and_adapt()``, and ``supports_json_type``
    reads ``self.version`` -- which raises on an unadapted dialect. The answer
    falls back to the linked library's own version rather than propagating the
    raise, because whether a caller has connected yet is not something a
    capability declaration should be sensitive to.
    """
    unadapted = SQLiteDialect()
    assert unadapted.supports_column_operation("JSONColumn", "json_path") is True
    assert unadapted.supports_column_operation("StringColumn", "ilike") is False


def test_operations_outside_the_two_narrowings_keep_the_default():
    """The burden of proof sits with the narrowing, not with the declaration."""
    dialect = sqlite_dialect()
    assert dialect.supports_column_operation("IntegerColumn", "mul") is True
    assert dialect.supports_column_operation("DateTimeColumn", "date_trunc") is True
    assert dialect.supports_column_operation("BooleanColumn", "is_true") is True
    assert dialect.supports_column_operation("UUIDColumn", "cast") is True


# ---------------------------------------------------------------------------
# 4. The dummy dialect is the baseline, not a copy of this backend
# ---------------------------------------------------------------------------


def test_the_dummy_dialect_keeps_the_neutral_baseline():
    """It stands for no server, so it states no backend's answers.

    SQLite is built into core and the dummy is the other dialect core ships, so
    the two are easy to conflate. They are deliberately different: the dummy is
    the dialect-less default a unit test reads, and copying a real backend's
    table into it would make "what does the neutral view say" unanswerable.
    """
    dialect = dummy_dialect()
    assert dialect.suggested_column_types() == NEUTRAL_COLUMN_TYPE_SUGGESTIONS


def test_the_dummy_dialect_resolves_every_entry_through_the_neutral_table():
    """Complete, as the baseline has to be, and still not SQLite's answer."""
    dialect = dummy_dialect()
    for entry in COLUMN_TYPE_ENTRIES:
        assert dialect.column_class_for(entry) is NEUTRAL_COLUMN_TYPE_SUGGESTIONS[entry]


def test_the_dummy_dialect_narrows_nothing():
    """No server means no evidence, and the default is "available"."""
    dialect = dummy_dialect()
    assert dialect.supports_column_operation("StringColumn", "ilike") is True
    assert dialect.supports_column_operation("JSONColumn", "json_path") is True


def test_the_two_dialects_really_do_differ_where_the_plan_says():
    """The distinction above is load-bearing, so it is checked rather than described."""
    sqlite, dummy = sqlite_dialect(), dummy_dialect()
    assert sqlite.column_class_for(list) is JSONColumn
    assert dummy.column_class_for(list) is ArrayColumn
    assert sqlite.column_class_for(decimal.Decimal) is DecimalColumn
    assert dummy.column_class_for(decimal.Decimal) is NumericColumn


# ---------------------------------------------------------------------------
# 5. The narrowed answers still build
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entry", COLUMN_TYPE_ENTRIES, ids=_ENTRY_IDS)
def test_every_entry_builds_a_column_that_renders(entry):
    """A suggestion is only real if the column it names can be constructed.

    ``column_class_for`` answering correctly and the object refusing to build
    would leave the failure at query time with a message about a column rather
    than about the annotation, which is the outcome the narrow column classes
    were introduced to remove. The two steps are written out here rather than
    imported from the query layer's helper because that is exactly what
    ``base/field_proxy.py`` does at runtime.
    """
    dialect = sqlite_dialect()
    column = dialect.column_class_for(entry)(dialect, "c")
    assert isinstance(column, ColumnBase)
    assert column.to_sql() == ('"c"', ())
