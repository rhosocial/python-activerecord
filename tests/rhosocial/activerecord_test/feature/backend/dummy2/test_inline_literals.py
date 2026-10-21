# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_inline_literals.py
"""Tests for per-value inline-vs-bound rendering (``Literal.inline``).

Covers:
- ``inline=False`` (the default, every data position): a bind-parameter
  placeholder, and nothing in ``params`` to quote
- ``inline=True`` (DDL syntax positions): escaped SQL text, no params
- The decision is per **position**, so one node holding two values can render
  one inline and the other bound
- Escaping still goes through the dialect's controlled literal construction
- DDL conditions built from ordinary data-position nodes render inline, because
  the DDL renderer marks the values it owns
"""

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonPredicate,
    InPredicate,
    Literal,
)


def _dummy_dialect():
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    return DummyDialect()


class TestLiteralInlineDecision:
    """A literal renders inline or bound according to its own ``inline``."""

    def test_default_binds(self):
        lit = Literal(_dummy_dialect(), "abc")
        assert lit.inline is False
        assert lit.to_sql() == ("?", ("abc",))

    def test_inline_writes_sql_text(self):
        lit = Literal(_dummy_dialect(), "abc", inline=True)
        assert lit.to_sql() == ("'abc'", ())

    def test_inline_escapes_quotes(self):
        lit = Literal(_dummy_dialect(), "it's", inline=True)
        sql, params = lit.to_sql()
        assert sql == "'it''s'"
        assert params == ()

    def test_inline_numeric(self):
        assert Literal(_dummy_dialect(), 42, inline=True).to_sql() == ("42", ())

    def test_repr_shows_the_decision(self):
        assert repr(Literal(_dummy_dialect(), 1)) == "Literal(1)"
        assert repr(Literal(_dummy_dialect(), 1, inline=True)) == "Literal(1, inline)"

    def test_the_decision_is_per_instance(self):
        """Two literals of the same class, decided differently."""
        one = Literal(_dummy_dialect(), 1)
        other = Literal(_dummy_dialect(), 2, inline=True)
        assert one.to_sql() == ("?", (1,))
        assert other.to_sql() == ("2", ())


class TestMixedPositionsInOneNode:
    """A node holding several values renders each by its own decision."""

    def test_one_inline_one_bound(self):
        dialect = _dummy_dialect()
        pred = ComparisonPredicate(
            dialect, "=",
            Literal(dialect, "a", inline=True),
            Literal(dialect, "b"),
        )
        assert pred.to_sql() == ("'a' = ?", ("b",))

    def test_in_list_honours_each_value(self):
        dialect = _dummy_dialect()
        pred = InPredicate(
            dialect, Column(dialect, "status"),
            Literal(dialect, ("debit", "credit"), inline=True),
        )
        sql, params = pred.to_sql()
        assert sql == '"status" IN (\'debit\', \'credit\')'
        assert params == ()

    def test_in_list_bound_by_default(self):
        dialect = _dummy_dialect()
        pred = InPredicate(
            dialect, Column(dialect, "status"), Literal(dialect, ("a", "b"))
        )
        assert pred.to_sql() == ('"status" IN (?, ?)', ("a", "b"))


class TestLiteralClaimsNoType:
    """A value at a position says nothing about what the position's type is."""

    def test_no_comparison_operations(self):
        lit = Literal(_dummy_dialect(), 7)
        assert not hasattr(lit, "like")
        assert not hasattr(lit, "sqrt")

    def test_not_a_sql_value(self):
        from rhosocial.activerecord.backend.expression.bases import SQLValue
        assert not isinstance(Literal(_dummy_dialect(), 7), SQLValue)


class TestDdlPositionsDemandInlineValues:
    """A DDL position renders the values it is given, and refuses the rest.

    There is no pass that copies the tree and lifts anything into it any more.
    A caller who composes a ``CHECK`` condition owns every literal in it and
    says ``inline=True`` on each; one that does not renders bind parameters
    into a statement that has nowhere to put them, and the refusal names the
    fix rather than guarding against a hypothetical.
    """

    def test_check_condition_inlines_the_callers_literals(self):
        """A CHECK built from inline-marked values renders inline."""
        from rhosocial.activerecord.backend.expression import TableCheckConstraint

        dialect = _dummy_dialect()
        condition = ComparisonPredicate(
            dialect, ">", Column(dialect, "age"), Literal(dialect, 0, inline=True)
        )
        constraint = TableCheckConstraint(dialect, condition)
        assert constraint.to_sql() == ('CHECK ("age" > 0)', ())

    def test_a_value_the_caller_did_not_mark_is_refused(self):
        """The contract is enforced where the bind value would appear."""
        from rhosocial.activerecord.backend.expression import TableCheckConstraint

        dialect = _dummy_dialect()
        condition = ComparisonPredicate(
            dialect, ">", Column(dialect, "age"), Literal(dialect, 0)
        )
        with pytest.raises(ValueError, match="inline=True"):
            TableCheckConstraint(dialect, condition).to_sql()

    def test_partial_index_where_inlines_the_callers_literals(self):
        from rhosocial.activerecord.backend.expression.objects import Index, Table
        from rhosocial.activerecord.backend.expression.statements.ddl_index import (
            CreateIndexStatement,
        )

        dialect = _dummy_dialect()
        where = ComparisonPredicate(
            dialect, "=", Column(dialect, "status"), Literal(dialect, "active", inline=True)
        )
        stmt = CreateIndexStatement(
            dialect, index=Index(dialect, "idx_active"), table=Table(dialect, "users"),
            columns=["email"], where=where,
        )
        sql, params = stmt.to_sql()
        assert "WHERE \"status\" = 'active'" in sql
        assert params == ()

    def test_check_with_in_list(self):
        from rhosocial.activerecord.backend.expression import TableCheckConstraint

        dialect = _dummy_dialect()
        condition = InPredicate(
            dialect, Column(dialect, "kind"),
            Literal(dialect, ("a", "b"), inline=True),
        )
        assert TableCheckConstraint(dialect, condition).to_sql() == (
            """CHECK ("kind" IN ('a', 'b'))""", ()
        )
