# tests/rhosocial/activerecord_test/feature/query/sqlite/test_explain_conditions.py
"""Test explain functionality with various conditions for SQLite."""
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


def test_explain_simple_where(order_fixtures):
    """Test explain with simple WHERE conditions"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00'),
        status='pending'
    )
    order.save()

    # Test EXPLAIN with normal output (opcode sequence)
    plan = (Order.query()
            .where('status = ?', ('pending',))
            .explain()
            .all())
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test EXPLAIN QUERY PLAN
    plan = (Order.query()
            .where('status = ?', ('pending',))
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    # Non-indexed column should use SCAN
    assert "SCAN" in plan


def test_explain_primary_key_condition(order_fixtures):
    """Test explain with primary key conditions"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    # Query on primary key should use index
    plan = (Order.query()
            .where('id = ?', (order.id,))
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert "SEARCH" in plan  # Should use index search
    assert "PRIMARY KEY" in plan


def test_explain_foreign_key_condition(order_fixtures):
    """Test explain with foreign key conditions"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(user_id=user.id, order_number='ORD-001')
    order.save()

    # Query on foreign key uses SCAN by default (no index)
    plan = (Order.query()
            .where('user_id = ?', (user.id,))
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert "SCAN" in plan  # Should use table scan since no index
    assert "orders" in plan.lower()  # Verify scanning orders table

    # Note: If you want to optimize foreign key lookups,
    # you need to explicitly create an index on the foreign key column
    # CREATE INDEX idx_orders_user_id ON orders(user_id)


def test_explain_complex_conditions(order_fixtures):
    """Test explain with complex condition combinations"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('150.00'),
        status='pending'
    )
    order.save()

    # Test compound conditions
    plan = (Order.query()
            .where('total_amount > ?', (Decimal('100.00'),))
            .where('status = ?', ('pending',))
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert "SCAN" in plan  # Should use table scan for non-indexed columns


def test_explain_or_conditions(order_fixtures):
    """Test explain with OR conditions"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses
    statuses = ['pending', 'paid', 'shipped']
    for status in statuses:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{status}',
            status=status
        )
        order.save()

    # Test OR conditions
    plan = (Order.query()
            .where('status = ?', ('pending',))
            .or_where('status = ?', ('paid',))
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert "SCAN" in plan  # OR typically causes full table scan


def test_explain_range_conditions(order_fixtures):
    """Test explain with range conditions"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for amount in amounts:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{amount}',
            total_amount=amount
        )
        order.save()

    # Test BETWEEN condition
    plan = (Order.query()
            .between('total_amount', Decimal('150.00'), Decimal('250.00'))
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert "SCAN" in plan  # Range query on non-indexed column uses scan

    # Test LIKE condition
    plan = (Order.query()
            .like('order_number', 'ORD-%')
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert "SCAN" in plan  # LIKE typically causes full table scan


def test_explain_in_conditions(order_fixtures):
    """Test explain with IN conditions"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses
    statuses = ['pending', 'paid', 'shipped']
    for status in statuses:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{status}',
            status=status
        )
        order.save()

    # Test IN condition
    plan = (Order.query()
            .in_list('status', ['pending', 'paid'])
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert "SCAN" in plan  # IN on non-indexed column uses scan

    # Test IN condition on primary key
    orders = Order.query().limit(2).all()
    order_ids = [o.id for o in orders]
    plan = (Order.query()
            .in_list('id', order_ids)
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert "SEARCH" in plan  # IN on indexed column might use index
