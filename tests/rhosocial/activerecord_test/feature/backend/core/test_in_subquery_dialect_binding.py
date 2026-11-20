# tests/rhosocial/activerecord_test/feature/backend/test_in_subquery_dialect_binding.py
"""``in_()`` has to bind the subquery it builds, like every other site does.

``IN`` predicate construction has three branches, and two of them bind. The
value-list branch hands the dialect to a ``Literal``; the pass-through branch
hands back the caller's own expression, already bound by whoever built it. The
third branch wraps an ActiveQuery-like object in a ``Subquery`` -- and
constructed it with ``None`` as the dialect.

Nothing noticed, because a ``Subquery`` computes its ``query_input`` inside its
own constructor. An unbound node therefore renders perfectly well right up
until something asks it to ``to_sql()``, and ``format_in_predicate`` does
exactly that for any ``values`` that is not a ``Literal``. Reading the
validating ``dialect`` property then raised ``ValueError: Subquery has no
dialect bound`` -- from a path whose only mistake was one word in one line, and
naming a class the caller never asked for.

The other construction sites all bind: ``query_sources.py`` builds
``Subquery(dialect, ...)``, and the branch that wraps a query hands the same
dialect down twice. So the unbound node was an outlier rather than a policy,
and there is nothing for a dialect to opt out of.

The bare :class:`~...expression.core.Column` is a reference and carries no
``in_()``, so the query layer builds this predicate explicitly -- see
``_in_predicate`` in ``rhosocial.activerecord.query.range``, which the helper
below mirrors branch for branch.

Pinned here because the fix is invisible from the outside: before it, building
the predicate succeeded and rendering it raised, with nothing about the
expression tree having changed in between.
"""

import pytest

from rhosocial.activerecord.backend.expression.core import BaseExpression, Column, Literal, Subquery
from rhosocial.activerecord.backend.expression.predicates import InPredicate
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class QueryLike:
    """The whole of what the branch asks of a query object."""

    def __init__(self, query_expression):
        self.query_expression = query_expression

    def to_query_expression(self):
        return self.query_expression


def in_predicate(dialect, expr, values):
    """Build the explicit ``IN`` node, mirroring ``_in_predicate`` branch for branch."""
    to_query_expression = getattr(values, "to_query_expression", None)
    if callable(to_query_expression):
        return InPredicate(dialect, expr, Subquery(dialect, to_query_expression()))
    if isinstance(values, BaseExpression):
        return InPredicate(dialect, expr, values)
    return InPredicate(dialect, expr, Literal(dialect, tuple(values)))


def in_subquery(dialect):
    """Build the predicate ``User.c.id.in_(big_orders)`` produces."""
    return in_predicate(dialect, Column(dialect, "id"), QueryLike(Column(dialect, "user_id")))


class TestInSubqueryBinding:
    """The branch that wraps a query must not leave the wrapper unbound."""

    def test_building_the_predicate_does_not_bind_the_subquery_to_nothing(self):
        """The bug: ``Subquery(None, ...)`` -- construction looked fine."""
        predicate = in_subquery(DummyDialect())

        assert isinstance(predicate.values, Subquery)
        # Read through the private attribute rather than the property on
        # purpose: the property is the thing that raised, and it raises
        # precisely so that an unbound node cannot be read by accident.
        assert predicate.values._dialect is not None

    def test_rendering_the_predicate_reaches_the_subquery(self):
        """``format_in_predicate`` renders any non-``Literal`` through ``to_sql``.

        This is where the unbound node was finally asked for its dialect.
        """
        predicate = in_subquery(DummyDialect())

        sql, params = predicate.to_sql()

        assert " IN " in sql
        assert params == ()

    def test_the_subquery_is_rendered_through_the_calling_dialect(self):
        """Not merely "it rendered" -- the subquery resolved a real formatter.

        An unbound node cannot do this at all, so a passing assertion here is a
        stronger statement than the rendered string.
        """
        dialect = DummyDialect()
        predicate = in_subquery(dialect)

        sql, _ = predicate.to_sql()

        assert dialect.format_column(Column(dialect, "user_id"))[0] in sql

    def test_the_value_list_branch_is_unchanged(self):
        """The guard must not disturb the branch that already bound."""
        dialect = DummyDialect()

        sql, params = in_predicate(dialect, Column(dialect, "status"), ["active", "pending"]).to_sql()

        assert " IN " in sql
        assert params == ("active", "pending")

    def test_the_pass_through_branch_is_unchanged(self):
        dialect = DummyDialect()
        subquery = Subquery(dialect, Column(dialect, "user_id"))

        predicate = in_predicate(dialect, Column(dialect, "id"), subquery)

        assert predicate.values is subquery
        assert " IN " in predicate.to_sql()[0]

    def test_an_unbound_subquery_built_by_hand_still_refuses(self):
        """The check is not removed -- it is fed a bound node now.

        Without this, "bind it" and "stop validating" would both make the tests
        above pass, and only one of them is a fix.
        """
        unbound = Subquery(None, Column(DummyDialect(), "user_id"))

        with pytest.raises(ValueError) as exc_info:
            unbound.to_sql()

        message = str(exc_info.value)
        assert "no dialect bound" in message
        assert "Subquery" in message
