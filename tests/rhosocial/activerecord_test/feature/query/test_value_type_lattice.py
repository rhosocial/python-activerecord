# tests/rhosocial/activerecord_test/feature/query/test_value_type_lattice.py
"""Every operation declares a result type, and the type gates the next operation.

The rule this file pins: an operation's result determines which operations are
available next. ``upper()`` returns a string, so ``substr()`` follows.
``length()`` is a legal string operation whose result is a *number*, so
``upper()`` does not — and that falls out of the types rather than out of a
check somewhere.

The two halves that are easy to get wrong are both pinned here: a result must
not lose its own surface, and it must not gain a surface belonging to another
family.
"""

# tests/rhosocial/activerecord_test/feature/query/test_value_type_lattice.py
import pytest

from rhosocial.activerecord.backend.expression import (
    IntegerValueExpression,
    StringValueExpression,
)


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    d = SQLiteDialect()
    d._version = (3, 46, 1)
    return d


@pytest.fixture
def name(dialect):
    from column_helpers import build_column

    return build_column(dialect, "name", str)


# ---------------------------------------------------------------------------
# A string operation whose result is a number
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method, args, function",
    [
        ("length", (), "LENGTH"),
        ("ascii", (), "ASCII"),
        ("octet_length", (), "OCTET_LENGTH"),
        ("bit_length", (), "BIT_LENGTH"),
        ("strpos", ("a",), "STRPOS"),
        ("position", ("a",), "POSITION"),
    ],
    ids=["length", "ascii", "octet_length", "bit_length", "strpos", "position"],
)
def test_number_returning_operation_yields_an_integer(name, method, args, function):
    """These read a string and produce a count or a code."""
    result = getattr(name, method)(*args)
    assert isinstance(result, IntegerValueExpression)
    assert function in result.to_sql()[0]


def test_the_whole_string_surface_offers_them(name):
    """They are string operations, so they belong on the string surface.

    Their absence earlier was a gap in the surface, not a rule that only
    string-to-string operations exist.
    """
    for method in ("length", "ascii", "strpos", "position", "octet_length", "bit_length"):
        assert hasattr(name, method), f"StringColumn is missing {method}"


# ---------------------------------------------------------------------------
# The result type gates the next operation
# ---------------------------------------------------------------------------


#: How many arguments each string operation *requires*, so the parametrized
#: test can call them all the same way. `substr` also takes an optional length
#: and `trim` optional characters and a direction; passing the minimum is
#: enough to reach the return, which is what is under test here.
_REQUIRED_ARGS = {
    "upper": 0, "lower": 0, "trim": 0, "initcap": 0,
    "substr": 1, "left": 1, "right": 1, "concat": 1,
    "replace": 2,
}


def _call(name, method):
    return getattr(name, method)(*(["x"] * _REQUIRED_ARGS[method]))


@pytest.mark.parametrize(
    "method", ["upper", "lower", "substr", "trim", "concat", "replace", "left", "initcap"]
)
def test_string_result_keeps_the_string_surface(name, method):
    assert isinstance(_call(name, method), StringValueExpression)


@pytest.mark.parametrize(
    "chained, expected_functions",
    [
        (lambda c: c.upper().substr(1, 3), ["UPPER", "SUBSTRING"]),
        (lambda c: c.trim().replace("a", "b"), ["TRIM", "REPLACE"]),
        (lambda c: c.upper().lower().initcap(), ["UPPER", "LOWER", "INITCAP"]),
    ],
    ids=["upper-substr", "trim-replace", "case-chain"],
)
def test_string_chain_stays_string(name, chained, expected_functions):
    sql, _ = chained(name).to_sql()
    for function in expected_functions:
        assert function in sql


def test_number_result_loses_the_string_surface(name):
    """A length has no case, so ``upper()`` must not exist on it."""
    result = name.length()
    for method in ("upper", "lower", "substr", "trim", "initcap", "reverse"):
        assert not hasattr(result, method), (
            f"an integer result wrongly offers {method}"
        )


def test_number_result_keeps_integer_operations(name):
    """Arithmetic is legal on an integer, and stays an integer."""
    result = name.length()
    assert hasattr(result, "__add__")
    assert hasattr(result, "__sub__")
    assert hasattr(result, "__mul__")


# ---------------------------------------------------------------------------
# The chain crosses families correctly
# ---------------------------------------------------------------------------


def test_string_then_number(name):
    """upper() is a string, length() of it is a number."""
    result = name.upper().length()
    assert isinstance(result, IntegerValueExpression)
    assert "LENGTH" in result.to_sql()[0] and "UPPER" in result.to_sql()[0]


def test_number_comparison_chains(name):
    sql, _ = (name.length() > 5).to_sql()
    assert "LENGTH" in sql and ">" in sql


def test_arithmetic_on_a_number_result(name):
    """``length + 1`` is an arithmetic expression over an integer value."""
    sql, params = (name.length() + 1).to_sql()
    assert "LENGTH" in sql
    assert params == (1,)


def test_a_number_result_can_be_compared_but_not_matched(name):
    """Comparison is universal; ``LIKE`` is not.

    Every value can be compared, so ``length() > 5`` is offered. ``LIKE`` is
    text matching and a whole number is not text, so the operation is not
    offered — it fails here, at the point of the call, rather than at the
    database. This used to be the other way round and the reason the typed
    column classes exist at all.
    """
    result = name.length()
    assert " > " in (result > 0).to_sql()[0]
    with pytest.raises(AttributeError):
        result.like("1%")


# ---------------------------------------------------------------------------
# Crossing into a predicate ends the value chain
# ---------------------------------------------------------------------------


def test_predicate_ends_the_chain(name):
    """A predicate is the end of the value chain whatever produced it."""
    predicate = name.upper().like("A%")
    for method in ("upper", "length", "substr"):
        assert not hasattr(predicate, method), (
            f"predicate wrongly offers {method}; the value chain should have ended"
        )


def test_integer_value_can_be_aliased(name):
    sql, _ = name.length().as_("n").to_sql()
    assert " AS " in sql
