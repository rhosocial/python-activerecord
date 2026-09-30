# Moved here from the testsuite package.
#
# The bridge version of this file did
#     from rhosocial.activerecord.testsuite.feature...import *
# which only resolved against an unpublished testsuite checkout, so the
# module failed to import in CI. The tests are inlined instead. The
# fixtures and helpers they use (order_fixtures, requires_inner_join)
# are published, so the dependency on the testsuite package remains and
# is limited to infrastructure.
# tests/rhosocial/activerecord_test/feature/query/predicates/test_in_predicate_parity.py
"""``in_()`` and ``not_in()`` must accept the same input shapes.

``in_()`` dispatches over three input shapes -- a query object exposing
``to_query_expression()``, an expression exposing ``to_sql()``, and a plain
list/tuple. ``not_in()`` used to call ``tuple(values)`` unconditionally, so a
subquery passed to it was silently exploded into a bind-parameter list instead
of being rendered as ``NOT IN (SELECT ...)``.

``not_in()`` now delegates to ``in_()`` and negates the result, so the two
cannot drift apart again.
"""

def _seed(users, orders, rich_name, poor_name):
    """One user with a large order, one with a small order."""
    rich = users(username=rich_name, email=f"{rich_name}@example.com", age=60)
    poor = users(username=poor_name, email=f"{poor_name}@example.com", age=61)
    rich.save()
    poor.save()
    orders(user_id=rich.id, order_number="R-1", total_amount=999).save()
    orders(user_id=poor.id, order_number="P-1", total_amount=1).save()
    return rich, poor


def test_not_in_accepts_a_query_object(order_fixtures):
    """A query passed to not_in() renders as NOT IN (SELECT ...)."""
    User, Order, _ = order_fixtures
    rich, poor = _seed(User, Order, "ni_rich", "ni_poor")

    big_spenders = Order.query().select(Order.c.user_id).where(Order.c.total_amount > 100)
    names = [
        row["username"]
        for row in User.query()
        .where(User.c.id.not_in(big_spenders))
        .select(User.c.username)
        .aggregate()
    ]

    assert "ni_poor" in names
    assert "ni_rich" not in names, "NOT IN (big spenders) must exclude the rich user"


def test_in_and_not_in_are_exact_complements(order_fixtures):
    """For the same query, in_() and not_in() partition the same row set."""
    User, Order, _ = order_fixtures
    _seed(User, Order, "cmp_rich", "cmp_poor")

    big_spenders = Order.query().select(Order.c.user_id).where(Order.c.total_amount > 100)

    inside = {
        row["username"]
        for row in User.query()
        .where(User.c.id.in_(big_spenders))
        .select(User.c.username)
        .aggregate()
    }
    outside = {
        row["username"]
        for row in User.query()
        .where(User.c.id.not_in(big_spenders))
        .select(User.c.username)
        .aggregate()
    }
    everyone = {
        row["username"]
        for row in User.query().select(User.c.username).aggregate()
    }

    assert inside & outside == set()
    assert inside | outside == everyone


def test_not_in_with_plain_list_is_unchanged(order_fixtures):
    """The ordinary list form keeps its previous behaviour."""
    User, _, _ = order_fixtures
    keep = User(username="keep", email="keep@example.com", age=20)
    drop = User(username="drop", email="drop@example.com", age=20)
    keep.save()
    drop.save()

    names = [
        row["username"]
        for row in User.query()
        .where(User.c.username.not_in(["drop"]))
        .select(User.c.username)
        .aggregate()
    ]

    assert "keep" in names
    assert "drop" not in names


def test_not_in_with_tuple_is_unchanged(order_fixtures):
    """Tuples behave the same as lists (tuple() is idempotent on tuples)."""
    User, _, _ = order_fixtures
    User(username="t_keep", email="tk@example.com", age=21).save()
    User(username="t_drop", email="td@example.com", age=21).save()

    names = [
        row["username"]
        for row in User.query()
        .where(User.c.username.not_in(("t_drop",)))
        .select(User.c.username)
        .aggregate()
    ]

    assert "t_keep" in names
    assert "t_drop" not in names
