# tests/rhosocial/activerecord_test/query/sqlite/test_explain_basic.py
"""Test basic explain functionality for SQLite."""
from decimal import Decimal

import pytest

from src.rhosocial.activerecord.backend.dialect import ExplainType, ExplainFormat
from ..utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()

def test_basic_explain(order_fixtures, request):
    """Test basic EXPLAIN output"""
    if 'sqlite' not in request.node.name:
        pytest.skip("This test is only applicable to SQLite")

    User, Order, OrderItem = order_fixtures

    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    # Default EXPLAIN should output opcode trace
    plan = Order.query().explain().all()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

def test_query_plan_explain(order_fixtures, request):
    """Test EXPLAIN QUERY PLAN output"""
    if 'sqlite' not in request.node.name:
        pytest.skip("This test is only applicable to SQLite")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # QUERY PLAN format should output readable plan
    plan = Order.query().explain(type=ExplainType.QUERYPLAN).all()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['SCAN', 'SEARCH'])

def test_explain_with_options(order_fixtures, request):
    """Test explain with different options"""
    if 'sqlite' not in request.node.name:
        pytest.skip("This test is only applicable to SQLite")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # With default format (TEXT)
    plan = Order.query().explain(format=ExplainFormat.TEXT).all()
    assert isinstance(plan, str)

    # With default type (BASIC)
    plan = Order.query().explain(type=ExplainType.BASIC).all()
    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])

    # Non-functional options should be silently ignored
    plan = Order.query().explain(
        buffers=True,  # Should be ignored
        costs=True,  # Should be ignored
        timing=True  # Should be ignored
    ).all()
    assert isinstance(plan, str)

def test_explain_query_building(order_fixtures, request):
    """Test explain with query building methods"""
    if 'sqlite' not in request.node.name:
        pytest.skip("This test is only applicable to SQLite")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Query can be built before explain
    query = Order.query().where('id > ?', (0,))
    plan = query.explain().all()
    assert isinstance(plan, str)

    # Explain can be added before other methods
    plan = Order.query().explain().where('id > ?', (0,)).all()
    assert isinstance(plan, str)


def test_invalid_explain_options(order_fixtures, request):
    """Test invalid explain options"""
    if 'sqlite' not in request.node.name:
        pytest.skip("This test is only applicable to SQLite")

    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Only TEXT format is supported
    try:
        Order.query().explain(format=ExplainFormat.JSON).all()
        assert False, "Should raise ValueError for unsupported format"
    except ValueError as e:
        assert "format" in str(e).lower()

    try:
        Order.query().explain(format=ExplainFormat.XML).all()
        assert False, "Should raise ValueError for unsupported format"
    except ValueError as e:
        assert "format" in str(e).lower()

    try:
        Order.query().explain(format=ExplainFormat.YAML).all()
        assert False, "Should raise ValueError for unsupported format"
    except ValueError as e:
        assert "format" in str(e).lower()