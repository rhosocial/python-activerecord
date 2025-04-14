"""Test CASE expression functionality in ActiveQuery."""
import logging
from decimal import Decimal

import pytest

from src.rhosocial.activerecord.query.expression import CaseExpression
from .utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_simple_case_when(order_fixtures):
    """Test simple CASE WHEN expressions with aggregate query."""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses
    statuses = ['pending', 'paid', 'shipped', 'cancelled']
    for i, status in enumerate(statuses):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=Decimal('100.00')
        )
        order.save()

    # Test simple case expression using aggregate query with id as group
    query = Order.query().select("id", "status").group_by("id")
    query.case([
        ("status = 'pending'", "New"),
        ("status = 'paid'", "Completed"),
        ("status = 'shipped'", "Delivered")
    ], else_result="Other", alias="status_label")

    # Order results for predictable testing
    query.order_by("id")
    results = query.aggregate()

    # Verify results
    assert len(results) == 4

    # Check that both original columns and the case expression are present
    assert 'id' in results[0], "Original 'id' column is missing from result"
    assert 'status' in results[0], "Original 'status' column is missing from result"
    assert 'status_label' in results[0], "Case expression 'status_label' is missing from result"

    status_map = {
        'pending': 'New',
        'paid': 'Completed',
        'shipped': 'Delivered',
        'cancelled': 'Other'  # Uses ELSE clause
    }

    for result in results:
        assert result['status_label'] == status_map[result['status']], \
            f"Expected {status_map[result['status']]} for status {result['status']}, got {result['status_label']}"


def test_case_with_aggregates(order_fixtures):
    """Test CASE expression with aggregate functions."""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses and amounts
    data = [
        ('pending', Decimal('100.00')),
        ('pending', Decimal('200.00')),
        ('paid', Decimal('150.00')),
        ('paid', Decimal('300.00')),
        ('shipped', Decimal('250.00'))
    ]

    for i, (status, amount) in enumerate(data):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=amount
        )
        order.save()

    # Test case with aggregates
    query = Order.query().group_by("status")

    # Count all orders by status
    query.count("*", "order_count")

    # Case to categorize statuses
    query.case([
        ("status = 'pending'", "Not Processed"),
        ("status = 'paid'", "Processing")
    ], else_result="Completed", alias="status_category")

    # Sum by case condition
    query.select('status')

    # Sum orders that are pending or paid
    query.select("SUM(CASE WHEN status IN ('pending', 'paid') THEN total_amount ELSE 0 END) as active_amount")

    # Execute query
    query.order_by("status")
    results = query.aggregate()

    # Verify results
    assert len(results) == 3  # Three status categories

    status_categories = {
        'pending': 'Not Processed',
        'paid': 'Processing',
        'shipped': 'Completed'
    }

    # Expected counts
    counts = {
        'pending': 2,
        'paid': 2,
        'shipped': 1
    }

    for result in results:
        status = result['status']
        assert result['status_category'] == status_categories[status]
        assert result['order_count'] == counts[status]


def test_nested_case_expressions(order_fixtures):
    """Test nested CASE expressions with aggregate query."""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses and amounts
    data = [
        ('pending', Decimal('50.00')),  # Low value, pending
        ('pending', Decimal('300.00')),  # High value, pending
        ('paid', Decimal('75.00')),  # Low value, paid
        ('paid', Decimal('500.00')),  # High value, paid
        ('shipped', Decimal('100.00'))  # Regular value, shipped
    ]

    for i, (status, amount) in enumerate(data):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=amount
        )
        order.save()

    # Test with nested conditions using SQL CASE syntax
    # Group by id to get all rows in the aggregate result
    query = Order.query().select("id", "status", "total_amount").group_by("id")
    query.select("""
        CASE 
            WHEN status = 'pending' THEN 
                CASE 
                    WHEN total_amount < 100 THEN 'Low Priority'
                    ELSE 'High Priority' 
                END
            WHEN status = 'paid' THEN 
                CASE 
                    WHEN total_amount < 100 THEN 'Regular Shipping'
                    ELSE 'Express Shipping' 
                END
            ELSE 'Completed'
        END as shipping_priority
    """)

    # Execute query
    query.order_by("id")
    results = query.aggregate()

    # Verify results
    assert len(results) == 5

    # Expected categories
    expected = [
        'Low Priority',  # Low value, pending
        'High Priority',  # High value, pending
        'Regular Shipping',  # Low value, paid
        'Express Shipping',  # High value, paid
        'Completed'  # Shipped order
    ]

    for i, result in enumerate(results):
        assert result['shipping_priority'] == expected[i]


def test_case_with_calculations(order_fixtures):
    """Test CASE expressions with calculations in aggregate query."""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different statuses and amounts
    data = [
        ('pending', Decimal('100.00')),
        ('paid', Decimal('200.00')),
        ('shipped', Decimal('300.00')),
        ('cancelled', Decimal('150.00'))
    ]

    for i, (status, amount) in enumerate(data):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=amount
        )
        order.save()

    # Test case with calculations
    # Group by id to ensure all rows are returned
    query = Order.query().select("id", "status", "total_amount").group_by("id")

    # Calculate different taxes based on status
    query.select("""
        CASE 
            WHEN status = 'pending' THEN total_amount * 0.05
            WHEN status = 'paid' THEN total_amount * 0.08
            WHEN status = 'shipped' THEN total_amount * 0.1
            ELSE 0  -- No tax for cancelled orders
        END as tax_amount
    """, append=True)

    # Add calculated tax to original amount
    query.select("""
        total_amount + 
        CASE 
            WHEN status = 'pending' THEN total_amount * 0.05
            WHEN status = 'paid' THEN total_amount * 0.08
            WHEN status = 'shipped' THEN total_amount * 0.1
            ELSE 0
        END as total_with_tax
    """, append=True)

    # Execute query
    query.order_by("id")
    results = query.aggregate()

    # Verify results
    assert len(results) == 4

    tax_rates = {
        'pending': 0.05,
        'paid': 0.08,
        'shipped': 0.1,
        'cancelled': 0
    }

    for result in results:
        status = result['status']
        amount = float(result['total_amount'])
        tax_rate = tax_rates[status]

        expected_tax = amount * tax_rate
        expected_total = amount + expected_tax

        assert abs(float(result['tax_amount']) - expected_tax) < 0.01
        assert abs(float(result['total_with_tax']) - expected_total) < 0.01


def test_case_in_complex_query(order_fixtures):
    """Test CASE expressions in a complex query with other features.

    This test verifies combining multiple SQL features:
    - JOIN across tables
    - GROUP BY with table-qualified columns
    - Multiple CASE expressions for conditional aggregation
    - SUM with CASE for conditional counting and summing
    """
    User, Order, OrderItem = order_fixtures

    # Create test data with verification
    user_ids = []
    for i in range(2):
        user = User(
            username=f'user{i + 1}',
            email=f'user{i + 1}@example.com',
            age=30 + i * 10
        )
        # Verify user creation
        save_result = user.save()
        assert save_result == 1, f"Expected user save to return 1, got {save_result}"
        assert user.id is not None, "User ID should not be None after save"
        user_ids.append(user.id)

        # Create orders for each user with different statuses and amounts
        statuses = ['pending', 'paid', 'shipped']
        for j, status in enumerate(statuses):
            amount = Decimal(f'{(j + 1) * 100}.00')
            order = Order(
                user_id=user.id,
                order_number=f'ORD-U{i + 1}-{j + 1}',
                status=status,
                total_amount=amount
            )
            # Verify order creation
            save_result = order.save()
            assert save_result == 1, f"Expected order save to return 1, got {save_result}"
            assert order.id is not None, "Order ID should not be None after save"

    # Verify the test data was created correctly
    for i, user_id in enumerate(user_ids):
        user_orders = Order.query().where("user_id = ?", (user_id,)).all()
        assert len(user_orders) == 3, f"Expected 3 orders for user{i + 1}, got {len(user_orders)}"

        # Check status distribution
        statuses = [order.status for order in user_orders]
        assert "pending" in statuses, f"Missing 'pending' order for user{i + 1}"
        assert "paid" in statuses, f"Missing 'paid' order for user{i + 1}"
        assert "shipped" in statuses, f"Missing 'shipped' order for user{i + 1}"

    # Build complex query with case expressions, joins, group by
    user_table = User.table_name()
    order_table = Order.table_name()

    # First, verify the basic join works as expected
    join_query = Order.query().select(
        f"{order_table}.id",
        f"{order_table}.status",
        f"{user_table}.username"
    )

    join_query.join(f"""
        INNER JOIN {user_table}
        ON {order_table}.user_id = {user_table}.id
    """)

    join_results = join_query.to_dict(direct_dict=True).all()
    assert len(join_results) == 6, f"Expected 6 rows from join query, got {len(join_results)}"

    # Now build the complex aggregate query
    query = Order.query().select(f"{user_table}.username")

    # Join with users
    query.join(f"""
        INNER JOIN {user_table}
        ON {order_table}.user_id = {user_table}.id
    """)

    # Group by user
    query.group_by(f"{user_table}.username")

    # Count orders by status category
    query.select(f"""
        SUM(CASE WHEN {order_table}.status = 'pending' THEN 1 ELSE 0 END) as pending_count,
        SUM(CASE WHEN {order_table}.status = 'paid' THEN 1 ELSE 0 END) as paid_count,
        SUM(CASE WHEN {order_table}.status = 'shipped' THEN 1 ELSE 0 END) as shipped_count
    """, append=True)

    # Sum order amounts by status
    query.select(f"""
        SUM(CASE WHEN {order_table}.status = 'pending' THEN {order_table}.total_amount ELSE 0 END) as pending_amount,
        SUM(CASE WHEN {order_table}.status = 'paid' THEN {order_table}.total_amount ELSE 0 END) as paid_amount,
        SUM(CASE WHEN {order_table}.status = 'shipped' THEN {order_table}.total_amount ELSE 0 END) as shipped_amount
    """, append=True)

    # Log the query for debugging
    sql, params = query.to_sql()
    logger = logging.getLogger('activerecord_test')
    logger.debug(f"Complex query SQL: {sql}")
    logger.debug(f"Complex query parameters: {params}")

    # Execute query with ordering for consistent results
    query.order_by(f"{user_table}.username")
    results = query.aggregate()

    # Verify results
    assert len(results) == 2, f"Expected 2 result groups (one per user), got {len(results)}"

    # Verify each user has correct results
    user_results = {result['username']: result for result in results}
    assert 'user1' in user_results, "Missing results for user1"
    assert 'user2' in user_results, "Missing results for user2"

    # Status counts should be equal for each user
    for username, result in user_results.items():
        # Verify counts
        assert result['pending_count'] == 1, f"Expected 1 pending order for {username}, got {result['pending_count']}"
        assert result['paid_count'] == 1, f"Expected 1 paid order for {username}, got {result['paid_count']}"
        assert result['shipped_count'] == 1, f"Expected 1 shipped order for {username}, got {result['shipped_count']}"

        # Verify amounts (100 for pending, 200 for paid, 300 for shipped)
        assert float(result[
                         'pending_amount']) == 100.0, f"Expected pending_amount=100.0 for {username}, got {result['pending_amount']}"
        assert float(
            result['paid_amount']) == 200.0, f"Expected paid_amount=200.0 for {username}, got {result['paid_amount']}"
        assert float(result[
                         'shipped_amount']) == 300.0, f"Expected shipped_amount=300.0 for {username}, got {result['shipped_amount']}"


def test_status_summary_with_case(order_fixtures):
    """Test using CASE to create a status summary report."""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create various orders with different status combinations
    statuses = ['pending', 'pending', 'paid', 'paid', 'shipped', 'shipped', 'cancelled']
    amounts = [50, 150, 200, 300, 100, 400, 250]

    for i, (status, amount) in enumerate(zip(statuses, amounts)):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=Decimal(str(amount))
        )
        order.save()

    # Create a summary query with case expressions
    # Group by a derived status category column
    query = Order.query()

    # First add the status category expression that we'll group by
    query.case([
        ("status IN ('pending', 'paid')", "Active"),
        ("status = 'shipped'", "Completed"),
        ("status = 'cancelled'", "Cancelled")
    ], alias="status_category")

    # Group by the status category
    query.group_by("status_category")

    # Count orders in each category
    query.count("*", "order_count")

    # Add sum of order amounts
    query.sum("total_amount", "total_value")

    # Add average of order amounts
    query.avg("total_amount", "average_value")

    # Execute query
    query.order_by("status_category")
    results = query.aggregate()

    # Verify results
    assert len(results) == 3  # Three categories

    # Build expected results
    expected = {
        'Active': {
            'order_count': 4,  # 2 pending + 2 paid
            'total_value': Decimal('700'),  # 50 + 150 + 200 + 300
            'average_value': Decimal('175')  # 700 / 4
        },
        'Completed': {
            'order_count': 2,  # 2 shipped
            'total_value': Decimal('500'),  # 100 + 400
            'average_value': Decimal('250')  # 500 / 2
        },
        'Cancelled': {
            'order_count': 1,  # 1 cancelled
            'total_value': Decimal('250'),  # 250
            'average_value': Decimal('250')  # 250 / 1
        }
    }

    for result in results:
        category = result['status_category']
        assert result['order_count'] == expected[category]['order_count']
        assert result['total_value'] == expected[category]['total_value']
        assert float(result['average_value']) == float(expected[category]['average_value'])