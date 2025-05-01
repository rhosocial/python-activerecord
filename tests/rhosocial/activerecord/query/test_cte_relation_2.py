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
        # Use the orders_query method to get a query object
        orders_query = user.orders_query()
        user_orders = orders_query.all()

        # Verify correct number of orders
        user_number = int(user.username.replace('user', ''))
        expected_order_count = user_number  # user2 has 2 orders, user3 has 3
        assert len(user_orders) == expected_order_count

        # Also test the standard relation accessor
        orders_direct = user.orders()
        assert len(orders_direct) == expected_order_count


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

    # Check comment counts
    # The first post should have 0 visible comments (1 total - 1 hidden)
    visible_comments_post1 = published_posts[0].comments()
    assert len(visible_comments_post1) == 0

    # The second post should have 1 visible comment (2 total - 1 hidden)
    visible_comments_post2 = published_posts[1].comments()
    assert len(visible_comments_post2) == 1

    # Also test the query method
    comments_query = published_posts[1].comments_query()
    assert comments_query.count() == 1
    assert not comments_query.one().is_hidden


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
        assert float(result['total_spent']) == float(f'{(i + 1) * 200}.00')  # Each user's 2 orders have same amount

    # Verify we can still access relations on a regular model
    # First, get a normal user instance
    user = User.query().where('id = ?', (users[0].id,)).one()

    # Then access its orders relation
    orders = user.orders()
    assert len(orders) == 2

    # And use the query method
    orders_query = user.orders_query()
    assert orders_query.count() == 2


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
        items = order.items()
        assert len(items) == 2  # Each order has 2 items

        # Also test the query method
        items_query = order.items_query()
        assert items_query.count() == 2


def test_cte_deep_nested_relations(blog_fixtures):
    """Test CTE with deeply nested relations"""
    User, Post, Comment = blog_fixtures

    # Create a hierarchy of users, posts, and comments
    admin = User(username='admin', email='admin@example.com', age=40)
    admin.save()

    moderator = User(username='moderator', email='mod@example.com', age=35)
    moderator.save()

    user1 = User(username='user1', email='user1@example.com', age=25)
    user1.save()

    # Create posts
    announcement = Post(
        user_id=admin.id,
        title='Important Announcement',
        content='This is an important announcement',
        status='published'
    )
    announcement.save()

    discussion = Post(
        user_id=moderator.id,
        title='Discussion Thread',
        content='Let\'s discuss this topic',
        status='published'
    )
    discussion.save()

    # Create comments with nested structure
    mod_comment = Comment(
        user_id=moderator.id,
        post_id=announcement.id,
        content='First official response',
        is_hidden=False
    )
    mod_comment.save()

    user_reply = Comment(
        user_id=user1.id,
        post_id=announcement.id,
        content='User response to announcement',
        is_hidden=False,
        parent_comment_id=mod_comment.id
    )
    user_reply.save()

    # Create a CTE for admin posts
    query = Post.query().with_cte(
        'admin_posts',
        f"""
        SELECT p.* 
        FROM {Post.__table_name__} p
        JOIN {User.__table_name__} u ON p.user_id = u.id
        WHERE u.username = 'admin'
        """
    ).from_cte('admin_posts')

    # Use deeply nested eager loading
    query.with_('user', 'comments.user')

    # Get admin posts with all related data
    admin_posts = query.all()

    # Verify the results
    assert len(admin_posts) == 1
    post = admin_posts[0]

    # Check first level relation
    post_author = post.user()
    assert post_author is not None
    assert post_author.username == 'admin'

    # Check second level relation
    comments = post.comments()
    assert len(comments) >= 1

    # Test querying the comments
    comments_query = post.comments_query()
    comments_from_query = comments_query.all()
    assert len(comments_from_query) >= 1

    # For each comment, check the user relation
    for comment in comments:
        comment_author = comment.user()
        assert comment_author is not None
        if comment.content == 'First official response':
            assert comment_author.username == 'moderator'
        else:
            assert comment_author.username == 'user1'


def test_cte_relation_with_instance_cache(blog_fixtures):
    """Test CTE relations with the instance cache system"""
    User, Post, Comment = blog_fixtures

    # Create test data
    user = User(username='cache_test', email='cache@example.com', age=30)
    user.save()

    post = Post(
        user_id=user.id,
        title='Cache Testing Post',
        content='Testing the instance cache system',
        status='published'
    )
    post.save()

    # Create a CTE to get the post
    query = Post.query().with_cte(
        'test_post',
        f"""
        SELECT * FROM {Post.__table_name__}
        WHERE id = {post.id}
        """
    ).from_cte('test_post')

    # Get the post and access the user relation
    cte_post = query.one()
    assert cte_post is not None

    # First access should load the relation
    first_user = cte_post.user()
    assert first_user is not None
    assert first_user.id == user.id

    # Second access should use the instance cache
    second_user = cte_post.user()
    assert second_user is not None
    assert second_user.id == user.id

    # Clear the cache and verify it works
    cte_post.clear_relation_cache('user')

    # Access again after clearing cache
    third_user = cte_post.user()
    assert third_user is not None
    assert third_user.id == user.id

    # Test clear_relation_cache with invalid relation
    with pytest.raises(ValueError):
        cte_post.clear_relation_cache('invalid_relation')


def test_cte_relation_query_methods_basic(blog_fixtures):
    """Test basic relation query methods with CTE."""
    User, Post, Comment = blog_fixtures

    # Create test data
    user = User(username='query_methods_test', email='query@example.com', age=30)
    user.save()

    # Create multiple posts with different statuses
    posts = []
    for i in range(5):
        status = 'published' if i % 2 == 0 else 'draft'
        post = Post(
            user_id=user.id,
            title=f'Post {i + 1}',
            content=f'Content of post {i + 1}',
            status=status
        )
        post.save()
        posts.append(post)

    # Create a CTE for the user
    query = User.query().with_cte(
        'test_user',
        f"""
        SELECT * FROM {User.__table_name__}
        WHERE id = {user.id}
        """
    ).from_cte('test_user')

    # Get the user from CTE
    cte_user = query.one()
    assert cte_user is not None

    # Test posts_query method
    posts_query = cte_user.posts_query()
    assert posts_query is not None

    # Test filtering using query methods on the relation
    published_posts_query = posts_query.where('status = ?', ('published',))
    published_posts = published_posts_query.all()

    # Verify the results
    assert len(published_posts) == 3  # Should find 3 published posts
    assert all(post.status == 'published' for post in published_posts)

    # Test order by on relation query
    ordered_posts = cte_user.posts_query().order_by('id DESC').all()
    assert len(ordered_posts) == 5
    assert ordered_posts[0].id > ordered_posts[-1].id

    # Test limit on relation query
    limited_posts = cte_user.posts_query().limit(2).all()
    assert len(limited_posts) == 2

    # Test multiple conditions
    filtered_posts = cte_user.posts_query().where('status = ?', ('published',)).limit(2).all()
    assert len(filtered_posts) == 2
    assert all(post.status == 'published' for post in filtered_posts)


def test_cte_relation_query_methods_chaining(order_fixtures):
    """Test chaining relation query methods with CTE."""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='chaining_test', email='chaining@example.com', age=35)
    user.save()

    # Create orders with different statuses and amounts
    statuses = ['pending', 'paid', 'shipped', 'delivered', 'cancelled']
    for i, status in enumerate(statuses):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=status,
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()

        # Create items for each order
        for j in range(2):
            item = OrderItem(
                order_id=order.id,
                product_name=f'Product {i + 1}-{j + 1}',
                quantity=j + 1,
                unit_price=Decimal('100.00'),
                subtotal=Decimal(f'{(j + 1) * 100}.00')
            )
            item.save()

    # Create a CTE for the user
    query = User.query().with_cte(
        'test_user',
        f"""
        SELECT * FROM {User.__table_name__}
        WHERE id = {user.id}
        """
    ).from_cte('test_user')

    # Get the user from CTE
    cte_user = query.one()
    assert cte_user is not None

    # Test complex query chaining on orders relation
    complex_query = cte_user.orders_query() \
        .where('status IN (?, ?)', ('paid', 'shipped')) \
        .where('total_amount > ?', (Decimal('150.00'),)) \
        .order_by('total_amount DESC') \
        .limit(2)

    # Execute the query
    filtered_orders = complex_query.all()

    # Verify the results
    assert 0 < len(filtered_orders) <= 2
    assert all(order.status in ('paid', 'shipped') for order in filtered_orders)
    assert all(order.total_amount > Decimal('150.00') for order in filtered_orders)

    # Check ordering
    if len(filtered_orders) > 1:
        assert filtered_orders[0].total_amount >= filtered_orders[1].total_amount

    # Test that we can continue to build on the relation query
    first_order = filtered_orders[0] if filtered_orders else None
    if first_order:
        # Get items for the first order
        items_query = first_order.items_query().order_by('quantity DESC')
        items = items_query.all()

        assert len(items) > 0
        assert all(item.order_id == first_order.id for item in items)

        # Test further query refinement
        expensive_items = first_order.items_query() \
            .where('unit_price >= ?', (Decimal('100.00'),)) \
            .all()

        assert len(expensive_items) > 0
        assert all(item.unit_price >= Decimal('100.00') for item in expensive_items)


def test_cte_relation_query_methods_aggregation(blog_fixtures):
    """Test relation query methods with aggregation and CTE."""
    User, Post, Comment = blog_fixtures

    # Create test data
    user = User(username='aggregation_test', email='agg@example.com', age=40)
    user.save()

    # Create posts
    posts = []
    for i in range(3):
        post = Post(
            user_id=user.id,
            title=f'Post {i + 1}',
            content=f'Content of post {i + 1}',
            status='published'
        )
        post.save()
        posts.append(post)

    # Add varying numbers of comments to each post
    for i, post in enumerate(posts):
        # Post i gets i+1 comments
        for j in range(i + 1):
            comment = Comment(
                user_id=user.id,
                post_id=post.id,
                content=f'Comment {j + 1} on post {i + 1}',
                is_hidden=False
            )
            comment.save()

    # Create a CTE for the user's posts
    query = Post.query().with_cte(
        'user_posts',
        f"""
        SELECT * FROM {Post.__table_name__}
        WHERE user_id = {user.id}
        """
    ).from_cte('user_posts')

    # Get the posts
    cte_posts = query.all()
    assert len(cte_posts) == 3

    # Test aggregate functions on relation query
    for i, post in enumerate(cte_posts):
        # Count comments
        comment_count = post.comments_query().count()
        assert comment_count == i + 1  # Post i has i+1 comments

        # Test more complex aggregation
        if comment_count > 0:
            comment_stats = post.comments_query() \
                .select('COUNT(*) as total', 'MAX(id) as newest_id') \
                .to_dict(direct_dict=True) \
                .one()

            assert comment_stats is not None
            assert int(comment_stats['total']) == i + 1


def test_cte_relation_query_methods_with_joins(order_fixtures):
    """Test relation query methods with joins and CTE."""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='join_test', email='join@example.com', age=45)
    user.save()

    # Create orders
    orders = []
    for i in range(2):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status='paid',
            total_amount=Decimal(f'{(i + 1) * 200}.00')
        )
        order.save()
        orders.append(order)

    # Create items with different categories
    categories = ['electronics', 'clothing', 'books', 'food']
    for i, order in enumerate(orders):
        for j in range(3):
            category = categories[j % len(categories)]
            item = OrderItem(
                order_id=order.id,
                product_name=f'Product {category}',
                category=category,
                quantity=j + 1,
                unit_price=Decimal('50.00'),
                subtotal=Decimal(f'{(j + 1) * 50}.00')
            )
            item.save()

    # Create a CTE for user's orders
    query = Order.query().with_cte(
        'user_orders',
        f"""
        SELECT * FROM {Order.__table_name__}
        WHERE user_id = {user.id}
        """
    ).from_cte('user_orders')

    # Get orders
    cte_orders = query.all()
    assert len(cte_orders) == 2

    # Test relation query with joins
    first_order = cte_orders[0]

    # Join with another table (simulating a category table)
    joined_query = first_order.items_query() \
        .select('order_items.*', 'order_items.category') \
        .where('category = ?', ('electronics',))

    electronic_items = joined_query.all()

    # Verify the results
    assert len(electronic_items) > 0
    assert all(item.category == 'electronics' for item in electronic_items)

    # Test more complex joins if available
    if hasattr(Order, 'left_join'):
        # If the left_join method is available, use it
        complex_query = Order.query() \
            .left_join('order_items', 'order_id') \
            .where('orders.user_id = ?', (user.id,)) \
            .select('orders.id', 'orders.order_number', 'COUNT(order_items.id) as item_count') \
            .group_by('orders.id') \
            .to_dict(direct_dict=True)

        results = complex_query.all()
        assert len(results) == 2

        for result in results:
            assert int(result['item_count']) == 3  # Each order has 3 items


def test_cte_relation_query_methods_with_custom_where(blog_fixtures):
    """Test relation query methods with custom where conditions and CTE."""
    User, Post, Comment = blog_fixtures

    # Create test data
    user = User(username='custom_where_test', email='where@example.com', age=50)
    user.save()

    # Create posts with different creation dates
    from datetime import datetime, timedelta

    base_date = datetime.now()
    for i in range(5):
        created_at = base_date - timedelta(days=i * 10)
        post = Post(
            user_id=user.id,
            title=f'Post {i + 1}',
            content=f'Content of post {i + 1}',
            status='published',
            created_at=created_at
        )
        post.save()

    # Create a CTE for the user
    query = User.query().with_cte(
        'test_user',
        f"""
        SELECT * FROM {User.__table_name__}
        WHERE id = {user.id}
        """
    ).from_cte('test_user')

    # Get the user from CTE
    cte_user = query.one()
    assert cte_user is not None

    # Test date-based filtering on relation query
    one_month_ago = base_date - timedelta(days=30)
    recent_posts_query = cte_user.posts_query() \
        .where('created_at > ?', (one_month_ago,))

    recent_posts = recent_posts_query.all()

    # Verify the results - should find posts less than 30 days old
    assert len(recent_posts) > 0
    assert all(post.created_at > one_month_ago for post in recent_posts)

    # Test between condition if available
    if hasattr(cte_user.posts_query(), 'between'):
        two_months_ago = base_date - timedelta(days=60)

        date_range_posts = cte_user.posts_query() \
            .between('created_at', two_months_ago, one_month_ago) \
            .all()

        # Verify the results
        assert len(date_range_posts) > 0
        for post in date_range_posts:
            assert two_months_ago <= post.created_at <= one_month_ago

    # Test custom where conditions like LIKE
    if hasattr(cte_user.posts_query(), 'like'):
        title_search = cte_user.posts_query() \
            .like('title', 'Post %') \
            .all()

        assert len(title_search) == 5  # All posts match "Post %"