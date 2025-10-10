# tests/rhosocial/activerecord_test/feature/query/sqlite/test_explain_arithmetic.py
"""Test explain functionality with arithmetic expressions for SQLite."""
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


def test_explain_basic_arithmetic(order_fixtures):
    """Test explain with basic arithmetic operations (+, -, *, /)."""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create order with specified amount
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    # Test explain with addition
    query = Order.query()
    query.arithmetic('total_amount', '+', '50', 'increased_amount')
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan

    # Detailed explain output
    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Test explain with multiplication
    query = Order.query()
    query.arithmetic('total_amount', '*', '1.1', 'with_tax')
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan

    # Test explain with division
    query = Order.query()
    query.arithmetic('total_amount', '/', '2', 'half_amount')
    plan = query.explain().aggregate()

    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function', 'Divide'])


def test_explain_complex_arithmetic(order_fixtures):
    """Test explain with complex arithmetic expressions."""
    User, Order, OrderItem = order_fixtures

    # Create test user and order
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
        quantity=2,
        unit_price=Decimal('50.00'),
        subtotal=Decimal('100.00')
    )
    item.save()

    # Test explain with arithmetic on two columns
    query = OrderItem.query()
    query.arithmetic('quantity', '*', 'unit_price', 'calculated_subtotal')
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan

    # Test explain with complex calculation (nested operations)
    query = OrderItem.query()
    query.select("quantity")
    query.select("unit_price")
    query.select("(quantity * unit_price) * 1.1 as with_tax")

    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function', 'Multiply'])


def test_explain_arithmetic_with_aggregates(order_fixtures):
    """Test explain with arithmetic on aggregate functions."""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create multiple orders
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=amount,
            status='pending' if i % 2 == 0 else 'paid'
        )
        order.save()

    # Test explain with arithmetic on aggregate
    query = Order.query().group_by('status')
    query.arithmetic('AVG(total_amount)', '*', '1.1', 'avg_with_tax')

    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()
    assert isinstance(plan, str)
    assert "SCAN" in plan
    assert "GROUP BY" in plan.upper()

    # Detailed explain
    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Aggregate', 'Function'])

    # Test explain with arithmetic on multiple aggregates
    query = Order.query().group_by('status')
    query.arithmetic('SUM(total_amount)', '/', 'COUNT(*)', 'manual_avg')

    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()
    assert isinstance(plan, str)
    assert "SCAN" in plan
    assert "GROUP BY" in plan.upper()

    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Aggregate', 'Function', 'Divide'])


def test_explain_arithmetic_with_joins(order_fixtures):
    """Test explain with arithmetic expressions and joins."""
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

    # Test with join and arithmetic
    query = Order.query()

    # Add join
    query.join(f"""
        INNER JOIN {User.__table_name__}
        ON {Order.__table_name__}.user_id = {User.__table_name__}.id
    """)

    # Add arithmetic with columns from both tables
    query.select(f"{Order.__table_name__}.id", f"{Order.__table_name__}.total_amount", f"{User.__table_name__}.age")
    query.arithmetic(f"{Order.__table_name__}.total_amount", '+', f"{User.__table_name__}.age", 'combined_value')

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).aggregate()

    assert isinstance(plan, str)
    assert "SCAN" in plan
    assert any(table_name.lower() in plan.lower()
               for table_name in [User.__table_name__, Order.__table_name__])

    # Detailed execution plan
    plan = query.explain().aggregate()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Add', 'Function'])


def test_explain_arithmetic_with_case(order_fixtures):
    """Test explain with arithmetic and CASE expressions."""
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
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Test with CASE and arithmetic
    query = Order.query()

    # Complex expression with CASE and arithmetic
    query.select("id", "status", "total_amount")
    query.select("""
    total_amount * 
    CASE 
        WHEN status = 'pending' THEN 1.05  -- 5% tax
        WHEN status = 'paid' THEN 1.08     -- 8% tax
        ELSE 1.1                           -- 10% tax 
    END as with_tax
    """)

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).all()

    assert isinstance(plan, str)
    assert "SCAN" in plan

    # Detailed execution plan
    plan = query.explain().all()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Compare', 'Function', 'Ne'])


def test_explain_complex_arithmetic_expressions(order_fixtures):
    """Test explain with multiple arithmetic operations in one query."""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Test with multiple arithmetic expressions
    query = Order.query()

    # Add basic arithmetic
    query.arithmetic('total_amount', '*', '1.1', 'with_tax')

    # Add arithmetic on the result of another arithmetic
    query.select("id", "total_amount")
    query.select("(total_amount * 1.1) - total_amount as tax_amount")

    # Add another complex expression
    query.select("(total_amount * 1.1) + 10 as with_tax_and_fee")

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).all()

    assert isinstance(plan, str)
    assert "SCAN" in plan

    # Detailed execution plan
    plan = query.explain().all()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function', 'Multiply', 'Add', 'Subtract'])


def test_explain_arithmetic_with_subquery(order_fixtures):
    """Test explain with arithmetic expressions on subquery results."""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create multiple orders
    for i in range(5):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Test with subquery and arithmetic
    # Execute explain on raw query
    query = Order.query().select(f"""
        id, 
        total_amount,
        total_amount - (SELECT AVG(total_amount) FROM {Order.__table_name__}) as diff_from_avg,
        total_amount / (SELECT MAX(total_amount) FROM {Order.__table_name__}) as percent_of_max
    """)
    plan = query.explain(type=ExplainType.QUERYPLAN).all()

    assert isinstance(plan, str)
    assert "SCAN" in plan
    assert "SUBQUERY" in plan.upper() or "TEMP" in plan.upper()

    # Detailed execution plan
    plan = query.explain().all()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])
