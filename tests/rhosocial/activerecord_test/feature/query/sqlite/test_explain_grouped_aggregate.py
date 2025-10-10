# tests/rhosocial/activerecord_test/feature/query/sqlite/test_explain_grouped_aggregate.py
"""Test explain functionality with grouped aggregates for SQLite."""
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


def test_explain_basic_group_by(order_fixtures):
    """Test explain with basic GROUP BY"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    statuses = ['pending', 'paid']
    for status in statuses:
        for i in range(2):
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{status}-{i}',
                status=status,
                total_amount=Decimal('100.00')
            )
            order.save()

    # Test EXPLAIN (opcode sequence)
    plan = (Order.query()
            .group_by('status')
            .count('*', 'count')
            .explain()
            .aggregate())
    assert isinstance(plan, str)
    # Should see opcodes for creating and using temporary B-Tree
    assert any(op in plan for op in ['OpenEphemeral', 'SorterOpen'])

    # Test EXPLAIN QUERY PLAN
    plan = (Order.query()
            .group_by('status')
            .count('*', 'count')
            .explain(type=ExplainType.QUERYPLAN)
            .aggregate())
    assert isinstance(plan, str)
    # Should see scanning and use of temporary tables
    assert "SCAN" in plan
    assert "GROUP BY" in plan.upper()


def test_explain_aggregate_with_having(order_fixtures):
    """Test explain with GROUP BY and HAVING"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders with different statuses
    statuses = ['pending', 'paid', 'shipped']
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]

    for status in statuses:
        for amount in amounts:
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{status}-{amount}',
                status=status,
                total_amount=amount
            )
            order.save()

    # Test explain with more complex HAVING condition
    plan = (Order.query()
            .group_by('status')
            .having('COUNT(*) > ? AND SUM(total_amount) > ?',
                    (2, Decimal('500.00')))
            .explain(type=ExplainType.QUERYPLAN)
            .aggregate())
    assert isinstance(plan, str)
    assert "SCAN" in plan
    assert "GROUP BY" in plan.upper()
    # Note: HAVING might be optimized into the GROUP BY B-TREE operation
    assert "TEMP B-TREE" in plan.upper()


def test_explain_multiple_aggregates(order_fixtures):
    """Test explain with multiple aggregate functions"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i}',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Test explain with multiple aggregates
    plan = (Order.query()
            .group_by('status')
            .count('*', 'count')
            .sum('total_amount', 'total')
            .avg('total_amount', 'average')
            .explain()
            .aggregate())
    assert isinstance(plan, str)
    # Should see multiple aggregate function operations
    assert any(op in plan for op in ['Aggregate', 'Function', 'Column'])


def test_explain_multiple_group_by(order_fixtures):
    """Test explain with multiple GROUP BY columns"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    for i in range(2):
        user = User(
            username=f'user{i}',
            email=f'user{i}@example.com',
            age=30 + i
        )
        user.save()

        for status in ['pending', 'paid']:
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{i}-{status}',
                status=status,
                total_amount=Decimal('100.00')
            )
            order.save()

    # Test multiple grouping columns
    plan = (Order.query()
            .group_by('user_id', 'status')
            .count('*', 'count')
            .explain(type=ExplainType.QUERYPLAN)
            .aggregate())
    assert isinstance(plan, str)
    assert "SCAN" in plan
    assert "GROUP BY" in plan.upper()
    # Multiple columns in GROUP BY create more complex sort operations
    assert "COMPOUND" in plan.upper() or "TEMP" in plan.upper()


def test_explain_aggregate_with_joins(order_fixtures):
    """Test explain with aggregates and joins"""
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

    # Test explain with join and aggregates
    plan = (Order.query()
            .join(f"""
                INNER JOIN {User.__table_name__}
                ON {Order.__table_name__}.user_id = {User.__table_name__}.id
            """)
            .group_by(f'{User.__table_name__}.username')
            .count('*', 'order_count')
            .explain(type=ExplainType.QUERYPLAN)
            .aggregate())
    assert isinstance(plan, str)
    assert "SCAN" in plan
    assert any(table.lower() in plan.lower()
               for table in [Order.__table_name__, User.__table_name__])
    assert "GROUP BY" in plan.upper()


def test_explain_aggregate_with_subqueries(order_fixtures):
    """Test explain with aggregates containing subqueries"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i}',
            status='pending',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Test with subquery in HAVING
    plan = (Order.query()
            .group_by('status')
            .having('COUNT(*) > (SELECT COUNT(*)/2 FROM orders)')
            .explain(type=ExplainType.QUERYPLAN)
            .aggregate())
    assert isinstance(plan, str)
    assert "SCAN" in plan
    assert "GROUP BY" in plan.upper()
    assert "SUBQUERY" in plan.upper() or "TEMP" in plan.upper()
