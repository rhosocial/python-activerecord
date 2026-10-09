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
from rhosocial.activerecord.backend.expression.core import (
    DateValueExpression,
    TimeValueExpression,
    TimestampValueExpression,
    IntervalValueExpression,
    NumericValueExpression,
    IntegerValueExpression,
)
from rhosocial.activerecord.backend.expression.datetime import (
    DatePartExpression,
    DateTimeAddExpression,
    DateTimeDiffExpression,
    DateTimeSubtractExpression,
    DateTruncExpression,
    ExtractExpression,
    IntervalExpression,
)


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    d = SQLiteDialect()
    d._version = (3, 46, 1)
    return d


@pytest.fixture
def timestamp(dialect):
    from column_helpers import build_column

    return build_column(dialect, "ts", datetime.datetime)


# ---------------------------------------------------------------------------
# The present, in each of its precisions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory, cls",
    [
        ("now", TimestampValueExpression),
        ("current_timestamp", TimestampValueExpression),
        ("localtimestamp", TimestampValueExpression),
        ("current_date", DateValueExpression),
        ("current_time", TimeValueExpression),
    ],
)
def test_the_present_keeps_its_precision(dialect, factory, cls):
    """A date is not a timestamp and a time is not either.

    Four separate classes now, where there was one class and a label saying
    which it was standing in for. Each factory returns the class its own
    precision calls for, and that is readable off the result.
    """
    assert isinstance(getattr(datetime_functions, factory)(dialect), cls)


# ---------------------------------------------------------------------------
# Pulling a component out of a timestamp gives a whole number
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory", ["year", "month", "day", "hour", "minute", "second"]
)
def test_a_component_is_a_whole_number(dialect, timestamp, factory):
    assert isinstance(getattr(datetime_functions, factory)(dialect, timestamp), IntegerValueExpression)


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
    assert isinstance(getattr(datetime_functions, factory)(dialect, "year", timestamp), NumericValueExpression)


def test_date_diff_counts_whole_units(dialect):
    now = datetime_functions.now(dialect)
    assert isinstance(now.date_diff("day", now), IntegerValueExpression)


# ---------------------------------------------------------------------------
# Arithmetic on time stays time
# ---------------------------------------------------------------------------


def test_truncation_stays_a_timestamp(dialect):
    assert isinstance(datetime_functions.now(dialect).date_trunc("day"), TimestampValueExpression)


@pytest.mark.parametrize("method", ["date_add", "date_sub"])
def test_shifting_time_stays_a_timestamp(dialect, method):
    now = datetime_functions.now(dialect)
    result = getattr(now, method)(1, "days")
    assert isinstance(result, TimestampValueExpression)
    assert isinstance(result, (DateTimeAddExpression, DateTimeSubtractExpression))


def test_an_interval_is_its_own_family(dialect):
    """A span is not a point in time, which is why date_add takes one."""
    assert isinstance(datetime_functions.interval(dialect, 1, "day"), IntervalValueExpression)


# ---------------------------------------------------------------------------
# A node with a class of its own is its type; there is nothing to declare
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory, args, result_cls",
    [
        ("extract", ("year",), NumericValueExpression),
        ("date_part", ("year",), NumericValueExpression),
        ("interval", (1, "day"), IntervalValueExpression),
        ("date_diff", ("day",), IntegerValueExpression),
    ],
)
def test_a_temporal_operation_yields_its_own_type(dialect, timestamp, factory, args, result_cls):
    """What a temporal operation yields is decided where it is built.

    ``EXTRACT`` yields a number and ``DATE_DIFF`` a whole number; each is
    decided by the factory that builds the node, and neither needed a label to
    say so afterwards.
    """
    if factory == "interval":
        result = getattr(datetime_functions, factory)(dialect, *args)
    elif factory == "date_diff":
        result = getattr(datetime_functions, factory)(dialect, *args, timestamp, timestamp)
    else:
        result = getattr(datetime_functions, factory)(dialect, *args, timestamp)
    assert isinstance(result, result_cls)


def test_a_temporal_value_offers_temporal_operations(dialect):
    now = datetime_functions.now(dialect)
    for method in ("date_add", "date_sub", "date_diff", "date_part", "extract"):
        assert hasattr(now, method), f"a timestamp lost {method}"


def test_a_temporal_value_does_not_offer_string_operations(dialect):
    assert not hasattr(datetime_functions.now(dialect), "upper")


@pytest.mark.parametrize(
    "cls",
    [TimestampValueExpression, DateValueExpression, TimeValueExpression,
     IntervalValueExpression],
)
def test_each_temporal_type_is_its_own_class(dialect, cls):
    """They offer the same operations, so they share a base -- but they are four
    different types, and each says so with its own class."""
    from rhosocial.activerecord.backend.expression import FunctionCall
    from rhosocial.activerecord.backend.expression.core import TemporalValueExpression

    wrapped = cls(dialect, FunctionCall(dialect, "SOME_FUNC"))
    assert isinstance(wrapped, cls)
    assert isinstance(wrapped, TemporalValueExpression)
    assert hasattr(wrapped, "date_add")


def test_the_sql_does_not_change_when_a_value_is_wrapped(dialect, timestamp):
    """Typing is a surface decision, never a rendering one."""
    from rhosocial.activerecord.backend.expression import FunctionCall

    call = FunctionCall(dialect, "MY_FUNC", timestamp)
    assert TimestampValueExpression(dialect, call).to_sql() == call.to_sql()


def test_an_alias_survives_wrapping(dialect, timestamp):
    from rhosocial.activerecord.backend.expression import FunctionCall

    call = FunctionCall(dialect, "MY_FUNC", timestamp)
    assert " AS " in TimestampValueExpression(dialect, call).as_("when").to_sql()[0]
