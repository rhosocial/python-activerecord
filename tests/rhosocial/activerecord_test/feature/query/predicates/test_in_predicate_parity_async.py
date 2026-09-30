# Moved here from the testsuite package.
#
# The bridge version of this file did
#     from rhosocial.activerecord.testsuite.feature...import *
# which only resolved against an unpublished testsuite checkout, so the
# module failed to import in CI. The tests are inlined instead. The
# fixtures and helpers they use (order_fixtures, requires_inner_join)
# are published, so the dependency on the testsuite package remains and
# is limited to infrastructure.
# tests/rhosocial/activerecord_test/feature/query/predicates/test_in_predicate_parity_async.py
"""Async ``in_()`` / ``not_in()`` input-shape parity.

Async mirror of :mod:`test_in_predicate_parity`.
"""

async def _seed(users, orders, rich_name, poor_name):
    """One user with a large order, one with a small order."""
    rich = users(username=rich_name, email=f"{rich_name}@example.com", age=60)
    poor = users(username=poor_name, email=f"{poor_name}@example.com", age=61)
    await rich.save()
    await poor.save()
    await orders(user_id=rich.id, order_number="R-1", total_amount=999).save()
    await orders(user_id=poor.id, order_number="P-1", total_amount=1).save()
    return rich, poor


async def test_not_in_accepts_a_query_object_async(async_order_fixtures):
    """A query passed to not_in() renders as NOT IN (SELECT ...) (async)."""
    AsyncUser, AsyncOrder, _ = async_order_fixtures
    await _seed(AsyncUser, AsyncOrder, "ni_rich", "ni_poor")

    big_spenders = AsyncOrder.query().select(AsyncOrder.c.user_id).where(AsyncOrder.c.total_amount > 100)
    rows = (
        await AsyncUser.query()
        .where(AsyncUser.c.id.not_in(big_spenders))
        .select(AsyncUser.c.username)
        .aggregate()
    )
    names = [row["username"] for row in rows]

    assert "ni_poor" in names
    assert "ni_rich" not in names


async def test_in_and_not_in_are_exact_complements_async(async_order_fixtures):
    """For the same query, in_() and not_in() partition the same row set."""
    AsyncUser, AsyncOrder, _ = async_order_fixtures
    await _seed(AsyncUser, AsyncOrder, "cmp_rich", "cmp_poor")

    big_spenders = AsyncOrder.query().select(AsyncOrder.c.user_id).where(AsyncOrder.c.total_amount > 100)

    inside_rows = (
        await AsyncUser.query().where(AsyncUser.c.id.in_(big_spenders)).select(AsyncUser.c.username).aggregate()
    )
    outside_rows = (
        await AsyncUser.query().where(AsyncUser.c.id.not_in(big_spenders)).select(AsyncUser.c.username).aggregate()
    )
    everyone_rows = await AsyncUser.query().select(AsyncUser.c.username).aggregate()

    inside = {row["username"] for row in inside_rows}
    outside = {row["username"] for row in outside_rows}
    everyone = {row["username"] for row in everyone_rows}

    assert inside & outside == set()
    assert inside | outside == everyone


async def test_not_in_with_plain_list_is_unchanged_async(async_order_fixtures):
    """The ordinary list form keeps its previous behaviour (async)."""
    AsyncUser, _, _ = async_order_fixtures
    await AsyncUser(username="keep", email="keep@example.com", age=20).save()
    await AsyncUser(username="drop", email="drop@example.com", age=20).save()

    rows = (
        await AsyncUser.query()
        .where(AsyncUser.c.username.not_in(["drop"]))
        .select(AsyncUser.c.username)
        .aggregate()
    )
    names = [row["username"] for row in rows]

    assert "keep" in names
    assert "drop" not in names
