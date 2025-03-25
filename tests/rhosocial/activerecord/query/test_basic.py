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


def test_exists_method(order_fixtures):
    """Test exists() method for checking if records exist"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='exists_test_user',
        email='exists_test@example.com',
        age=35
    )
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='EXISTS-TEST-001',
        total_amount=Decimal('150.00'),
        status='pending'
    )
    order.save()

    # Test exists on records that do exist
    exists_result = Order.query().where('order_number = ?', ('EXISTS-TEST-001',)).exists()
    assert exists_result is True

    # Test exists with conditions matching multiple records
    for i in range(3):
        Order(
            user_id=user.id,
            order_number=f'EXISTS-MULTI-{i + 1:03d}',
            total_amount=Decimal('100.00'),
            status='active'
        ).save()

    exists_result = Order.query().where('status = ?', ('active',)).exists()
    assert exists_result is True

    # Test exists on records that do not exist
    exists_result = Order.query().where('order_number = ?', ('NON-EXISTENT',)).exists()
    assert exists_result is False

    # Test exists with complex conditions
    exists_result = (Order.query()
                     .where('total_amount > ?', (Decimal('120.00'),))
                     .where('status = ?', ('pending',))
                     .exists())
    assert exists_result is True

    exists_result = (Order.query()
                     .where('total_amount < ?', (Decimal('50.00'),))
                     .exists())
    assert exists_result is False


def test_exists_with_or_conditions(order_fixtures):
    """Test exists() method with OR conditions"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='exists_or_user',
        email='exists_or@example.com',
        age=40
    )
    user.save()

    # Create test orders with different statuses
    Order(
        user_id=user.id,
        order_number='OR-TEST-001',
        total_amount=Decimal('200.00'),
        status='shipped'
    ).save()

    Order(
        user_id=user.id,
        order_number='OR-TEST-002',
        total_amount=Decimal('300.00'),
        status='delivered'
    ).save()

    # Test exists with OR conditions
    exists_result = (Order.query()
                     .where('status = ?', ('canceled',))
                     .or_where('status = ?', ('shipped',))
                     .exists())
    assert exists_result is True

    # Test OR conditions with non-existent values
    exists_result = (Order.query()
                     .where('status = ?', ('canceled',))
                     .or_where('status = ?', ('rejected',))
                     .exists())
    assert exists_result is False


def test_exists_with_or_groups(order_fixtures):
    """Test exists() method with OR groups"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='exists_group_user',
        email='exists_group@example.com',
        age=45
    )
    user.save()

    # Create test orders
    Order(
        user_id=user.id,
        order_number='GROUP-TEST-001',
        total_amount=Decimal('250.00'),
        status='completed'
    ).save()

    # Test exists with OR groups
    exists_result = (Order.query()
                     .where('status = ?', ('completed',))
                     .start_or_group()
                     .where('total_amount > ?', (Decimal('200.00'),))
                     .or_where('order_number = ?', ('GROUP-TEST-001',))
                     .end_or_group()
                     .exists())
    assert exists_result is True

    # Test with non-matching OR group
    exists_result = (Order.query()
                     .where('status = ?', ('completed',))
                     .start_or_group()
                     .where('total_amount < ?', (Decimal('100.00'),))
                     .or_where('order_number = ?', ('NON-EXISTENT',))
                     .end_or_group()
                     .exists())
    assert exists_result is False


def test_exists_with_limit_and_offset(order_fixtures):
    """Test exists() method with LIMIT and OFFSET clauses"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='exists_limit_user',
        email='exists_limit@example.com',
        age=50
    )
    user.save()

    # Create multiple test orders
    for i in range(5):
        Order(
            user_id=user.id,
            order_number=f'LIMIT-TEST-{i + 1:03d}',
            total_amount=Decimal('100.00'),
            status='active'
        ).save()

    # Test exists with limit
    exists_result = Order.query().where('status = ?', ('active',)).limit(1).exists()
    assert exists_result is True

    # Test exists with limit and offset
    exists_result = Order.query().where('status = ?', ('active',)).limit(3).offset(2).exists()
    assert exists_result is False

    # Test exists with limit and offset that exceeds available records
    exists_result = Order.query().where('status = ?', ('active',)).limit(1).offset(10).exists()
    assert exists_result is False


def test_exists_with_joins(order_fixtures):
    """Test exists() method with JOIN clauses"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='exists_join_user',
        email='exists_join@example.com',
        age=55
    )
    user.save()

    # Create test order
    order = Order(
        user_id=user.id,
        order_number='JOIN-EXISTS-001',
        total_amount=Decimal('350.00'),
        status='pending'
    )
    order.save()

    # Create order item
    item = OrderItem(
        order_id=order.id,
        product_name='Test Product',
        quantity=2,
        price=Decimal('175.00'),
        unit_price=Decimal('150.00')
    )
    item.save()

    # Test exists with JOIN
    exists_result = (Order.query()
                     .join('JOIN order_items ON orders.id = order_items.order_id')
                     .join('JOIN users ON orders.user_id = users.id')
                     .where('orders.order_number = ?', ('JOIN-EXISTS-001',))
                     .where('users.username = ?', ('exists_join_user',))
                     .where('order_items.product_name = ?', ('Test Product',))
                     .exists())
    assert exists_result is True

    # Test exists with JOIN and non-matching condition
    exists_result = (Order.query()
                     .join('JOIN order_items ON orders.id = order_items.order_id')
                     .join('JOIN users ON orders.user_id = users.id')
                     .where('orders.order_number = ?', ('JOIN-EXISTS-001',))
                     .where('order_items.product_name = ?', ('Non-Existent Product',))
                     .exists())
    assert exists_result is False