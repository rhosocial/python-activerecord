# tests/rhosocial/activerecord_test/feature/query/test_temporal_value_families.py
"""What each temporal operation answers with.

A datetime is not one type. ``YEAR(ts)`` is a whole number, ``EXTRACT`` is a
number, ``NOW() + interval`` is a timestamp again, and ``NOW() - NOW()`` is a
count of units. Getting these confused is silent — the SQL is still valid and
the answer is simply the wrong kind of thing — so each one is pinned here.

The result's family is what decides the next operation, so the surface is
asserted too: a year may be added to, a timestamp may not be upper-cased.
"""

# tests/rhosocial/activerecord_test/feature/query/test_temporal_value_families.py
import datetime

import pytest

from rhosocial.activerecord.backend.expression import functions as datetime_functions
from rhosocial.activerecord.backend.expression.core import DateTimeValueExpression
from rhosocial.activerecord.backend.expression.datetime import (
    DatePartExpression,
    DateTimeAddExpression,
    DateTimeDiffExpression,
    DateTimeSubtractExpression,
    DateTruncExpression,
    ExtractExpression,
    IntervalExpression,
)
from rhosocial.activerecord.backend.expression.value_types import (
    DATE,
    DATETIME,
    INTEGER,
    INTERVAL,
    NUMERIC,
    TIME,
    value_type_of,
    wrap_as,
)


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    d = SQLiteDialect()
    d._version = (3, 46, 1)
    return d


@pytest.fixture
def timestamp(dialect):
    from rhosocial.activerecord.base.column_dispatch import build_column

    return build_column(dialect, "ts", datetime.datetime)


# ---------------------------------------------------------------------------
# The present, in each of its precisions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory, expected",
    [
        ("now", DATETIME),
        ("current_timestamp", DATETIME),
        ("localtimestamp", DATETIME),
        ("current_date", DATE),
        ("current_time", TIME),
    ],
)
def test_the_present_keeps_its_precision(dialect, factory, expected):
    """A date is not a timestamp and a time is not either."""
    assert value_type_of(getattr(datetime_functions, factory)(dialect)) == expected


# ---------------------------------------------------------------------------
# Pulling a component out of a timestamp gives a whole number
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory", ["year", "month", "day", "hour", "minute", "second"]
)
def test_a_component_is_a_whole_number(dialect, timestamp, factory):
    assert value_type_of(getattr(datetime_functions, factory)(dialect, timestamp)) == INTEGER


def test_a_component_takes_arithmetic_and_not_string_operations(dialect, timestamp):
    """A year is a number, so the number surface follows and the string one
    does not. Getting this wrong is how ``str(year(ts))`` sneaks in."""
    year = datetime_functions.year(dialect, timestamp)
    assert hasattr(year, "__add__")
    assert not hasattr(year, "upper")


# ---------------------------------------------------------------------------
# Extraction is numeric because the unit decides it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("factory", ["extract", "date_part"])
def test_extraction_is_numeric(dialect, timestamp, factory):
    """``EXTRACT(EPOCH FROM ts)`` is fractional, so the family is too wide to
    be a whole number. Widening here is deliberate: claiming integer would
    offer ``bit_length`` on a value that may be a million and a half."""
    assert value_type_of(getattr(datetime_functions, factory)(dialect, "year", timestamp)) == NUMERIC


def test_date_diff_counts_whole_units(dialect):
    now = datetime_functions.now(dialect)
    assert value_type_of(now.date_diff("day", now)) == INTEGER


# ---------------------------------------------------------------------------
# Arithmetic on time stays time
# ---------------------------------------------------------------------------


def test_truncation_stays_a_timestamp(dialect):
    assert value_type_of(datetime_functions.now(dialect).date_trunc("day")) == DATETIME


@pytest.mark.parametrize("method", ["date_add", "date_sub"])
def test_shifting_time_stays_a_timestamp(dialect, method):
    now = datetime_functions.now(dialect)
    result = getattr(now, method)(1, "days")
    assert value_type_of(result) == DATETIME
    assert isinstance(result, (DateTimeAddExpression, DateTimeSubtractExpression))


def test_an_interval_is_its_own_family(dialect):
    """A span is not a point in time, which is why date_add takes one."""
    assert value_type_of(datetime_functions.interval(dialect, 1, "day")) == INTERVAL


# ---------------------------------------------------------------------------
# Nodes that have their own class declare their family on it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cls, expected",
    [
        (ExtractExpression, NUMERIC),
        (DatePartExpression, NUMERIC),
        (DateTruncExpression, DATETIME),
        (IntervalExpression, INTERVAL),
        (DateTimeAddExpression, DATETIME),
        (DateTimeSubtractExpression, DATETIME),
        (DateTimeDiffExpression, INTEGER),
    ],
)
def test_a_dedicated_node_declares_its_family(cls, expected):
    """No wrapper needed: the class already exists, so it says what it is."""
    assert value_type_of(cls) == expected


# ---------------------------------------------------------------------------
# One class, four temporal families
# ---------------------------------------------------------------------------


def test_a_temporal_value_offers_temporal_operations(dialect):
    now = datetime_functions.now(dialect)
    for method in ("date_add", "date_sub", "date_diff", "date_part", "extract"):
        assert hasattr(now, method), f"a timestamp lost {method}"


def test_a_temporal_value_does_not_offer_string_operations(dialect):
    assert not hasattr(datetime_functions.now(dialect), "upper")


@pytest.mark.parametrize("family", [DATETIME, DATE, TIME, INTERVAL])
def test_one_class_serves_every_temporal_family(dialect, family):
    """They offer the same operations, so they share a class, but the family
    is still reported because it is what a result propagates."""
    from rhosocial.activerecord.backend.expression import FunctionCall

    wrapped = wrap_as(dialect, FunctionCall(dialect, "SOME_FUNC"), family)
    assert isinstance(wrapped, DateTimeValueExpression)
    assert value_type_of(wrapped) == family
    assert hasattr(wrapped, "date_add")


def test_the_sql_does_not_change_when_a_value_is_wrapped(dialect, timestamp):
    """Typing is a surface decision, never a rendering one."""
    from rhosocial.activerecord.backend.expression import FunctionCall

    call = FunctionCall(dialect, "MY_FUNC", timestamp)
    assert wrap_as(dialect, call, DATETIME).to_sql() == call.to_sql()


def test_an_alias_survives_wrapping(dialect, timestamp):
    from rhosocial.activerecord.backend.expression import FunctionCall

    call = FunctionCall(dialect, "MY_FUNC", timestamp)
    assert " AS " in wrap_as(dialect, call, DATETIME).as_("when").to_sql()[0]
