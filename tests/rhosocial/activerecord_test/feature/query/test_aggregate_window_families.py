# tests/rhosocial/activerecord_test/feature/query/test_aggregate_window_families.py
"""What aggregating and windowing a value gives back.

COUNT and SUM look alike and are not: one counts, the other adds, and the
count is a whole number however wide the thing being counted is. MIN and MAX
are the opposite — they hand back something of the input's kind, so the
minimum of a string column is a string and can still be compared and matched.

A window function is either a count or a value from another row, and confusing
the two is how a name column ends up arithmetic. ROW_NUMBER counts; LAG
borrows.
"""

# tests/rhosocial/activerecord_test/feature/query/test_aggregate_window_families.py
import pytest

from rhosocial.activerecord.backend.expression import functions as F
from rhosocial.activerecord.backend.expression.aggregates import AggregateFunctionCall
from rhosocial.activerecord.backend.expression.value_types import (
    ARRAY,
    INTEGER,
    JSON,
    NUMERIC,
    STRING,
    value_type_of,
)


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    d = SQLiteDialect()
    d._version = (3, 46, 1)
    return d


@pytest.fixture
def columns(dialect):
    from rhosocial.activerecord.base.column_dispatch import build_column

    return {
        "int": build_column(dialect, "i", int),
        "float": build_column(dialect, "f", float),
        "str": build_column(dialect, "s", str),
        "json": build_column(dialect, "j", dict),
    }


# ---------------------------------------------------------------------------
# Counting
# ---------------------------------------------------------------------------


def test_count_is_always_a_whole_number(dialect, columns):
    """However wide the thing counted, the answer is a number of rows."""
    for column in columns.values():
        assert value_type_of(F.count(dialect, column)) == INTEGER


def test_count_takes_arithmetic_and_not_string_operations(dialect, columns):
    count = F.count(dialect, columns["int"])
    assert hasattr(count, "__add__")
    assert not hasattr(count, "upper")


# ---------------------------------------------------------------------------
# Averaging widens
# ---------------------------------------------------------------------------


def test_avg_is_numeric_whatever_it_averages(dialect, columns):
    """Averaging whole numbers gives a fraction, so the family has to allow
    one. SQL Server is the exception that returns an integer here, which is
    exactly why it is not something to build an operation surface on."""
    for column in columns.values():
        assert value_type_of(F.avg(dialect, column)) == NUMERIC


# ---------------------------------------------------------------------------
# Adding, minimising and maximising keep the input's kind
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("factory", ["sum_", "min_", "max_"])
def test_a_reduction_keeps_the_input_family(dialect, columns, factory):
    """SUM of a float column is fractional and MIN of a string column is a
    string, which can still be compared and matched."""
    reduce_it = getattr(F, factory)
    assert value_type_of(reduce_it(dialect, columns["int"])) == INTEGER
    assert value_type_of(reduce_it(dialect, columns["float"])) == NUMERIC
    assert value_type_of(reduce_it(dialect, columns["str"])) == STRING


@pytest.mark.parametrize("factory", ["sum_", "min_", "max_"])
def test_a_literal_input_has_no_family_to_keep(dialect, factory):
    """A literal does not declare a kind, so the result is unknown rather than
    guessed. Unknown is safe: the node is handed back untouched."""
    result = getattr(F, factory)(dialect, 1)
    assert value_type_of(result) is None
    assert isinstance(result, AggregateFunctionCall)


def test_min_of_a_string_column_is_still_a_string(dialect, columns):
    result = F.min_(dialect, columns["str"])
    assert hasattr(result, "like")
    assert not hasattr(result, "sqrt")


# ---------------------------------------------------------------------------
# Building a document or a sequence
# ---------------------------------------------------------------------------


def test_building_a_json_aggregate_gives_json(dialect, columns):
    assert value_type_of(F.json_objectagg(dialect, columns["int"], columns["str"])) == JSON
    assert value_type_of(F.json_arrayagg(dialect, columns["json"])) == JSON


def test_collecting_into_an_array_gives_an_array(dialect, columns):
    assert value_type_of(F.array_agg(dialect, columns["int"])) == ARRAY


# ---------------------------------------------------------------------------
# Windowing: a count, or a value from another row
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("factory", ["row_number", "rank", "dense_rank"])
def test_a_rank_is_a_whole_number(dialect, factory):
    for windowed in (getattr(F, factory)(dialect),):
        assert value_type_of(windowed) == INTEGER
        assert hasattr(windowed, "__add__")
        assert not hasattr(windowed, "upper")


@pytest.mark.parametrize(
    "factory, extra",
    [("lag", ()), ("lead", ()), ("first_value", ()), ("last_value", ()), ("nth_value", (2,))],
)
def test_a_value_from_another_row_keeps_its_family(dialect, columns, factory, extra):
    """LAG over a name column is a name, not a count."""
    windowed = getattr(F, factory)(dialect, columns["str"], *extra)
    assert value_type_of(windowed) == STRING
    assert hasattr(windowed, "like")
    assert not hasattr(windowed, "upper")


def test_lag_over_a_float_column_is_fractional(dialect, columns):
    assert value_type_of(F.lag(dialect, columns["float"])) == NUMERIC


# ---------------------------------------------------------------------------
# The node states its family, and the round trip survives it
# ---------------------------------------------------------------------------


def test_a_typed_aggregate_reports_its_family_for_introspection(dialect, columns):
    """Introspection has to see the family, or nothing downstream can read it.

    Not a round trip: the constructor takes *args, which get_params() reports
    as a list and cannot be splatted back as keywords. The family is a keyword
    parameter, so it survives on its own — that is what is asserted.
    """
    result = F.count(dialect, columns["int"])
    assert result.get_params()["family"] == INTEGER


def test_a_typed_window_reports_its_family_for_introspection(dialect, columns):
    result = F.lag(dialect, columns["int"])
    assert result.get_params()["family"] == INTEGER


def test_an_untyped_aggregate_reports_no_family(dialect, columns):
    """A node constructed without one says so rather than defaulting."""
    result = AggregateFunctionCall(dialect, "COUNT", columns["int"])
    assert result.get_params()["family"] is None
    assert value_type_of(result) is None


def test_declaring_a_family_does_not_change_the_sql(dialect, columns):
    """Typing is a surface decision, never a rendering one."""
    assert F.count(dialect, columns["int"]).to_sql()[0] == "COUNT(\"i\")"
    assert F.lag(dialect, columns["int"]).to_sql()[0] == "LAG(\"i\", ?)"
