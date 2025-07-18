# tests/rhosocial/activerecord_test/query/test_cte_aggregate.py
"""Test advanced aggregate functions with CTE."""
from decimal import Decimal

from .utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_cte_group_by(order_fixtures):
    """Test GROUP BY with CTE"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders with different statuses
    statuses = ['pending', 'paid', 'shipped']
    for i, status in enumerate(statuses):
        for j in range(2):  # Create 2 orders per status
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{status}-{j}',
                status=status,
                total_amount=Decimal(f'{(i + 1) * 100}.00')
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

    # Group by status and count
    query.group_by('status')
    query.count('*', 'order_count')
    results = query.aggregate()

    assert len(results) == 3  # Three different statuses

    # Create a status -> count mapping
    status_counts = {r['status']: r['order_count'] for r in results}
    assert status_counts['pending'] == 2
    assert status_counts['paid'] == 2
    assert status_counts['shipped'] == 2


def test_cte_group_by_with_multiple_aggregates(order_fixtures):
    """Test GROUP BY with multiple aggregates using CTE"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders with different statuses and amounts
    statuses = ['pending', 'paid', 'shipped']
    for i, status in enumerate(statuses):
        for j in range(2):
            # Vary amounts: first order 100*i, second 150*i
            amount = Decimal(f'{(i + 1) * (100 if j == 0 else 150)}.00')
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{status}-{j}',
                status=status,
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

    # Group by status with multiple aggregates
    query.group_by('status')
    query.count('*', 'order_count')
    query.sum('total_amount', 'total_amount')
    query.avg('total_amount', 'avg_amount')
    query.min('total_amount', 'min_amount')
    query.max('total_amount', 'max_amount')

    # Order by status for consistent results
    query.order_by('status')

    results = query.aggregate()

    assert len(results) == 3  # Three different statuses

    # Verify results for each status
    pending = results[1]  # Assuming the second result is 'pending'
    assert pending['status'] == 'pending'
    assert pending['order_count'] == 2
    assert pending['total_amount'] == Decimal('250.00')  # 100 + 150 = 250
    assert float(pending['avg_amount']) == 125.00  # (100 + 150) / 2 = 125
    assert pending['min_amount'] == Decimal('100.00')
    assert pending['max_amount'] == Decimal('150.00')


def test_cte_having(order_fixtures):
    """Test GROUP BY with HAVING clause using CTE"""
    User, Order, OrderItem = order_fixtures

    # Create test users
    users = []
    for i in range(3):
        user = User(
            username=f'user{i + 1}',
            email=f'user{i + 1}@example.com',
            age=25 + i * 5
        )
        user.save()
        users.append(user)

    # Create test orders with different statuses and amounts
    statuses = ['pending', 'paid', 'shipped']
    for i, user in enumerate(users):
        for status in statuses:
            # First user: 100, Second: 200, Third: 300
            amount = Decimal(f'{(i + 1) * 100}.00')
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{user.id}-{status}',
                status=status,
                total_amount=amount
            )
            order.save()

    # Define a CTE for all orders with user info
    query = Order.query().with_cte(
        'user_orders',
        f"""
        SELECT o.*, u.username
        FROM {Order.__table_name__} o
        JOIN {User.__table_name__} u ON o.user_id = u.id
        """
    ).from_cte('user_orders')

    # Group by username with HAVING to filter groups
    query.group_by('username')
    query.sum('total_amount', 'total_spent')
    query.having('SUM(total_amount) > ?', (Decimal('500.00'),))

    results = query.aggregate()

    # Only users who spent more than 500 should be included
    assert len(results) == 2  # user2 (600) and user3 (900)

    # Sort by username for consistent testing
    results.sort(key=lambda r: r['username'])

    assert results[0]['username'] == 'user2'
    assert results[0]['total_spent'] == Decimal('600.00')  # 3 orders × 200 = 600

    assert results[1]['username'] == 'user3'
    assert results[1]['total_spent'] == Decimal('900.00')  # 3 orders × 300 = 900


def test_cte_nested_aggregates(order_fixtures):
    """Test nested aggregates using CTEs"""
    User, Order, OrderItem = order_fixtures

    # Create test users
    users = []
    for i in range(3):
        user = User(
            username=f'user{i + 1}',
            email=f'user{i + 1}@example.com',
            age=25 + i * 5
        )
        user.save()
        users.append(user)

    # Create orders with different statuses and amounts
    statuses = ['pending', 'paid', 'shipped']
    for i, user in enumerate(users):
        for j, status in enumerate(statuses):
            amount = Decimal(f'{(i + 1) * (j + 1) * 50}.00')  # Varies by user and status
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{user.id}-{status}',
                status=status,
                total_amount=amount
            )
            order.save()

    # First CTE to calculate averages by status
    query = Order.query().with_cte(
        'status_averages',
        """
        SELECT status, AVG(total_amount) as avg_amount
        FROM orders
        GROUP BY status
        """
    )

    # Second CTE to find statuses with averages above 150
    query.with_cte(
        'high_value_statuses',
        """
        SELECT status, avg_amount
        FROM status_averages
        WHERE avg_amount > 150.00
        """
    ).from_cte('high_value_statuses')

    # Execute the query
    results = query.aggregate()

    # Calculate expected results:
    # pending: (50 + 100 + 150) / 3 = 100
    # paid: (100 + 200 + 300) / 3 = 200
    # shipped: (150 + 300 + 450) / 3 = 300
    # So 'paid' and 'shipped' should be in the results

    assert len(results) == 2
    statuses = [r["status"] for r in results]
    assert 'paid' in statuses
    assert 'shipped' in statuses
    assert 'pending' not in statuses
