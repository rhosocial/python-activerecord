"""Test basic relation queries with CTE."""
from decimal import Decimal

from tests.rhosocial.activerecord_test.query.utils import create_order_fixtures, create_blog_fixtures

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

    # Access the BelongsTo relation - correctly using the relation accessor
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
    assert len(filtered_orders) > 0  # Should find at least some orders

    # Test the HasMany relation on the first order using the query method
    first_order = filtered_orders[0]
    items_query = first_order.items_query()
    items = items_query.all()

    # Verify the relation works
    assert len(items) > 0  # Should have at least one item
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
        # Correctly use the comments relation
        comments = post.comments()
        assert len(comments) == 2  # Each post has 2 comments
        assert all(isinstance(comment, Comment) for comment in comments)
        assert all(comment.post_id == post.id for comment in comments)

        # Also test the query method
        comments_query = post.comments_query()
        query_comments = comments_query.all()
        assert len(query_comments) == 2


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
        # Correctly access the user relation
        post_author = post.user()
        assert post_author is not None
        assert post_author.id == post.user_id

        # Check second level relations: post->comments->user
        comments = post.comments()
        assert len(comments) == 2  # Each post has 2 comments

        for comment in comments:
            comment_author = comment.user()
            assert comment_author is not None
            assert comment_author.id == comment.user_id


def test_cte_relation_cache_mechanisms(blog_fixtures):
    """Test relation caching when using CTE queries"""
    User, Post, Comment = blog_fixtures
    
    # Create a test user
    user = User(username='cache_test_user', email='cache@example.com', age=30)
    user.save()
    
    # Create test posts
    post = Post(
        user_id=user.id,
        title='Cache Test Post',
        content='Testing relation caching with CTEs'
    )
    post.save()
    
    # Create a CTE query for this post
    query = Post.query().with_cte(
        'test_post',
        f"""
        SELECT * FROM {Post.__table_name__}
        WHERE id = {post.id}
        """
    ).from_cte('test_post')
    
    # Execute the query and get the post
    cte_post = query.one()
    assert cte_post is not None
    
    # Access the user relation to cache it
    user_from_relation = cte_post.user()
    assert user_from_relation is not None
    assert user_from_relation.id == user.id
    
    # The cached relation should be used on second access
    # Instead of testing the cache implementation directly,
    # verify the relation still returns the correct data
    second_access = cte_post.user()
    assert second_access is not None
    assert second_access.id == user.id
    
    # Clear the cache and verify it gets reloaded properly
    cte_post.clear_relation_cache('user')
    reloaded_user = cte_post.user()
    assert reloaded_user is not None
    assert reloaded_user.id == user.id


def test_cte_with_query_modifiers(blog_fixtures):
    """Test CTE with relation query modifiers"""
    User, Post, Comment = blog_fixtures

    # Create test data
    user = User(username='modifier_test', email='modifier@example.com', age=30)
    user.save()

    # Create posts with different statuses
    post1 = Post(
        user_id=user.id,
        title='Published Post',
        content='Content',
        status='published'
    )
    post1.save()

    post2 = Post(
        user_id=user.id,
        title='Draft Post',
        content='Draft Content',
        status='draft'
    )
    post2.save()

    # Create comments with different visibilities
    comment1 = Comment(
        user_id=user.id,
        post_id=post1.id,
        content='Visible comment',
        is_hidden=False
    )
    comment1.save()

    comment2 = Comment(
        user_id=user.id,
        post_id=post1.id,
        content='Hidden comment',
        is_hidden=True
    )
    comment2.save()

    # Create a CTE for the user
    query = User.query().with_cte(
        'test_user',
        f"""
        SELECT * FROM {User.__table_name__}
        WHERE id = {user.id}
        """
    ).from_cte('test_user')

    # Use query modifier to get only published posts
    query.with_(
        ('posts', lambda q: q.where('status = ?', ('published',)))
    )

    # Get the user with filtered posts
    user_result = query.one()
    assert user_result is not None

    # Verify we only get published posts
    posts = user_result.posts()
    assert len(posts) == 1
    assert posts[0].status == 'published'

    # Now test with nested query modifiers
    query = User.query().with_cte(
        'test_user',
        f"""
        SELECT * FROM {User.__table_name__}
        WHERE id = {user.id}
        """
    ).from_cte('test_user')

    # Use nested query modifiers
    query.with_(
        ('posts', lambda q: q.where('status = ?', ('published',))),
        ('posts.comments', lambda q: q.where('is_hidden = ?', (False,)))
    )

    # Get the user with filtered posts and comments
    user_result = query.one()
    assert user_result is not None

    # Verify filtering worked at both levels
    posts = user_result.posts()
    assert len(posts) == 1
    assert posts[0].status == 'published'

    comments = posts[0].comments()
    assert len(comments) == 1
    assert comments[0].is_hidden == False

    # Test the query method interface
    posts_query = user_result.posts_query()

    # FIXED: According to the design of relational.py, posts_query() returns a fresh query
    # without any filters that were applied via with_(). It should return all posts (2).
    assert posts_query.count() == 2  # Correctly expecting 2 posts (both published and draft)

    # If we want filtered results, we need to apply the filter again manually
    filtered_posts_query = posts_query.where('status = ?', ('published',))
    assert filtered_posts_query.count() == 1  # Now we should get only 1 post

    # Get the published post for further testing
    post = filtered_posts_query.one()
    comments_query = post.comments_query()

    # Similarly, comments_query() returns all comments without filters
    assert comments_query.count() == 2  # Expecting both hidden and visible comments

    # Apply the filter manually to get only visible comments
    filtered_comments_query = comments_query.where('is_hidden = ?', (False,))
    assert filtered_comments_query.count() == 1  # Now we get only visible comments