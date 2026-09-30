# Moved here from the testsuite package.
#
# The bridge version of this file did
#     from rhosocial.activerecord.testsuite.feature...import *
# which only resolved against an unpublished testsuite checkout, so the
# module failed to import in CI. The tests are inlined instead. The
# fixtures and helpers they use (order_fixtures, requires_inner_join)
# are published, so the dependency on the testsuite package remains and
# is limited to infrastructure.
# tests/rhosocial/activerecord_test/feature/query/joins/test_one_respects_join_async.py
"""Async ``one()`` must honour the accumulated join clause.

Async mirror of :mod:`test_one_respects_join`; the defect existed in both
``ActiveQuery.one`` and ``AsyncActiveQuery.one``.
"""

from rhosocial.activerecord.testsuite.utils import requires_inner_join


async def _seed_user_with_orders(AsyncUser, AsyncOrder, username, order_numbers):
    """Create a user owning one order per name in ``order_numbers``."""
    user = AsyncUser(username=username, email=f"{username}@example.com", age=30)
    await user.save()
    for number in order_numbers:
        await AsyncOrder(user_id=user.id, order_number=number, total_amount=10).save()
    return user


@requires_inner_join()
async def test_inner_join_one_skips_users_without_orders_async(async_order_fixtures):
    """INNER JOIN must restrict the rows one() may return (async).

    On the unfixed code the join was discarded, so the order_by put the
    order-less user first and one() returned it -- a wrong record, silently.

    Asserted on ``username`` rather than ``id``; see the sync module docstring
    for why ``SELECT *`` across a join makes ``.id`` ambiguous.
    """
    AsyncUser, AsyncOrder, _ = async_order_fixtures
    await _seed_user_with_orders(AsyncUser, AsyncOrder, "lonely", [])
    await _seed_user_with_orders(AsyncUser, AsyncOrder, "buyer", ["B-1"])

    found = (
        await AsyncUser.query()
        .join(AsyncOrder, on=AsyncUser.c.id == AsyncOrder.c.user_id)
        .order_by(AsyncUser.c.id)
        .one()
    )

    assert found is not None
    assert found.username == "buyer"


@requires_inner_join()
async def test_joined_one_applies_join_and_where_together_async(async_order_fixtures):
    """A WHERE clause on the joined table only resolves when the join is kept."""
    AsyncUser, AsyncOrder, _ = async_order_fixtures
    await _seed_user_with_orders(AsyncUser, AsyncOrder, "small", ["S-1"])
    big = await _seed_user_with_orders(AsyncUser, AsyncOrder, "big", ["B-1", "B-2"])

    found = (
        await AsyncOrder.query()
        .join(AsyncUser, on=AsyncOrder.c.user_id == AsyncUser.c.id)
        .where(AsyncUser.c.username == "big")
        .order_by(AsyncOrder.c.id)
        .one()
    )

    assert found is not None
    assert found.user_id == big.id


@requires_inner_join()
async def test_joined_one_returns_none_when_join_excludes_everything_async(async_order_fixtures):
    """An INNER JOIN with no match yields None, not an unfiltered base row."""
    AsyncUser, AsyncOrder, _ = async_order_fixtures
    await _seed_user_with_orders(AsyncUser, AsyncOrder, "only", ["O-1"])

    found = (
        await AsyncUser.query()
        .join(AsyncOrder, on=AsyncUser.c.id == AsyncOrder.c.user_id)
        .where(AsyncUser.c.username == "does-not-exist")
        .one()
    )

    assert found is None


@requires_inner_join()
async def test_one_without_join_is_unchanged_async(async_order_fixtures):
    """The un-joined path keeps its previous behaviour (async, no regression)."""
    AsyncUser, _, _ = async_order_fixtures
    first = AsyncUser(username="solo", email="solo@example.com", age=30)
    await first.save()

    found = await AsyncUser.query().order_by(AsyncUser.c.id).one()

    assert found is not None
    assert found.id == first.id
