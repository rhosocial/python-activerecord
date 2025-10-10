# tests/rhosocial/activerecord_test/feature/query/sqlite/test_explain_cte_multiple.py
"""Test explain functionality with multiple CTEs for SQLite."""
from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.dialect import ExplainType
from rhosocial.activerecord.testsuite.feature.query.conftest import (
    order_fixtures,
    blog_fixtures,
    json_user_fixture,
    tree_fixtures,
    extended_order_fixtures,
    combined_fixtures,
)


def test_explain_multiple_ctes(order_fixtures):
    """Test EXPLAIN with multiple CTEs"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses and amounts
    statuses = ['pending', 'paid', 'shipped']
    for i, status in enumerate(statuses):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Create a query with multiple CTEs
    query = Order.query()

    # First CTE: active orders
    query.with_cte(
        'active_orders',
        "SELECT * FROM orders WHERE status IN ('pending', 'paid')"
    )

    # Second CTE: expensive orders from active orders
    query.with_cte(
        'expensive_orders',
        "SELECT * FROM active_orders WHERE total_amount > 150.00"
    )

    # Use the second CTE
    query.from_cte('expensive_orders')

    # Get execution plan
    plan = query.explain().all()

    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])
    # assert "WITH" in plan.upper()
    # assert all(cte_name in plan.lower() for cte_name in ['active_orders', 'expensive_orders'])

    # Test EXPLAIN QUERY PLAN
    plan = query.explain(type=ExplainType.QUERYPLAN).all()
    assert isinstance(plan, str)
    assert "SCAN" in plan or "SEARCH" in plan
    # assert any(kw in plan.upper() for kw in ['WITH', 'CTE'])


def test_explain_cte_with_join(order_fixtures):
    """Test EXPLAIN with CTE and JOIN operations"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create order
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    # Create order item
    item = OrderItem(
        order_id=order.id,
        product_name='Test Product',
        quantity=1,
        unit_price=Decimal('100.00'),
        subtotal=Decimal('100.00')
    )
    item.save()

    # Create a CTE with join operations
    query = Order.query()

    # Define a CTE for orders with items
    query.with_cte(
        'orders_with_items',
        f"""
        SELECT o.*, i.product_name, i.quantity
        FROM {Order.__table_name__} o
        JOIN {OrderItem.__table_name__} i ON o.id = i.order_id
        """
    )

    # Use the CTE
    query.from_cte('orders_with_items')

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).all()

    assert isinstance(plan, str)
    assert "SCAN" in plan or "SEARCH" in plan
    # assert any(kw in plan.upper() for kw in ['WITH', 'JOIN'])

    # Get detailed plan
    detailed_plan = query.explain().all()
    assert isinstance(detailed_plan, str)
    assert any(op in detailed_plan for op in ['Trace', 'Goto', 'OpenRead'])
    # assert all(table_name.lower() in detailed_plan.lower() for table_name in [Order.__table_name__, OrderItem.__table_name__])


def test_explain_cte_with_or_conditions(order_fixtures):
    """Test EXPLAIN with CTE and OR conditions"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses
    statuses = ['pending', 'paid', 'shipped', 'cancelled']
    for i, status in enumerate(statuses):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Define a CTE with OR conditions
    query = Order.query().with_cte(
        'filtered_orders',
        """
        SELECT *
        FROM orders
        WHERE status = 'pending'
           OR total_amount > 300.00
        """
    ).from_cte('filtered_orders')

    # Add additional conditions to main query
    query.start_or_group()
    query.where('total_amount < ?', (Decimal('200.00'),))
    query.or_where('total_amount > ?', (Decimal('350.00'),))
    query.end_or_group()

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).all()

    assert isinstance(plan, str)
    assert "SCAN" in plan or "SEARCH" in plan
    assert any(kw in plan.upper() for kw in ['WITH', 'OR'])

    # Get detailed plan
    detailed_plan = query.explain().all()
    assert isinstance(detailed_plan, str)
    assert any(op in detailed_plan for op in ['Trace', 'Goto', 'OpenRead', 'Ne', 'Le', 'Gt'])
