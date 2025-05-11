"""Test integration of CTE with ActiveQuery for building Common Table Expressions."""
from decimal import Decimal
from .utils import create_order_fixtures, create_tree_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()
tree_fixtures = create_tree_fixtures()


def test_active_query_cte_with_where_conditions(order_fixtures):
    """Test CTE using ActiveQuery with WHERE conditions in main query"""
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

    # Define CTE using an ActiveQuery instance instead of SQL string
    all_orders_query = Order.query()
    query = Order.query().with_cte(
        'all_orders',
        all_orders_query
    ).from_cte('all_orders')

    # Add WHERE conditions to the main query
    query.where('status = ?', ('pending',))
    query.where('total_amount > ?', (Decimal('200.00'),))

    results = query.all()
    assert len(results) == 1
    assert results[0].status == 'pending'
    assert results[0].total_amount > Decimal('200.00')


def test_active_query_cte_with_filtered_source(order_fixtures):
    """Test CTE using ActiveQuery with filtered source query"""
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

    # Define CTE with filtered ActiveQuery
    # Only include paid orders in the CTE
    paid_orders_query = Order.query().where('status = ?', ('paid',))
    query = Order.query().with_cte(
        'paid_orders',
        paid_orders_query
    ).from_cte('paid_orders')

    # No need for additional filtering, CTE already filters for paid status
    results = query.all()
    assert len(results) == 2
    assert all(r.status == 'paid' for r in results)
    assert Decimal('200.00') in [r.total_amount for r in results]
    assert Decimal('500.00') in [r.total_amount for r in results]


def test_active_query_cte_with_order_limit_offset(order_fixtures):
    """Test CTE using ActiveQuery with ORDER BY, LIMIT, and OFFSET"""
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

    # Define CTE using ActiveQuery instance
    all_orders_query = Order.query()
    query = Order.query().with_cte(
        'all_orders',
        all_orders_query
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


def test_active_query_cte_with_ordered_source(order_fixtures):
    """Test CTE using ActiveQuery with ordering in the source query"""
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

    # Define CTE with ordering in ActiveQuery
    ordered_query = Order.query().order_by('total_amount DESC')
    query = Order.query().with_cte(
        'ordered_orders',
        ordered_query
    ).from_cte('ordered_orders')

    # Add limit and offset
    query.limit(2)

    results = query.all()
    assert len(results) == 2
    # Should return the 1st and 2nd highest amounts
    assert results[0].total_amount == Decimal('500.00')
    assert results[1].total_amount == Decimal('400.00')


def test_active_query_cte_with_range_conditions(order_fixtures):
    """Test CTE using ActiveQuery with range-based conditions (IN, BETWEEN, LIKE, etc.)"""
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

    # Define CTE using ActiveQuery
    all_orders_query = Order.query()
    query = Order.query().with_cte(
        'all_orders',
        all_orders_query
    ).from_cte('all_orders')

    # Test IN condition
    query.in_list('status', ['pending'])

    results = query.all()
    assert len(results) == 3
    assert all(r.status == 'pending' for r in results)

    # Create new query with BETWEEN condition
    all_orders_query = Order.query()
    query = Order.query().with_cte(
        'all_orders',
        all_orders_query
    ).from_cte('all_orders')

    query.between('total_amount', Decimal('200.00'), Decimal('400.00'))

    results = query.all()
    assert len(results) == 3
    assert all(Decimal('200.00') <= r.total_amount <= Decimal('400.00') for r in results)

    # Create new query with LIKE condition
    all_orders_query = Order.query()
    query = Order.query().with_cte(
        'all_orders',
        all_orders_query
    ).from_cte('all_orders')

    query.like('order_number', 'ORD-_')  # Match ORD-1, ORD-2, etc.

    results = query.all()
    assert len(results) == 5
    assert all(r.order_number.startswith('ORD-') for r in results)


def test_active_query_cte_with_aggregation(order_fixtures):
    """Test CTE using ActiveQuery with aggregation in main query"""
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

    # Define CTE using ActiveQuery
    all_orders_query = Order.query()
    query = Order.query().with_cte(
        'all_orders',
        all_orders_query
    ).from_cte('all_orders')

    # Group by status and count orders
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


def test_active_query_cte_with_aggregated_source(order_fixtures):
    """Test CTE using aggregated ActiveQuery as source"""
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

    # Define CTE with aggregated ActiveQuery
    agg_query = Order.query() \
        .select('status') \
        .group_by('status') \
        .count('*', 'order_count') \
        .sum('total_amount', 'total_sum')

    query = Order.query().with_cte(
        'status_summary',
        agg_query
    ).from_cte('status_summary')

    # Order the results
    query.order_by('order_count DESC')

    # Need to use direct_dict since results don't match Order model structure
    results = query.to_dict(direct_dict=True).all()

    # Verify aggregation results
    assert len(results) == 3  # Three unique statuses

    # First should be the statuses with most orders (pending and paid with 2 each)
    assert results[0]['order_count'] == 2
    assert results[1]['order_count'] == 2
    assert results[2]['order_count'] == 1

    # Verify one of the high count statuses is 'pending' with correct sum
    pending_result = next((r for r in results if r['status'] == 'pending'), None)
    assert pending_result is not None
    assert pending_result['order_count'] == 2
    assert pending_result['total_sum'] == Decimal('500.00')  # 100 + 400


def test_active_query_cte_with_or_conditions(order_fixtures):
    """Test CTE using ActiveQuery with OR conditions and condition groups"""
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

    # Define CTE using ActiveQuery
    all_orders_query = Order.query()
    query = Order.query().with_cte(
        'all_orders',
        all_orders_query
    ).from_cte('all_orders')

    # Add OR condition
    query.where('status = ?', ('pending',))
    query.or_where('status = ?', ('paid',))

    results = query.all()
    assert len(results) == 2
    assert all(r.status in ('pending', 'paid') for r in results)

    # Create new query with condition groups
    all_orders_query = Order.query()
    query = Order.query().with_cte(
        'all_orders',
        all_orders_query
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


def test_active_query_cte_with_or_conditions_in_source(order_fixtures):
    """Test CTE using ActiveQuery with OR conditions in the source query"""
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

    # Define CTE with filtered ActiveQuery
    # Include orders with status pending OR paid
    filtered_query = Order.query() \
        .where('status = ?', ('pending',)) \
        .or_where('status = ?', ('paid',))

    query = Order.query().with_cte(
        'selected_orders',
        filtered_query
    ).from_cte('selected_orders')

    results = query.all()
    assert len(results) == 2
    assert all(r.status in ('pending', 'paid') for r in results)

    # Try with a different approach using condition groups in source
    filtered_query = Order.query() \
        .where('total_amount > ?', (Decimal('200.00'),)) \
        .start_or_group() \
        .where('status = ?', ('shipped',)) \
        .or_where('status = ?', ('cancelled',)) \
        .end_or_group()

    query = Order.query().with_cte(
        'selected_orders',
        filtered_query
    ).from_cte('selected_orders')

    results = query.all()
    assert len(results) == 2
    assert all(r.total_amount > Decimal('200.00') for r in results)
    assert all(r.status in ('shipped', 'cancelled') for r in results)


def test_active_query_cte_with_dict_query(order_fixtures):
    """Test CTE using ActiveQuery with dictionary query conversion"""
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

    # Define CTE using ActiveQuery and convert result to dictionary
    all_orders_query = Order.query()
    query = Order.query().with_cte(
        'all_orders',
        all_orders_query
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


def test_active_query_cte_with_selected_columns(order_fixtures):
    """Test CTE using ActiveQuery with explicit column selection"""
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

    # Define CTE with selected columns
    selected_query = Order.query().select('id', 'order_number', 'total_amount')
    query = Order.query().with_cte(
        'simple_orders',
        selected_query
    ).from_cte('simple_orders')

    # Need direct_dict since result may not have all Order model fields
    results = query.to_dict(direct_dict=True).all()

    assert len(results) == 3
    assert all('id' in r for r in results)
    assert all('order_number' in r for r in results)
    assert all('total_amount' in r for r in results)


def test_active_query_cte_with_advanced_expressions(order_fixtures):
    """Test CTE using ActiveQuery with advanced expressions (CASE, functions)"""
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

    # Define CTE using ActiveQuery
    all_orders_query = Order.query()
    query = Order.query().with_cte(
        'all_orders',
        all_orders_query
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


def test_active_query_cte_with_advanced_expressions_in_source(order_fixtures):
    """Test CTE using ActiveQuery with advanced expressions in the source query"""
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

    # Define CTE with case expression in ActiveQuery
    case_query = Order.query() \
        .select('id', 'order_number', 'total_amount', 'status') \
        .case([
        ("status = 'pending'", "New"),
        ("status = 'paid'", "Completed")
    ], else_result="Other", alias="status_label")

    query = Order.query().with_cte(
        'labeled_orders',
        case_query
    ).from_cte('labeled_orders')

    # Add a filter to only show completed orders
    query.where("status_label = ?", ("Completed",))

    # Use direct dict since result doesn't match Order model structure
    results = query.to_dict(direct_dict=True).all()

    assert len(results) == 1
    assert results[0]['status_label'] == 'Completed'
    assert results[0]['status'] == 'paid'


def test_active_query_cte_with_multiple_ctes(order_fixtures):
    """Test using multiple CTEs with ActiveQuery"""
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

    # Define first CTE for pending orders
    pending_query = Order.query().where('status = ?', ('pending',))

    # Define second CTE for paid orders
    paid_query = Order.query().where('status = ?', ('paid',))

    # Define query with multiple CTEs
    query = Order.query() \
        .with_cte('pending_orders', pending_query) \
        .with_cte('paid_orders', paid_query) \
        .with_cte(
        'combined_orders',
        "SELECT * FROM pending_orders UNION ALL SELECT * FROM paid_orders"
    ) \
        .from_cte('combined_orders')

    # Order results
    query.order_by('total_amount ASC')

    results = query.all()

    # Should only include pending and paid orders, not shipped
    assert len(results) == 4
    assert all(r.status in ('pending', 'paid') for r in results)
    assert results[0].total_amount == Decimal('100.00')
    assert results[3].total_amount == Decimal('500.00')


def test_active_query_recursive_cte(tree_fixtures):
    """Test recursive CTE with ActiveQuery"""
    Node = tree_fixtures[0]

    # Create a tree structure
    #       1
    #      / \
    #     2   3
    #    / \   \
    #   4   5   6

    root = Node(name="Root", value=Decimal('100.00'))
    root.save()

    node2 = Node(name="Node 2", parent_id=root.id, value=Decimal('50.00'))
    node2.save()

    node3 = Node(name="Node 3", parent_id=root.id, value=Decimal('60.00'))
    node3.save()

    node4 = Node(name="Node 4", parent_id=node2.id, value=Decimal('20.00'))
    node4.save()

    node5 = Node(name="Node 5", parent_id=node2.id, value=Decimal('30.00'))
    node5.save()

    node6 = Node(name="Node 6", parent_id=node3.id, value=Decimal('40.00'))
    node6.save()

    # Create a recursive CTE to find all descendants of Root
    query = Node.query().with_recursive_cte(
        'descendants',
        f"""
        SELECT id, name, parent_id, value FROM nodes WHERE id = {root.id}
        UNION ALL
        SELECT n.id, n.name, n.parent_id, n.value 
        FROM nodes n JOIN descendants d ON n.parent_id = d.id
        """
    ).from_cte('descendants')

    # Order by id to get a consistent order
    query.order_by('id')

    results = query.all()

    # Should include all nodes
    assert len(results) == 6

    # Verify specific values
    assert results[0].name == "Root"
    assert results[1].name == "Node 2"
    assert results[5].name == "Node 6"

    # Sum of all values should be 100 + 50 + 60 + 20 + 30 + 40 = 300
    total_value = sum(node.value for node in results)
    assert total_value == Decimal('300.00')


def test_active_query_cte_with_chained_from(order_fixtures):
    """Test chained FROM in CTE with ActiveQuery"""
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

        # Add some items to each order
        for j in range(2):
            item = OrderItem(
                order_id=order.id,
                product_name=f"Product {j + 1}",
                quantity=j + 1,
                unit_price=Decimal('10.00'),
                subtotal=Decimal((j + 1) * 10)
            )
            item.save()

    # First CTE: Get all orders
    orders_query = Order.query()

    # Second CTE: Join orders with items
    items_query = OrderItem.query()

    # Define query with chained CTEs
    query = Order.query() \
        .with_cte('all_orders', orders_query) \
        .with_cte(
        'order_with_items',
        """
        SELECT o.id            as order_id,
               o.order_number,
               o.status,
               o.total_amount,
               COUNT(i.id)     as item_count,
               SUM(i.subtotal) as items_subtotal
        FROM all_orders o
                 JOIN order_items i ON o.id = i.order_id
        GROUP BY o.id, o.order_number, o.status, o.total_amount
        """
    ) \
        .from_cte('order_with_items')

    # Filter to only show orders with more than one item
    query.where('item_count > ?', (1,))

    # Use direct_dict since result doesn't match Order model structure
    results = query.to_dict(direct_dict=True).all()

    # We should have orders with item_count = 2
    assert len(results) > 0
    assert all(r['item_count'] > 1 for r in results)

    # Verify that items_subtotal matches what we expect
    # For orders with 2 items (1 x $10 and 2 x $10), subtotal should be $30
    assert any(r['items_subtotal'] == Decimal('30.00') for r in results)