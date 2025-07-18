# tests/rhosocial/activerecord_test/query/test_relations_with_query.py
"""Test cases for relation eager loading query execution."""

from decimal import Decimal
from typing import List, Tuple

import pytest

from src.rhosocial.activerecord.backend import RecordNotFound
from .utils import create_order_fixtures, create_blog_fixtures

order_fixtures = create_order_fixtures()
blog_fixtures = create_blog_fixtures()


@pytest.fixture
def setup_order_data(order_fixtures) -> Tuple[List[int], List[int]]:
    """Create sample order data for testing."""
    User, Order, OrderItem = order_fixtures

    # Create test users
    user1 = User(username="user1", email="user1@example.com", age=25)
    user1.save()
    user2 = User(username="user2", email="user2@example.com", age=30)
    user2.save()

    # Create orders for users
    order1 = Order(
        user_id=user1.id,
        order_number="ORD001",
        total_amount=Decimal("100.00")
    )
    order1.save()

    order2 = Order(
        user_id=user1.id,
        order_number="ORD002",
        total_amount=Decimal("200.00")
    )
    order2.save()

    order3 = Order(
        user_id=user2.id,
        order_number="ORD003",
        total_amount=Decimal("150.00")
    )
    order3.save()

    # Create order items
    item1 = OrderItem(
        order_id=order1.id,
        product_name="Product 1",
        quantity=2,
        unit_price=Decimal("50.00"),
        subtotal=Decimal("100.00")
    )
    item1.save()

    item2 = OrderItem(
        order_id=order2.id,
        product_name="Product 2",
        quantity=1,
        unit_price=Decimal("200.00"),
        subtotal=Decimal("200.00")
    )
    item2.save()

    return [user1.id, user2.id], [order1.id, order2.id, order3.id]


@pytest.fixture
def setup_blog_data(blog_fixtures) -> Tuple[List[int], List[int], List[int]]:
    """Create sample blog data for testing."""
    User, Post, Comment = blog_fixtures

    # Create test users
    user1 = User(username="blogger1", email="blogger1@example.com", age=28)
    user1.save()
    user2 = User(username="blogger2", email="blogger2@example.com", age=35)
    user2.save()

    # Create posts
    post1 = Post(
        user_id=user1.id,
        title="First Post",
        content="Content 1"
    )
    post1.save()

    post2 = Post(
        user_id=user1.id,
        title="Second Post",
        content="Content 2"
    )
    post2.save()

    # Create comments
    comment1 = Comment(
        user_id=user2.id,
        post_id=post1.id,
        content="Great post!"
    )
    comment1.save()

    comment2 = Comment(
        user_id=user1.id,
        post_id=post1.id,
        content="Thanks!"
    )
    comment2.save()

    return [user1.id, user2.id], [post1.id, post2.id], [comment1.id, comment2.id]


def test_load_single_belongs_to_relation(order_fixtures, setup_order_data):
    """Test loading a single belongs-to relation (Order -> User)."""
    User, Order, _ = order_fixtures
    user_ids, order_ids = setup_order_data

    # Query order with user
    order = Order.query().with_("user").where("id = ?", (order_ids[0],)).one()

    assert order is not None
    assert order.user() is not None  # 修改为函数调用
    assert order.user().id == user_ids[0]
    assert order.user().username == "user1"

    # 测试关系查询函数
    user_query = order.user_query()
    assert user_query is not None
    assert user_query.one().id == user_ids[0]


def test_load_has_many_relation(order_fixtures, setup_order_data):
    """Test loading a has-many relation (Order -> OrderItems)."""
    _, Order, OrderItem = order_fixtures
    _, order_ids = setup_order_data

    # Query order with items
    order = Order.query().with_("items").where("id = ?", (order_ids[0],)).one()

    assert order is not None
    assert len(order.items()) == 1  # 修改为函数调用
    assert order.items()[0].product_name == "Product 1", order.items()[0]
    assert order.items()[0].quantity == 2

    # 测试关系查询函数
    items_query = order.items_query()
    assert items_query is not None
    assert items_query.count() == 1


def test_load_belongs_to_with_conditions(order_fixtures, setup_order_data):
    """Test loading a belongs-to relation with conditions."""
    User, Order, _ = order_fixtures
    user_ids, order_ids = setup_order_data

    # Query order with active user only
    query = Order.query().with_(
        ("user", lambda q: q.where("age > ?", (20,)))
    ).where("id = ?", (order_ids[0],))

    order = query.one()
    assert order is not None
    assert order.user() is not None  # 修改为函数调用
    assert order.user().age > 20


def test_load_multiple_relations(order_fixtures, setup_order_data):
    """Test loading multiple relations simultaneously."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # Query order with both user and items
    order = Order.query() \
        .with_("user", "items") \
        .where("id = ?", (order_ids[0],)) \
        .one()

    assert order is not None
    assert order.user() is not None  # 修改为函数调用
    assert len(order.items()) == 1  # 修改为函数调用
    assert order.user().id == user_ids[0]
    assert order.items()[0].product_name == "Product 1"


def test_load_nested_relations_blog(blog_fixtures, setup_blog_data):
    """Test loading nested relations in blog context."""
    User, Post, Comment = blog_fixtures
    user_ids, post_ids, comment_ids = setup_blog_data

    # Query post with user and comments
    post = Post.query() \
        .with_("user", "comments.user") \
        .where("id = ?", (post_ids[0],)) \
        .one()

    assert post is not None
    assert post.user() is not None  # 修改为函数调用
    assert len(post.comments()) == 2  # 修改为函数调用
    assert post.comments()[0].user() is not None  # 修改为函数调用
    assert post.comments()[1].user() is not None  # 修改为函数调用

    # 测试关系查询函数
    comments_query = post.comments_query()
    assert comments_query is not None
    assert comments_query.count() == 2


def test_load_empty_relations(order_fixtures, setup_order_data):
    """Test loading relations that return no results."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # Query order with no items
    order = Order.query() \
        .with_("items") \
        .where("id = ?", (order_ids[2],)) \
        .one()

    assert order is not None
    assert len(order.items()) == 0, order.items()[0]  # 修改为函数调用


def test_load_filtered_has_many_relation(order_fixtures, setup_order_data):
    """Test loading filtered has-many relation."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # Query user with filtered orders
    user = User.query() \
        .with_(("orders",
                lambda q: q.where("total_amount > ?", (150,))
                )) \
        .where("id = ?", (user_ids[0],)) \
        .one()

    assert user is not None
    assert len(user.orders()) == 1  # 修改为函数调用
    assert user.orders()[0].total_amount == Decimal("200.00")


def test_load_relations_on_collection(order_fixtures, setup_order_data):
    """Test loading relations on a collection of records."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # Query multiple orders with relations
    orders = Order.query() \
        .with_("user", "items") \
        .where("user_id = ?", (user_ids[0],)) \
        .all()

    assert len(orders) == 2
    for order in orders:
        assert order.user() is not None  # 修改为函数调用
        assert order.user().id == user_ids[0]
        assert len(order.items()) > 0, order  # 修改为函数调用


def test_load_complex_blog_relations(blog_fixtures, setup_blog_data):
    """Test loading complex relations in blog context."""
    User, Post, Comment = blog_fixtures
    user_ids, post_ids, comment_ids = setup_blog_data

    # Query user with posts and their comments
    user = User.query() \
        .with_("posts.comments") \
        .where("id = ?", (user_ids[0],)) \
        .one()

    assert user is not None
    assert len(user.posts()) == 2  # 修改为函数调用
    # First post has comments
    assert len(user.posts()[0].comments()) == 2  # 修改为函数调用
    # Second post has no comments
    assert len(user.posts()[1].comments()) == 0  # 修改为函数调用


def test_relation_one_or_fail(order_fixtures, setup_order_data):
    """Test one_or_fail with relations."""
    User, Order, _ = order_fixtures
    user_ids, order_ids = setup_order_data

    # Test successful case
    order = Order.query() \
        .with_("user") \
        .where("id = ?", (order_ids[0],)) \
        .one_or_fail()

    assert order is not None
    assert order.user is not None

    # Test failure case
    with pytest.raises(RecordNotFound):
        Order.query() \
            .with_("user") \
            .where("id = ?", (99999,)) \
            .one_or_fail()


def test_relation_query_with_no_results(order_fixtures, setup_order_data):
    """Test relation loading when main query returns no results."""
    User, Order, _ = order_fixtures

    # Query with non-existent ID
    order = Order.query() \
        .with_("user", "items") \
        .where("id = ?", (99999,)) \
        .one()

    assert order is None
