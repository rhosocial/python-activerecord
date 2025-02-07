from decimal import Decimal
from .utils import create_order_fixtures

# 创建多表测试夹具
order_fixtures = create_order_fixtures()


def test_find_by_id(order_fixtures):
    """测试通过ID查找记录"""
    User, Order, OrderItem = order_fixtures

    # 创建测试用户
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # 创建订单
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('100.00')
    )
    order.save()

    found = Order.find_one(order.id)
    assert found is not None
    assert found.order_number == 'ORD-001'


def test_find_by_condition(order_fixtures):
    """测试条件查找记录"""
    User, Order, OrderItem = order_fixtures

    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-TEST',
        status='processing'
    )
    order.save()

    found = Order.find_one({'status': 'processing'})
    assert found is not None
    assert found.order_number == 'ORD-TEST'


def test_find_all(order_fixtures):
    """测试查找所有记录"""
    User, Order, OrderItem = order_fixtures

    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1:03d}',
            total_amount=Decimal('100.00')
        )
        order.save()

    all_orders = Order.query().all()
    assert len(all_orders) == 3


def test_count(order_fixtures):
    """测试记录计数"""
    User, Order, OrderItem = order_fixtures

    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    for i in range(3):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1:03d}'
        )
        order.save()

    count = Order.query().count()
    assert count == 3