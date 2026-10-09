# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_interval_qualifier.py
"""``INTERVAL``'s qualifier is a closed vocabulary, not a free string.

``IntervalType.fields`` reaches DDL: three dialects interpolate it straight into
``INTERVAL <fields>`` and one of them upper-cases it. A DDL position cannot take
a bound parameter, so an unchecked string there is an injection — and until this
was closed, ``IntervalType(dialect, fields="DAY TO SECOND); DROP TABLE t--")``
rendered that text into a ``CREATE TABLE``.

The replacement has one hard requirement: **every currently-rendering dialect
must produce byte-identical SQL.** Oracle, PostgreSQL and the dummy dialect all
interpolate the value directly, so the fix could not be an ``enum.Enum`` — that
would have rewritten their output to ``INTERVAL IntervalField.YEAR``. The value
is therefore an ``IntervalQualifier``, a validated ``str``, and these tests pin
both halves of that bargain: the rendered bytes stay the same, and an unknown
qualifier is now an error naming it.
"""

import json

import pytest

from rhosocial.activerecord.backend.expression.types import (
    INTERVAL_QUALIFIERS,
    InvalidIntervalQualifierError,
    IntervalQualifier,
    IntervalType,
    is_valid_interval_qualifier,
    validate_interval_qualifier,
)


def _dummy():
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

    return DummyDialect()


def _sqlite():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    return SQLiteDialect(version=(3, 45, 0))


# ---------------------------------------------------------------------------
# The vocabulary
# ---------------------------------------------------------------------------


def test_the_vocabulary_is_the_thirteen_sql_qualifiers():
    """Closed means closed: the set is enumerated, and it is the standard's.

    Six single fields and seven contiguous ranges. Not a free string that happens
    to look like one, and not the sixteen combinations a naive "field TO field"
    grammar would accept — ``YEAR TO DAY`` is not a resolution any backend has.
    """
    assert INTERVAL_QUALIFIERS == {
        "YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND",
        "YEAR TO MONTH",
        "DAY TO HOUR", "DAY TO MINUTE", "DAY TO SECOND",
        "HOUR TO MINUTE", "HOUR TO SECOND", "MINUTE TO SECOND",
    }


@pytest.mark.parametrize("qualifier", sorted(INTERVAL_QUALIFIERS))
def test_every_member_of_the_vocabulary_is_accepted(qualifier):
    assert is_valid_interval_qualifier(qualifier)
    assert validate_interval_qualifier(qualifier) == qualifier
    assert IntervalQualifier(qualifier) == qualifier


@pytest.mark.parametrize("qualifier", [
    # Not contiguous ranges — a resolution has to be a span, not a pair.
    "YEAR TO DAY",
    "MONTH TO YEAR",
    "SECOND TO YEAR",
    "DAY TO MONTH",
    # A field the standard does not name for an interval.
    "QUARTER",
    "EPOCH",
    # Injections and near-misses. The position takes no bound parameter, so
    # this is the whole defence.
    "DAY TO SECOND); DROP TABLE t--",
    "DAY TO SECOND, HOUR",
    "SECOND)",
    "",
    "   ",
    "YEAR TO",
    "TO MONTH",
    "DAY TO SECOND EXTRA",
    42,
])
def test_an_unknown_qualifier_is_refused_and_named(qualifier):
    """A refusal a caller can act on: it names the value and the accepted set."""
    with pytest.raises(InvalidIntervalQualifierError) as excinfo:
        IntervalType(_dummy(), fields=qualifier)
    message = str(excinfo.value)
    assert repr(qualifier) in message or str(qualifier) in message
    assert "DAY TO SECOND" in message, "the message must list what is accepted"
    assert not is_valid_interval_qualifier(qualifier)


def test_no_qualifier_is_not_a_qualifier():
    """``None`` means "unqualified", which is a different thing from unknown.

    A bare ``IntervalType()`` is legal SQL on every backend and means the
    backend's default resolution, so it must keep constructing; it just is not a
    member of the vocabulary.
    """
    dialect = _dummy()
    assert IntervalType(dialect).fields is None
    assert not is_valid_interval_qualifier(None)


def test_a_precision_is_part_of_the_vocabulary_not_a_way_past_it():
    """Oracle writes ``DAY(2) TO SECOND(6)`` and introspection reads it back.

    So the precision belongs to the grammar and to the accepted shapes, and a
    precision cannot smuggle a different field past the shape check.
    """
    for qualifier in ("SECOND(6)", "DAY(3)", "DAY(2) TO SECOND(6)",
                      "YEAR(3) TO MONTH(6)"):
        assert is_valid_interval_qualifier(qualifier), qualifier
    assert not is_valid_interval_qualifier("YEAR(3) TO DAY(9)")
    assert not is_valid_interval_qualifier("SECOND(6) TO MINUTE")
    assert not is_valid_interval_qualifier("DAY(x) TO SECOND(y)")


def test_a_refused_qualifier_leaves_no_type_behind():
    """The type is not half-built: the refusal happens before anything is set."""
    dialect = _dummy()
    with pytest.raises(InvalidIntervalQualifierError):
        IntervalType(dialect, fields="YEAR TO DAY")
    assert IntervalType(dialect).fields is None


# ---------------------------------------------------------------------------
# Byte-identical rendering
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fields,expected", [
    (None, "INTERVAL"),
    ("YEAR", "INTERVAL YEAR"),
    ("MONTH", "INTERVAL MONTH"),
    ("YEAR TO MONTH", "INTERVAL YEAR TO MONTH"),
    ("DAY TO SECOND", "INTERVAL DAY TO SECOND"),
    ("HOUR TO SECOND", "INTERVAL HOUR TO SECOND"),
    ("SECOND(6)", "INTERVAL SECOND(6)"),
    ("DAY(2) TO SECOND(6)", "INTERVAL DAY(2) TO SECOND(6)"),
])
def test_a_rendering_dialect_renders_the_same_bytes_it_did_before(fields, expected):
    """The dummy dialect interpolates verbatim, exactly as it always has.

    This is the regression guard for the *design*, not for the vocabulary: if the
    qualifier ever becomes an object whose ``str()`` is not the qualifier, this is
    the test that says the backends' DDL moved.
    """
    dialect = _dummy()
    sql, params = dialect.format_data_type(IntervalType(dialect, fields=fields))
    assert (sql, params) == (expected, ())


def test_a_dialect_with_no_interval_type_ignores_the_qualifier_as_before():
    """SQLite has no interval type and stores the span as a number.

    Its formatter returns ``NUMERIC`` and never reads ``fields``, which is the
    honest answer — there is nowhere in an INTEGER-affinity column for a
    resolution to live. The qualifier is validated on the way in and simply not
    rendered.
    """
    dialect = _sqlite()
    for fields in (None, "YEAR TO MONTH", "DAY(2) TO SECOND(6)"):
        assert dialect.format_data_type(
            IntervalType(dialect, fields=fields)
        ) == ("NUMERIC", ())


# ---------------------------------------------------------------------------
# The value type is a ``str``, on purpose
# ---------------------------------------------------------------------------


def test_the_qualifier_is_a_string_so_no_rendering_moves():
    """Every use a backend could make of the value behaves as it did.

    Oracle upper-cases it, PostgreSQL and dummy interpolate it, the schema
    snapshot serialises it to JSON, equality and hashing compare it, and ``repr``
    shows up in test failures. All five would have changed under an enum.
    """
    qualifier = IntervalQualifier("YEAR TO MONTH")
    assert isinstance(qualifier, str)
    assert f"INTERVAL {qualifier}" == "INTERVAL YEAR TO MONTH"
    assert qualifier.upper() == "YEAR TO MONTH"
    assert qualifier == "YEAR TO MONTH"
    assert hash(qualifier) == hash("YEAR TO MONTH")
    assert repr(qualifier) == "'YEAR TO MONTH'"
    assert json.dumps({"fields": qualifier}) == '{"fields": "YEAR TO MONTH"}'


def test_the_spelling_is_written_the_way_it_was_given():
    """No case normalisation: a backend that renders verbatim must not change.

    Oracle upper-cases, PostgreSQL and dummy do not. Normalising here would
    silently rewrite what a caller wrote on two of them, which is a rendering
    change dressed up as a tidy-up.
    """
    dialect = _dummy()
    assert dialect.format_data_type(
        IntervalType(dialect, fields="year to month")
    )[0] == "INTERVAL year to month"


def test_identity_and_serialisation_round_trip():
    """``fields`` is part of identity and of the constructor round trip.

    Two intervals of different resolution are different types, and a snapshot
    taken with one has to come back as one.
    """
    from rhosocial.activerecord.backend.schema.snapshot import (
        _data_type_from_dict,
        _data_type_to_dict,
    )

    year = IntervalType(_dummy(), fields="YEAR TO MONTH")
    day = IntervalType(_dummy(), fields="DAY TO SECOND")
    assert year == IntervalType(_dummy(), fields="YEAR TO MONTH")
    assert year != day
    assert year.identity() == ("YEAR TO MONTH",)
    assert year.get_params()["fields"] == "YEAR TO MONTH"

    restored = _data_type_from_dict(_data_type_to_dict(year))
    assert type(restored) is IntervalType
    assert restored == year
    assert json.loads(json.dumps(_data_type_to_dict(year))) == _data_type_to_dict(year)