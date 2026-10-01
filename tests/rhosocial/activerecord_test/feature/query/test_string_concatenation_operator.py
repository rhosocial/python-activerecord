# tests/rhosocial/activerecord_test/feature/query/test_string_concatenation_operator.py
"""``||`` is concatenation in SQL and logical OR in several backends.

PostgreSQL, Oracle, Snowflake, Firebird and ClickHouse read ``||`` as string
concatenation. MySQL and MariaDB read it as logical OR unless the server runs
with ``PIPES_AS_CONCAT``, and SQL Server reads it as logical OR outright.
Emitting the bare token on those backends returns a boolean where a string was
meant — a wrong answer rather than a syntax error, which is why it can survive
a test suite.

So the node records the *intent* and the dialect picks the spelling. These
tests pin the contract: the intent survives the round trip, the default is the
standard operator, and a dialect that declares a function gets one.
"""

# tests/rhosocial/activerecord_test/feature/query/test_string_concatenation_operator.py
import pytest

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression import functions as string_functions
from rhosocial.activerecord.backend.expression.operators import (
    BinaryExpression,
    StringConcatExpression,
)


@pytest.fixture
def dialect():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    d = SQLiteDialect()
    d._version = (3, 46, 1)
    return d


@pytest.fixture
def operands(dialect):
    return Column(dialect, "a", table="t"), Column(dialect, "b", table="t")


# ---------------------------------------------------------------------------
# The node carries intent, not an operator
# ---------------------------------------------------------------------------


def test_concat_op_builds_an_intent_node(dialect, operands):
    left, right = operands
    expr = string_functions.concat_op(dialect, left, right)
    assert isinstance(expr, StringConcatExpression)


def test_intent_node_is_a_binary_expression(dialect, operands):
    """Existing BinaryExpression handling must keep working."""
    left, right = operands
    expr = string_functions.concat_op(dialect, left, right)
    assert isinstance(expr, BinaryExpression)
    assert expr.left is left and expr.right is right


def test_the_operator_is_not_chosen_by_the_expression(dialect, operands):
    """``op`` is fixed, but it is the *node type* that carries the meaning.

    A bare BinaryExpression with op ``||`` says nothing about intent, which is
    exactly why concat_op stopped producing one.
    """
    left, right = operands
    assert StringConcatExpression(dialect, left, right).op == "||"


# ---------------------------------------------------------------------------
# The default spelling
# ---------------------------------------------------------------------------


def test_default_dialect_uses_the_standard_operator(dialect, operands):
    """SQLite and PostgreSQL both read ``||`` as concatenation."""
    left, right = operands
    assert dialect.string_concatenation_function() is None
    assert string_functions.concat_op(dialect, left, right).to_sql()[
        0
    ] == '"t"."a" || "t"."b"'


def test_a_declared_function_replaces_the_operator(dialect, operands):
    """The declaration is consulted, so the same node renders differently."""
    left, right = operands
    dialect.STRING_CONCATENATION = "CONCAT"
    assert dialect.string_concatenation_function() == "CONCAT"
    assert string_functions.concat_op(dialect, left, right).to_sql()[0] == (
        'CONCAT("t"."a", "t"."b")'
    )


def test_declaration_must_be_a_string(dialect):
    """A non-string declaration is ignored rather than interpolated."""
    dialect.STRING_CONCATENATION = None
    assert dialect.string_concatenation_function() is None
    dialect.STRING_CONCATENATION = 42
    assert dialect.string_concatenation_function() is None


# ---------------------------------------------------------------------------
# Chaining: the result is a string
# ---------------------------------------------------------------------------


def test_result_keeps_the_string_value_surface(operands):
    left, _ = operands
    result = left.concat_using_operator("x")
    for method in ("upper", "substr", "like", "trim", "concat_using_operator"):
        assert hasattr(result, method), f"concatenation lost {method}"


def test_chaining_after_concatenation(operands):
    left, right = operands
    sql, _ = left.concat_using_operator(right).upper().to_sql()
    assert "UPPER" in sql
    assert "||" in sql or "CONCAT" in sql


def test_alias_reaches_the_sql(operands):
    left, right = operands
    sql, _ = left.concat_using_operator(right).as_("joined").to_sql()
    assert " AS " in sql


def test_no_alias_means_no_as(operands):
    left, right = operands
    sql, _ = left.concat_using_operator(right).to_sql()
    assert " AS " not in sql


def test_parameters_are_preserved(operands):
    left, right = operands
    _, params = left.concat_using_operator(right).to_sql()
    assert params == ()


# ---------------------------------------------------------------------------
# concat_op is not the path for logical OR
# ---------------------------------------------------------------------------


def test_logical_or_does_not_go_through_concatenation(operands):
    """OR has its own node and formatter, so the two never meet."""
    left, _ = operands
    predicate = left.like("a%") | left.like("b%")
    assert not isinstance(predicate, StringConcatExpression)
    assert " OR " in predicate.to_sql()[0]
