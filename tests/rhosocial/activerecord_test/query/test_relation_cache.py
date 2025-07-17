# tests/rhosocial/activerecord_test/query/test_relation_cache.py
"""Test cases for relation caching behavior."""
import random
import string
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import List

import pytest

from .utils import create_order_fixtures


@dataclass
class UserFixture:
    id: int
    username: str
    email: str
    age: int


@dataclass
class OrderFixture:
    id: int
    user_id: int
    order_number: str
    total_amount: Decimal


@dataclass
class OrderItemFixture:
    id: int
    order_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


@dataclass
class TestData:
    users: List[UserFixture]
    orders: List[OrderFixture]
    items: List[OrderItemFixture]


def generate_random_string(prefix: str, length: int = 8) -> str:
    """生成带前缀的随机字符串"""
    chars = string.ascii_letters + string.digits
    random_part = ''.join(random.choice(chars) for _ in range(length))
    return f"{prefix}_{random_part}"


def generate_random_decimal(min_val: int = 10, max_val: int = 500) -> Decimal:
    """生成随机Decimal金额"""
    return Decimal(str(round(random.uniform(min_val, max_val), 2)))


def generate_random_quantity(min_val: int = 1, max_val: int = 10) -> int:
    """生成随机数量"""
    return random.randint(min_val, max_val)


@pytest.fixture
def setup_order_data(order_fixtures) -> TestData:
    """创建随机样本订单数据用于测试。"""
    User, Order, OrderItem = order_fixtures
    test_id = str(uuid.uuid4())[:8]  # 为每次测试生成唯一标识

    # 创建测试用户
    users = []
    for i in range(2):
        username = generate_random_string(f"user{i}_{test_id}")
        email = f"{username}@example.com"
        age = random.randint(20, 60)

        user = User(username=username, email=email, age=age)
        user.save()

        users.append(UserFixture(
            id=user.id,
            username=username,
            email=email,
            age=age
        ))

    # 为用户创建订单
    orders = []
    # 用户1的两个订单
    for i in range(2):
        order_number = generate_random_string(f"ORD{i}_{test_id}")
        total_amount = generate_random_decimal()

        order = Order(
            user_id=users[0].id,
            order_number=order_number,
            total_amount=total_amount
        )
        order.save()

        orders.append(OrderFixture(
            id=order.id,
            user_id=users[0].id,
            order_number=order_number,
            total_amount=total_amount
        ))

    # 用户2的一个空订单（无订单项）
    order_number = generate_random_string(f"ORD_EMPTY_{test_id}")
    total_amount = generate_random_decimal()

    order = Order(
        user_id=users[1].id,
        order_number=order_number,
        total_amount=total_amount
    )
    order.save()

    orders.append(OrderFixture(
        id=order.id,
        user_id=users[1].id,
        order_number=order_number,
        total_amount=total_amount
    ))

    # 创建订单项
    items = []

    # 为第一个订单创建一个订单项
    product_name = generate_random_string("Product1")
    quantity = generate_random_quantity()
    unit_price = generate_random_decimal()
    subtotal = unit_price * quantity

    item = OrderItem(
        order_id=orders[0].id,
        product_name=product_name,
        quantity=quantity,
        unit_price=unit_price,
        subtotal=subtotal
    )
    item.save()

    items.append(OrderItemFixture(
        id=item.id,
        order_id=orders[0].id,
        product_name=product_name,
        quantity=quantity,
        unit_price=unit_price,
        subtotal=subtotal
    ))

    # 为第二个订单创建一个订单项
    product_name = generate_random_string("Product2")
    quantity = generate_random_quantity()
    unit_price = generate_random_decimal()
    subtotal = unit_price * quantity

    item = OrderItem(
        order_id=orders[1].id,
        product_name=product_name,
        quantity=quantity,
        unit_price=unit_price,
        subtotal=subtotal
    )
    item.save()

    items.append(OrderItemFixture(
        id=item.id,
        order_id=orders[1].id,
        product_name=product_name,
        quantity=quantity,
        unit_price=unit_price,
        subtotal=subtotal
    ))

    # 返回带有所有测试数据的数据类
    return TestData(users=users, orders=orders, items=items)

order_fixtures = create_order_fixtures()

def test_basic_relation_caching(order_fixtures, setup_order_data):
    """Test basic relation caching behavior."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    # 从测试数据中获取第一个订单ID
    order_id = test_data.orders[0].id
    expected_product_name = test_data.items[0].product_name

    # 第一次查询 - 应该从数据库加载
    order = Order.query().with_("items").where("id = ?", (order_id,)).one()

    assert order is not None
    assert len(order.items()) == 1
    assert order.items()[0].product_name == expected_product_name

    # 第二次查询 - 应该使用缓存
    order_again = Order.query().with_("items").where("id = ?", (order_id,)).one()

    assert order_again is not None
    assert len(order_again.items()) == 1
    assert order_again.items()[0].product_name == expected_product_name


def test_empty_relation_consistency(order_fixtures, setup_order_data):
    """Test that empty relations are correctly loaded and not affected by other queries."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    # 获取空订单ID（第三个订单）
    empty_order_id = test_data.orders[2].id
    order_with_items_id = test_data.orders[0].id
    expected_product_name = test_data.items[0].product_name

    # 第一次查询 - 空订单应该没有订单项
    order3 = Order.query().with_("items").where("id = ?", (empty_order_id,)).one()

    assert order3 is not None
    assert len(order3.items()) == 0, f"Order {empty_order_id} should have no items initially"

    # 加载带有订单项的不同订单，潜在地影响缓存
    order1 = Order.query().with_("items").where("id = ?", (order_with_items_id,)).one()
    assert len(order1.items()) > 0, f"Order {order_with_items_id} should have items"
    assert order1.items()[0].product_name == expected_product_name

    # 再次查询order3 - 无论其他查询如何，仍然应该没有订单项
    order3_again = Order.query().with_("items").where("id = ?", (empty_order_id,)).one()

    assert order3_again is not None
    assert order3 is not order3_again, "Each query should return a new instance"
    assert len(order3_again.items()) == 0, f"Order {empty_order_id} should still have no items"

    # 向order3添加一个订单项
    new_product_name = f"TestProduct_for_{empty_order_id}"
    new_item = OrderItem(
        order_id=empty_order_id,
        product_name=new_product_name,
        quantity=1,
        unit_price=Decimal("10.00"),
        subtotal=Decimal("10.00")
    )
    new_item.save()

    # 再次查询 - 现在应该有新的订单项
    order3_updated = Order.query().with_("items").where("id = ?", (empty_order_id,)).one()

    assert order3_updated is not None
    assert len(order3_updated.items()) == 1, f"Order {empty_order_id} should now have one item"
    assert order3_updated.items()[0].product_name == new_product_name

    # 原始实例不应该受到新查询的影响
    assert len(order3.items()) == 0, "Original order3 instance should still show no items"
    assert len(order3_again.items()) == 0, "Second order3 instance should still show no items"


def test_cache_isolation_between_records(order_fixtures, setup_order_data):
    """Test that relation caches are properly isolated between different records."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    # 获取两个带有订单项的订单ID
    order_id1 = test_data.orders[0].id
    order_id2 = test_data.orders[1].id
    expected_product_name1 = test_data.items[0].product_name
    expected_product_name2 = test_data.items[1].product_name

    # 加载两个订单及其订单项
    orders = Order.query().with_("items").where("id IN (?,?)", (order_id1, order_id2)).all()

    assert len(orders) == 2
    # 按ID排序以确保一致的顺序
    orders.sort(key=lambda o: o.id)

    # 按ID找出对应订单
    order1 = next((o for o in orders if o.id == order_id1), None)
    order2 = next((o for o in orders if o.id == order_id2), None)

    assert order1 is not None, f"Failed to find order with id {order_id1}"
    assert order2 is not None, f"Failed to find order with id {order_id2}"

    # 第一个订单应该有预期的产品
    assert len(order1.items()) == 1
    assert order1.items()[0].product_name == expected_product_name1

    # 第二个订单应该有预期的产品
    assert len(order2.items()) == 1
    assert order2.items()[0].product_name == expected_product_name2, f"Expected {expected_product_name2}, got {order2.items()[0].product_name}"

    # 现在单独测试以确保缓存不相互干扰
    order1 = Order.query().with_("items").where("id = ?", (order_id1,)).one()
    assert len(order1.items()) == 1
    assert order1.items()[0].product_name == expected_product_name1

    order2 = Order.query().with_("items").where("id = ?", (order_id2,)).one()
    assert len(order2.items()) == 1
    assert order2.items()[0].product_name == expected_product_name2, f"Expected {expected_product_name2}, got {order2.items()[0].product_name}"


def test_mixed_empty_and_populated_relations(order_fixtures, setup_order_data):
    """Test behavior when querying a mix of records with and without related data."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    order_ids = [order.id for order in test_data.orders]
    expected_product_names = [item.product_name for item in test_data.items]

    # 加载所有订单，包括没有订单项的order3
    orders = Order.query().with_("items").where(f"id IN ({','.join(['?'] * len(order_ids))})", order_ids).all()

    assert len(orders) == 3, f"Expected 3 orders, got {len(orders)}"

    # 为了进行一致性测试，创建ID到订单的映射
    orders_by_id = {order.id: order for order in orders}

    # 检查每个订单的订单项
    # 第一个订单有一个订单项
    order1 = orders_by_id[test_data.orders[0].id]
    assert len(order1.items()) == 1, f"Expected order {test_data.orders[0].id} to have 1 item, got {len(order1.items())}"
    assert order1.items()[0].product_name == expected_product_names[0], f"Expected product {expected_product_names[0]}, got {order1.items()[0].product_name}"

    # 第二个订单有一个订单项
    order2 = orders_by_id[test_data.orders[1].id]
    assert len(order2.items()) == 1, f"Expected order {test_data.orders[1].id} to have 1 item, got {len(order2.items())}"
    assert order2.items()[0].product_name == expected_product_names[1], f"Expected product {expected_product_names[1]}, got {order2.items()[0].product_name}"

    # 第三个订单没有订单项
    order3 = orders_by_id[test_data.orders[2].id]
    assert len(order3.items()) == 0, f"Expected order {test_data.orders[2].id} to have 0 items, got {len(order3.items())}"


def test_cache_consistency_across_queries(order_fixtures, setup_order_data):
    """Test that relation cache remains consistent across multiple queries."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    # 获取空订单ID
    empty_order_id = test_data.orders[2].id

    # 第一次查询 - 空订单
    order = Order.query().with_("items").where("id = ?", (empty_order_id,)).one()
    assert order is not None
    assert len(order.items()) == 0, f"Expected order {empty_order_id} to have 0 items, got {len(order.items())}"

    # 向之前空的订单添加一个订单项
    new_product_name = f"NewProduct_for_{empty_order_id}"
    new_item = OrderItem(
        order_id=empty_order_id,
        product_name=new_product_name,
        quantity=3,
        unit_price=Decimal("50.00"),
        subtotal=Decimal("150.00")
    )
    new_item.save()

    # 第二次查询 - 应该检测到变更
    order_updated = Order.query().with_("items").where("id = ?", (empty_order_id,)).one()
    assert order_updated is not None
    assert len(order_updated.items()) == 1, f"Expected order {empty_order_id} to have 1 item after update, got {len(order_updated.items())}"
    assert order_updated.items()[0].product_name == new_product_name, f"Expected product {new_product_name}, got {order_updated.items()[0].product_name}"


def test_repeated_empty_relation_queries(order_fixtures, setup_order_data):
    """Test repeatedly querying empty relations to check for cache consistency."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    # 获取空订单ID
    empty_order_id = test_data.orders[2].id

    # 多次测试空关系
    for i in range(5):  # 测试5次以提高检测问题的几率
        order = Order.query().with_("items").where("id = ?", (empty_order_id,)).one()
        assert order is not None, f"Failed to get order {empty_order_id} on iteration {i}"
        assert len(order.items()) == 0, f"Expected order {empty_order_id} to have 0 items on iteration {i}, got {len(order.items())}"


def test_cache_clearing_on_update(order_fixtures, setup_order_data):
    """Test that relation cache is properly cleared when related records are updated."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    # 获取有订单项的订单ID
    order_id = test_data.orders[0].id
    original_product_name = test_data.items[0].product_name

    # 第一次查询
    order = Order.query().with_("items").where("id = ?", (order_id,)).one()
    assert len(order.items()) == 1, f"Expected order {order_id} to have 1 item, got {len(order.items())}"
    assert order.items()[0].product_name == original_product_name, f"Expected product {original_product_name}, got {order.items()[0].product_name}"

    # 更新订单项
    item = order.items()[0]
    updated_product_name = f"{original_product_name}_Updated_{order_id}"
    item.product_name = updated_product_name
    item.save()

    # 再次查询 - 应该获取更新后的数据
    order_updated = Order.query().with_("items").where("id = ?", (order_id,)).one()
    assert len(order_updated.items()) == 1, f"Expected order {order_id} to still have 1 item, got {len(order_updated.items())}"
    assert order_updated.items()[0].product_name == updated_product_name, f"Expected updated product {updated_product_name}, got {order_updated.items()[0].product_name}"


def test_relation_query_with_different_modifiers(order_fixtures, setup_order_data):
    """Test that different query modifiers don't interfere with relation caching."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    # 获取有订单项的订单ID和数量信息
    order_id = test_data.orders[0].id
    quantity = test_data.items[0].quantity

    # 根据量判断高阈值和低阈值
    low_threshold = max(1, quantity - 1)  # 确保至少为1
    high_threshold = quantity + 1

    # 第一次查询 - 获取所有订单项
    order = Order.query().with_("items").where("id = ?", (order_id,)).one()
    assert len(order.items()) == 1, f"Expected order {order_id} to have 1 item, got {len(order.items())}"

    # 第二次查询 - 带有条件地获取订单项
    order_with_condition = Order.query().with_(
        ("items", lambda q: q.where("quantity > ?", (low_threshold - 1,)))  # 确保条件满足
    ).where("id = ?", (order_id,)).one()

    assert len(order_with_condition.items()) == 1, f"Expected order {order_id} to have 1 item with quantity > {low_threshold-1}, got {len(order_with_condition.items())}"

    # 第三次查询 - 带有不同条件
    order_with_different_condition = Order.query().with_(
        ("items", lambda q: q.where("quantity > ?", (high_threshold,)))  # 确保条件不满足
    ).where("id = ?", (order_id,)).one()

    assert len(order_with_different_condition.items()) == 0, f"Expected order {order_id} to have 0 items with quantity > {high_threshold}, got {len(order_with_different_condition.items())}"


def test_relation_loading_on_empty_result_set(order_fixtures, setup_order_data):
    """Test relation loading behavior when primary query returns no results."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    # 使用不存在的ID查询
    non_existent_id = max([order.id for order in test_data.orders]) + 9999

    order = Order.query() \
        .with_("user", "items") \
        .where("id = ?", (non_existent_id,)) \
        .one()

    assert order is None, f"Expected no result for non-existent ID {non_existent_id}, but got a result"



def test_basic_relation_loading(order_fixtures, setup_order_data):
    """Test basic relation loading functionality."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    # Get test data
    order_id1 = test_data.orders[0].id
    order_id2 = test_data.orders[1].id
    expected_product_name1 = test_data.items[0].product_name
    expected_product_name2 = test_data.items[1].product_name

    # Test first order
    order1 = Order.query().with_("items").where("id = ?", (order_id1,)).one()
    assert len(order1.items()) == 1, f"Expected order {order_id1} to have 1 item, got {len(order1.items())}"
    assert order1.items()[0].product_name == expected_product_name1, \
        f"Expected product {expected_product_name1}, got {order1.items()[0].product_name}"

    # Test second order
    order2 = Order.query().with_("items").where("id = ?", (order_id2,)).one()
    assert len(order2.items()) == 1, f"Expected order {order_id2} to have 1 item, got {len(order2.items())}"
    assert order2.items()[0].product_name == expected_product_name2, \
        f"Expected product {expected_product_name2}, got {order2.items()[0].product_name}"

    # Test cache isolation
    order1_again = Order.query().with_("items").where("id = ?", (order_id1,)).one()
    assert len(order1_again.items()) == 1
    assert order1_again.items()[0].product_name == expected_product_name1

    order2_again = Order.query().with_("items").where("id = ?", (order_id2,)).one()
    assert len(order2_again.items()) == 1
    assert order2_again.items()[0].product_name == expected_product_name2

def test_relation_loading_with_conditions(order_fixtures, setup_order_data):
    """Test relation loading with specific conditions."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    order_id = test_data.orders[0].id
    expected_price = test_data.items[0].unit_price

    # Test loading with price condition
    order = Order.query().with_(
        ("items", lambda q: q.where("unit_price >= ?", (expected_price,)))
    ).where("id = ?", (order_id,)).one()

    assert len(order.items()) == 1
    assert order.items()[0].unit_price == expected_price

def test_relation_loading_with_ordering(order_fixtures, setup_order_data):
    """Test relation loading with specific ordering."""
    User, Order, OrderItem = order_fixtures
    test_data = setup_order_data

    # Add multiple items to first order
    order_id = test_data.orders[0].id
    new_item = OrderItem(
        order_id=order_id,
        product_name="Additional_Product",
        quantity=1,
        unit_price=Decimal("10.00"),
        subtotal=Decimal("10.00")
    )
    new_item.save()

    # Test loading with ordering
    order = Order.query().with_(
        ("items", lambda q: q.order_by("product_name ASC"))
    ).where("id = ?", (order_id,)).one()

    items = order.items()
    assert len(items) == 2
    assert items[0].product_name < items[1].product_name