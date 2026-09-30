# tests/rhosocial/activerecord_test/feature/query/special/test_exists_expression.py
"""``ExistsExpression`` against a real database.

``ExistsExpression`` had coverage only against the dummy dialect
(``tests/.../feature/backend/dummy2/test_advanced_functions.py``), so nothing
exercised it through a real driver: neither the ``EXISTS``/``NOT EXISTS``
rendering nor the correlated form, where the subquery references a column of
the enclosing query.

This covers it end to end on SQLite. ``ActiveQuery.exists()`` is a separate
thing -- it issues ``SELECT COUNT(*)`` and is deliberately left alone; the point
here is that the expression node itself works when composed by hand.
"""

import pytest

from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.advanced_functions import ExistsExpression
from rhosocial.activerecord.backend.expression import QueryExpression, TableExpression


def _subquery(dialect, model, where=None):
    """A ``SELECT 1 FROM <table> [WHERE ...]`` expression for EXISTS to wrap."""
    return QueryExpression(
        dialect,
        select=[Column(dialect, "1")],
        from_=TableExpression(dialect, model.table_name(), schema_name=model.schema_name()),
        where=where,
    )


@pytest.fixture
def users_with_orders(order_fixtures):
    """A user who has ordered and one who has not."""
    User, Order, _ = order_fixtures
    buyer = User(username="ex_buyer", email="exb@example.com", age=30)
    loner = User(username="ex_loner", email="exl@example.com", age=31)
    buyer.save()
    loner.save()
    Order(user_id=buyer.id, order_number="EX-1", total_amount=10).save()
    return User, Order, buyer, loner


class TestUncorrelatedExists:
    """An uncorrelated EXISTS is a constant -- it does not depend on the outer row.

    Worth pinning precisely because that makes it a poor filter: the same
    answer comes back for every row, so it selects all users or none. The
    correlated tests below are the useful shape.
    """

    def test_uncorrelated_exists_keeps_every_row_when_the_subquery_matches(
        self, users_with_orders
    ):
        User, Order, _, _ = users_with_orders
        dialect = User.backend().dialect

        sub = _subquery(dialect, Order, Order.c.order_number == "EX-1")
        names = [
            row["username"]
            for row in User.query()
            .where(ExistsExpression(dialect, sub))
            .select(User.c.username)
            .aggregate()
        ]

        assert sorted(names) == ["ex_buyer", "ex_loner"]

    def test_uncorrelated_not_exists_drops_every_row_when_the_subquery_matches(
        self, users_with_orders
    ):
        User, Order, _, _ = users_with_orders
        dialect = User.backend().dialect

        sub = _subquery(dialect, Order, Order.c.order_number == "EX-1")
        names = [
            row["username"]
            for row in User.query()
            .where(ExistsExpression(dialect, sub, is_not=True))
            .select(User.c.username)
            .aggregate()
        ]

        assert names == []

    def test_uncorrelated_not_exists_keeps_every_row_when_nothing_matches(
        self, users_with_orders
    ):
        User, Order, _, _ = users_with_orders
        dialect = User.backend().dialect

        sub = _subquery(dialect, Order, Order.c.order_number == "NO-SUCH-ORDER")
        names = [
            row["username"]
            for row in User.query()
            .where(ExistsExpression(dialect, sub, is_not=True))
            .select(User.c.username)
            .aggregate()
        ]

        assert sorted(names) == ["ex_buyer", "ex_loner"]


class TestCorrelatedExists:
    """The subquery's WHERE names a column of the enclosing query."""

    def test_correlated_exists_references_the_outer_query(self, users_with_orders):
        User, Order, _, _ = users_with_orders
        dialect = User.backend().dialect

        sub = _subquery(dialect, Order, Order.c.user_id == User.c.id)
        names = [
            row["username"]
            for row in User.query()
            .where(ExistsExpression(dialect, sub))
            .select(User.c.username)
            .aggregate()
        ]

        assert names == ["ex_buyer"], "only the user with an order matches"

    def test_correlated_not_excludes_the_matching_row_only(self, users_with_orders):
        User, Order, _, _ = users_with_orders
        dialect = User.backend().dialect

        sub = _subquery(dialect, Order, Order.c.user_id == User.c.id)
        names = [
            row["username"]
            for row in User.query()
            .where(ExistsExpression(dialect, sub, is_not=True))
            .select(User.c.username)
            .aggregate()
        ]

        assert names == ["ex_loner"]

    def test_correlated_exists_composes_with_other_predicates(self, users_with_orders):
        User, Order, _, _ = users_with_orders
        dialect = User.backend().dialect

        sub = _subquery(dialect, Order, Order.c.user_id == User.c.id)
        names = [
            row["username"]
            for row in User.query()
            .where(ExistsExpression(dialect, sub))
            .where(User.c.username == "ex_loner")
            .select(User.c.username)
            .aggregate()
        ]

        assert names == [], "the AND partner rules the row out"
