from decimal import Decimal
from .utils import create_order_fixtures

# 创建多表测试夹具
order_fixtures = create_order_fixtures()


def test_equal_condition(order_fixtures):
    """测试等值条件查询"""
    User, Order, OrderItem = order_fixtures

    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        status='processing'
    )
    order.save()

    result = Order.query().where('status = ?', ('processing',)).one()
    assert result is not None
    assert result.id == order.id


def test_multiple_conditions(order_fixtures):
    """测试多个查询条件"""
    User, Order, OrderItem = order_fixtures

    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('150.00'),
        status='paid'
    )
    order.save()

    result = Order.query() \
        .where('status = ?', ('paid',)) \
        .where('total_amount > ?', (Decimal('100.00'),)) \
        .one()
    assert result is not None
    assert result.order_number == 'ORD-001'


def test_in_condition(order_fixtures):
    """测试IN条件查询"""
    User, Order, OrderItem = order_fixtures

    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    result = user.save()
    assert result == 1

    # 创建三个不同状态的订单
    statuses = ['pending', 'paid', 'shipped']
    for status in statuses:
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{status}',
            status=status
        )
        result = order.save()
        assert result == 1

    results = (Order.query()
               .in_list('status', ['pending', 'paid'])  # .where('status IN (?, ?)', ('pending', 'paid',))
               .all())
    assert len(results) == 2
    assert all(r.status in ('pending', 'paid') for r in results)

    results = Order.query().not_in('status', ['pending', 'paid']).all()
    assert len(results) == 1
    assert all(r.status in ('shipped') for r in results)


def test_or_condition(order_fixtures):
    """测试OR条件查询"""
    User, Order, OrderItem = order_fixtures

    # 创建用户
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # 创建不同状态的订单
    orders = [
        Order(user_id=user.id, order_number='ORD-001', status='pending', total_amount=Decimal('100.00')),
        Order(user_id=user.id, order_number='ORD-002', status='paid', total_amount=Decimal('200.00')),
        Order(user_id=user.id, order_number='ORD-003', status='shipped', total_amount=Decimal('300.00')),
    ]
    for order in orders:
        order.save()

    # 测试基本的OR条件
    results = Order.query() \
        .where('status = ?', ('pending',)) \
        .or_where('status = ?', ('paid',)) \
        .all()
    assert len(results) == 2
    assert set(r.status for r in results) == {'pending', 'paid'}

    # 测试OR和AND的组合
    results = Order.query() \
        .where('total_amount > ?', (Decimal('150.00'),)) \
        .start_or_group() \
        .where('status = ?', ('paid',)) \
        .or_where('status = ?', ('shipped',)) \
        .end_or_group() \
        .all()
    assert len(results) == 2
    assert all(r.total_amount > Decimal('150.00') for r in results)
    assert set(r.status for r in results) == {'paid', 'shipped'}


def test_complex_conditions(order_fixtures):
    """测试复杂条件组合查询"""
    User, Order, OrderItem = order_fixtures

    # 创建测试用户
    users = [
        User(username=f'user{i}', email=f'user{i}@example.com', age=25 + i)
        for i in range(3)
    ]
    for user in users:
        user.save()

    # 创建订单
    orders = []
    statuses = ['pending', 'paid', 'shipped']
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]

    for i, user in enumerate(users):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=statuses[i],
            total_amount=amounts[i]
        )
        order.save()
        orders.append(order)

    # 测试条件 1：状态为pending或paid，且金额小于150或大于250
    results = Order.query() \
        .in_list('status', ['pending', 'paid']) \
        .start_or_group() \
        .where('total_amount < ?', (Decimal('150.00'),)) \
        .or_where('total_amount > ?', (Decimal('250.00'),)) \
        .end_or_group() \
        .all()

    # 应该返回：
    # - ORD-1 (pending, 100.00 < 150.00)
    assert len(results) == 1
    assert results[0].order_number == 'ORD-1'

    # 修改查询条件以测试更多场景
    results = Order.query() \
        .in_list('status', ['pending', 'paid']) \
        .start_or_group() \
        .where('total_amount < ?', (Decimal('250.00'),)) \
        .or_where('total_amount > ?', (Decimal('250.00'),)) \
        .end_or_group() \
        .all()

    # 应该返回：
    # - ORD-1 (pending, 100.00 < 250.00)
    # - ORD-2 (paid, 200.00 < 250.00)
    assert len(results) == 2
    assert set(r.order_number for r in results) == {'ORD-1', 'ORD-2'}


def test_empty_conditions(order_fixtures):
    """测试空值条件处理"""
    User, Order, OrderItem = order_fixtures

    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # 创建测试订单
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        status='pending'
    )
    order.save()

    # 测试空 IN 列表
    results = Order.query().in_list('id', [], empty_result=True).all()
    assert len(results) == 0

    results = Order.query().in_list('id', [], empty_result=False).all()
    assert len(results) == 1  # 返回所有记录

    # 测试空 NOT IN 列表
    results = Order.query().not_in('id', [], empty_result=True).all()
    assert len(results) == 0

    results = Order.query().not_in('id', [], empty_result=False).all()
    assert len(results) == 1  # 返回所有记录


def test_between_condition(order_fixtures):
    """Test BETWEEN condition queries"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create orders with different amounts
    amounts = [Decimal('50.00'), Decimal('150.00'), Decimal('250.00')]
    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1}',
            total_amount=amount
        )
        order.save()

    # Test BETWEEN query
    results = Order.query().between('total_amount', Decimal('100.00'), Decimal('200.00')).all()
    assert len(results) == 1
    assert results[0].total_amount == Decimal('150.00')

    # Test NOT BETWEEN query
    results = Order.query().not_between('total_amount', Decimal('100.00'), Decimal('200.00')).all()
    assert len(results) == 2
    assert all(r.total_amount in [Decimal('50.00'), Decimal('250.00')] for r in results)

def test_like_condition(order_fixtures):
    """Test LIKE condition queries"""
    User, Order, OrderItem = order_fixtures

    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create orders with different order numbers
    order_numbers = ['ABC-001', 'BCD-002', 'CDE-003']
    for order_num in order_numbers:
        order = Order(
            user_id=user.id,
            order_number=order_num
        )
        order.save()

    # Test LIKE query
    results = Order.query().like('order_number', 'ABC%').all()
    assert len(results) == 1
    assert results[0].order_number == 'ABC-001'

    # Test NOT LIKE query
    results = Order.query().not_like('order_number', 'ABC%').all()
    assert len(results) == 2
    assert all(not r.order_number.startswith('ABC') for r in results)

def test_null_condition(order_fixtures):
    """Test IS NULL and IS NOT NULL condition queries"""
    User, Order, OrderItem = order_fixtures

    # Create test users with varying age values
    users = [
        User(username='user1', email='user1@example.com', age=None),
        User(username='user2', email='user2@example.com', age=25),
        User(username='user3', email='user3@example.com', age=None)
    ]
    for user in users:
        user.save()

    # Test IS NULL query
    results = User.query().is_null('age').all()
    assert len(results) == 2
    assert all(r.age is None for r in results)

    # Test IS NOT NULL query
    results = User.query().is_not_null('age').all()
    assert len(results) == 1
    assert results[0].age == 25


def test_complex_conditions_2(order_fixtures):
    """Test complex combinations of query conditions including new methods"""
    User, Order, OrderItem = order_fixtures

    # Create test users with varying attributes
    users = [
        User(username='user1', email='user1@example.com', age=25),
        User(username='user2', email='user2@example.com', age=None),
        User(username='user3', email='user3@example.com', age=35)
    ]
    for user in users:
        user.save()

    # Create orders with various characteristics
    orders_data = [
        ('ORD-A001', 'pending', Decimal('150.00')),  # Outside 200-400 range but pending
        ('ORD-B002', 'paid', Decimal('250.00')),  # In 200-400 range and starts with ORD-B
        ('ORD-C003', 'shipped', Decimal('350.00')),  # In 200-400 range but not ORD-B
        ('ORD-D004', 'pending', Decimal('450.00'))  # Outside 200-400 range but pending
    ]

    # Track created orders for verification
    created_orders = []

    for i, (order_num, status, amount) in enumerate(orders_data):
        user = users[i % len(users)]
        order = Order(
            user_id=user.id,
            order_number=order_num,
            status=status,
            total_amount=amount
        )
        order.save()
        created_orders.append(order)

        # Create order items for some orders
        if i % 2 == 0:
            item = OrderItem(
                order_id=order.id,
                product_name=f'Product {i}',
                quantity=i + 1,
                unit_price=Decimal('100.00'),
                subtotal=amount
            )
            item.save()

    # Print all created orders for debugging
    print("\nCreated orders:")
    for order in created_orders:
        print(f"Order #{order.id}: {order.order_number}, Status: {order.status}, "
              f"Amount: {order.total_amount}, Created at: {order.created_at}")

    # Complex query combining multiple conditions
    # Build the query with proper OR relationship between main conditions
    query = Order.query() \
        .start_or_group() \
        .where('total_amount BETWEEN ? AND ? AND order_number LIKE ?',
               (Decimal('200.00'), Decimal('400.00'), 'ORD-B%')) \
        .or_where('status = ? AND created_at IS NOT NULL',
                  ('pending',)) \
        .end_or_group()

    # Get and print the SQL for debugging
    sql, params = query.to_sql()
    print(f"\nQuery SQL: {sql}")
    print(f"Query params: {params}")

    # Execute the query
    results = query.all()

    # Print query results for debugging
    print("\nQuery results:")
    for result in results:
        print(f"Result #{result.id}: {result.order_number}, Status: {result.status}, "
              f"Amount: {result.total_amount}, Created at: {result.created_at}")

    # The query should match orders that either:
    # 1. Have amount between 200-400 AND order number starts with 'ORD-B'
    # OR
    # 2. Have status 'pending' AND created_at is not null
    assert len(results) > 0, "Query should return at least one result"

    for result in results:
        condition1 = (
                Decimal('200.00') <= result.total_amount <= Decimal('400.00')
                and result.order_number.startswith('ORD-B')
        )
        condition2 = (
                result.status == 'pending'
                and result.created_at is not None
        )

        assert condition1 or condition2, (
            f"Order #{result.id} ({result.order_number}) doesn't match either condition:\n"
            f"Condition 1 (amount in range and ORD-B): {condition1}\n"
            f"Condition 2 (pending and has created_at): {condition2}"
        )

    # Verify that all matching orders were returned
    expected_orders = [
        order for order in created_orders
        if (
                (Decimal('200.00') <= order.total_amount <= Decimal('400.00')
                 and order.order_number.startswith('ORD-B'))
                or
                (order.status == 'pending' and order.created_at is not None)
        )
    ]

    print("\nExpected matching orders:")
    for order in expected_orders:
        print(f"Expected #{order.id}: {order.order_number}, Status: {order.status}, "
              f"Amount: {order.total_amount}, Created at: {order.created_at}")

    assert len(results) == len(expected_orders), (
        f"Expected {len(expected_orders)} results, but got {len(results)}"
    )