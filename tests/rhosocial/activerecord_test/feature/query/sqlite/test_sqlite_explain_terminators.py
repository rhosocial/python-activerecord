# tests/rhosocial/activerecord_test/feature/query/sqlite/test_sqlite_explain_terminators.py
"""EXPLAIN termination semantics.

- ``all()`` / ``one()`` return model instances and must refuse to run while
  EXPLAIN is enabled, with a message that points to ``aggregate()``.
- Scalar aggregates (count/sum_/avg/min_/max_) forward the opaque plan when
  EXPLAIN is enabled, and unwrap the scalar otherwise. They all share the
  same helper, so a user-defined aggregate reusing it behaves identically.
- ``exists()`` is an EXISTS(subquery) clause: it returns a bool normally and
  forwards the plan under EXPLAIN.
"""
import pytest

from rhosocial.activerecord.query.base import ExplainOnModelQueryError


@pytest.mark.sqlite
class TestExplainModelTerminators:
    """all()/one() must refuse EXPLAIN and point to aggregate()."""

    def test_all_refuses_explain(self, order_fixtures):
        User, _, _ = order_fixtures
        with pytest.raises(ExplainOnModelQueryError, match="aggregate"):
            User.query().explain().all()

    def test_one_refuses_explain(self, order_fixtures):
        User, _, _ = order_fixtures
        with pytest.raises(ExplainOnModelQueryError, match="aggregate"):
            User.query().explain().one()

    @pytest.mark.asyncio
    async def test_all_async_refuses_explain(self, async_order_fixtures):
        User, _, _ = async_order_fixtures
        with pytest.raises(ExplainOnModelQueryError, match="aggregate"):
            await User.query().explain().all()

    @pytest.mark.asyncio
    async def test_one_async_refuses_explain(self, async_order_fixtures):
        User, _, _ = async_order_fixtures
        with pytest.raises(ExplainOnModelQueryError, match="aggregate"):
            await User.query().explain().one()


@pytest.mark.sqlite
class TestExplainScalarAggregates:
    """Scalar aggregates forward the plan under EXPLAIN, scalar otherwise."""

    def test_count_plan_is_opaque_rows(self, order_fixtures):
        _, Order, _ = order_fixtures
        plan = Order.query().explain().count()
        assert isinstance(plan, list) and plan
        assert all(isinstance(row, dict) for row in plan)

    def test_avg_plan_is_opaque_rows(self, order_fixtures):
        _, Order, _ = order_fixtures
        plan = Order.query().explain().avg(Order.c.total_amount)
        assert isinstance(plan, list) and plan
        assert all(isinstance(row, dict) for row in plan)

    def test_count_normal_is_scalar(self, order_fixtures):
        _, Order, _ = order_fixtures
        result = Order.query().count()
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_count_async_plan_and_scalar(self, async_order_fixtures):
        _, Order, _ = async_order_fixtures
        plan = await Order.query().explain().count()
        assert isinstance(plan, list) and plan
        scalar = await Order.query().count()
        assert isinstance(scalar, int)


@pytest.mark.sqlite
class TestExistsClause:
    """exists() is an EXISTS(subquery) clause, not count() > 0."""

    def test_exists_bool(self, order_fixtures):
        User, _, _ = order_fixtures
        result = User.query().exists()
        assert isinstance(result, bool)

    def test_exists_false_when_no_match(self, order_fixtures):
        User, _, _ = order_fixtures
        assert User.query().where(User.c.username == "__none__").exists() is False

    def test_exists_under_explain_returns_plan(self, order_fixtures):
        User, _, _ = order_fixtures
        plan = User.query().explain().exists()
        assert isinstance(plan, list) and plan
        assert all(isinstance(row, dict) for row in plan)

    @pytest.mark.asyncio
    async def test_exists_async(self, async_order_fixtures):
        User, _, _ = async_order_fixtures
        assert isinstance(await User.query().exists(), bool)
        plan = await User.query().explain().exists()
        assert isinstance(plan, list) and plan
