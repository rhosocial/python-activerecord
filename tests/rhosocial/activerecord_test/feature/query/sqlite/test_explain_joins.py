# tests/rhosocial/activerecord_test/feature/query/sqlite/test_explain_joins.py
"""Test explain functionality with various joins for SQLite."""
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


def test_explain_inner_join(order_fixtures):
    """Test explain with INNER JOIN"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    # Test regular EXPLAIN (opcode sequence)
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .explain()
            .all())
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test EXPLAIN QUERY PLAN
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert any(op in plan.upper() for op in ['SCAN', 'SEARCH'])


def test_explain_left_join(order_fixtures):
    """Test explain with LEFT JOIN"""
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

    # Test regular EXPLAIN (opcode sequence)
    plan = (Order.query()
            .join(f"""
                LEFT JOIN {OrderItem.__table_name__}
                ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
            """)
            .explain()
            .all())
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test EXPLAIN QUERY PLAN
    plan = (Order.query()
            .join(f"""
                LEFT JOIN {OrderItem.__table_name__}
                ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
            """)
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert any(op in plan.upper() for op in ['SCAN', 'SEARCH'])


def test_explain_multiple_joins(order_fixtures):
    """Test explain with multiple JOINs"""
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

    item = OrderItem(
        order_id=order.id,
        product_name='Test Product',
        quantity=1,
        unit_price=Decimal('100.00'),
        subtotal=Decimal('100.00')
    )
    item.save()

    # Test regular EXPLAIN (opcode sequence)
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .join(f"""
                LEFT JOIN {OrderItem.__table_name__}
                ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
            """)
            .explain()
            .all())
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test EXPLAIN QUERY PLAN
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .join(f"""
                LEFT JOIN {OrderItem.__table_name__}
                ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
            """)
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert any(op in plan.upper() for op in ['SCAN', 'SEARCH'])


def test_explain_join_with_conditions(order_fixtures):
    """Test explain with JOINs and WHERE conditions"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00'),
        status='pending'
    )
    order.save()

    # Test regular EXPLAIN (opcode sequence)
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .where(f'{Order.__table_name__}.status = ?', ('pending',))
            .explain()
            .all())
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test EXPLAIN QUERY PLAN
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .where(f'{Order.__table_name__}.status = ?', ('pending',))
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert any(op in plan.upper() for op in ['SCAN', 'SEARCH'])


def test_explain_join_with_aggregates(order_fixtures):
    """Test explain with JOINs and aggregate functions"""
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

    # Test regular EXPLAIN (opcode sequence)
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .select(f"COUNT({Order.__table_name__}.id) as order_count")
            .explain()
            .all())
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test EXPLAIN QUERY PLAN
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .select(f"COUNT({Order.__table_name__}.id) as order_count")
            .explain(type=ExplainType.QUERYPLAN)
            .all())
    assert isinstance(plan, str)
    assert any(op in plan.upper() for op in ['SCAN', 'SEARCH'])
