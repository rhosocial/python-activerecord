# tests/rhosocial/activerecord_test/query/test_function_expressions.py
"""Test function expression functionality in ActiveQuery."""
import re
from decimal import Decimal

import pytest

from rhosocial.activerecord.query.expression import FunctionExpression
from .utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_string_functions(order_fixtures):
    """Test string manipulation functions."""
    User, Order, OrderItem = order_fixtures

    # Create test users with various names
    users_data = [
        {
            "username": "JOHN_DOE",
            "email": "john@example.com",
            "age": 30
        },
        {
            "username": "jane_smith",
            "email": "jane@example.com",
            "age": 25
        },
        {
            "username": "  mike_brown  ",
            "email": "mike@example.com",
            "age": 35
        }
    ]

    for data in users_data:
        user = User(**data)
        user.save()

    # Test UPPER function
    query = User.query().where('username = ?', ('jane_smith',))
    query.function('UPPER', 'username', alias='upper_name')
    results = query.aggregate()[0]

    assert 'upper_name' in results
    assert results['upper_name'] == 'JANE_SMITH'

    # Test LOWER function
    query = User.query().where('username = ?', ('JOHN_DOE',))
    query.function('LOWER', 'username', alias='lower_name')
    results = query.aggregate()[0]

    assert 'lower_name' in results
    assert results['lower_name'] == 'john_doe'

    # Test TRIM function
    query = User.query().where('username LIKE ?', ('%mike%',))
    query.function('TRIM', 'username', alias='trimmed_name')
    results = query.aggregate()[0]

    assert 'trimmed_name' in results
    assert results['trimmed_name'] == 'mike_brown'

    # Test LENGTH function
    query = User.query().where('username = ?', ('jane_smith',))
    query.function('LENGTH', 'username', alias='name_length')
    results = query.aggregate()[0]

    assert 'name_length' in results
    assert results['name_length'] == 10

    # Test SUBSTR function
    query = User.query().where('username = ?', ('JOHN_DOE',))
    query.function('SUBSTR', 'username', '1', '4', alias='name_substring')
    results = query.aggregate()[0]

    assert 'name_substring' in results
    assert results['name_substring'] == 'JOHN'


def test_numeric_functions(order_fixtures):
    """Test numeric functions."""
    User, Order, OrderItem = order_fixtures

    # Create test orders with various amounts
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with positive and negative amounts
    amounts = [Decimal('100.50'), Decimal('-75.25'), Decimal('250.75'), Decimal('-125.30')]
    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=amount
        )
        order.save()

    # Test ABS function
    query = Order.query().where('total_amount < ?', (0,))
    query.select_expr(FunctionExpression('ABS', 'total_amount', alias='absolute_amount'))
    # query.function('ABS', 'total_amount', alias='absolute_amount')
    query.select("*")
    results = query.aggregate()

    assert len(results) == 2  # Two negative values
    for result in results:
        assert 'absolute_amount' in result
        absolute = float(result['absolute_amount'])
        original = float(result['total_amount'])
        assert absolute > 0  # Absolute value should be positive
        assert abs(absolute + original) < 0.01  # Original value was negative, so abs = -original

    # Test ROUND function
    query = Order.query().where('total_amount > ?', (0,))
    # query.function('ROUND', 'total_amount', '0', alias='rounded_amount')
    query.select_expr(FunctionExpression('ROUND', 'total_amount', '0', alias='rounded_amount'))
    query.select("*")
    results = query.aggregate()

    for result in results:
        assert 'rounded_amount' in result
        # Check if it's correctly rounded to nearest integer
        original = float(result['total_amount'])
        rounded = float(result['rounded_amount'])
        import math
        assert abs(rounded - math.floor(original + 0.5)) < 0.01

    # Test MAX aggregate function
    query = Order.query()
    query.function('MAX', 'total_amount', alias='max_amount')
    results = query.aggregate()[0]

    assert 'max_amount' in results
    assert float(results['max_amount']) == 250.75  # Highest amount

    # Test MIN aggregate function
    query = Order.query()
    query.function('MIN', 'total_amount', alias='min_amount')
    results = query.aggregate()[0]

    assert 'min_amount' in results
    assert float(results['min_amount']) == -125.30  # Lowest amount


def test_datetime_functions(order_fixtures, request):
    """Test date and time functions."""
    if 'mysql' in request.node.name:
        pytest.skip("This test is not applicable to MySQL")
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
        query.function('STRFTIME', "'%Y-%m-%d'", 'created_at', alias='order_date')
        results = query.aggregate()[0]

        assert 'order_date' in results
        # Verify it's a properly formatted date
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', results['order_date']) is not None

        # Test DATE function
        query = Order.query().where('id = ?', (order.id,))
        query.function('DATE', 'created_at', alias='order_date_only')
        results = query.aggregate()[0]

        assert 'order_date_only' in results
        # Should be in YYYY-MM-DD format
        assert re.match(r'^\d{4}-\d{2}-\d{2}$', results['order_date_only']) is not None

        # Test current date/time functions
        query = Order.query().where('id = ?', (order.id,))
        query.function('DATE', "'now'", alias='current_date')
        results = query.aggregate()[0]

        assert 'current_date' in results
        # SQLite's DATE('now') returns the date in UTC
        # So we need to get today's date in UTC for comparison
        import datetime as dt
        today_utc = dt.datetime.now(dt.timezone.utc).date().strftime('%Y-%m-%d')
        assert results['current_date'] == today_utc
    except Exception as e:
        # Some SQLite versions might not fully support all datetime functions
        # Just make sure we can execute the query
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't fully support the tested datetime functions")
        elif 'no such column' in str(e).lower() and 'created_at' in str(e).lower():
            pytest.skip("Order model doesn't have created_at column")
        raise


def test_conditional_functions(order_fixtures):
    """Test conditional functions like COALESCE, NULLIF."""
    User, Order, OrderItem = order_fixtures

    # Create test users with NULL and non-NULL values
    users_data = [
        {
            "username": "user1",
            "email": "user1@example.com",
            "age": None  # NULL age
        },
        {
            "username": "user2",
            "email": "user2@example.com",
            "age": 0  # Zero age (for NULLIF testing)
        },
        {
            "username": "user3",
            "email": "user3@example.com",
            "age": 30  # Regular age
        }
    ]

    for data in users_data:
        user = User(**data)
        user.save()

    # Test COALESCE function
    query = User.query()
    query.function('COALESCE', 'age', '25', alias='age_or_default')
    query.order_by('username')
    results = query.aggregate()

    assert len(results) == 3

    # First user has NULL age, should get default
    assert results[0]['age_or_default'] == 25
    # Second user has 0 age, should NOT get default
    assert results[1]['age_or_default'] == 0
    # Third user has normal age, should get that
    assert results[2]['age_or_default'] == 30

    # Test NULLIF function
    query = User.query()
    query.function('NULLIF', 'age', '0', alias='non_zero_age')
    query.order_by('username')
    results = query.aggregate()

    assert len(results) == 3

    # First user has NULL age, should stay NULL
    assert results[0]['non_zero_age'] is None
    # Second user has 0 age, should become NULL
    assert results[1]['non_zero_age'] is None
    # Third user has normal age, should stay normal
    assert results[2]['non_zero_age'] == 30


def test_aggregate_functions(order_fixtures):
    """Test aggregate functions."""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create multiple orders with varying amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00'), Decimal('400.00'), Decimal('500.00')]
    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=amount,
            status='pending' if i % 2 == 0 else 'paid'
        )
        order.save()

    # Test COUNT function
    query = Order.query()
    query.function('COUNT', '*', alias='order_count')
    results = query.aggregate()[0]

    assert 'order_count' in results
    assert results['order_count'] == 5

    # Test COUNT DISTINCT
    query = Order.query()
    query.function('COUNT', 'DISTINCT status', alias='status_count')
    results = query.aggregate()[0]

    assert 'status_count' in results
    assert results['status_count'] == 2  # pending and paid

    # Test SUM function
    query = Order.query()
    query.function('SUM', 'total_amount', alias='total_sum')
    results = query.aggregate()[0]

    assert 'total_sum' in results
    assert float(results['total_sum']) == 1500.00  # Sum of all order amounts

    # Test AVG function
    query = Order.query()
    query.function('AVG', 'total_amount', alias='avg_amount')
    results = query.aggregate()[0]

    assert 'avg_amount' in results
    assert abs(float(results['avg_amount']) - 300.00) < 0.01  # Average is 300

    # Test GROUP BY with aggregate functions
    query = Order.query().group_by('status')
    query.function('COUNT', '*', alias='status_count')
    query.function('SUM', 'total_amount', alias='status_total')
    query.function('AVG', 'total_amount', alias='status_avg')
    results = query.aggregate()

    assert len(results) == 2  # Two statuses

    # Create mapping for easy verification
    status_results = {r['status']: r for r in results}

    # Verify each status group
    for status in ['pending', 'paid']:
        assert status in status_results
        assert 'status_count' in status_results[status]
        assert 'status_total' in status_results[status]
        assert 'status_avg' in status_results[status]


def test_nested_functions(order_fixtures):
    """Test nested function calls."""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('123.45')
    )
    order.save()

    # In SQL, function nesting is usually done as a raw expression
    # since our API doesn't directly support nested function calls
    query = Order.query().where('id = ?', (order.id,))
    query.select("ROUND(ABS(total_amount), 0) as rounded_abs_amount")
    results = query.aggregate()[0]

    assert 'rounded_abs_amount' in results
    assert float(results['rounded_abs_amount']) == 123.0  # Rounded down from 123.45

    # Test more complex nested functions
    query = Order.query().where('id = ?', (order.id,))
    query.select("LENGTH(UPPER(order_number)) as upper_length")
    results = query.aggregate()[0]

    assert 'upper_length' in results
    assert results['upper_length'] == 7  # Length of 'ORD-001'


def test_function_with_joins(order_fixtures):
    """Test functions with joined tables."""
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

    # Test functions with JOINs
    query = Order.query()
    query.join(f"""
        INNER JOIN {User.__table_name__}
        ON {Order.__table_name__}.user_id = {User.__table_name__}.id
    """)

    # Function on joined column
    query.select(f"{Order.__table_name__}.id", f"{Order.__table_name__}.order_number")
    query.function('UPPER', f"{User.__table_name__}.username", alias='upper_username')

    results = query.aggregate()

    assert len(results) == 1
    assert 'upper_username' in results[0]
    assert results[0]['upper_username'] == 'TEST_USER'


def test_function_with_conditions(order_fixtures):
    """Test functions in WHERE clauses."""
    User, Order, OrderItem = order_fixtures

    # Create test data
    users_data = [
        {
            "username": "john_smith",
            "email": "john@example.com",
            "age": 30
        },
        {
            "username": "JANE_DOE",
            "email": "jane@example.com",
            "age": 25
        }
    ]

    for data in users_data:
        user = User(**data)
        user.save()

    # Test function in WHERE clause
    query = User.query()
    query.where("LOWER(username) = ?", ('john_smith',))
    results = query.aggregate()

    assert len(results) == 1
    assert results[0]['username'] == 'john_smith'

    # Test another function in WHERE
    query = User.query()
    query.where("UPPER(username) = ?", ('JANE_DOE',))
    results = query.aggregate()

    assert len(results) == 1
    assert results[0]['username'] == 'JANE_DOE'

    # Test with function in WHERE and SELECT
    query = User.query()
    query.where("LENGTH(username) >= ?", (8,))
    query.function('UPPER', 'username', alias='upper_name')
    # query.select("*")
    results = query.aggregate()

    assert len(results) == 2  # Both usernames are longer than 8 chars
    assert 'upper_name' in results[0]
    assert results[0]['upper_name'] in ['JOHN_SMITH', 'JANE_DOE']
    assert results[1]['upper_name'] in ['JOHN_SMITH', 'JANE_DOE']
