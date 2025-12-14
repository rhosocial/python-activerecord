# tests/rhosocial/activerecord_test/feature/query/sqlite/test_datetime_functions.py
"""SQLite-specific datetime function tests."""
import re
from decimal import Decimal
import pytest


def test_sqlite_datetime_functions(order_fixtures):
    """Test SQLite-specific datetime functions."""
    from rhosocial.activerecord.base.expression import FunctionExpression, Column
    
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders with specific timestamps if we have updated_at field
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    try:
        # Test STRFTIME function (SQLite datetime function)
        query = Order.query().where('id = ?', (order.id,))
        date_expr = FunctionExpression('STRFTIME', '%Y-%m-%d', Column('created_at'))
        query.select_expr(date_expr, alias='order_date')
        results = query.aggregate()[0]

        assert 'order_date' in results
        # Convert to string for consistent comparison across different database drivers
        order_date_str = str(results['order_date'])
        # Verify it's a properly formatted date
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', order_date_str) is not None

        # Test DATE function
        query = Order.query().where('id = ?', (order.id,))
        date_only_expr = FunctionExpression('DATE', Column('created_at'))
        query.select_expr(date_only_expr, alias='order_date_only')
        results = query.aggregate()[0]

        assert 'order_date_only' in results
        # Convert to string for consistent comparison across different database drivers
        order_date_only_str = str(results['order_date_only'])
        # Should be in YYYY-MM-DD format
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', order_date_only_str) is not None

        # Test current date/time functions
        query = Order.query().where('id = ?', (order.id,))
        current_date_expr = FunctionExpression('DATE', 'now')
        query.select_expr(current_date_expr, alias='current_date')
        results = query.aggregate()[0]

        # Convert to string for consistent comparison across different database drivers
        current_date_str = str(results['current_date'])
        # SQLite's DATE('now') returns the date in UTC
        # So we need to get today's date in UTC for comparison
        import datetime as dt
        today_utc = dt.datetime.now(dt.timezone.utc).date().strftime('%Y-%m-%d')
        assert current_date_str == today_utc

    except Exception as e:
        # Some SQLite versions might not fully support all datetime functions
        # Just make sure we can execute the query
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't fully support the tested datetime functions")
        elif 'no such column' in str(e).lower() and 'created_at' in str(e).lower():
            pytest.skip("Order model doesn't have created_at column")
        raise