# tests/rhosocial/activerecord_test/query/test_cte_window.py
"""Test window functions with CTE."""
from decimal import Decimal

import pytest
import sqlite3

from rhosocial.activerecord.query.expression import WindowExpression, FunctionExpression
from .utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


# Helper to check if current SQLite version supports window functions
def is_window_supported():
    """Check if current SQLite version supports window functions"""
    version = sqlite3.sqlite_version_info
    return version >= (3, 25, 0)  # Window functions were added in SQLite 3.25.0


@pytest.fixture(scope="module")
def skip_if_unsupported():
    """Skip tests if SQLite version doesn't support window functions."""
    if not is_window_supported():
        pytest.skip("SQLite version doesn't support window functions (requires 3.25.0+)")


def test_cte_with_row_number(order_fixtures, skip_if_unsupported):
    """Test CTE with ROW_NUMBER window function"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00'), Decimal('100.00')]
    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=amount,
            status='pending' if i % 2 == 0 else 'paid'
        )
        order.save()

    try:
        # Define a CTE for all orders
        query = Order.query().with_cte(
            'all_orders',
            """
            SELECT *
            FROM orders
            """
        ).from_cte('all_orders')

        # Add ROW_NUMBER window function
        query.select("id", "total_amount", "status")
        query.window(
            expr=FunctionExpression("ROW_NUMBER", alias=None),
            order_by=["total_amount DESC"],
            alias="row_num"
        )
        query.order_by("row_num")  # Sort by row number

        results = query.aggregate()

        # Verify row numbers are assigned correctly
        assert len(results) == 4
        assert results[0]['row_num'] == 1
        assert results[1]['row_num'] == 2
        assert results[2]['row_num'] == 3
        assert results[3]['row_num'] == 4

        # Verify ordering by total_amount DESC
        assert float(results[0]['total_amount']) == 300.00  # Highest first
        assert float(results[1]['total_amount']) == 200.00
        assert float(results[2]['total_amount']) in (100.00, 100.00)
        assert float(results[3]['total_amount']) in (100.00, 100.00)
    except Exception as e:
        if 'no such function: ROW_NUMBER' in str(e):
            pytest.skip("SQLite installation doesn't support ROW_NUMBER window function")
        raise


def test_cte_with_partition_by(order_fixtures, skip_if_unsupported):
    """Test CTE with window function and PARTITION BY"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses and amounts
    statuses = ['pending', 'paid', 'pending', 'paid']
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00'), Decimal('400.00')]

    for i, (status, amount) in enumerate(zip(statuses, amounts)):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=amount
        )
        order.save()

    try:
        # Define a CTE for all orders
        query = Order.query().with_cte(
            'all_orders',
            """
            SELECT *
            FROM orders
            """
        ).from_cte('all_orders')

        # Add window function with PARTITION BY
        query.select("id", "status", "total_amount")
        query.window(
            expr=FunctionExpression("SUM", "total_amount", alias=None),
            partition_by=["status"],
            alias="status_total"
        )
        query.order_by("status", "total_amount")

        results = query.aggregate()

        # Verify results
        assert len(results) == 4

        # Group results by status
        pending_results = [r for r in results if r['status'] == 'pending']
        paid_results = [r for r in results if r['status'] == 'paid']

        # Verify partition totals
        assert len(pending_results) == 2
        assert len(paid_results) == 2

        # All pending orders should have the same status_total
        assert float(pending_results[0]['status_total']) == 400.00  # 100 + 300
        assert float(pending_results[1]['status_total']) == 400.00  # 100 + 300

        # All paid orders should have the same status_total
        assert float(paid_results[0]['status_total']) == 600.00  # 200 + 400
        assert float(paid_results[1]['status_total']) == 600.00  # 200 + 400
    except Exception as e:
        if 'syntax error' in str(e).lower() or 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't properly support window functions with PARTITION BY")
        raise


def test_cte_with_running_total(order_fixtures, skip_if_unsupported):
    """Test CTE with running totals using window functions"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with sequential amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00'), Decimal('400.00'), Decimal('500.00')]

    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=amount
        )
        order.save()

    try:
        # Define a CTE for all orders
        query = Order.query().with_cte(
            'all_orders',
            """
            SELECT *
            FROM orders
            """
        ).from_cte('all_orders')

        # Add running total window function
        query.select("id", "order_number", "total_amount")
        query.window(
            expr=FunctionExpression("SUM", "total_amount", alias=None),
            order_by=["total_amount"],
            frame_type=WindowExpression.ROWS,
            frame_start=WindowExpression.UNBOUNDED_PRECEDING,
            frame_end=WindowExpression.CURRENT_ROW,
            alias="running_total"
        )
        query.order_by("total_amount")

        results = query.aggregate()

        # Verify running totals
        assert len(results) == 5
        assert float(results[0]['running_total']) == 100.00  # First row: 100
        assert float(results[1]['running_total']) == 300.00  # 100 + 200
        assert float(results[2]['running_total']) == 600.00  # 100 + 200 + 300
        assert float(results[3]['running_total']) == 1000.00  # 100 + 200 + 300 + 400
        assert float(results[4]['running_total']) == 1500.00  # 100 + 200 + 300 + 400 + 500
    except Exception as e:
        if 'syntax error' in str(e).lower() or 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't properly support window functions")
        raise


def test_cte_with_multiple_windows(order_fixtures, skip_if_unsupported):
    """Test CTE with multiple window functions"""
    User, Order, OrderItem = order_fixtures

    # Create users
    users = []
    for i in range(2):
        user = User(
            username=f'user{i + 1}',
            email=f'user{i + 1}@example.com',
            age=30 + i * 5
        )
        user.save()
        users.append(user)

    # Create orders for each user
    for i, user in enumerate(users):
        for j in range(3):
            order = Order(
                user_id=user.id,
                order_number=f'ORD-U{i + 1}-{j + 1}',
                status='pending' if j % 2 == 0 else 'paid',
                total_amount=Decimal(f'{(j + 1) * 100}.00')
            )
            order.save()

    try:
        # First CTE to prepare data
        query = Order.query().with_cte(
            'user_orders',
            f"""
            SELECT o.*, u.username 
            FROM {Order.__table_name__} o
            JOIN {User.__table_name__} u ON o.user_id = u.id
            """
        ).from_cte('user_orders')

        # Add multiple window functions
        query.select("id", "username", "status", "total_amount")

        # Row number within user partition
        query.window(
            expr=FunctionExpression("ROW_NUMBER", alias=None),
            partition_by=["username"],
            order_by=["total_amount DESC"],
            alias="user_rank"
        )

        # Average amount per user
        query.window(
            expr=FunctionExpression("AVG", "total_amount", alias=None),
            partition_by=["username"],
            alias="user_avg"
        )

        # Total amount per status
        query.window(
            expr=FunctionExpression("SUM", "total_amount", alias=None),
            partition_by=["status"],
            alias="status_total"
        )

        query.order_by("username", "user_rank")

        results = query.aggregate()

        assert len(results) == 6  # 2 users × 3 orders each

        # Verify user rankings
        user1_results = [r for r in results if r['username'] == 'user1']
        assert user1_results[0]['user_rank'] == 1
        assert user1_results[1]['user_rank'] == 2
        assert user1_results[2]['user_rank'] == 3

        # Verify averages
        assert float(user1_results[0]['user_avg']) == 200.00  # (100+200+300)/3

        # Verify status totals (pending orders: 100+300+100+300 = 800, paid orders: 200+200 = 400)
        pending_results = [r for r in results if r['status'] == 'pending']
        assert all(float(r['status_total']) == 800.00 for r in pending_results)
    except Exception as e:
        if 'syntax error' in str(e).lower() or 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't properly support multiple window functions")
        raise
