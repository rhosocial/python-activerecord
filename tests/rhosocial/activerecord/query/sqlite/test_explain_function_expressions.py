"""Test EXPLAIN with function expressions for SQLite."""
from decimal import Decimal

import pytest

from tests.rhosocial.activerecord.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_explain_functions(order_fixtures, request):
    """Test EXPLAIN with function expressions."""
    if 'sqlite' not in request.node.name:
        pytest.skip("This test is only applicable to SQLite")

    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    # Test EXPLAIN with string function
    query = Order.query()
    query.function('UPPER', 'order_number', alias='upper_order')

    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])

    # Test EXPLAIN with numeric function
    query = Order.query()
    query.function('ABS', 'total_amount', alias='abs_amount')

    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])

    # Test EXPLAIN with conditional function
    query = User.query()
    query.function('COALESCE', 'age', '0', alias='age_or_zero')

    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])

    # Test EXPLAIN with aggregate function
    query = Order.query()
    query.function('COUNT', '*', alias='order_count')

    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Aggregate', 'Function'])

    # Test EXPLAIN with function in GROUP BY
    query = Order.query()
    query.group_by('status')
    query.function('SUM', 'total_amount', alias='status_total')

    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'GroupBy', 'Aggregate', 'Function'])