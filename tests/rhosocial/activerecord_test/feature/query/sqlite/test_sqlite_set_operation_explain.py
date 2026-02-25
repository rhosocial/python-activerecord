# tests/rhosocial/activerecord_test/feature/query/sqlite/test_sqlite_set_operation_explain.py
"""
Tests for EXPLAIN clause with SetOperationQuery (UNION, INTERSECT, EXCEPT).

These tests verify that the .explain() method works correctly with set operations.
The generic testsuite does not cover backend-specific EXPLAIN functionality
for set operations.
"""
import pytest
from typing import List, Dict, Any


def _validate_explain_output(plan: List[Dict[str, Any]], test_name: str = ""):
    """
    Helper to validate the structure of the EXPLAIN query plan for SQLite.
    """
    if test_name:
        print(f"\nPlan for {test_name}: {plan}")

    assert isinstance(plan, list)
    assert len(plan) > 0
    for row in plan:
        assert isinstance(row, dict)
        assert 'addr' in row
        assert 'opcode' in row


@pytest.mark.sqlite
class TestSqliteSetOperationExplain:
    """Tests for EXPLAIN clause with SetOperationQuery."""

    def test_explain_union(self, order_fixtures):
        """Test EXPLAIN on UNION query."""
        User, Order, _ = order_fixtures

        user1 = User(username='user1', email='user1@test.com', age=20)
        user1.save()

        user2 = User(username='user2', email='user2@test.com', age=25)
        user2.save()

        query1 = User.query().where(User.c.username == 'user1')
        query2 = User.query().where(User.c.username == 'user2')

        union_query = query1.union(query2)
        plan = union_query.explain().aggregate()

        _validate_explain_output(plan, "UNION with explain")


@pytest.mark.sqlite
@pytest.mark.asyncio
class TestAsyncSqliteSetOperationExplain:
    """Tests for EXPLAIN clause with AsyncSetOperationQuery."""

    async def test_async_explain_union(self, async_order_fixtures):
        """Test async EXPLAIN on UNION query."""
        AsyncUser, AsyncOrder, _ = async_order_fixtures

        user1 = AsyncUser(username='async_user1', email='async1@test.com', age=20)
        await user1.save()

        user2 = AsyncUser(username='async_user2', email='async2@test.com', age=25)
        await user2.save()

        query1 = AsyncUser.query().where(AsyncUser.c.username == 'async_user1')
        query2 = AsyncUser.query().where(AsyncUser.c.username == 'async_user2')

        union_query = query1.union(query2)
        plan = await union_query.explain().aggregate()

        _validate_explain_output(plan, "async UNION with explain")

    async def test_async_explain_intersect(self, async_order_fixtures):
        """Test async EXPLAIN on INTERSECT query."""
        AsyncUser, AsyncOrder, _ = async_order_fixtures

        user = AsyncUser(username='async_same', email='async_same@test.com', age=20)
        await user.save()

        query1 = AsyncUser.query().where(AsyncUser.c.username == 'async_same')
        query2 = AsyncUser.query().where(AsyncUser.c.email == 'async_same@test.com')

        intersect_query = query1.intersect(query2)
        plan = await intersect_query.explain().aggregate()

        _validate_explain_output(plan, "async INTERSECT with explain")

    async def test_async_explain_except(self, async_order_fixtures):
        """Test async EXPLAIN on EXCEPT query."""
        AsyncUser, AsyncOrder, _ = async_order_fixtures

        user = AsyncUser(username='async_only', email='async_only@test.com', age=20)
        await user.save()

        query1 = AsyncUser.query().where(AsyncUser.c.username == 'async_only')
        query2 = AsyncUser.query().where(AsyncUser.c.email == 'nonexistent@test.com')

        except_query = query1.except_(query2)
        plan = await except_query.explain().aggregate()

        _validate_explain_output(plan, "async EXCEPT with explain")

    async def test_async_union_without_explain(self, async_order_fixtures):
        """Test async UNION query without EXPLAIN returns actual results."""
        AsyncUser, AsyncOrder, _ = async_order_fixtures

        user1 = AsyncUser(username='async_alice', email='async_alice@test.com', age=20)
        await user1.save()

        user2 = AsyncUser(username='async_bob', email='async_bob@test.com', age=25)
        await user2.save()

        query1 = AsyncUser.query().where(AsyncUser.c.username == 'async_alice')
        query2 = AsyncUser.query().where(AsyncUser.c.username == 'async_bob')

        union_result = await query1.union(query2).aggregate()

        assert len(union_result) == 2
        usernames = [row.get('username') for row in union_result]
        assert 'async_alice' in usernames
        assert 'async_bob' in usernames
