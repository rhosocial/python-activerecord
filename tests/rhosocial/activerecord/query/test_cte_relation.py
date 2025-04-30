"""Test basic relation queries with CTE."""
from decimal import Decimal

import pytest

from tests.rhosocial.activerecord.query.utils import create_order_fixtures, create_blog_fixtures

# Create test fixtures
order_fixtures = create_order_fixtures()
blog_fixtures = create_blog_fixtures()


def test_cte_with_belongsto_relation(order_fixtures):
    """Test CTE with BelongsTo relation"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

    # Get all orders
    orders = Order.query().all()

    # Create a CTE based on the orders' user relation
    # This should find the user associated with the first order
    query = User.query().with_cte(
        'order_users',
        f"""
        SELECT u.* 
        FROM {User.__table_name__} u
        JOIN {Order.__table_name__} o ON u.id = o.user_id
        WHERE o.id = {orders[0].id}
        """
    ).from_cte('order_users')

    result = query.one()

    # Verify that the CTE found the right user
    assert result is not None
    assert result.id == user.id
    assert result.username == 'test_user'

    # Test the BelongsTo relation on an order retrieved via CTE
    query = Order.query().with_cte(
        'specific_orders',
        f"""
        SELECT * FROM {Order.__table_name__}
        WHERE id = {orders[0].id}
        """
    ).from_cte('specific_orders')

    order = query.one()

    # Access the BelongsTo relation
    related_user = order.user()

    # Verify the relation works
    assert related_user is not None
    assert related_user.id == user.id
    assert related_user.username == 'test_user'


def test_cte_with_hasmany_relation(order_fixtures):
    """Test CTE with HasMany relation"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create test orders
    orders = []
    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()
        orders.append(order)

    # Create order items
    for i, order in enumerate(orders):
        # Create 2 items per order
        for j in range(2):
            item = OrderItem(
                order_id=order.id,
                product_name=f'Product {i + 1}-{j + 1}',
                quantity=j + 1,
                unit_price=Decimal('100.00'),
                subtotal=Decimal(f'{(j + 1) * 100}.00')
            )
            item.save()

    # Create a CTE to find orders with their items
    query = Order.query().with_cte(
        'orders_with_items',
        f"""
        SELECT DISTINCT o.* 
        FROM {Order.__table_name__} o
        JOIN {OrderItem.__table_name__} i ON o.id = i.order_id
        WHERE i.quantity > 1
        """
    ).from_cte('orders_with_items')

    # This should find orders that have at least one item with quantity > 1
    filtered_orders = query.all()

    # Verify we found the right orders
    assert len(filtered_orders) == 3  # All 3 orders have at least one item with quantity > 1

    # Test the HasMany relation on the first order
    first_order = filtered_orders[0]

    # Access the HasMany relation
    items = first_order.items().all()

    # Verify the relation works
    assert len(items) == 2  # Each order has 2 items
    assert all(isinstance(item, OrderItem) for item in items)
    assert all(item.order_id == first_order.id for item in items)


def test_cte_with_eager_loading(blog_fixtures):
    """Test CTE with eager loading of relations"""
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
            content=f'Content of post {i + 1}'
        )
        post.save()
        posts.append(post)

    # Create comments for each post
    for i, post in enumerate(posts):
        # Create 2 comments per post
        for j in range(2):
            comment = Comment(
                user_id=user.id,
                post_id=post.id,
                content=f'Comment {j + 1} on post {i + 1}'
            )
            comment.save()

    # Create a CTE to find posts with their comments
    query = Post.query().with_cte(
        'recent_posts',
        f"""
        SELECT * FROM {Post.__table_name__}
        ORDER BY id DESC
        LIMIT 2
        """
    ).from_cte('recent_posts')

    # Use eager loading to load comments relation
    query.with_('comments')

    # Get the posts with eagerly loaded comments
    recent_posts = query.all()

    # Verify the results
    assert len(recent_posts) == 2  # Limited to 2 posts

    # Check that comments were eagerly loaded
    for post in recent_posts:
        comments = post.comments.all()  # This should not trigger a new query
        assert len(comments) == 2  # Each post has 2 comments
        assert all(isinstance(comment, Comment) for comment in comments)
        assert all(comment.post_id == post.id for comment in comments)


def test_cte_with_nested_relations(blog_fixtures):
    """Test CTE with nested relations"""
    User, Post, Comment = blog_fixtures

    # Create test users
    users = []
    for i in range(2):
        user = User(
            username=f'user{i + 1}',
            email=f'user{i + 1}@example.com',
            age=30 + i * 5
        )
        user.save()
        users.append(user)

    # Create test posts for each user
    posts = []
    for i, user in enumerate(users):
        post = Post(
            user_id=user.id,
            title=f'Post by {user.username}',
            content=f'Content by {user.username}'
        )
        post.save()
        posts.append(post)

    # Create comments from both users on each post
    for post in posts:
        for user in users:
            comment = Comment(
                user_id=user.id,
                post_id=post.id,
                content=f'Comment by {user.username} on post {post.id}'
            )
            comment.save()

    # Create a CTE to find posts with nested relations
    query = Post.query().with_cte(
        'all_posts',
        f"""
        SELECT * FROM {Post.__table_name__}
        """
    ).from_cte('all_posts')

    # Use eager loading to load both post->user and post->comments->user
    query.with_('user')
    query.with_('comments.user')

    # Get the posts with eagerly loaded relations
    posts_with_relations = query.all()

    # Verify the results
    assert len(posts_with_relations) == 2

    # Check first level relations: post->user
    for post in posts_with_relations:
        post_author = post.user()
        assert post_author is not None
        assert post_author.id == post.user_id

        # Check second level relations: post->comments->user
        comments = post.comments.all()
        assert len(comments) == 2  # Each post has 2 comments

        for comment in comments:
            comment_author = comment.user()
            assert comment_author is not None
            assert comment_author.id == comment.user_id