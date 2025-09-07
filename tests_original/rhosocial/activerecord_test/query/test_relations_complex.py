# tests/rhosocial/activerecord_test/query/test_relations_complex.py
"""Test cases for complex relation loading scenarios with with_() method."""
from decimal import Decimal
from unittest.mock import patch

import pytest

from rhosocial.activerecord.query.relational import RelationNotFoundError
from .utils import create_combined_fixtures

# Use the combined fixture directly from utils.py
combined_fixtures = create_combined_fixtures()


@pytest.fixture
def setup_complex_data(combined_fixtures):
    """Create complex data structure for testing relation loading.

    Sets up users with orders, order items, posts, and comments in a
    connected graph to test various complex relation loading scenarios.
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures

    # Create test users
    users = []
    for i in range(3):
        user = User(
            username=f"user{i + 1}",
            email=f"user{i + 1}@example.com",
            age=25 + i * 5,
            is_active=True
        )
        user.save()
        users.append(user)

    # Create orders for users
    orders = []
    for i in range(5):
        user_index = i % len(users)
        order = Order(
            user_id=users[user_index].id,
            order_number=f"ORD00{i + 1}",
            total_amount=Decimal(f"{(i + 1) * 100}.00"),
            status="pending" if i % 2 == 0 else "completed"
        )
        order.save()
        orders.append(order)

    # Create order items
    items = []
    for i, order in enumerate(orders):
        # Each order gets 1-3 items
        for j in range(1, i % 3 + 2):
            item = OrderItem(
                order_id=order.id,
                product_name=f"Product {i + 1}-{j}",
                quantity=j,
                unit_price=Decimal(f"{(i + 1) * 50}.00"),
                subtotal=Decimal(f"{(i + 1) * 50 * j}.00")
            )
            item.save()
            items.append(item)

    # Create blog posts
    posts = []
    for i, user in enumerate(users):
        # Each user gets 2 posts
        for j in range(2):
            post = Post(
                user_id=user.id,
                title=f"Post {i + 1}-{j + 1}",
                content=f"Content for post {i + 1}-{j + 1}",
                status="published" if j % 2 == 0 else "draft"
            )
            post.save()
            posts.append(post)

    # Create comments
    comments = []
    for i, post in enumerate(posts):
        # Each post gets comments from all users
        for j, user in enumerate(users):
            if i % 2 == 0 or j == 0:  # Not all posts get comments from all users
                comment = Comment(
                    user_id=user.id,
                    post_id=post.id,
                    content=f"Comment from user{j + 1} on post {i + 1}",
                    is_hidden=False
                )
                comment.save()
                comments.append(comment)

    return {
        'users': users,
        'orders': orders,
        'items': items,
        'posts': posts,
        'comments': comments
    }


def test_with_mixed_usage_patterns(combined_fixtures, setup_complex_data):
    """Test with_() method with mixed usage patterns.

    Tests the ability to combine multiple relation types in a single with_() call:
    - Simple relation ("user")
    - Nested relation ("user.posts")
    - Relation with query modifier ("items", lambda...)
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Define query modifier
    def item_modifier(q):
        return q.where("quantity > ?", (1,))

    # Construct query with mixed patterns
    query = Order.query().with_(
        "user",
        "user.posts",
        ("items", item_modifier)
    )

    # Execute query and verify results
    orders = query.where("id = ?", (data['orders'][2].id,)).all()

    assert len(orders) == 1
    order = orders[0]

    # Verify 'user' relation was loaded
    assert order.user() is not None
    assert order.user().id == data['orders'][2].user_id

    # Verify 'user.posts' relation was loaded
    assert len(order.user().posts()) > 0

    # Verify 'items' relation was loaded with modifier applied
    items = order.items()
    assert all(item.quantity > 1 for item in items)


def test_with_overlapping_relations(combined_fixtures, setup_complex_data):
    """Test with_() method handling of overlapping relation paths.

    Tests how the system handles overlapping relation paths:
    - Adding "user.posts" and then just "posts"
    - Verifies that both are loaded correctly despite overlap
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Query user with overlapping relations
    user = User.query() \
        .with_("posts.comments") \
        .with_("posts") \
        .where("id = ?", (data['users'][0].id,)) \
        .one()

    assert user is not None

    # Verify 'posts' relation was loaded
    posts = user.posts()
    assert len(posts) > 0

    # Verify 'posts.comments' relation was also loaded
    for post in posts:
        assert hasattr(post, '_relation_cache_comments')  # Check if comments were cached
        comments = post.comments()
        if len(comments) > 0:  # Some posts may not have comments
            assert all(hasattr(c, 'content') for c in comments)


def test_with_multiple_chained_modifiers(combined_fixtures, setup_complex_data):
    """Test with_() method with multiple chained calls using query modifiers.

    Tests using different modifiers in separate chained with_() calls:
    - First modifier for "user" relation
    - Second modifier for "items" relation
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Construct query with chained modifiers
    query = Order.query() \
        .with_(("user", lambda q: q.where("is_active = ?", (True,)))) \
        .with_(("items", lambda q: q.where("quantity > ?", (1,))))

    # Execute query
    orders = query.all()

    # Not all orders will have associated items with quantity > 1
    orders_with_items = [o for o in orders if o.items()]

    # Verify results - users should all be active
    for order in orders:
        assert order.user() is not None
        assert order.user().is_active is True

    # Items should all have quantity > 1
    for order in orders_with_items:
        assert all(item.quantity > 1 for item in order.items())


def test_with_duplicate_modifiers_in_chain(combined_fixtures, setup_complex_data):
    """Test with_() method with duplicate modifiers in chain.

    Tests how the system handles applying multiple modifiers to the same relation
    in separate with_() calls. The last modifier should take precedence.
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Construct query with duplicate modifiers
    query = User.query() \
        .with_(("posts", lambda q: q.where("status = ?", ("draft",)))) \
        .with_(("posts", lambda q: q.where("status = ?", ("published",))))

    # Execute query
    users = query.all()

    # Verify results - only published posts should be loaded
    # since the second modifier should override the first
    for user in users:
        posts = user.posts()
        if posts:  # Only check users with posts
            assert all(post.status == "published" for post in posts)


def test_with_deeply_nested_relations_and_modifiers(combined_fixtures, setup_complex_data):
    """Test with_() method with deeply nested relations and modifiers.

    Tests loading deeply nested relation paths with modifiers at different levels:
    - Deep path: "posts.comments.user"
    - Modifier applied to middle level: "posts.comments"
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Construct query with deeply nested relations and modifiers
    query = User.query() \
        .with_("posts") \
        .with_(("posts.comments", lambda q: q.where("is_hidden = ?", (False,)))) \
        .with_("posts.comments.user")

    # Execute query
    users = query.all()
    user_with_data = next(u for u in users if u.posts() and
                          any(p.comments() for p in u.posts()))

    # Verify results - deep relations should be loaded
    for post in user_with_data.posts():
        if post.comments():
            # Comments should all be visible (not hidden)
            assert all(not comment.is_hidden for comment in post.comments())

            # Comment users should be loaded
            for comment in post.comments():
                assert comment.user() is not None
                assert hasattr(comment.user(), 'username')


def test_with_out_of_order_relations(combined_fixtures, setup_complex_data):
    """Test with_() method with out-of-order relation declarations.

    Tests declaring nested relations before their parent relations:
    - First loading deep path: "posts.comments.user"
    - Then loading just: "posts"
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Construct query with out-of-order relation declarations
    query = User.query() \
        .with_("posts.comments.user") \
        .with_("posts")

    # Execute query
    users = query.all()
    user_with_data = next(u for u in users if u.posts() and
                          any(p.comments() for p in u.posts()))

    # Verify results
    for post in user_with_data.posts():
        if post.comments():
            for comment in post.comments():
                # Should have loaded the user relation
                assert comment.user() is not None


def test_with_cross_referencing_relations(combined_fixtures, setup_complex_data):
    """Test with_() method with cross-referencing relations.

    Tests loading relations that reference back to the original model:
    - "posts.comments.user.posts" creates a cycle user -> posts -> comments -> user -> posts
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Construct query with cross-referencing relations
    query = User.query().with_("posts.comments.user.posts")

    # Execute query
    users = query.all()

    # Find a user with data for testing
    user_with_comments = None
    for user in users:
        has_comments = False
        for post in user.posts():
            if post.comments():
                has_comments = True
                break
        if has_comments:
            user_with_comments = user
            break

    if user_with_comments:
        # Verify cross-references are loaded
        for post in user_with_comments.posts():
            if post.comments():
                for comment in post.comments():
                    comment_user = comment.user()
                    assert comment_user is not None

                    # The comment user should have their posts loaded too
                    user_posts = comment_user.posts()
                    assert isinstance(user_posts, list)


def test_with_combined_complex_scenarios(combined_fixtures, setup_complex_data):
    """Test with_() method with combined complex scenarios.

    Tests combining multiple complex scenarios in a single query:
    - Deeply nested relations: "posts.comments.user"
    - Query modifier on middle relation: ("posts", lambda...)
    - Multiple relations in different with_() calls
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Construct query with multiple complex scenarios
    query = User.query() \
        .with_("posts.comments.user") \
        .with_(("posts", lambda q: q.where("status = ?", ("published",)))) \
        .with_("comments", "posts.comments")

    # Execute query
    users = query.all()

    # Find a user with all the required relations
    test_user = None
    for user in users:
        if user.posts() and any(p.comments() for p in user.posts()):
            test_user = user
            break

    if not test_user:
        pytest.skip("No user with required relations found")

    # Verify results
    # 1. Posts should all be published
    assert all(post.status == "published" for post in test_user.posts())

    # 2. Post comments should have users loaded
    for post in test_user.posts():
        for comment in post.comments():
            assert comment.user() is not None

    # 3. Direct comments relation should be loaded
    if hasattr(test_user, 'comments'):
        assert isinstance(test_user.comments(), list)


def test_with_invalid_relation_handling(combined_fixtures, setup_complex_data):
    """Test with_() method handling of invalid relation names.

    Tests how the system handles requests for non-existent relations:
    - Attempt to load a relation that doesn't exist
    - Verify appropriate error handling
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Use mock to bypass relation validation during query building
    with patch.object(User.query().__class__, '_validate_complete_relation_path', return_value=None):
        # Create query with invalid relation
        query = User.query().with_("non_existent_relation")

        # The error should occur only when executing the query and trying to load the relation
        users = query.all()

        # Accessing the invalid relation should raise an appropriate error
        with pytest.raises(Exception) as excinfo:
            # This should trigger relation loading attempt
            for user in users:
                # Try to access the non-existent relation
                getattr(user, 'non_existent_relation')()

        # Verify error message contains relation information
        error_message = str(excinfo.value).lower()
        assert "relation" in error_message or "attribute" in error_message


def test_with_large_number_of_relations(combined_fixtures, setup_complex_data):
    """Test with_() method with a large number of relations.

    Tests the system's ability to handle a large number of with_() calls:
    - Adds a large number of relations (though most will be invalid)
    - Verifies the system doesn't crash and handles it appropriately
    """
    from unittest.mock import patch

    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Create a simpler implementation
    # Instead of using side_effect which can be tricky with method arguments,
    # we'll directly mock the method to return None (allow all relations)
    with patch.object(User.query().__class__, '_validate_complete_relation_path', return_value=None):
        # Start with valid relations to ensure some success
        query = User.query().with_("posts", "comments")

        # Add many more relations (most will be invalid)
        for i in range(10):
            query = query.with_(f"relation{i}")

        # Execute query - should not crash
        users = query.all()

        # Verify valid relations still work
        for user in users:
            # These should work
            assert isinstance(user.posts(), list)
            if hasattr(user, 'comments'):
                assert isinstance(user.comments(), list)


def test_with_overlapping_modifiers(combined_fixtures, setup_complex_data):
    """Test with_() method with overlapping query modifiers.

    Tests applying multiple modifiers with overlapping conditions:
    - First modifier limits to published posts
    - Second modifier limits by creation date
    - Both conditions should be applied (AND logic)
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Get a reference date from an existing post
    reference_post = data['posts'][0]
    reference_date = reference_post.created_at

    # Create query with overlapping modifiers
    query = User.query() \
        .with_(("posts", lambda q: q.where("status = ?", ("published",)))) \
        .with_(("posts", lambda q: q.where("created_at <= ?", (reference_date,))))

    # Execute query
    users = query.all()

    # Verify results - should meet both conditions
    for user in users:
        posts = user.posts()
        if posts:
            assert all(post.status == "published" for post in posts)
            assert all(post.created_at <= reference_date for post in posts)


def test_with_circular_reference_handling(combined_fixtures, setup_complex_data):
    """Test with_() method handling of potential circular references.

    Tests loading relations that could create circular references:
    - Deep path that goes through the same models multiple times
    - Verifies the system handles this appropriately without infinite recursion

    This test respects the instance-level caching design where:
    - New instances obtained through relation chains maintain their own cache
    - Different instances (even of same record) don't share cache state
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Create query with potential circular reference path
    query = User.query().with_("posts.comments.user.posts")

    # Execute query - should not cause infinite recursion
    users = query.all()

    # Find a user with the necessary data
    test_user = None
    for user in users:
        if user.posts() and any(p.comments() for p in user.posts()):
            test_user = user
            break

    if not test_user:
        pytest.skip("No user with required relations found")

    # Navigate through the relation chain to verify loading
    for post in test_user.posts():
        if post.comments():
            for comment in post.comments():
                comment_user = comment.user()
                assert comment_user is not None

                # The comment_user is a different instance than test_user
                # even if it represents the same database record

                # Verify we can access its posts (loaded by the with_() call)
                user_posts = comment_user.posts()
                assert isinstance(user_posts, list)

                # In instance-level caching, this new user instance
                # maintains its own separate cache, so we don't expect
                # it to have the comments relation loaded

                # We can explicitly load additional relations on this new instance if needed
                if user_posts:
                    # Example of explicitly loading another relation on the new instance
                    comment_user_with_more = User.query().with_("posts.comments").where(
                        "id = ?", (comment_user.id,)
                    ).one()

                    if comment_user_with_more and comment_user_with_more.posts():
                        # Now we can access comments on posts for this explicitly loaded instance
                        post_with_comments = next((p for p in comment_user_with_more.posts()
                                                   if hasattr(p, 'comments')), None)
                        if post_with_comments:
                            assert isinstance(post_with_comments.comments(), list)


def test_with_relation_overrides_in_inheritance(combined_fixtures, setup_complex_data):
    """Test with_() method with relation overrides in class inheritance.

    Tests how with_() handles relations that are overridden in subclasses:
    - Base class defines a relation
    - Subclass overrides the same relation with different config
    - Verifies the correct relation is used
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Define a custom Order subclass with overridden relations
    class CustomOrder(Order):
        # Override the items relation with a query modifier
        items = Order.items  # Reuse the descriptor but customize in with_()

    # Create an instance of the original Order
    original_order = Order.query().with_("items").where("id = ?", (data['orders'][0].id,)).one()

    # Create an instance of CustomOrder (using same DB record)
    custom_order = CustomOrder.query() \
        .with_(("items", lambda q: q.where("quantity > ?", (1,)))) \
        .where("id = ?", (data['orders'][0].id,)) \
        .one()

    # Verify original order has all items
    assert len(original_order.items()) >= len(custom_order.items())

    # Verify custom order has only items with quantity > 1
    assert all(item.quantity > 1 for item in custom_order.items())


def test_with_nested_query_modifiers(combined_fixtures, setup_complex_data):
    """Test with_() method with query modifiers at multiple nesting levels.

    Tests applying different query modifiers at different levels of nesting:
    - Modifier for "posts" relation
    - Different modifier for "posts.comments" relation
    - Verifies both modifiers are correctly applied
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Create query with nested modifiers
    query = User.query() \
        .with_(("posts", lambda q: q.where("status = ?", ("published",)))) \
        .with_(("posts.comments", lambda q: q.where("is_hidden = ?", (False,))))

    # Execute query
    users = query.all()

    # Verify results
    for user in users:
        # Posts should all be published
        posts = user.posts()
        if posts:
            assert all(post.status == "published" for post in posts)

            # Comments should all be visible
            for post in posts:
                comments = post.comments()
                if comments:
                    assert all(not comment.is_hidden for comment in comments)


def test_with_complex_chain_and_modifiers_preservation(combined_fixtures, setup_complex_data):
    """Test that modifiers are correctly preserved in complex relation chains.

    This test verifies:
    1. Complex relation chains with multiple levels are properly processed
    2. Query modifiers are correctly associated with their target relations
    3. Each level in the chain maintains its own modifier
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Create tracking variables to verify modifier execution
    executed_modifiers = set()

    # Define modifiers with tracking
    def track_modifier(name):
        def modifier(q):
            executed_modifiers.add(name)
            return q.where(f"{name}_condition = ?", (True,))

        return modifier

    # Create specific modifiers for different paths
    # Using actual relations defined on the User model (posts, comments, orders)
    posts_modifier = track_modifier('posts')
    comments_modifier = track_modifier('comments')
    orders_modifier = track_modifier('orders')

    # Apply modifiers to relations at different levels
    query = User.query().with_(
        ('posts', posts_modifier),
        ('posts.comments', comments_modifier),
        ('orders', orders_modifier)
    )

    # Verify the modifiers are correctly associated with their targets
    configs = getattr(query, '_eager_loads')

    # Test key existence
    assert 'posts' in configs, "The 'posts' relation should be configured"
    assert 'posts.comments' in configs, "The 'posts.comments' relation should be configured"
    assert 'orders' in configs, "The 'orders' relation should be configured"

    # Test modifier assignment
    assert configs['posts'].query_modifier == posts_modifier, "'posts' should have posts_modifier assigned"
    assert configs[
               'posts.comments'].query_modifier == comments_modifier, "'posts.comments' should have comments_modifier assigned"
    assert configs['orders'].query_modifier == orders_modifier, "'orders' should have orders_modifier assigned"

    # Test nesting structure
    assert configs['posts'].nested == ['comments'], "'posts' should have 'comments' as nested relation"
    assert configs['posts.comments'].nested == [], "'posts.comments' should have no nested relations"
    assert configs['orders'].nested == [], "'orders' should have no nested relations"

    # Test error handling for non-existent relations
    with pytest.raises(RelationNotFoundError):
        User.query().with_('nonexistent_relation')

    # Execute a real query to test modifier execution
    test_user = data['users'][0]
    User.query().with_(
        ('posts', posts_modifier),
        ('posts.comments', comments_modifier),
        ('orders', orders_modifier)
    ).where('id = ?', (test_user.id,)).one()

    # Verify modifiers were executed (relations may not exist for all users)
    # Only verify the relations that definitely exist in the test data
    if test_user.posts():
        assert 'posts' in executed_modifiers, "Posts modifier should have been executed"


def test_with_query_modifier_priority_and_merging(combined_fixtures, setup_complex_data):
    """Test that query modifiers are applied in the correct order and later modifiers
    take precedence over earlier ones.

    This test verifies:
    1. When a relation is specified with a modifier multiple times,
       the last modifier completely replaces previous ones
    2. The execution order respects the replacement order
    3. The relation configuration is correctly updated
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Create tracking variables to verify execution order and state
    modifier_sequence = []
    applied_values = {}

    # Create modifiers that record their execution order and applied values
    def create_tracked_modifier(name, value):
        def modifier(q):
            modifier_sequence.append(name)
            applied_values[name] = value
            return q.where(f"test_field = ?", (value,))

        return modifier

    # Create specific modifiers for different scenarios
    early_posts_modifier = create_tracked_modifier('early_posts', 'early_value')
    later_posts_modifier = create_tracked_modifier('later_posts', 'later_value')
    early_comments_modifier = create_tracked_modifier('early_comments', 'early_comments_value')
    later_comments_modifier = create_tracked_modifier('later_comments', 'later_comments_value')

    # Test 1: Basic replacement - ensure later modifiers replace earlier ones
    query = User.query()

    # Step 1: Add initial modifiers
    query.with_(
        ('posts', early_posts_modifier),
        ('comments', early_comments_modifier)
    )

    # Step 1 verification
    configs = getattr(query, '_eager_loads')
    assert configs['posts'].query_modifier == early_posts_modifier, "posts should have early_posts_modifier initially"
    assert configs[
               'comments'].query_modifier == early_comments_modifier, "comments should have early_comments_modifier initially"

    # Step 2: Override the posts modifier with a new one
    query.with_(('posts', later_posts_modifier))

    # Step 2 verification
    assert configs[
               'posts'].query_modifier == later_posts_modifier, "posts should have later_posts_modifier after override"
    assert configs[
               'comments'].query_modifier == early_comments_modifier, "comments should still have early_comments_modifier (unchanged)"

    # Step 3: Override the comments modifier
    query.with_(('comments', later_comments_modifier))

    # Step 3 verification
    assert configs['posts'].query_modifier == later_posts_modifier, "posts should still have later_posts_modifier"
    assert configs[
               'comments'].query_modifier == later_comments_modifier, "comments should have later_comments_modifier after override"

    # Clear tracking and apply the query to a real record to verify execution
    modifier_sequence.clear()
    applied_values.clear()

    # Get a test user and execute the query
    test_user = data['users'][0]
    user = User.query().with_(
        ('posts', early_posts_modifier),
        ('comments', early_comments_modifier)
    ).with_(
        ('posts', later_posts_modifier)
    ).with_(
        ('comments', later_comments_modifier)
    ).where('id = ?', (test_user.id,)).one()

    # Verify that only the later modifiers were executed
    # Note: modifiers may not execute if relations don't exist or aren't loaded

    if 'later_posts' in modifier_sequence:
        # If posts modifier executed, verify early_posts was not executed
        assert 'early_posts' not in modifier_sequence, "early_posts_modifier should not execute when replaced"

    if 'later_comments' in modifier_sequence:
        # If comments modifier executed, verify early_comments was not executed
        assert 'early_comments' not in modifier_sequence, "early_comments_modifier should not execute when replaced"

    # Test 2: Complex scenario with multiple relation levels
    complex_query = User.query()

    # Define nested modifiers
    nested_m1 = create_tracked_modifier('nested_1', 'value1')
    nested_m2 = create_tracked_modifier('nested_2', 'value2')

    # Apply then override nested relation modifiers
    complex_query.with_(('posts.comments', nested_m1))
    complex_query.with_(('posts.comments', nested_m2))

    # Verify only the later modifier is used
    complex_configs = getattr(complex_query, '_eager_loads')
    assert complex_configs[
               'posts.comments'].query_modifier == nested_m2, "Later nested modifier should replace earlier one"

    # Clear tracking again
    modifier_sequence.clear()
    applied_values.clear()

    # Execute with a real user to verify modifiers
    if test_user.posts() and any(post.comments() for post in test_user.posts()):
        # Only execute if user has posts with comments
        complex_user = User.query().with_(
            ('posts.comments', nested_m1)
        ).with_(
            ('posts.comments', nested_m2)
        ).where('id = ?', (test_user.id,)).one()

        # Verify correct modifier execution
        if 'nested_2' in modifier_sequence:
            assert 'nested_1' not in modifier_sequence, "nested_1 should not execute when replaced by nested_2"
            assert applied_values.get('nested_2') == 'value2', "nested_2 should apply value2"


def test_with_complex_multibranch_relationships(combined_fixtures, setup_complex_data):
    """Test with_() method handling of complex multi-branch relationships.

    This test verifies:
    1. The system can correctly handle complex relation trees with multiple branches
    2. Different modifiers can be applied to different branches
    3. Nested relations are properly loaded even when defined in different with_() calls
    4. Relations can be overridden with new modifiers
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Test user with complex data
    test_user = data['users'][0]

    # Define query modifiers with tracking
    executed_paths = set()

    def track_path_modifier(path):
        def modifier(q):
            executed_paths.add(path)
            return q.where("id IS NOT NULL")  # Simple condition that won't filter anything

        return modifier

    # Create complex relation structure with multiple branches
    query = User.query().with_(
        # Branch 1: user -> posts -> comments
        ('posts', track_path_modifier('posts')),
        ('posts.comments', track_path_modifier('posts.comments')),

        # Branch 2: user -> orders -> items
        ('orders', track_path_modifier('orders')),
        ('orders.items', track_path_modifier('orders.items'))
    )

    # Add another branch after initial configuration
    query = query.with_(
        # Branch 3: user -> posts -> comments -> user (circular)
        ('posts.comments.user', track_path_modifier('posts.comments.user'))
    )

    # Override a previously defined modifier
    new_posts_modifier = track_path_modifier('posts_new')
    query = query.with_(('posts', new_posts_modifier))

    # Verify relation configurations
    configs = getattr(query, '_eager_loads')

    # Check all paths are configured
    expected_paths = {
        'posts', 'posts.comments', 'posts.comments.user',
        'orders', 'orders.items'
    }
    assert set(configs.keys()) == expected_paths, f"Expected paths {expected_paths}, got {set(configs.keys())}"

    # Check nesting structure
    assert set(configs['posts'].nested) == {'comments'}, "posts should have comments as nested relation"
    assert set(configs['posts.comments'].nested) == {'user'}, "posts.comments should have user as nested relation"
    assert set(configs['orders'].nested) == {'items'}, "orders should have items as nested relation"

    # Check modifier overrides
    assert configs[
               'posts'].query_modifier == new_posts_modifier, "posts modifier should be overridden with new_posts_modifier"

    # Execute query to verify loading behavior
    user = User.query().with_(
        ('posts', new_posts_modifier),
        ('posts.comments', track_path_modifier('posts.comments')),
        ('orders', track_path_modifier('orders')),
        ('orders.items', track_path_modifier('orders.items')),
        ('posts.comments.user', track_path_modifier('posts.comments.user'))
    ).where('id = ?', (test_user.id,)).one()

    # Verify the correct paths were executed based on available relations
    # (some paths may not execute if relations don't exist)
    if user.posts():
        assert 'posts_new' in executed_paths, "posts modifier should have executed"

        if any(post.comments() for post in user.posts()):
            assert 'posts.comments' in executed_paths, "posts.comments modifier should have executed"

    if user.orders():
        assert 'orders' in executed_paths, "orders modifier should have executed"

        if any(order.items() for order in user.orders()):
            assert 'orders.items' in executed_paths, "orders.items modifier should have executed"


def test_with_missing_intermediate_relations(combined_fixtures, setup_complex_data):
    """Test with_() handling of missing intermediate relations in deep paths.

    Tests the system's ability to handle relation chains where intermediate
    relations are not explicitly declared. For example, declaring
    "posts.comments.user" without explicitly declaring "posts.comments".

    Verifies:
    1. Deep relations are correctly loaded despite missing intermediates
    2. Modifiers for deep paths are correctly applied
    3. System doesn't crash when navigating through the relation chain
    """
    User, Order, OrderItem, Post, Comment = combined_fixtures
    data = setup_complex_data

    # Create a tracking variable for applied modifiers
    applied_relations = set()

    # Define a deep relation path with modifiers
    def deep_user_modifier(q):
        applied_relations.add('posts.comments.user')
        return q.where("username LIKE ?", ("user%",))

    # Build query with a gap in the relation declarations
    # We declare:
    # - posts (direct relation)
    # - posts.comments.user (deep relation, skipping posts.comments)
    # But not posts.comments explicitly
    query = User.query() \
        .with_("posts") \
        .with_(("posts.comments.user", deep_user_modifier))

    # Execute the query
    users = query.all()

    # Find a user with the complete relation chain for testing
    test_user = None
    for user in users:
        if user.posts() and any(p.comments() for p in user.posts()):
            for post in user.posts():
                if post.comments() and any(c.user() for c in post.comments()):
                    test_user = user
                    break
            if test_user:
                break

    if not test_user:
        pytest.skip("No user with required complete relation chain found")

    # Navigate through the relation chain to verify everything loaded
    post_with_comments = None
    for post in test_user.posts():
        if post.comments():
            post_with_comments = post
            break

    assert post_with_comments is not None

    # Verify comments were loaded even though not explicitly declared
    assert post_with_comments.comments() is not None
    assert len(post_with_comments.comments()) > 0

    # Verify the deep relation (user) was loaded with the modifier applied
    for comment in post_with_comments.comments():
        comment_user = comment.user()
        if comment_user:
            # Modifier should have limited to usernames like "user%"
            assert comment_user.username.startswith("user")
            # Mark that we verified the deep relation
            applied_relations.add('verified')

    # Verify we actually found and verified at least one deep relation
    assert 'verified' in applied_relations

    # Verify the deep modifier was applied
    assert 'posts.comments.user' in applied_relations

    # Additional test: add a new with_() call for the intermediate relation
    # to verify that existing loaded relations aren't affected
    query = User.query() \
        .with_("posts") \
        .with_(("posts.comments.user", deep_user_modifier)) \
        .with_("posts.comments")  # Add intermediate relation last

    # Execute query again
    users = query.all()
    user = next((u for u in users if u.id == test_user.id), None)

    if user:
        # Everything should still work and have the same filters applied
        for post in user.posts():
            if post.comments():
                for comment in post.comments():
                    if comment.user():
                        assert comment.user().username.startswith("user")
