# tests/rhosocial/activerecord_test/feature/query/sqlite/test_explain_simple_aggregate.py
"""Test explain functionality with simple aggregates for SQLite."""
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


def test_explain_count(order_fixtures):
    """Test explain with COUNT aggregate"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal('100.00')
        )
        order.save()

    # Test regular EXPLAIN output (opcode sequence)
    plan = Order.query().explain().count()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test EXPLAIN QUERY PLAN
    plan = (Order.query()
            .explain(type=ExplainType.QUERYPLAN)
            .count())
    assert isinstance(plan, str)
    assert "SCAN" in plan

    # Test EXPLAIN QUERY PLAN with distinct count
    plan = (Order.query()
            .explain(type=ExplainType.QUERYPLAN)
            .count('id', distinct=True))
    assert isinstance(plan, str)
    assert "SCAN" in plan  # SQLite optimizes this to table scan


def test_explain_sum(order_fixtures):
    """Test explain with SUM aggregate"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders with different amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for amount in amounts:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{amount}',
            total_amount=amount
        )
        order.save()

    # Test regular EXPLAIN (opcode sequence)
    plan = Order.query().explain().sum('total_amount')
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test EXPLAIN QUERY PLAN with condition
    plan = (Order.query()
            .where('total_amount > ?', (Decimal('150.00'),))
            .explain(type=ExplainType.QUERYPLAN)
            .sum('total_amount'))
    assert isinstance(plan, str)
    assert "SCAN" in plan


def test_explain_avg(order_fixtures):
    """Test explain with AVG aggregate"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for amount in amounts:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{amount}',
            total_amount=amount
        )
        order.save()

    # Test regular EXPLAIN (opcode sequence)
    plan = Order.query().explain().avg('total_amount')
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test EXPLAIN QUERY PLAN
    plan = (Order.query()
            .explain(type=ExplainType.QUERYPLAN)
            .avg('total_amount'))
    assert isinstance(plan, str)
    assert "SCAN" in plan


def test_explain_min_max(order_fixtures):
    """Test explain with MIN and MAX aggregates"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for amount in amounts:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{amount}',
            total_amount=amount
        )
        order.save()

    # Test MIN with EXPLAIN (opcode sequence)
    plan = Order.query().explain().min('total_amount')
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test MAX with QUERY PLAN
    plan = (Order.query()
            .explain(type=ExplainType.QUERYPLAN)
            .max('total_amount'))
    assert isinstance(plan, str)
    assert any(op in plan.upper() for op in ['SCAN', 'SEARCH'])


def test_explain_complex_aggregates(order_fixtures):
    """Test explain with aggregate functions and complex conditions"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00'),
            status='pending' if i % 2 == 0 else 'paid'
        )
        order.save()

    # Test regular EXPLAIN (opcode sequence)
    plan = (Order.query()
            .where('total_amount > ?', (Decimal('150.00'),))
            .start_or_group()
            .where('status = ?', ('pending',))
            .or_where('status = ?', ('paid',))
            .end_or_group()
            .explain()
            .sum('total_amount'))
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test EXPLAIN QUERY PLAN
    plan = (Order.query()
            .where('total_amount > ?', (Decimal('150.00'),))
            .start_or_group()
            .where('status = ?', ('pending',))
            .or_where('status = ?', ('paid',))
            .end_or_group()
            .explain(type=ExplainType.QUERYPLAN)
            .sum('total_amount'))
    assert isinstance(plan, str)
    assert "SCAN" in plan
