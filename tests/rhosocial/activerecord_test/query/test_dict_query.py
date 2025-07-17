# tests/rhosocial/activerecord_test/query/test_dict_query.py
"""Test dict query functionality in ActiveQuery."""
from decimal import Decimal
import logging
from .utils import create_order_fixtures, create_blog_fixtures

# Create fixtures for tests
order_fixtures = create_order_fixtures()
blog_fixtures = create_blog_fixtures()


def test_dict_query_all_with_model_instantiation(order_fixtures):
    """Test all() method with model instantiation (direct_dict=False)"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='dict_test_user',
        email='dict_test@example.com',
        age=30
    )
    user.save()

    # Create test orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'DICT-{i + 1:03d}',
            total_amount=Decimal('100.00'),
            status='pending'
        )
        order.save()

    # Retrieve orders as dictionaries
    orders_dict = Order.query().to_dict().all()

    # Log for debugging
    Order.log(logging.INFO, f"Retrieved {len(orders_dict)} orders as dictionaries")

    # Verify results
    assert len(orders_dict) == 3
    assert isinstance(orders_dict, list)
    assert all(isinstance(item, dict) for item in orders_dict)

    # Verify dictionary contents
    assert 'id' in orders_dict[0]
    assert 'order_number' in orders_dict[0]
    assert 'status' in orders_dict[0]
    assert orders_dict[0]['status'] == 'pending'


def test_dict_query_all_with_direct_dict(order_fixtures):
    """Test all() method with direct dictionary retrieval (direct_dict=True)"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='direct_dict_user',
        email='direct_dict@example.com',
        age=30
    )
    user.save()

    # Create test orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'DIRECT-{i + 1:03d}',
            total_amount=Decimal('100.00')
        )
        order.save()

    # Retrieve orders directly as dictionaries
    orders_dict = Order.query().to_dict(direct_dict=True).all()

    Order.log(logging.INFO, f"Retrieved {len(orders_dict)} orders with direct_dict=True")

    # Verify results
    assert len(orders_dict) == 3
    assert isinstance(orders_dict, list)
    assert all(isinstance(item, dict) for item in orders_dict)

    # Verify dictionary contents
    assert 'id' in orders_dict[0]
    assert 'order_number' in orders_dict[0]
    assert orders_dict[0]['order_number'].startswith('DIRECT-')


def test_dict_query_one_with_model_instantiation(order_fixtures):
    """Test one() method with model instantiation (direct_dict=False)"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='one_test_user',
        email='one_test@example.com',
        age=30
    )
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='ONE-TEST-001',
        total_amount=Decimal('150.00'),
        status='completed'
    )
    order.save()

    # Retrieve order as dictionary
    order_dict = Order.query().where('order_number = ?', ('ONE-TEST-001',)).to_dict().one()

    Order.log(logging.INFO, "Retrieved single order as dictionary")

    # Verify result
    assert order_dict is not None
    assert isinstance(order_dict, dict)
    assert order_dict['order_number'] == 'ONE-TEST-001'
    assert order_dict['status'] == 'completed'
    assert order_dict['total_amount'] == Decimal('150.00')


def test_dict_query_one_with_direct_dict(order_fixtures):
    """Test one() method with direct dictionary retrieval (direct_dict=True)"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='direct_one_user',
        email='direct_one@example.com',
        age=30
    )
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='DIRECT-ONE-001',
        total_amount=Decimal('200.00')
    )
    order.save()

    # Retrieve order directly as dictionary
    order_dict = Order.query().where('order_number = ?', ('DIRECT-ONE-001',)).to_dict(direct_dict=True).one()

    Order.log(logging.INFO, "Retrieved single order with direct_dict=True")

    # Verify result
    assert order_dict is not None
    assert isinstance(order_dict, dict)
    assert order_dict['order_number'] == 'DIRECT-ONE-001'
    assert 'total_amount' in order_dict


def test_dict_query_one_no_results(order_fixtures):
    """Test one() method when no results match the query"""
    User, Order, OrderItem = order_fixtures

    # Retrieve non-existent order
    result = Order.query().where('order_number = ?', ('NON-EXISTENT',)).to_dict().one()

    Order.log(logging.INFO, "Tested one() with no matching results")

    # Verify null result
    assert result is None


def test_dict_query_include_fields(order_fixtures):
    """Test to_dict() with include filter"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='include_test_user',
        email='include@example.com',
        age=40
    )
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='INCLUDE-TEST',
        total_amount=Decimal('300.00'),
        status='processed'
    )
    order.save()

    # Retrieve order with only specific fields
    include_fields = {'id', 'order_number', 'status'}
    order_dict = Order.query().where('order_number = ?', ('INCLUDE-TEST',)).to_dict(include=include_fields).one()

    Order.log(logging.INFO, f"Retrieved order with include fields: {include_fields}")

    # Verify included fields
    assert 'id' in order_dict
    assert 'order_number' in order_dict
    assert 'status' in order_dict
    assert order_dict['status'] == 'processed'

    # Verify excluded fields
    assert 'total_amount' not in order_dict
    assert 'user_id' not in order_dict


def test_dict_query_exclude_fields(order_fixtures):
    """Test to_dict() with exclude filter"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='exclude_test_user',
        email='exclude@example.com',
        age=35
    )
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='EXCLUDE-TEST',
        total_amount=Decimal('400.00'),
        status='shipped'
    )
    order.save()

    # Retrieve order excluding specific fields
    exclude_fields = {'created_at', 'updated_at'}
    order_dict = Order.query().where('order_number = ?', ('EXCLUDE-TEST',)).to_dict(exclude=exclude_fields).one()

    Order.log(logging.INFO, f"Retrieved order with exclude fields: {exclude_fields}")

    # Verify included fields
    assert 'id' in order_dict
    assert 'order_number' in order_dict
    assert 'status' in order_dict
    assert 'user_id' in order_dict
    assert 'total_amount' in order_dict

    # Verify excluded fields
    for field in exclude_fields:
        assert field not in order_dict


def test_dict_query_to_sql(order_fixtures):
    """Test to_sql() method returns the correct SQL and parameters"""
    User, Order, OrderItem = order_fixtures

    # Create a query
    query = Order.query().where('status = ?', ('pending',)).order_by('id DESC').limit(10)

    # Wrap with to_dict() and get SQL
    dict_query = query.to_dict()
    sql, params = dict_query.to_sql()

    Order.log(logging.INFO, f"Generated SQL: {sql}")
    Order.log(logging.INFO, f"SQL parameters: {params}")

    # Verify SQL contains expected clauses
    assert 'SELECT' in sql
    assert 'FROM' in sql and 'orders' in sql
    assert 'WHERE' in sql
    assert 'status = ?' in sql or 'status = %s' in sql
    assert 'ORDER BY' in sql
    assert 'LIMIT' in sql

    # Verify parameters
    assert params == ('pending',)


def test_dict_query_attribute_delegation(order_fixtures):
    """Test __getattr__ delegation to underlying query"""
    User, Order, OrderItem = order_fixtures

    # Create a dict query
    dict_query = Order.query().to_dict()

    # Delegate to underlying query's methods
    dict_query.where('status = ?', ('complete',))
    dict_query.limit(5)

    # Get SQL to verify delegation worked
    sql, params = dict_query.to_sql()

    Order.log(logging.INFO, "Tested attribute delegation to underlying query")

    # Verify delegated calls affected the query
    assert 'WHERE' in sql
    assert 'status = ?' in sql or 'status = %s' in sql
    assert 'LIMIT 5' in sql or 'LIMIT ? 5' in sql
    assert params == ('complete',)


def test_dict_query_with_join(order_fixtures):
    """Test to_dict() with JOIN queries using direct_dict"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='join_test_user',
        email='join@example.com',
        age=45
    )
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='JOIN-TEST-001',
        total_amount=Decimal('500.00')
    )
    order.save()

    # Create test order items
    item1 = OrderItem(
        order_id=order.id,
        product_name='Test Product 1',
        quantity=2,
        price=Decimal('250.00'),
        unit_price=Decimal('125.00')
    )
    item1.save()

    # Create complex JOIN query that selects columns from multiple tables
    joined_results = Order.query() \
        .join('JOIN order_items ON orders.id = order_items.order_id') \
        .join('JOIN users ON orders.user_id = users.id') \
        .select('orders.id', 'orders.order_number', 'users.username', 'order_items.product_name') \
        .where('orders.order_number = ?', ('JOIN-TEST-001',)) \
        .to_dict(direct_dict=True) \
        .all()

    Order.log(logging.INFO, f"Retrieved {len(joined_results)} records from JOIN query")

    # Verify join results
    assert len(joined_results) == 1
    assert joined_results[0]['order_number'] == 'JOIN-TEST-001'
    assert joined_results[0]['username'] == 'join_test_user'
    assert joined_results[0]['product_name'] == 'Test Product 1'


def test_dict_query_with_relations(blog_fixtures):
    """Test to_dict() with eager loaded relations"""
    User, Post, Comment = blog_fixtures

    # Create test user
    user = User(
        username='relation_test_user',
        email='relation@example.com',
        age=25
    )
    user.save()

    # Create test post
    post = Post(
        user_id=user.id,
        title='Test Post Title',
        content='Test post content for relation testing.'
    )
    post.save()

    # Create test comments
    comment1 = Comment(
        user_id=user.id,
        post_id=post.id,
        content='First test comment'
    )
    comment1.save()

    comment2 = Comment(
        user_id=user.id,
        post_id=post.id,
        content='Second test comment'
    )
    comment2.save()

    # Query with eager loading then convert to dict
    posts_with_comments = Post.query() \
        .with_('comments') \
        .where('id = ?', (post.id,)) \
        .to_dict() \
        .one()

    Post.log(logging.INFO, "Retrieved post with eager loaded comments as dictionary")

    # Verify that relations are loaded and converted to dictionaries
    assert 'id' in posts_with_comments
    assert 'title' in posts_with_comments
    assert posts_with_comments['title'] == 'Test Post Title'