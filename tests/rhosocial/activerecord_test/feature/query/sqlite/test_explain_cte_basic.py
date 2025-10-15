# tests/rhosocial/activerecord_test/feature/query/sqlite/test_explain_cte_basic.py
"""Test explain functionality with basic CTE for SQLite."""
from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from rhosocial.activerecord.testsuite.feature.query.conftest import (
    order_fixtures,
    blog_fixtures,
    json_user_fixture,
    tree_fixtures,
    extended_order_fixtures,
    combined_fixtures,
)


def test_explain_basic_cte(order_fixtures):
    """Test basic EXPLAIN output with CTE"""
    # This test is designed for SQLite-specific functionality
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

    # Test EXPLAIN with basic CTE
    query = Order.query().with_cte(
        "active_orders",
        "SELECT * FROM orders WHERE user_id > 0"
    ).from_cte("active_orders")

    # Default EXPLAIN should output opcode trace
    plan = query.explain().all()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])
    # assert "WITH" in plan.upper()

    # Test EXPLAIN QUERY PLAN
    plan = query.explain(type=ExplainType.QUERYPLAN).all()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['SCAN', 'SEARCH'])
    # assert "CTE" in plan.upper() or "WITH" in plan.upper()


def test_explain_cte_with_parameters(order_fixtures):
    """Test EXPLAIN with parameterized CTE"""
    # This test is designed for SQLite-specific functionality
    User, Order, OrderItem = order_fixtures

    # Create test user and orders
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Create subquery with parameters
    subquery = Order.query().where('total_amount > ?', (Decimal('150.00'),))

    # Test EXPLAIN with CTE using the subquery
    query = Order.query().with_cte(
        "expensive_orders",
        subquery
    ).from_cte("expensive_orders")

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).all()

    assert isinstance(plan, str)
    assert "SCAN" in plan or "SEARCH" in plan
    # assert "expensive_orders" in plan.lower() or "WITH" in plan.upper()


def test_explain_cte_format_options(order_fixtures):
    """Test EXPLAIN format options with CTE"""
    # This test is designed for SQLite-specific functionality
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

    # Define a CTE query
    query = Order.query().with_cte(
        "all_orders",
        "SELECT * FROM orders"
    ).from_cte("all_orders")

    # Test valid format (TEXT is the only supported format in SQLite)
    plan = query.explain(format=ExplainFormat.TEXT).all()
    assert isinstance(plan, str)
    # assert "WITH" in plan.upper()

    # Test with unsupported format
    try:
        query.explain(format=ExplainFormat.JSON).all()
        assert False, "Should raise exception for unsupported format"
    except ValueError as e:
        assert "format" in str(e).lower()


def test_explain_cte_with_conditions(order_fixtures):
    """Test EXPLAIN with CTE and WHERE conditions"""
    # This test is designed for SQLite-specific functionality
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status='pending' if i % 2 == 0 else 'paid',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Test CTE with additional WHERE conditions
    query = Order.query().with_cte(
        "all_orders",
        "SELECT * FROM orders"
    ).from_cte("all_orders")

    # Add WHERE conditions to main query
    query.where('status = ?', ('pending',))

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).all()

    assert isinstance(plan, str)
    assert "SCAN" in plan
    # assert "all_orders" in plan.lower() or "WITH" in plan.upper()
    assert "DETAIL" in plan.upper()
