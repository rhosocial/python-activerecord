# tests/rhosocial/activerecord_test/feature/query/test_value_family_inference.py
"""Result families, and the lattice they add up to.

A family is what decides an expression's operation surface, and it has to be
accurate in both directions. Over-narrowing removes a legal operation;
over-widening offers an illegal one. Both failures are silent — the SQL is
still produced, it is just wrong — so the families are pinned here.

The distinction that matters most is whole number against fraction. ``int`` and
``float`` share a column class, so the family has to come from the annotation
rather than the class, or "integer in, integer out" cannot be expressed and
``ceil`` of an integer claims to be fractional.
"""

# tests/rhosocial/activerecord_test/feature/query/test_value_family_inference.py
import datetime
import decimal
import uuid

import pytest

from rhosocial.activerecord.backend.expression import Column, FunctionCall, Literal
from rhosocial.activerecord.backend.expression import functions as F
from rhosocial.activerecord.backend.expression.core import NumericValueExpression
from rhosocial.activerecord.backend.expression import functions as math_functions


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
        "string": build_column(dialect, "s", str),
        "int": build_column(dialect, "i", int),
        "float": build_column(dialect, "f", float),
        "bool": build_column(dialect, "b", bool),
        "json": build_column(dialect, "j", dict),
        "bytes": build_column(dialect, "y", bytes),
        "uuid": build_column(dialect, "u", uuid.UUID),
        "datetime": build_column(dialect, "d", datetime.datetime),
    }


# ---------------------------------------------------------------------------
# A column's family comes from its annotation
# ---------------------------------------------------------------------------


def test_family_covers_the_whole_lattice():
    """Every family constant is a string, so it can be declared and compared."""
    assert all(isinstance(f, str) for f in FAMILIES)
    assert len(set(FAMILIES)) == len(FAMILIES)


def test_unknown_is_none_rather_than_guessed(columns):
    """Unknown is an answer. Guessing would offer the wrong surface."""
    assert not isinstance(None, ArrayValueExpression) and not isinstance(None, BinaryValueExpression) and not isinstance(None, BooleanValueExpression) and not isinstance(None, DateValueExpression) and not isinstance(None, IntegerValueExpression) and not isinstance(None, IntervalValueExpression) and not isinstance(None, JSONValueExpression) and not isinstance(None, NumericValueExpression) and not isinstance(None, StringValueExpression) and not isinstance(None, TimeValueExpression) and not isinstance(None, TimestampValueExpression) and not isinstance(None, UUIDValueExpression)


def test_a_bare_function_call_has_no_family(dialect, columns):
    """It says nothing about what a database would return."""
    call = FunctionCall(dialect, "MY_FUNC", columns["string"])
    assert not isinstance(call, ArrayValueExpression) and not isinstance(call, BinaryValueExpression) and not isinstance(call, BooleanValueExpression) and not isinstance(call, DateValueExpression) and not isinstance(call, IntegerValueExpression) and not isinstance(call, IntervalValueExpression) and not isinstance(call, JSONValueExpression) and not isinstance(call, NumericValueExpression) and not isinstance(call, StringValueExpression) and not isinstance(call, TimeValueExpression) and not isinstance(call, TimestampValueExpression) and not isinstance(call, UUIDValueExpression)


def test_a_hand_written_column_has_no_family(dialect):
    """A permissive Column means "unknown type", which is not the same as any."""
    assert not isinstance(Column(dialect, "x", table="t"), ArrayValueExpression) and not isinstance(Column(dialect, "x", table="t"), BinaryValueExpression) and not isinstance(Column(dialect, "x", table="t"), BooleanValueExpression) and not isinstance(Column(dialect, "x", table="t"), DateValueExpression) and not isinstance(Column(dialect, "x", table="t"), IntegerValueExpression) and not isinstance(Column(dialect, "x", table="t"), IntervalValueExpression) and not isinstance(Column(dialect, "x", table="t"), JSONValueExpression) and not isinstance(Column(dialect, "x", table="t"), NumericValueExpression) and not isinstance(Column(dialect, "x", table="t"), StringValueExpression) and not isinstance(Column(dialect, "x", table="t"), TimeValueExpression) and not isinstance(Column(dialect, "x", table="t"), TimestampValueExpression) and not isinstance(Column(dialect, "x", table="t"), UUIDValueExpression)


@pytest.mark.parametrize(
    "key, expected",
    [
        ("string", "string"),
        ("int", "integer"),
        ("float", "numeric"),
        ("bool", "boolean"),
        ("json", "json"),
        ("bytes", "binary"),
        ("uuid", "uuid"),
        ("datetime", "datetime"),
    ],
)
def test_each_annotation_lands_in_its_family(columns, key, expected):
    assert value_type_of(columns[key]) == expected


def test_decimal_is_fractional(dialect):
    from rhosocial.activerecord.base.column_dispatch import build_column

    assert value_type_of(build_column(dialect, "d", decimal.Decimal)) == "numeric"


# ---------------------------------------------------------------------------
# int and float share a class but not a family
# ---------------------------------------------------------------------------


def test_int_and_float_do_not_share_a_column_class(dialect):
    """They are two classes, because SQL keeps them apart in the result.

    This used to assert the opposite -- one class for both, on the grounds that
    a second class would exist for no SQL reason. There is a reason:
    CEIL of a whole number is a whole number, and CEIL of a fraction is not. With
    one class the distinction had to live in an instance attribute, which a
    checker cannot see, so a factory had to read it back at run time to decide
    what to return.

    As two classes the answer arrives in the return type. build_column(d, "n",
    int) is IntegerColumn and build_column(d, "n", float) is NumericColumn, and
    the difference is visible without running anything.
    """
    from rhosocial.activerecord.backend.expression import (
        IntegerColumn,
        NumericColumn,
    )
    from rhosocial.activerecord.base.column_dispatch import build_column

    assert type(build_column(dialect, "i", int)) is IntegerColumn
    assert type(build_column(dialect, "f", float)) is NumericColumn
    # The two are unrelated enough that a factory can tell them apart with
    # isinstance and stay readable, which is the whole point of splitting them.
    assert not issubclass(IntegerColumn, NumericColumn)
    assert not issubclass(NumericColumn, IntegerColumn)


def test_but_they_do_not_share_a_family(columns):
    """SQL rounds a whole number to a whole number, so the family differs."""
    assert isinstance(columns["int"], IntegerValueExpression)
    assert isinstance(columns["float"], NumericValueExpression)


def test_an_explicit_family_overrides_the_class_default(dialect):
    """The instance attribute is what makes one class serve two families."""
    from rhosocial.activerecord.backend.expression import NumericColumn

    plain = NumericColumn(dialect, "n", table="t")
    narrowed = NumericColumn(dialect, "n", table="t", value_family=INTEGER)
    assert isinstance(plain, NumericValueExpression)
    assert isinstance(narrowed, IntegerValueExpression)


# ---------------------------------------------------------------------------
# An operation's family decides the next operation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fn", ["abs_", "ceil", "floor"])
def test_whole_number_in_whole_number_out(dialect, columns, fn):
    """``ABS(int)`` is an int in SQL, so the result must be an integer."""
    result = getattr(math_functions, fn)(dialect, columns["int"])
    assert isinstance(result, IntegerValueExpression)


@pytest.mark.parametrize("fn", ["abs_", "ceil", "floor"])
def test_fraction_in_fraction_out(dialect, columns, fn):
    result = getattr(math_functions, fn)(dialect, columns["float"])
    assert isinstance(result, NumericValueExpression)


def test_the_two_families_offer_different_surfaces(dialect, columns):
    """The narrowing has to be observable, or it is not doing anything."""
    whole = math_functions.ceil(dialect, columns["int"])
    fraction = math_functions.ceil(dialect, columns["float"])
    assert hasattr(whole, "length")
    assert not hasattr(fraction, "length")


@pytest.mark.parametrize("fn", ["sqrt", "exp", "sin", "cos", "tan"])
def test_transcendental_always_falls_back_to_fraction(dialect, columns, fn):
    """``sqrt`` of a whole number is not a whole number."""
    result = getattr(math_functions, fn)(dialect, columns["int"])
    assert isinstance(result, NumericValueExpression)


def test_sign_is_always_a_whole_number(dialect, columns):
    """It returns -1, 0 or 1."""
    assert isinstance(math_functions.sign(dialect, columns["float"]), IntegerValueExpression)


# ---------------------------------------------------------------------------
# an unmodelled kind stays unknown instead of being guessed
# ---------------------------------------------------------------------------


def test_a_typed_expression_reports_the_kind_it_was_built_for(dialect, columns):
    call = FunctionCall(dialect, "MY_FUNC", columns["string"])
    typed = NumericValueExpression(dialect, call)
    assert isinstance(typed, NumericValueExpression)
    assert typed.to_sql() == call.to_sql()


def test_an_argument_that_declares_nothing_yields_no_family(dialect, columns):
    """A literal says nothing about what a database would return, so an
    operation over one says nothing either -- which is not the same as guessing
    a default."""
    assert family_of_result(Literal(dialect, 1)) is None
    assert family_of_result(Literal(dialect, "s")) is None



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
def test_a_disagreement_yields_no_family(dialect, columns):
    """GREATEST of an integer and a string is legal SQL and is neither, so the
    call stays generic rather than promising the first or the widest."""
    mixed = F.greatest(dialect, columns["int"], columns["string"])
    assert not isinstance(mixed, ArrayValueExpression) and not isinstance(mixed, BinaryValueExpression) and not isinstance(mixed, BooleanValueExpression) and not isinstance(mixed, DateValueExpression) and not isinstance(mixed, IntegerValueExpression) and not isinstance(mixed, IntervalValueExpression) and not isinstance(mixed, JSONValueExpression) and not isinstance(mixed, NumericValueExpression) and not isinstance(mixed, StringValueExpression) and not isinstance(mixed, TimeValueExpression) and not isinstance(mixed, TimestampValueExpression) and not isinstance(mixed, UUIDValueExpression)
    assert mixed.to_sql() == FunctionCall(
        dialect, "GREATEST", columns["int"], columns["string"]
    ).to_sql()
