# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_logical_predicate_precedence.py
"""Logical predicates must be grouped when an operand binds looser.

SQL gives the boolean connectives a precedence: ``NOT`` binds tightest, then
``AND``, then ``OR``. A tree therefore carries *two* facts -- the operands and
the grouping -- and a flat rendering can only keep the second when the
parentheses are written:

    a AND (b OR c)   ->  a AND b OR c     WRONG: the OR escapes the AND
    (a AND b) OR c   ->  a AND b OR c     right: AND already binds tighter

``format_logical_predicate`` joins the operands with the bare operator, so every
nesting renders flat. That is harmless while the nesting follows the
precedence (an AND under an OR) and silently wrong the moment it does not (an
OR under an AND) -- the query still parses, the server still answers, and the
answer is a different question's answer.

The realistic shape is a default filter OR-ed against the caller's condition:
"everything except the system catalogue, or anything the caller named". Written
as ``X AND (relation IS NULL OR relation NOT LIKE 'RDB$%')`` it means one
thing; rendered flat it means ``(X AND relation IS NULL) OR ...``, which
returns every non-system row regardless of ``X``.

This module states the rule at the layer that writes the SQL, using
``DummyDialect`` because the rule is the shared dialect base's, not a
backend's. The shapes it asserts are the two the precedence decides.
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonPredicate,
    IsNullPredicate,
    LikePredicate,
    Literal,
    LogicalPredicate,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


def eq(dialect: DummyDialect, name: str, value) -> ComparisonPredicate:
    """``"name" = ?`` -- the leaf every shape below is built from."""
    return ComparisonPredicate(dialect, "=", Column(dialect, name), Literal(dialect, value))


class TestLogicalPredicatePrecedence:
    """Which nestings need parentheses, and what they must render to."""

    def test_or_under_and_is_parenthesised(self, dummy_dialect: DummyDialect):
        """``a AND (b OR c)``: the OR must not escape the AND.

        Without the parentheses the rendered text means ``(a AND b) OR c``,
        which is a different predicate: it accepts a row where ``a`` is false
        but ``c`` is true.
        """
        inner = LogicalPredicate(
            dummy_dialect,
            "OR",
            eq(dummy_dialect, "b", 2),
            eq(dummy_dialect, "c", 3),
        )
        pred = LogicalPredicate(dummy_dialect, "AND", eq(dummy_dialect, "a", 1), inner)

        sql, params = pred.to_sql()

        assert sql == '"a" = ? AND ("b" = ? OR "c" = ?)'
        assert params == (1, 2, 3)

    def test_and_under_or_is_left_flat(self, dummy_dialect: DummyDialect):
        """``(a AND b) OR c``: no parentheses are needed, and none are invented.

        ``AND`` binds tighter than ``OR``, so this shape already means what the
        tree says. Writing brackets here would be harmless but would also make
        the rule "always bracket a nested group", which is not the rule.
        """
        inner = LogicalPredicate(
            dummy_dialect,
            "AND",
            eq(dummy_dialect, "a", 1),
            eq(dummy_dialect, "b", 2),
        )
        pred = LogicalPredicate(dummy_dialect, "OR", inner, eq(dummy_dialect, "c", 3))

        sql, params = pred.to_sql()

        assert sql == '"a" = ? AND "b" = ? OR "c" = ?'
        assert params == (1, 2, 3)

    def test_or_chain_under_and_is_one_group(self, dummy_dialect: DummyDialect):
        """A chain of ORs under an AND is one group, not one bracket per operand."""
        chain = LogicalPredicate(
            dummy_dialect,
            "OR",
            eq(dummy_dialect, "b", 2),
            eq(dummy_dialect, "c", 3),
            eq(dummy_dialect, "d", 4),
        )
        pred = LogicalPredicate(dummy_dialect, "AND", eq(dummy_dialect, "a", 1), chain)

        sql, params = pred.to_sql()

        assert sql == '"a" = ? AND ("b" = ? OR "c" = ? OR "d" = ?)'
        assert params == (1, 2, 3, 4)

    def test_or_between_two_and_operands(self, dummy_dialect: DummyDialect):
        """``a AND (b OR c) AND d``: only the OR group is bracketed."""
        left = eq(dummy_dialect, "a", 1)
        middle = LogicalPredicate(
            dummy_dialect,
            "OR",
            eq(dummy_dialect, "b", 2),
            eq(dummy_dialect, "c", 3),
        )
        right = eq(dummy_dialect, "d", 4)
        pred = LogicalPredicate(dummy_dialect, "AND", left, middle, right)

        sql, params = pred.to_sql()

        assert sql == '"a" = ? AND ("b" = ? OR "c" = ?) AND "d" = ?'
        assert params == (1, 2, 3, 4)

    def test_and_inside_or_group_stays_flat(self, dummy_dialect: DummyDialect):
        """``a AND (b OR c AND d)``: the inner AND needs no brackets of its own."""
        inner_or = LogicalPredicate(
            dummy_dialect,
            "OR",
            eq(dummy_dialect, "b", 2),
            LogicalPredicate(
                dummy_dialect,
                "AND",
                eq(dummy_dialect, "c", 3),
                eq(dummy_dialect, "d", 4),
            ),
        )
        pred = LogicalPredicate(dummy_dialect, "AND", eq(dummy_dialect, "a", 1), inner_or)

        sql, params = pred.to_sql()

        assert sql == '"a" = ? AND ("b" = ? OR "c" = ? AND "d" = ?)'
        assert params == (1, 2, 3, 4)

    def test_not_operand_keeps_its_own_group(self, dummy_dialect: DummyDialect):
        """``NOT`` already brackets its operand; nesting it under AND changes nothing."""
        negated = LogicalPredicate(dummy_dialect, "NOT", eq(dummy_dialect, "b", 2))
        pred = LogicalPredicate(dummy_dialect, "AND", eq(dummy_dialect, "a", 1), negated)

        sql, params = pred.to_sql()

        assert sql == '"a" = ? AND NOT ("b" = ?)'
        assert params == (1, 2)

    def test_default_filter_shape_from_introspection(self, dummy_dialect: DummyDialect):
        """The shape that exposed this: a caller filter AND a system-exclusion OR.

        ``object = ? AND (relation IS NULL OR relation NOT LIKE 'RDB$%')``.
        Flattened, the OR swallows the object filter, so the row set stops
        depending on the object at all -- the answer is not merely unsorted, it
        is a different question's answer.
        """
        object_filter = eq(dummy_dialect, "object_name", "PROBE_ORDERS")
        system_exclusion = LogicalPredicate(
            dummy_dialect,
            "OR",
            IsNullPredicate(dummy_dialect, Column(dummy_dialect, "relation_name")),
            LikePredicate(
                dummy_dialect,
                "NOT LIKE",
                Column(dummy_dialect, "relation_name"),
                Literal(dummy_dialect, "RDB$%"),
            ),
        )
        pred = LogicalPredicate(dummy_dialect, "AND", object_filter, system_exclusion)

        sql, params = pred.to_sql()

        assert sql == (
            '"object_name" = ? AND '
            '("relation_name" IS NULL OR "relation_name" NOT LIKE ?)'
        )
        assert params == ("PROBE_ORDERS", "RDB$%")

    @pytest.mark.parametrize(
        "op",
        ["AND", "OR"],
    )
    def test_every_connective_keeps_parameter_order(self, dummy_dialect: DummyDialect, op):
        """Grouping must not reorder the parameter tuple it travels with.

        The tuple is positional against the text; a formatter that regrouped by
        copying operands around could still render the right SQL and bind the
        wrong values.
        """
        pred = LogicalPredicate(
            dummy_dialect,
            op,
            eq(dummy_dialect, "a", 1),
            LogicalPredicate(
                dummy_dialect,
                "OR" if op == "AND" else "AND",
                eq(dummy_dialect, "b", 2),
                eq(dummy_dialect, "c", 3),
            ),
            eq(dummy_dialect, "d", 4),
        )

        _, params = pred.to_sql()

        assert params == (1, 2, 3, 4)
