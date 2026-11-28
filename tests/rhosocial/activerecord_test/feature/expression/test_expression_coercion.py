# tests/rhosocial/activerecord_test/feature/expression/test_expression_coercion.py
"""Raw values are accepted at value positions and always bind.

A caller passes a Python value; the framework wraps it in ``Parameter`` so the
SQL text keeps a placeholder and the value travels in the parameter sequence.
The coercion never applies to name positions: a raw string there is an
identifier, not a value.
"""

import pytest

from rhosocial.activerecord.backend.expression import Parameter
from rhosocial.activerecord.backend.expression.column_types.column import Column
from rhosocial.activerecord.backend.expression.functions.function_call import FunctionCall
from rhosocial.activerecord.backend.expression.predicates.predicates import (
    BetweenPredicate,
    ComparisonPredicate,
    InPredicate,
    LikeOperator,
    LikePredicate,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def _dialect() -> SQLiteDialect:
    return SQLiteDialect((3, 38, 0))


def test_a_comparison_wraps_a_raw_right_operand():
    dialect = _dialect()
    predicate = ComparisonPredicate(dialect, "=", Column(dialect, "age"), 18)
    assert isinstance(predicate.right, Parameter)
    assert predicate.right.inline is False
    assert predicate.to_sql() == ('"age" = ?', (18,))


def test_a_comparison_wraps_both_raw_operands():
    dialect = _dialect()
    predicate = ComparisonPredicate(dialect, "=", "left", "right")
    assert predicate.to_sql() == ("? = ?", ("left", "right"))


def test_a_comparison_keeps_an_explicit_parameter_as_is():
    dialect = _dialect()
    explicit = Parameter(dialect, 18)
    predicate = ComparisonPredicate(dialect, "=", Column(dialect, "age"), explicit)
    assert predicate.right is explicit
    assert predicate.to_sql() == ('"age" = ?', (18,))


def test_an_in_list_wraps_a_raw_collection_into_one_parameter():
    dialect = _dialect()
    predicate = InPredicate(dialect, Column(dialect, "id"), [1, 2, 3])
    assert isinstance(predicate.values, Parameter)
    assert predicate.values.value == (1, 2, 3)
    assert predicate.to_sql() == ('"id" IN (?, ?, ?)', (1, 2, 3))


def test_between_wraps_raw_bounds():
    dialect = _dialect()
    predicate = BetweenPredicate(dialect, Column(dialect, "age"), 18, 30)
    assert predicate.to_sql() == ('"age" BETWEEN ? AND ?', (18, 30))


def test_like_wraps_a_raw_pattern():
    dialect = _dialect()
    predicate = LikePredicate(
        dialect, LikeOperator.LIKE, Column(dialect, "name"), "%a%"
    )
    assert predicate.to_sql() == ('"name" LIKE ?', ("%a%",))


def test_a_function_call_wraps_raw_arguments():
    dialect = _dialect()
    call = FunctionCall(dialect, "COALESCE", Column(dialect, "x"), 0)
    assert isinstance(call.args[1], Parameter)
    assert call.to_sql() == ('COALESCE("x", ?)', (0,))


@pytest.mark.parametrize(
    "payload",
    [
        "'; DROP TABLE users; --",
        "a'b",
        "%' OR 1=1 --",
    ],
)
def test_a_raw_value_never_reaches_the_sql_text(payload):
    """The injection property the coercion exists for."""
    dialect = _dialect()
    predicate = ComparisonPredicate(dialect, "=", Column(dialect, "name"), payload)
    sql, params = predicate.to_sql()
    assert payload not in sql
    assert sql == '"name" = ?'
    assert params == (payload,)


def test_inline_is_still_an_internal_decision():
    """Coercion binds; inline stays available where a grammar position needs it."""
    dialect = _dialect()
    inline = Parameter(dialect, "abc", inline=True)
    assert inline.to_sql() == ("'abc'", ())
    bind = Parameter(dialect, "abc")
    assert bind.to_sql() == ("?", ("abc",))
