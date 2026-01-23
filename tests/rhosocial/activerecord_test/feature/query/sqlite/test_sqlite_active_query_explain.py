# tests/rhosocial/activerecord_test/feature/query/sqlite/test_sqlite_active_query_explain.py
"""
Tests for the EXPLAIN clause functionality specific to the SQLite backend.

The generic testsuite does not cover backend-specific clauses like EXPLAIN.
This file provides tests for ActiveQuery and AsyncActiveQuery to ensure
the .explain() method works correctly for various query types.

Note:
- EXPLAIN tests for Set Operations (UNION, INTERSECT, EXCEPT) are not
  included because the SetOperationQuery class does not currently implement
  an .explain() method.
"""
import pytest
from typing import List, Dict, Any

# Fixtures are imported from the testsuite via the top-level conftest.py
# in the current directory.
# These fixtures provide configured User, Order, and OrderItem models.


def _validate_explain_output(plan: List[Dict[str, Any]], test_name: str = ""):
    """
    Helper to validate the structure of the EXPLAIN query plan for SQLite.
    """
    if test_name:
        print(f"\nPlan for {test_name}: {plan}") # Debug print
    
    assert isinstance(plan, list)
    assert len(plan) > 0
    for row in plan:
        assert isinstance(row, dict)
        # SQLite's EXPLAIN output typically includes these columns
        assert 'addr' in row
        assert 'opcode' in row
        assert 'p1' in row
        assert 'p2' in row
        assert 'p3' in row
        assert 'p4' in row
        assert 'p5' in row
        assert 'comment' in row


@pytest.mark.sqlite
class TestSqliteActiveQueryExplain:
    """Synchronous tests for EXPLAIN clause with ActiveQuery."""

    def test_explain_on_simple_query(self, order_fixtures):
        """Tests EXPLAIN on a simple .all() query."""
        User, _, _ = order_fixtures
        plan = User.query().where(User.c.age > 30).explain().aggregate()
        _validate_explain_output(plan, "Sync Simple Query")

    def test_explain_on_one_query(self, order_fixtures):
        """Tests EXPLAIN on a simple .one() query."""
        User, _, _ = order_fixtures
        # Note: .one() implicitly adds LIMIT 1, so the plan will reflect that.
        plan = User.query().where(User.c.age == 30).limit(1).explain().aggregate()
        _validate_explain_output(plan, "Sync One Query")

    def test_explain_on_aggregate_query(self, order_fixtures):
        """Tests EXPLAIN on an aggregate query."""
        User, _, _ = order_fixtures
        from rhosocial.activerecord.backend.expression import functions
        plan = (
            User.query()
            .select(User.c.is_active, functions.count(User.query().backend().dialect, User.c.id).as_("count"))
            .group_by(User.c.is_active)
            .explain()
            .aggregate()
        )
        _validate_explain_output(plan, "Sync Aggregate Query")

    def test_explain_on_join_query(self, order_fixtures):
        """Tests EXPLAIN on a query with a JOIN clause."""
        User, Order, _ = order_fixtures
        plan = (
            User.query()
            .join(Order, on=(User.c.id == Order.c.user_id))
            .where(User.c.age > 25)
            .explain()
            .aggregate()
        )
        _validate_explain_output(plan, "Sync Join Query")


@pytest.mark.sqlite
@pytest.mark.asyncio
class TestAsyncSqliteActiveQueryExplain:
    """Asynchronous tests for EXPLAIN clause with AsyncActiveQuery."""

    async def test_explain_on_simple_query_async(self, async_order_fixtures):
        """Tests EXPLAIN on a simple async .all() query."""
        User, _, _ = async_order_fixtures
        plan = await User.query().where(User.c.age > 30).explain().aggregate()
        _validate_explain_output(plan, "Async Simple Query")

    async def test_explain_on_one_query_async(self, async_order_fixtures):
        """Tests EXPLAIN on a simple async .one() query."""
        User, _, _ = async_order_fixtures
        plan = await User.query().where(User.c.age == 30).limit(1).explain().aggregate()
        _validate_explain_output(plan, "Async One Query")

    async def test_explain_on_aggregate_query_async(self, async_order_fixtures):
        """Tests EXPLAIN on an async aggregate query."""
        User, _, _ = async_order_fixtures
        from rhosocial.activerecord.backend.expression import functions
        plan = await (
            User.query()
            .select(User.c.is_active, functions.count(User.query().backend().dialect, User.c.id).as_("count"))
            .group_by(User.c.is_active)
            .explain()
            .aggregate()
        )
        _validate_explain_output(plan, "Async Aggregate Query")

    async def test_explain_on_join_query_async(self, async_order_fixtures):
        """Tests EXPLAIN on an async query with a JOIN clause."""
        User, Order, _ = async_order_fixtures
        plan = await (
            User.query()
            .join(Order, on=(User.c.id == Order.c.user_id))
            .where(User.c.age > 25)
            .explain()
            .aggregate()
        )
        _validate_explain_output(plan, "Async Join Query")
