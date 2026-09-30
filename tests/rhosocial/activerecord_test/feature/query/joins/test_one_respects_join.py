# Moved here from the testsuite package.
#
# The bridge version of this file did
#     from rhosocial.activerecord.testsuite.feature...import *
# which only resolved against an unpublished testsuite checkout, so the
# module failed to import in CI. The tests are inlined instead. The
# fixtures and helpers they use (order_fixtures, requires_inner_join)
# are published, so the dependency on the testsuite package remains and
# is limited to infrastructure.
# tests/rhosocial/activerecord_test/feature/query/joins/test_one_respects_join.py
"""``one()`` must honour the accumulated join clause.

Regression coverage for a silent-wrong-answer defect: ``ActiveQuery.one()``
built its internal ``QueryExpression`` from a bare ``TableExpression`` and
ignored ``self.join_clause``, while ``all()``, ``to_sql()`` and ``aggregate()``
all passed the join through. A joined ``.one()`` therefore dropped the join
without raising, returning rows from the base table alone.

The functional tests below are the load-bearing ones: they fail with a
*wrong result* on the unfixed code, not merely with different SQL.
"""

from rhosocial.activerecord.testsuite.utils import requires_inner_join


def _seed_user_with_orders(User, Order, username, order_numbers):
    """Create a user owning one order per name in ``order_numbers``."""
    user = User(username=username, email=f"{username}@example.com", age=30)
    user.save()
    for number in order_numbers:
        Order(user_id=user.id, order_number=number, total_amount=10).save()
    return user


@requires_inner_join()
def test_inner_join_one_skips_users_without_orders(order_fixtures):
    """INNER JOIN must restrict the rows one() may return.

    On the unfixed code the join was discarded, so the order_by put the
    order-less user first and one() returned it -- a wrong record with no
    error raised.

    Asserted on ``username`` rather than ``id``: a bare ``SELECT *`` across a
    join emits two columns named ``id`` (``users.id`` and ``orders.id``) and the
    row mapping keeps the last one, so ``.id`` is not the user's id. That
    ambiguity predates this fix and is shared with ``all()``; joins are expected
    to narrow the projection with ``select()``.
    """
    User, Order, _ = order_fixtures
    _seed_user_with_orders(User, Order, "lonely", [])
    _seed_user_with_orders(User, Order, "buyer", ["B-1"])

    found = (
        User.query()
        .join(Order, on=User.c.id == Order.c.user_id)
        .order_by(User.c.id)
        .one()
    )

    assert found is not None, "INNER JOIN matched a user, so one() must not return None"
    assert found.username == "buyer"


@requires_inner_join()
def test_joined_one_applies_join_and_where_together(order_fixtures):
    """A WHERE clause on the joined table only resolves when the join is kept."""
    User, Order, _ = order_fixtures
    _seed_user_with_orders(User, Order, "small", ["S-1"])
    big = _seed_user_with_orders(User, Order, "big", ["B-1", "B-2"])

    found = (
        Order.query()
        .join(User, on=Order.c.user_id == User.c.id)
        .where(User.c.username == "big")
        .order_by(Order.c.id)
        .one()
    )

    assert found is not None
    assert found.user_id == big.id


@requires_inner_join()
def test_joined_one_returns_none_when_join_excludes_everything(order_fixtures):
    """An INNER JOIN with no match yields None, not an unfiltered base row."""
    User, Order, _ = order_fixtures
    _seed_user_with_orders(User, Order, "only", ["O-1"])

    found = (
        User.query()
        .join(Order, on=User.c.id == Order.c.user_id)
        .where(User.c.username == "does-not-exist")
        .one()
    )

    assert found is None


@requires_inner_join()
def test_one_without_join_is_unchanged(order_fixtures):
    """The un-joined path keeps its previous behaviour (no regression)."""
    User, _, _ = order_fixtures
    first = User(username="solo", email="solo@example.com", age=30)
    first.save()

    found = User.query().order_by(User.c.id).one()

    assert found is not None
    assert found.id == first.id
