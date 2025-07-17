# tests/rhosocial/activerecord_test/query/test_cte_basic.py
"""Test basic CTE functionality in ActiveQuery."""
from decimal import Decimal
from .utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_basic_cte(order_fixtures):
    """Test basic CTE definition and query"""
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

    # Define and use a simple CTE
    query = Order.query().with_cte(
        'active_orders',
        "SELECT * FROM orders WHERE status IN ('pending', 'paid')"
    ).from_cte('active_orders')
    print(query.to_sql())
    results = query.all()
    assert len(results) == 2
    assert all(r.status in ('pending', 'paid') for r in results)


def test_cte_with_parameters(order_fixtures):
    """Test CTE with parameters in the subquery"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create test orders with different amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=amount
        )
        order.save()

    # Define a CTE with parameters using ActiveQuery instance
    subquery = Order.query().where('total_amount > ?', (Decimal('150.00'),))

    # Use the CTE in the main query
    query = Order.query().with_cte(
        'expensive_orders',
        subquery
    ).from_cte('expensive_orders')

    results = query.all()
    assert len(results) == 2
    assert all(r.total_amount > Decimal('150.00') for r in results)


def test_cte_with_columns(order_fixtures):
    """Test CTE with explicit column definitions"""
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

    # Define a CTE with explicit columns
    query = Order.query().with_cte(
        'order_summary',
        "SELECT order_number, total_amount FROM orders",
        columns=['order_no', 'amount']  # Rename columns in the CTE
    ).from_cte('order_summary')

    # Need to select all columns from the CTE
    query.select('order_summary.*')

    # Since we're bypassing the model, use dict query for results
    results = query.to_dict(direct_dict=True).all()
    assert len(results) == 3

    # Verify column renaming
    assert 'order_no' in results[0]
    assert 'amount' in results[0]
    assert results[0]['order_no'].startswith('ORD-')


def test_multiple_ctes(order_fixtures):
    """Test using multiple CTEs in a single query"""
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

    # Define multiple CTEs
    query = Order.query()

    # First CTE: active orders
    query.with_cte(
        'active_orders',
        "SELECT * FROM orders WHERE status IN ('pending', 'paid')"
    )

    # Second CTE: expensive orders
    query.with_cte(
        'expensive_orders',
        "SELECT * FROM active_orders WHERE total_amount > 300.00"
    )

    # Use the second CTE
    query.from_cte('expensive_orders')

    results = query.all()
    assert len(results) == 2
    assert all(r.status in ('pending', 'paid') for r in results)
    assert all(r.total_amount > Decimal('300.00') for r in results)


def test_cte_with_alias(order_fixtures):
    """Test CTE with table alias in FROM clause"""
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

    # Define a CTE and use it with an alias
    query = Order.query().with_cte(
        'all_orders',
        "SELECT * FROM orders"
    ).from_cte('all_orders', alias='o')

    # Reference the alias in WHERE clause
    query.where('o.total_amount > ?', (Decimal('150.00'),))

    results = query.all()
    assert len(results) == 2
    assert all(r.total_amount > Decimal('150.00') for r in results)


def test_cte_with_join(order_fixtures):
    """Test CTE with JOIN operation"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create test orders
    for i in range(2):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00'),
            status='pending' if i == 0 else 'paid'
        )
        order.save()

        # Create order items
        for j in range(2):
            item = OrderItem(
                order_id=order.id,
                product_name=f'Product {i + 1}-{j + 1}',
                quantity=j + 1,
                price=Decimal(f'{(j + 1) * 50}.00'),
                subtotal=Decimal(f'{(j + 1) * 50}.00'),
                unit_price=Decimal(1),
            )
            item.save()

    # Define a CTE for filtered orders
    query = Order.query().with_cte(
        'filtered_orders',
        "SELECT * FROM orders WHERE status = 'pending'"
    )

    # Use the CTE and join with order_items
    query.from_cte('filtered_orders')
    query.join('JOIN order_items ON filtered_orders.id = order_items.order_id')

    # Select specific columns
    query.select('filtered_orders.*', 'order_items.product_name', 'order_items.quantity')

    # Use direct_dict to get all selected columns
    results = query.to_dict(direct_dict=True).all()
    assert len(results) == 2  # 1 pending order with 2 items
    assert all(r['status'] == 'pending' for r in results)
    assert all('product_name' in r for r in results)
    assert all('quantity' in r for r in results)