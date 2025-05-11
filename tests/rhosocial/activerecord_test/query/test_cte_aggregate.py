"""Test basic aggregate functions with CTE."""
from decimal import Decimal

import pytest

from tests.rhosocial.activerecord_test.query.utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_cte_count(order_fixtures):
    """Test COUNT aggregation with CTE"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders
    statuses = ['pending', 'paid', 'shipped']
    for i, status in enumerate(statuses):
        for j in range(2):  # Create 2 orders per status
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{status}-{j}',
                status=status,
                total_amount=Decimal('100.00')
            )
            order.save()

    # Define a CTE with all orders
    query = Order.query().with_cte(
        'all_orders',
        """
        SELECT *
        FROM orders
        """
    ).from_cte('all_orders')

    # Count all orders
    count = query.count()
    assert count == 6  # 3 statuses × 2 orders each = 6 total orders

    # Define a CTE with filtered orders
    query = Order.query().with_cte(
        'pending_orders',
        """
        SELECT *
        FROM orders
        WHERE status = 'pending'
        """
    ).from_cte('pending_orders')

    # Count filtered orders
    count = query.count()
    assert count == 2  # Only pending orders

    # Define a CTE using an ActiveQuery instance with parameters
    subquery = Order.query().where('status = ?', ('paid',))
    query = Order.query().with_cte(
        'paid_orders',
        subquery
    ).from_cte('paid_orders')

    # Count with the parameterized CTE
    count = query.count()
    assert count == 2  # Only paid orders


def test_cte_sum(order_fixtures):
    """Test SUM aggregation with CTE"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders with different amounts
    statuses = ['pending', 'paid', 'shipped']
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]

    for i, status in enumerate(statuses):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{status}',
            status=status,
            total_amount=amounts[i]
        )
        order.save()

    # Define a CTE with all orders
    query = Order.query().with_cte(
        'all_orders',
        """
        SELECT *
        FROM orders
        """
    ).from_cte('all_orders')

    # Sum all order amounts
    total = query.sum('total_amount')
    assert total == Decimal('600.00')  # 100 + 200 + 300 = 600

    # Define a CTE with filtered orders
    query = Order.query().with_cte(
        'expensive_orders',
        """
        SELECT *
        FROM orders
        WHERE total_amount > 150.00
        """
    ).from_cte('expensive_orders')

    # Sum filtered orders
    total = query.sum('total_amount')
    assert total == Decimal('500.00')  # 200 + 300 = 500


def test_cte_avg_min_max(order_fixtures):
    """Test AVG, MIN, and MAX aggregations with CTE"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders with different amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00'), Decimal('400.00'), Decimal('500.00')]

    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=amount
        )
        order.save()

    # Define a CTE with all orders
    query = Order.query().with_cte(
        'all_orders',
        """
        SELECT *
        FROM orders
        """
    ).from_cte('all_orders')

    # Test AVG
    avg_amount = query.avg('total_amount')
    assert avg_amount == 300.00  # (100 + 200 + 300 + 400 + 500) / 5 = 300

    # Test MIN
    min_amount = query.min('total_amount')
    assert min_amount == Decimal('100.00')

    # Test MAX
    max_amount = query.max('total_amount')
    assert max_amount == Decimal('500.00')

    # Define a CTE with filtered orders
    query = Order.query().with_cte(
        'mid_range_orders',
        """
        SELECT *
        FROM orders
        WHERE total_amount BETWEEN 200.00 AND 400.00
        """
    ).from_cte('mid_range_orders')

    # Test aggregate functions on filtered CTE
    assert query.avg('total_amount') == 300.00  # (200 + 300 + 400) / 3 = 300
    assert query.min('total_amount') == Decimal('200.00')
    assert query.max('total_amount') == Decimal('400.00')


def test_cte_with_conditions_and_aggregates(order_fixtures):
    """Test CTE with conditions and aggregates"""
    User, Order, OrderItem = order_fixtures

    # Create test users with different ages
    ages = [25, 30, 35, 40]
    users = []

    for i, age in enumerate(ages):
        user = User(
            username=f'user{i + 1}',
            email=f'user{i + 1}@example.com',
            age=age
        )
        user.save()
        users.append(user)

    # Create test orders for each user
    for i, user in enumerate(users):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Define a CTE with user age and order amounts
    query = Order.query().with_cte(
        'user_orders',
        f"""
        SELECT o.*, u.age 
        FROM {Order.__table_name__} o
        JOIN {User.__table_name__} u ON o.user_id = u.id
        """
    ).from_cte('user_orders')

    # Create a separate query for each test case
    # Test with conditions from the CTE - for younger users
    query_young = query.clone().where('age < ?', (35,))
    avg_amount_young = query_young.avg('total_amount')
    assert avg_amount_young == 150.00  # (100 + 200) / 2 = 150

    # Test with conditions from the CTE - for older users
    query_older = query.clone().where('age >= ?', (35,))
    sum_amount_older = query_older.sum('total_amount')
    assert sum_amount_older == Decimal('700.00')  # 300 + 400 = 700