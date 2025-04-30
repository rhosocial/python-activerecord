"""Test complex relation queries with CTE."""
from decimal import Decimal

import pytest

from tests.rhosocial.activerecord.query.utils import create_order_fixtures, create_blog_fixtures

# Create test fixtures
order_fixtures = create_order_fixtures()
blog_fixtures = create_blog_fixtures()


def test_cte_relation_with_subquery(order_fixtures):
    """Test CTE with relations and subqueries"""
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

    # Create test orders for each user
    orders = []
    for i, user in enumerate(users):
        # Each user gets i+1 orders
        for j in range(i + 1):
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{user.id}-{j + 1}',
                total_amount=Decimal(f'{(j + 1) * 100}.00')
            )
            order.save()
            orders.append(order)

    # Create a CTE with a subquery that finds users with multiple orders
    query = User.query().with_cte(
        'users_with_orders',
        f"""
        SELECT u.* 
        FROM {User.__table_name__} u
        WHERE (
            SELECT COUNT(*)
            FROM {Order.__table_name__} o
            WHERE o.user_id = u.id
        ) > 1
        """
    ).from_cte('users_with_orders')

    # Get users with more than one order
    users_with_multiple_orders = query.all()

    # Verify the results (only user2 and user3 have more than 1 order)
    assert len(users_with_multiple_orders) == 2
    user_ids = [u.id for u in users_with_multiple_orders]
    assert users[1].id in user_ids  # user2 has 2 orders
    assert users[2].id in user_ids  # user3 has 3 orders

    # Test accessing orders relation from these users
    for user in users_with_multiple_orders:
        # Get user's orders through the relation
        user_orders = user.orders().all()

        # Verify correct number of orders
        user_number = int(user.username.replace('user', ''))
        expected_order_count = user_number  # user2 has 2 orders, user3 has 3
        assert len(user_orders) == expected_order_count


def test_cte_relation_filtered_eager_loading(blog_fixtures):
    """Test CTE with filtered eager loading"""
    User, Post, Comment = blog_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test posts
    posts = []
    for i in range(3):
        post = Post(
            user_id=user.id,
            title=f'Post {i + 1}',
            content=f'Content of post {i + 1}',
            status='published' if i < 2 else 'draft'  # Make one post draft
        )
        post.save()
        posts.append(post)

    # Create comments for each post
    for i, post in enumerate(posts):
        # Create varying number of comments per post
        for j in range(i + 1):  # Post 1: 1 comment, Post 2: 2 comments, Post 3: 3 comments
            comment = Comment(
                user_id=user.id,
                post_id=post.id,
                content=f'Comment {j + 1} on post {i + 1}',
                is_hidden=(j == 0)  # First comment on each post is hidden
            )
            comment.save()

    # Create a CTE for published posts only
    query = Post.query().with_cte(
        'published_posts',
        f"""
        SELECT * FROM {Post.__table_name__}
        WHERE status = 'published'
        """
    ).from_cte('published_posts')

    # Eager load visible comments only using a query modifier
    query.with_(('comments', lambda q: q.where('is_hidden = ?', (False,))))

    # Get the published posts with filtered visible comments
    published_posts = query.all()

    # Verify the results
    assert len(published_posts) == 2  # Only 2 published posts

    # First post should have 0 visible comments (1 total - 1 hidden)
    assert len(published_posts[0].comments.all()) == 0

    # Second post should have 1 visible comment (2 total - 1 hidden)
    assert len(published_posts[1].comments.all()) == 1


def test_cte_relation_cross_model_aggregation(order_fixtures):
    """Test CTE with cross-model aggregation"""
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

    # Create test orders for each user
    for i, user in enumerate(users):
        for j in range(2):  # 2 orders per user
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{user.id}-{j + 1}',
                status='pending' if j == 0 else 'paid',
                total_amount=Decimal(f'{(i + 1) * 100}.00')
            )
            order.save()

    # Create a CTE that joins users and orders with aggregation
    query = User.query().with_cte(
        'user_order_stats',
        f"""
        SELECT 
            u.id, u.username, u.email, u.age,
            COUNT(o.id) as order_count,
            SUM(o.total_amount) as total_spent
        FROM {User.__table_name__} u
        LEFT JOIN {Order.__table_name__} o ON u.id = o.user_id
        GROUP BY u.id
        """
    ).from_cte('user_order_stats')

    # Add selection for the aggregated columns
    query.select('*')

    # Convert to dictionary for accessing non-model columns
    results = query.to_dict(direct_dict=True).all()

    # Verify the results
    assert len(results) == 3  # 3 users

    # Check computed columns for each user
    for i, result in enumerate(results):
        assert result['username'] == f'user{i + 1}'
        assert result['order_count'] == 2  # Each user has 2 orders
        assert result['total_spent'] == Decimal(f'{(i + 1) * 200}.00')  # Each user's 2 orders have same amount

    # Verify we can still access relations on a regular model
    # First, get a normal user instance
    user = User.query().where('id = ?', (users[0].id,)).one()

    # Then access its orders relation
    user_orders = user.orders().all()
    assert len(user_orders) == 2


def test_cte_relation_complex_join(order_fixtures):
    """Test CTE with complex joined relations"""
    User, Order, OrderItem = order_fixtures

    # Create test users
    users = []
    for i in range(2):
        user = User(
            username=f'user{i + 1}',
            email=f'user{i + 1}@example.com',
            age=30 + i * 10
        )
        user.save()
        users.append(user)

    # Create test orders
    orders = []
    statuses = ['pending', 'paid', 'shipped']
    for i, user in enumerate(users):
        for j, status in enumerate(statuses):
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{user.id}-{j + 1}',
                status=status,
                total_amount=Decimal(f'{(j + 1) * 100}.00')
            )
            order.save()
            orders.append(order)

    # Create order items
    for order in orders:
        for j in range(2):  # 2 items per order
            item = OrderItem(
                order_id=order.id,
                product_name=f'Product for {order.order_number}-{j + 1}',
                quantity=j + 1,
                unit_price=Decimal('100.00'),
                subtotal=Decimal(f'{(j + 1) * 100}.00')
            )
            item.save()

    # Create a complex CTE with multiple joins and conditions
    query = User.query().with_cte(
        'user_order_details',
        f"""
        SELECT 
            u.id, u.username, u.email, u.age,
            o.id as order_id, o.order_number, o.status,
            i.id as item_id, i.product_name, i.quantity
        FROM {User.__table_name__} u
        JOIN {Order.__table_name__} o ON u.id = o.user_id
        JOIN {OrderItem.__table_name__} i ON o.id = i.order_id
        WHERE o.status = 'paid' AND i.quantity > 1
        """
    ).from_cte('user_order_details')

    # Select all fields from the CTE
    query.select('*')

    # Convert to dictionary for accessing non-model columns
    results = query.to_dict(direct_dict=True).all()

    # Verify the results
    assert len(results) > 0

    # Check that all results match our criteria
    for result in results:
        assert result['status'] == 'paid'
        assert result['quantity'] > 1

    # Verify we can still load normal relations after CTE queries
    # First, get a user instance
    user = User.query().where('id = ?', (users[0].id,)).one()

    # Then load orders with eager loading
    orders_query = Order.query().with_('items').where('user_id = ?', (user.id,))
    user_orders = orders_query.all()

    assert len(user_orders) == 3  # 3 statuses = 3 orders

    # Check eager loaded items
    for order in user_orders:
        items = order.items.all()
        assert len(items) == 2  # Each order has 2 items