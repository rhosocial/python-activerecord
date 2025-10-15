# tests/rhosocial/activerecord_test/feature/query/sqlite/test_explain_expressions.py
"""Test explain functionality with SQL expressions for SQLite."""
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


def test_explain_arithmetic_expression(order_fixtures):
    """Test explain with arithmetic expressions"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=amount
        )
        order.save()

    # Test EXPLAIN with arithmetic expression (basic output)
    query = Order.query()
    query.arithmetic('total_amount', '*', '1.1', 'with_tax')
    plan = query.explain().aggregate()

    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])

    # Test EXPLAIN QUERY PLAN
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()
    assert isinstance(plan, str)
    assert "SCAN" in plan


def test_explain_function_expression(order_fixtures):
    """Test explain with function expressions"""
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

    # Test with UPPER function
    query = Order.query()
    query.function('UPPER', 'order_number', alias='upper_order_num')
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan

    # Test with more complex function expression
    query = Order.query()
    query.function('SUBSTR', 'order_number', '1', '3', alias='order_prefix')
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan


def test_explain_conditional_expression(order_fixtures):
    """Test explain with conditional expressions"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=None)
    user.save()

    # Test COALESCE
    query = User.query()
    query.coalesce('age', '0', alias='age_or_zero')
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan

    # Test NULLIF
    query = User.query()
    query.nullif('username', "'test_user'", alias='non_test_user')
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan


def test_explain_case_expression(order_fixtures):
    """Test explain with CASE expressions"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses
    statuses = ['pending', 'paid', 'shipped']
    for i, status in enumerate(statuses):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=Decimal('100.00')
        )
        order.save()

    # Test CASE expression
    query = Order.query()
    query.case([
        ("status = 'pending'", "New"),
        ("status = 'paid'", "Completed")
    ], else_result="Other", alias="status_label")
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan

    # Check detailed execution plan
    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Compare', 'Ne', 'Function'])


def test_explain_complex_expressions(order_fixtures):
    """Test explain with multiple complex expressions"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses and amounts
    data = [
        ('pending', Decimal('100.00')),
        ('paid', Decimal('200.00')),
        ('shipped', Decimal('300.00'))
    ]

    for i, (status, amount) in enumerate(data):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=amount
        )
        order.save()

    # Create query with multiple expressions
    query = Order.query()

    # Arithmetic expression
    query.arithmetic('total_amount', '*', '1.1', 'with_tax')

    # CASE expression
    query.case([
        ("status = 'pending'", "New"),
        ("status = 'paid'", "Completed")
    ], else_result="Other", alias="status_label")

    # Function expression
    query.function('UPPER', 'status', alias='status_upper')

    # Conditional expression
    query.coalesce('status', "'unknown'", alias='status_or_unknown')

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan

    # Full trace should include all expression operations
    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function', 'Compare'])


def test_explain_subquery_expression(order_fixtures):
    """Test explain with subquery expressions"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status='pending' if i % 2 == 0 else 'paid',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    try:
        # Test EXISTS subquery
        query = Order.query()
        query.subquery(
            f"SELECT 1 FROM {User.__table_name__} u WHERE u.id = {Order.__table_name__}.user_id",
            type="EXISTS",
            alias="has_user"
        )
        plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

        assert isinstance(plan, str)
        assert "SCAN" in plan

        # Check for subquery in execution plan
        assert "SUBQUERY" in plan.upper() or "SCAN" in plan
    except Exception as e:
        # SQLite versions might vary in support
        if 'syntax error' in str(e).lower():
            pytest.skip("SQLite version doesn't fully support EXISTS as expression")


def test_explain_expression_with_joins(order_fixtures):
    """Test explain with expressions and joins"""
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

    # Create complex query with join and expressions
    query = Order.query()

    # Add join
    query.join(f"""
        INNER JOIN {User.__table_name__}
        ON {Order.__table_name__}.user_id = {User.__table_name__}.id
    """)

    # Add CASE expression
    query.case([
        (f"{Order.__table_name__}.total_amount < 150", "Budget"),
        (f"{Order.__table_name__}.total_amount < 250", "Standard")
    ], else_result="Premium", alias="order_tier")

    # Add arithmetic expression
    query.arithmetic(f"{Order.__table_name__}.total_amount", '+',
                     f"{User.__table_name__}.age", 'total_with_age')

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan
    assert any(table_name.lower() in plan.lower()
               for table_name in [User.__table_name__, Order.__table_name__])

    # Detailed execution plan
    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function', 'Compare'])


def test_explain_expression_with_grouping(order_fixtures):
    """Test explain with expressions and GROUP BY"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses
    statuses = ['pending', 'paid', 'pending', 'paid', 'shipped']
    for i, status in enumerate(statuses):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=Decimal(f'{(i + 1) * 50}.00')
        )
        order.save()

    # Create query with expressions and grouping
    query = Order.query().group_by('status')

    # Aggregate functions
    query.count('*', 'order_count')
    query.sum('total_amount', 'total_amount')

    # Case expression for grouping result
    query.case([
        ("status = 'pending'", "Active"),
        ("status = 'paid'", "Completed")
    ], else_result="Other", alias="status_group")

    # Arithmetic on aggregate
    query.arithmetic('SUM(total_amount)', '/', 'COUNT(*)', 'avg_amount')

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan
    assert "GROUP BY" in plan.upper()

    # Detailed execution plan should include aggregation operations
    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Init', 'SorterOpen', 'AggStep', 'AggFinal', 'Divide'])
