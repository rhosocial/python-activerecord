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

from rhosocial.activerecord.backend.expression import FunctionCall
from rhosocial.activerecord.backend.expression import functions as F


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    d = SQLiteDialect()
    d._version = (3, 46, 1)
    return d


@pytest.fixture
def columns(dialect):
    from rhosocial.activerecord_test.feature.query.column_helpers import build_column

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
        assert isinstance(F.count(dialect, column), IntegerValueExpression)


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
        assert isinstance(F.avg(dialect, column), NumericValueExpression)


# ---------------------------------------------------------------------------
# Adding, minimising and maximising keep the input's kind
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("factory", ["sum_", "min_", "max_"])
def test_a_reduction_keeps_the_input_family(dialect, columns, factory):
    """SUM of a float column is fractional and MIN of a string column is a
    string, which can still be compared and matched."""
    reduce_it = getattr(F, factory)
    assert isinstance(reduce_it(dialect, columns["int"]), IntegerValueExpression)
    assert isinstance(reduce_it(dialect, columns["float"]), NumericValueExpression)
    assert isinstance(reduce_it(dialect, columns["str"]), StringValueExpression)


@pytest.mark.parametrize("factory", ["sum_", "min_", "max_"])
def test_a_literal_input_has_no_family_to_keep(dialect, factory):
    """A literal does not declare a kind, so the result is unknown rather than
    guessed. Unknown is safe: the node is handed back untouched."""
    result = getattr(F, factory)(dialect, 1)
    assert not isinstance(result, ArrayValueExpression) and not isinstance(result, BinaryValueExpression) and not isinstance(result, BooleanValueExpression) and not isinstance(result, DateValueExpression) and not isinstance(result, IntegerValueExpression) and not isinstance(result, IntervalValueExpression) and not isinstance(result, JSONValueExpression) and not isinstance(result, NumericValueExpression) and not isinstance(result, StringValueExpression) and not isinstance(result, TimeValueExpression) and not isinstance(result, TimestampValueExpression) and not isinstance(result, UUIDValueExpression)
    assert isinstance(result, FunctionCall)


def test_min_of_a_string_column_is_still_a_string(dialect, columns):
    result = F.min_(dialect, columns["str"])
    assert hasattr(result, "like")
    assert not hasattr(result, "sqrt")


# ---------------------------------------------------------------------------
# Building a document or a sequence
# ---------------------------------------------------------------------------


def test_building_a_json_aggregate_gives_json(dialect, columns):
    assert isinstance(F.json_objectagg(dialect, columns["int"], columns["str"]), JSONValueExpression)
    assert isinstance(F.json_arrayagg(dialect, columns["json"]), JSONValueExpression)


def test_collecting_into_an_array_gives_an_array(dialect, columns):
    assert isinstance(F.array_agg(dialect, columns["int"]), ArrayValueExpression)


# ---------------------------------------------------------------------------
# Windowing: a count, or a value from another row
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("factory", ["row_number", "rank", "dense_rank"])
def test_a_rank_is_a_whole_number(dialect, factory):
    for windowed in (getattr(F, factory)(dialect),):
        assert isinstance(windowed, IntegerValueExpression)
        assert hasattr(windowed, "__add__")
        assert not hasattr(windowed, "upper")


@pytest.mark.parametrize(
    "factory, extra",
    [("lag", ()), ("lead", ()), ("first_value", ()), ("last_value", ()), ("nth_value", (2,))],
)
def test_a_value_from_another_row_keeps_its_family(dialect, columns, factory, extra):
    """LAG over a name column is a name, not a count.

    Which is asserted by the arithmetic that is *absent*: a name is not a
    number, so no ``sqrt``. The string operations are present, because the
    result genuinely is a string -- it was ``not hasattr(windowed, "upper")``
    before the class replaced the tag, and that assertion is what the tag was
    costing: the node carried ``family="string"`` while offering none of the
    string surface, so a caller could not tell from the object which operations
    it had. Now the class says it, and the operations come with it.
    """
    windowed = getattr(F, factory)(dialect, columns["str"], *extra)
    assert isinstance(windowed, StringValueExpression)
    assert hasattr(windowed, "like")
    assert not hasattr(windowed, "sqrt")


def test_lag_over_a_float_column_is_fractional(dialect, columns):
    assert isinstance(F.lag(dialect, columns["float"]), NumericValueExpression)


# ---------------------------------------------------------------------------
# The node states its family, and the round trip survives it
# ---------------------------------------------------------------------------


def test_a_typed_aggregate_reports_its_family_for_introspection(dialect, columns):
    """Introspection has to see what a result is, or nothing downstream can
    read it.

    It used to read ``get_params()["family"]``. That keyword is gone: it
    duplicated the class, and a tag that can disagree with the class it sits on
    is worse than no tag at all. The class is the introspection surface now, so
    this asserts the class -- which is what a caller would have branched on
    anyway.
    """
    result = F.count(dialect, columns["int"])
    assert isinstance(result, IntegerValueExpression)


def test_a_typed_window_reports_its_family_for_introspection(dialect, columns):
    """Same for a window function: the class, not the removed ``family`` tag."""
    result = F.lag(dialect, columns["int"])
    assert isinstance(result, IntegerValueExpression)


def test_an_untyped_aggregate_reports_no_family(dialect, columns):
    """A node constructed directly is the untyped one, and says so by being it.

    ``get_params()["family"] is None`` was how this used to be checked. There is
    no ``family`` parameter to be ``None`` now, so the assertion is the class:
    a bare ``FunctionCall`` is not a typed value, which is the same
    statement without the tag that could contradict it.
    """
    result = FunctionCall(dialect, "COUNT", columns["int"], is_aggregate=True)
    assert not isinstance(result, ArrayValueExpression) and not isinstance(result, BinaryValueExpression) and not isinstance(result, BooleanValueExpression) and not isinstance(result, DateValueExpression) and not isinstance(result, IntegerValueExpression) and not isinstance(result, IntervalValueExpression) and not isinstance(result, JSONValueExpression) and not isinstance(result, NumericValueExpression) and not isinstance(result, StringValueExpression) and not isinstance(result, TimeValueExpression) and not isinstance(result, TimestampValueExpression) and not isinstance(result, UUIDValueExpression)



from rhosocial.activerecord.backend.expression.core import (
    NumericValueExpression,
    IntegerValueExpression,
    StringValueExpression,
    BooleanValueExpression,
    BinaryValueExpression,
    UUIDValueExpression,
    JSONValueExpression,
    ArrayValueExpression,
    TimestampValueExpression,
    DateValueExpression,
    TimeValueExpression,
    IntervalValueExpression,
)
def test_declaring_a_family_does_not_change_the_sql(dialect, columns):
    """Typing is a surface decision, never a rendering one."""
    assert F.count(dialect, columns["int"]).to_sql()[0] == "COUNT(\"i\")"
    assert F.lag(dialect, columns["int"]).to_sql()[0] == "LAG(\"i\", ?)"
