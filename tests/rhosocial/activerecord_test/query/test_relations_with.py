"""Test cases for relation eager loading configuration."""
from unittest.mock import patch

from .utils import create_order_fixtures

order_fixtures = create_order_fixtures()


def test_relations_with_single_relation(order_fixtures):
    """Test with_ method with a single relation string."""
    User, Order, _ = order_fixtures

    query = Order.query().with_("user")

    assert len(query._eager_loads) == 1
    assert "user" in query._eager_loads
    assert query._eager_loads["user"].name == "user"
    assert query._eager_loads["user"].nested == []
    assert query._eager_loads["user"].query_modifier is None


def test_relations_with_nested_relations(order_fixtures):
    """Test with_ method with nested relation paths."""
    User, Order, OrderItem = order_fixtures

    query = Order.query().with_("user.posts")

    assert len(query._eager_loads) == 2
    assert "user" in query._eager_loads
    assert "user.posts" in query._eager_loads
    assert query._eager_loads["user"].nested == ["posts"]
    assert query._eager_loads["user.posts"].name == "user.posts"
    assert query._eager_loads["user.posts"].nested == []


def test_relations_with_query_modifier(order_fixtures):
    """Test with_ method with query modifier function."""
    User, Order, _ = order_fixtures

    def modifier(q):
        return q.where("active = ?", True)

    query = Order.query().with_(("user", modifier))

    assert len(query._eager_loads) == 1
    assert "user" in query._eager_loads
    assert query._eager_loads["user"].query_modifier == modifier


def test_relations_with_multiple_relations(order_fixtures):
    """Test with_ method with multiple relations."""
    User, Order, OrderItem = order_fixtures

    def modifier(q):
        return q.where("status = ?", "active")

    query = Order.query().with_(
        "user",
        ("items", modifier),
        "user.posts"
    )

    assert len(query._eager_loads) == 3
    assert "user" in query._eager_loads
    assert "items" in query._eager_loads
    assert "user.posts" in query._eager_loads
    assert query._eager_loads["items"].query_modifier == modifier
    assert query._eager_loads["user"].nested == ["posts"]


def test_relations_with_duplicate_relations(order_fixtures):
    """Test with_ method handling of duplicate relations."""
    User, Order, _ = order_fixtures

    def modifier1(q):
        return q.where("status = ?", "active")

    def modifier2(q):
        return q.where("type = ?", "premium")

    # Add same relation twice with different modifiers
    query = Order.query().with_(
        ("user", modifier1),
        ("user", modifier2)
    )

    assert len(query._eager_loads) == 1
    assert "user" in query._eager_loads
    # Last modifier should override
    assert query._eager_loads["user"].query_modifier == modifier2


def test_relations_with_chained_calls(order_fixtures):
    """Test with_ method with multiple chained calls."""
    User, Order, _ = order_fixtures

    query = Order.query() \
        .with_("user") \
        .with_("items") \
        .with_("user.posts")

    assert len(query._eager_loads) == 3
    assert all(name in query._eager_loads
               for name in ["user", "items", "user.posts"])
    assert query._eager_loads["user"].nested == ["posts"]


def test_relations_with_deep_nesting(order_fixtures):
    """Test with_ method with deeply nested relations."""
    User, Order, _ = order_fixtures

    with patch.object(Order.query().__class__, '_validate_complete_relation_path', return_value=None):
        query = Order.query().with_("user.posts.comments.author")

        assert len(query._eager_loads) == 4
        assert all(name in query._eager_loads for name in [
            "user",
            "user.posts",
            "user.posts.comments",
            "user.posts.comments.author"
        ])

        # Verify nested relations are properly configured
        assert query._eager_loads["user"].nested == ["posts"]
        assert query._eager_loads["user.posts"].nested == ["comments"]
        assert query._eager_loads["user.posts.comments"].nested == ["author"]
        assert query._eager_loads["user.posts.comments.author"].nested == []