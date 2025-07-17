# tests/rhosocial/activerecord_test/query/test_cte_integration.py
"""Test integration of CTE with other ActiveQuery features."""
from decimal import Decimal
from .utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_cte_with_where_conditions(order_fixtures):
    """Test CTE with WHERE conditions in main query"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create test orders with different statuses and amounts
    data = [
        ('pending', Decimal('100.00')),
        ('paid', Decimal('200.00')),
        ('shipped', Decimal('300.00')),
        ('pending', Decimal('400.00')),
        ('paid', Decimal('500.00')),
    ]

    for i, (status, amount) in enumerate(data):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=amount
        )
        order.save()

    # Define a CTE and then apply WHERE conditions on the main query
    query = Order.query().with_cte(
        'all_orders',
        "SELECT * FROM orders"
    ).from_cte('all_orders')

    # Add WHERE conditions to the main query
    query.where('status = ?', ('pending',))
    query.where('total_amount > ?', (Decimal('200.00'),))

    results = query.all()
    assert len(results) == 1
    assert results[0].status == 'pending'
    assert results[0].total_amount > Decimal('200.00')


def test_cte_with_order_limit_offset(order_fixtures):
    """Test CTE with ORDER BY, LIMIT, and OFFSET"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create test orders
    for i in range(5):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Define a CTE and apply ordering, limit, and offset
    query = Order.query().with_cte(
        'all_orders',
        "SELECT * FROM orders"
    ).from_cte('all_orders')

    # Add ordering, limit, and offset
    query.order_by('total_amount DESC')
    query.limit(2)
    query.offset(1)

    results = query.all()
    assert len(results) == 2
    # Should return the 2nd and 3rd highest amounts
    assert results[0].total_amount == Decimal('400.00')
    assert results[1].total_amount == Decimal('300.00')


def test_cte_with_range_conditions(order_fixtures):
    """Test CTE with range-based conditions (IN, BETWEEN, LIKE, etc.)"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create test orders
    for i in range(5):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00'),
            status='pending' if i % 2 == 0 else 'paid'
        )
        order.save()

    # Define a CTE for all orders
    query = Order.query().with_cte(
        'all_orders',
        "SELECT * FROM orders"
    ).from_cte('all_orders')

    # Test IN condition
    query.in_list('status', ['pending'])

    results = query.all()
    assert len(results) == 3
    assert all(r.status == 'pending' for r in results)

    # Create new query with BETWEEN condition
    query = Order.query().with_cte(
        'all_orders',
        "SELECT * FROM orders"
    ).from_cte('all_orders')

    query.between('total_amount', Decimal('200.00'), Decimal('400.00'))

    results = query.all()
    assert len(results) == 3
    assert all(Decimal('200.00') <= r.total_amount <= Decimal('400.00') for r in results)

    # Create new query with LIKE condition
    query = Order.query().with_cte(
        'all_orders',
        "SELECT * FROM orders"
    ).from_cte('all_orders')

    query.like('order_number', 'ORD-_')  # Match ORD-1, ORD-2, etc.

    results = query.all()
    assert len(results) == 5
    assert all(r.order_number.startswith('ORD-') for r in results)


def test_cte_with_aggregation(order_fixtures):
    """Test CTE with aggregation in main query"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create test orders with different statuses
    statuses = ['pending', 'paid', 'shipped', 'pending', 'paid']
    for i, status in enumerate(statuses):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Define a CTE for all orders
    query = Order.query().with_cte(
        'all_orders',
        "SELECT * FROM orders"
    ).from_cte('all_orders')

    # Group by status and count orders
    # query.select('status')  # this statement is not required.
    query.group_by('status')
    query.count('*', 'order_count')
    query.sum('all_orders.total_amount', 'total_amount')

    results = query.aggregate()

    # Verify aggregation results
    assert len(results) == 3  # Three unique statuses

    # Map results by status for easier checking
    by_status = {r['status']: r for r in results}

    assert by_status['pending']['order_count'] == 2
    assert by_status['paid']['order_count'] == 2
    assert by_status['shipped']['order_count'] == 1

    # Check totals
    assert by_status['pending']['total_amount'] == Decimal('500.00')  # 100 + 400
    assert by_status['paid']['total_amount'] == Decimal('700.00')  # 200 + 500
    assert by_status['shipped']['total_amount'] == Decimal('300.00')


def test_cte_with_or_conditions(order_fixtures):
    """Test CTE with OR conditions and condition groups"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create test orders
    for i in range(5):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00'),
            status=['pending', 'paid', 'shipped', 'cancelled', 'processing'][i]
        )
        order.save()

    # Define a CTE for all orders
    query = Order.query().with_cte(
        'all_orders',
        "SELECT * FROM orders"
    ).from_cte('all_orders')

    # Add OR condition
    query.where('status = ?', ('pending',))
    query.or_where('status = ?', ('paid',))

    results = query.all()
    assert len(results) == 2
    assert all(r.status in ('pending', 'paid') for r in results)

    # Create new query with condition groups
    query = Order.query().with_cte(
        'all_orders',
        "SELECT * FROM orders"
    ).from_cte('all_orders')

    # Add condition groups
    query.where('total_amount > ?', (Decimal('200.00'),))
    query.start_or_group()
    query.where('status = ?', ('shipped',))
    query.or_where('status = ?', ('cancelled',))
    query.end_or_group()

    results = query.all()
    assert len(results) == 2
    assert all(r.total_amount > Decimal('200.00') for r in results)
    assert all(r.status in ('shipped', 'cancelled') for r in results)


def test_cte_with_dict_query(order_fixtures):
    """Test CTE with dictionary query conversion"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create test orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Define a CTE and convert result to dictionary
    query = Order.query().with_cte(
        'all_orders',
        "SELECT * FROM orders"
    ).from_cte('all_orders')

    # Convert to dictionary
    dict_results = query.to_dict().all()

    assert len(dict_results) == 3
    assert all(isinstance(r, dict) for r in dict_results)
    assert all('id' in r for r in dict_results)
    assert all('order_number' in r for r in dict_results)
    assert all('total_amount' in r for r in dict_results)

    # Test with include filter
    include_fields = {'id', 'order_number'}
    dict_results = query.to_dict(include=include_fields).all()

    assert len(dict_results) == 3
    assert all('id' in r for r in dict_results)
    assert all('order_number' in r for r in dict_results)
    assert all('total_amount' not in r for r in dict_results)

    # Test direct dict conversion (bypass model instantiation)
    dict_results = query.to_dict(direct_dict=True).all()

    assert len(dict_results) == 3
    assert all(isinstance(r, dict) for r in dict_results)
    assert all('id' in r for r in dict_results)


def test_cte_with_advanced_expressions(order_fixtures):
    """Test CTE with advanced expressions (CASE, functions)"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create test orders with different statuses
    statuses = ['pending', 'paid', 'shipped']
    for i, status in enumerate(statuses):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Define a CTE for all orders
    query = Order.query().with_cte(
        'all_orders',
        "SELECT * FROM orders"
    ).from_cte('all_orders')

    # Add CASE expression in the main query
    query.case([
        ("status = 'pending'", "New"),
        ("status = 'paid'", "Completed")
    ], else_result="Other", alias="status_label")
    query.select("*")

    # Use direct dict to get the calculated expression
    results = query.to_dict(direct_dict=True).all()

    assert len(results) == 3
    assert 'status_label' in results[0]

    # Map status to expected label
    expected_labels = {
        'pending': 'New',
        'paid': 'Completed',
        'shipped': 'Other'
    }

    # Verify labels
    for result in results:
        assert result['status_label'] == expected_labels[result['status']]