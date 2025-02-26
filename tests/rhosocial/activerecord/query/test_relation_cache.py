"""Test cases for relation caching behavior."""
from decimal import Decimal
from typing import List, Tuple

import pytest

from .utils import create_order_fixtures

order_fixtures = create_order_fixtures()


@pytest.fixture
def setup_order_data(order_fixtures) -> Tuple[List[int], List[int]]:
    """Create sample order data for testing."""
    User, Order, OrderItem = order_fixtures

    # Create test users
    user1 = User(username="cache_user1", email="cache_user1@example.com", age=25)
    user1.save()
    user2 = User(username="cache_user2", email="cache_user2@example.com", age=30)
    user2.save()

    # Create orders for users
    order1 = Order(
        user_id=user1.id,
        order_number="CACHE001",
        total_amount=Decimal("100.00")
    )
    order1.save()

    order2 = Order(
        user_id=user1.id,
        order_number="CACHE002",
        total_amount=Decimal("200.00")
    )
    order2.save()

    # Empty order (with no items)
    order3 = Order(
        user_id=user2.id,
        order_number="CACHE003",
        total_amount=Decimal("150.00")
    )
    order3.save()

    # Create order items
    item1 = OrderItem(
        order_id=order1.id,
        product_name="CacheProduct1",
        quantity=2,
        unit_price=Decimal("50.00"),
        subtotal=Decimal("100.00")
    )
    item1.save()

    item2 = OrderItem(
        order_id=order2.id,
        product_name="CacheProduct2",
        quantity=1,
        unit_price=Decimal("200.00"),
        subtotal=Decimal("200.00")
    )
    item2.save()

    return [user1.id, user2.id], [order1.id, order2.id, order3.id]


def test_basic_relation_caching(order_fixtures, setup_order_data):
    """Test basic relation caching behavior."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # First query - should load from database
    order = Order.query().with_("items").where("id = ?", (order_ids[0],)).one()

    assert order is not None
    assert len(order.items()) == 1
    assert order.items()[0].product_name == "CacheProduct1"

    # Second query - should use cache
    order_again = Order.query().with_("items").where("id = ?", (order_ids[0],)).one()

    assert order_again is not None
    assert len(order_again.items()) == 1
    assert order_again.items()[0].product_name == "CacheProduct1"


def test_empty_relation_consistency(order_fixtures, setup_order_data):
    """Test that empty relations are correctly loaded and not affected by other queries."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # First query - empty order (order3) should have no items
    order3 = Order.query().with_("items").where("id = ?", (order_ids[2],)).one()

    assert order3 is not None
    assert len(order3.items()) == 0, "Order3 should have no items initially"

    # Load a different order with items to potentially affect caching
    order1 = Order.query().with_("items").where("id = ?", (order_ids[0],)).one()
    assert len(order1.items()) > 0, "Order1 should have items"

    # Query order3 again - should still have no items regardless of other queries
    order3_again = Order.query().with_("items").where("id = ?", (order_ids[2],)).one()

    assert order3_again is not None
    assert order3 is not order3_again, "Each query should return a new instance"
    assert len(order3_again.items()) == 0, "Order3 should still have no items"

    # Add an item to order3
    new_item = OrderItem(
        order_id=order_ids[2],
        product_name="TestProduct",
        quantity=1,
        unit_price=Decimal("10.00"),
        subtotal=Decimal("10.00")
    )
    new_item.save()

    # Query again - should now have the new item
    order3_updated = Order.query().with_("items").where("id = ?", (order_ids[2],)).one()

    assert order3_updated is not None
    assert len(order3_updated.items()) == 1, "Order3 should now have one item"
    assert order3_updated.items()[0].product_name == "TestProduct"

    # Original instances should not be affected by new queries
    assert len(order3.items()) == 0, "Original order3 instance should still show no items"
    assert len(order3_again.items()) == 0, "Second order3 instance should still show no items"


def test_cache_isolation_between_records(order_fixtures, setup_order_data):
    """Test that relation caches are properly isolated between different records."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # Load both orders with their items
    orders = Order.query().with_("items").where("id IN (?,?)", (order_ids[0], order_ids[1])).all()

    assert len(orders) == 2
    # Sort by ID to ensure consistent order
    orders.sort(key=lambda o: o.id)

    # First order should have CacheProduct1
    assert len(orders[0].items()) == 1
    assert orders[0].items()[0].product_name == "CacheProduct1"

    # Second order should have CacheProduct2
    assert len(orders[1].items()) == 1
    assert orders[1].items()[0].product_name == "CacheProduct2", orders[1].items()[0]

    # Now test them individually to make sure caches don't interfere
    order1 = Order.query().with_("items").where("id = ?", (order_ids[0],)).one()
    assert len(order1.items()) == 1
    assert order1.items()[0].product_name == "CacheProduct1"

    order2 = Order.query().with_("items").where("id = ?", (order_ids[1],)).one()
    assert len(order2.items()) == 1
    assert order2.items()[0].product_name == "CacheProduct2", order2.items()[0]


def test_mixed_empty_and_populated_relations(order_fixtures, setup_order_data):
    """Test behavior when querying a mix of records with and without related data."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # Load all orders, including order3 which has no items
    orders = Order.query().with_("items").where("id IN (?,?,?)", order_ids).all()

    assert len(orders) == 3
    # Sort by ID for consistent testing
    orders.sort(key=lambda o: o.id)

    # Check each order's items
    assert len(orders[0].items()) == 1
    assert orders[0].items()[0].product_name == "CacheProduct1"

    assert len(orders[1].items()) == 1
    assert orders[1].items()[0].product_name == "CacheProduct2", orders[1].items()[0]

    assert len(orders[2].items()) == 0, orders[2].items()  # Empty relation


def test_cache_consistency_across_queries(order_fixtures, setup_order_data):
    """Test that relation cache remains consistent across multiple queries."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # First query - empty order (order3)
    order = Order.query().with_("items").where("id = ?", (order_ids[2],)).one()
    assert order is not None
    assert len(order.items()) == 0, order.items()

    # Add an item to the previously empty order
    new_item = OrderItem(
        order_id=order_ids[2],
        product_name="CacheProduct3",
        quantity=3,
        unit_price=Decimal("50.00"),
        subtotal=Decimal("150.00")
    )
    new_item.save()

    # Second query - should detect the change
    order_updated = Order.query().with_("items").where("id = ?", (order_ids[2],)).one()
    assert order_updated is not None
    assert len(order_updated.items()) == 1
    assert order_updated.items()[0].product_name == "CacheProduct3"


def test_repeated_empty_relation_queries(order_fixtures, setup_order_data):
    """Test repeatedly querying empty relations to check for cache consistency."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # Test empty relation multiple times
    for _ in range(5):  # Test 5 times to increase chance of detecting issues
        order = Order.query().with_("items").where("id = ?", (order_ids[2],)).one()
        assert order is not None
        assert len(order.items()) == 0, order.items()


def test_cache_clearing_on_update(order_fixtures, setup_order_data):
    """Test that relation cache is properly cleared when related records are updated."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # First query
    order = Order.query().with_("items").where("id = ?", (order_ids[0],)).one()
    assert len(order.items()) == 1
    assert order.items()[0].product_name == "CacheProduct1", order.items()[0]

    # Update the item
    item = order.items()[0]
    item.product_name = "CacheProductUpdated"
    item.save()

    # Query again - should get updated data
    order_updated = Order.query().with_("items").where("id = ?", (order_ids[0],)).one()
    assert len(order_updated.items()) == 1
    assert order_updated.items()[0].product_name == "CacheProductUpdated", order_updated.items()[0]


def test_relation_query_with_different_modifiers(order_fixtures, setup_order_data):
    """Test that different query modifiers don't interfere with relation caching."""
    User, Order, OrderItem = order_fixtures
    user_ids, order_ids = setup_order_data

    # First query - get all items
    order = Order.query().with_("items").where("id = ?", (order_ids[0],)).one()
    assert len(order.items()) == 1

    # Second query - get items with a condition
    order_with_condition = Order.query().with_(
        ("items", lambda q: q.where("quantity > ?", (1,)))
    ).where("id = ?", (order_ids[0],)).one()

    assert len(order_with_condition.items()) == 1, order_with_condition  # Still has 1 item (quantity = 2)

    # Third query - get items with different condition
    order_with_different_condition = Order.query().with_(
        ("items", lambda q: q.where("quantity > ?", (2,)))
    ).where("id = ?", (order_ids[0],)).one()

    assert len(order_with_different_condition.items()) == 0, order_with_condition.items()[0]  # No items (quantity <= 2)


def test_relation_loading_on_empty_result_set(order_fixtures, setup_order_data):
    """Test relation loading behavior when primary query returns no results."""
    User, Order, OrderItem = order_fixtures

    # Query with non-existent ID
    order = Order.query() \
        .with_("user", "items") \
        .where("id = ?", (99999,)) \
        .one()

    assert order is None