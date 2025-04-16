from decimal import Decimal
from .utils import create_order_fixtures

# 创建多表测试夹具
order_fixtures = create_order_fixtures()


def test_inner_join(order_fixtures):
    """测试内连接查询"""
    User, Order, OrderItem = order_fixtures

    # 创建用户
    user = User(
        username='test_user',
        email='test@example.com',
        age=30,
        balance=Decimal('1000.00')
    )
    user.save()

    # 创建订单
    order = Order(
        user_id=user.id,
        order_number='ORD-001',
        total_amount=Decimal('150.00')
    )
    order.save()

    # 创建订单项
    item = OrderItem(
        order_id=order.id,
        product_name='Test Product',
        quantity=2,
        unit_price=Decimal('75.00'),
        subtotal=Decimal('150.00')
    )
    item.save()

    # 测试三表INNER JOIN
    results = Order.query() \
        .join(f"""
            INNER JOIN {OrderItem.__table_name__} 
            ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
        """) \
        .join(f"""
            INNER JOIN {User.__table_name__}
            ON {Order.__table_name__}.user_id = {User.__table_name__}.id
        """) \
        .where(f'{Order.__table_name__}.id = ?', (order.id,)) \
        .all()

    assert len(results) == 1
    assert results[0].id == order.id


def test_left_join(order_fixtures):
    """测试左连接查询"""
    User, Order, OrderItem = order_fixtures

    # 创建用户
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # 创建两个订单：一个有订单项，一个没有
    order1 = Order(user_id=user.id, order_number='ORD-001')
    order1.save()

    order2 = Order(user_id=user.id, order_number='ORD-002')
    order2.save()

    # 只给order1创建订单项
    item = OrderItem(
        order_id=order1.id,
        product_name='Test Product',
        quantity=1,
        unit_price=Decimal('100.00'),
        subtotal=Decimal('100.00')
    )
    item.save()

    # 测试LEFT JOIN
    results = Order.query().select('orders.*') \
        .join(f"""
            LEFT JOIN {OrderItem.__table_name__} 
            ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
        """) \
        .where(f'{Order.__table_name__}.user_id = ?', (user.id,)) \
        .order_by(f'{Order.__table_name__}.order_number') \
        .all()

    assert len(results) == 2  # 应该返回两个订单


def test_join_with_conditions(order_fixtures):
    """测试带条件的连接查询"""
    User, Order, OrderItem = order_fixtures

    # 创建用户
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # 创建订单
    order = Order(user_id=user.id, order_number='ORD-001')
    order.save()

    # 创建两个订单项，数量不同
    items = [
        OrderItem(
            order_id=order.id,
            product_name=f'Product {i}',
            quantity=i + 1,
            unit_price=Decimal('100.00'),
            subtotal=Decimal(f'{(i + 1) * 100}.00')
        )
        for i in range(2)
    ]
    for item in items:
        item.save()

    # 测试带条件的JOIN
    results = Order.query() \
        .join(f"""
            INNER JOIN {User.__table_name__}
            ON {Order.__table_name__}.user_id = {User.__table_name__}.id
        """) \
        .join(f"""
            INNER JOIN {OrderItem.__table_name__} 
            ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
            AND {OrderItem.__table_name__}.quantity > 1
        """) \
        .where(f'{User.__table_name__}.username = ?', ('test_user',)) \
        .all()

    assert len(results) == 1  # 只有一个订单项的quantity > 1


def test_join_with_or_conditions(order_fixtures):
    """测试带OR条件的连接查询"""
    User, Order, OrderItem = order_fixtures

    # 创建两个用户
    users = [
        User(username=f'user{i}', email=f'user{i}@example.com', age=25 + i)
        for i in range(2)
    ]
    for user in users:
        user.save()

    # 为每个用户创建订单
    orders = []
    for i, user in enumerate(users):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status='pending' if i == 0 else 'paid',
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()
        orders.append(order)

        # 创建订单项
        item = OrderItem(
            order_id=order.id,
            product_name=f'Product {i + 1}',
            quantity=i + 1,
            unit_price=Decimal('100.00'),
            subtotal=Decimal(f'{(i + 1) * 100}.00')
        )
        item.save()

    # 测试JOIN和OR条件组合
    results = Order.query() \
        .join(f"""
            INNER JOIN {User.__table_name__}
            ON {Order.__table_name__}.user_id = {User.__table_name__}.id
        """) \
        .where(f'{Order.__table_name__}.total_amount > ?', (Decimal('50.00'),)) \
        .start_or_group() \
        .where(f'{User.__table_name__}.username = ?', ('user0',)) \
        .or_where(f'{Order.__table_name__}.status = ?', ('paid',)) \
        .end_or_group() \
        .all()

    assert len(results) == 2
    assert all(r.total_amount > Decimal('50.00') for r in results)


def test_join_with_in_conditions(order_fixtures):
    """测试带IN条件的连接查询"""
    User, Order, OrderItem = order_fixtures

    # 创建测试用户
    users = [
        User(username=f'user{i}', email=f'user{i}@example.com', age=25 + i)
        for i in range(3)
    ]
    for user in users:
        user.save()

    # 创建订单和订单项
    orders = []
    for i, user in enumerate(users):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=['pending', 'paid', 'shipped'][i],
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()
        orders.append(order)

        item = OrderItem(
            order_id=order.id,
            product_name=f'Product {i + 1}',
            quantity=i + 1,
            unit_price=Decimal('100.00'),
            subtotal=Decimal(f'{(i + 1) * 100}.00')
        )
        item.save()

    # 测试JOIN和IN条件组合
    results = Order.query() \
        .join(f"""
            INNER JOIN {OrderItem.__table_name__}
            ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
        """) \
        .in_list(f'{Order.__table_name__}.status', ['pending', 'paid']) \
        .where(f'{OrderItem.__table_name__}.quantity > ?', (1,)) \
        .all()

    assert len(results) == 1
    assert results[0].status in ['pending', 'paid']

    # 测试JOIN和NOT IN条件组合
    results = Order.query() \
        .join(f"""
            INNER JOIN {User.__table_name__}
            ON {Order.__table_name__}.user_id = {User.__table_name__}.id
        """) \
        .not_in(f'{Order.__table_name__}.status', ['shipped']) \
        .order_by(f'{Order.__table_name__}.total_amount') \
        .all()

    assert len(results) == 2
    assert all(r.status != 'shipped' for r in results)


def test_complex_join_conditions(order_fixtures):
    """测试复杂JOIN条件组合"""
    User, Order, OrderItem = order_fixtures

    # 创建测试用户
    users = [
        User(username=f'user{i}', email=f'user{i}@example.com', age=25 + i)
        for i in range(3)
    ]
    for user in users:
        user.save()

    # 创建订单和订单项
    orders = []
    statuses = ['pending', 'paid', 'shipped']
    for i, user in enumerate(users):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i + 1}',
            status=statuses[i],
            total_amount=Decimal(f'{(i + 1) * 100}.00')
        )
        order.save()
        orders.append(order)

        # 每个订单创建两个订单项
        for j in range(2):
            item = OrderItem(
                order_id=order.id,
                product_name=f'Product {i}-{j}',
                quantity=i + j + 1,
                unit_price=Decimal('100.00'),
                subtotal=Decimal(f'{(i + j + 1) * 100}.00')
            )
            item.save()

    # 测试复杂条件组合
    results = Order.query()\
        .select(f'{Order.__table_name__}.*', f'{User.__table_name__}.age')\
        .join(f"""
            INNER JOIN {User.__table_name__}
            ON {Order.__table_name__}.user_id = {User.__table_name__}.id
        """)\
        .join(f"""
            INNER JOIN {OrderItem.__table_name__}
            ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
        """)\
        .start_or_group()\
        .in_list(f'{Order.__table_name__}.status', ['pending', 'paid'])\
        .where(f'{OrderItem.__table_name__}.quantity >= ?', (3,))\
        .end_or_group()\
        .where(f'{User.__table_name__}.age < ?', (30,))\
        .order_by(f'{Order.__table_name__}.total_amount')\
        .all()

    # 验证结果：用户年龄小于30，且（订单状态为pending或paid，或者订单项数量大于等于3）
    for result in results:
        user = User.find_one(result.user_id)  # 获取关联的用户
        assert user.age < 30  # 使用关联用户的age
        assert (
            result.status in ['pending', 'paid'] or
            any(item.quantity >= 3 for item in result.items.all())
        )


def test_complex_join_conditions_2(order_fixtures):
    """Test complex join queries with new condition methods"""
    User, Order, OrderItem = order_fixtures

    # Create test users with varying attributes
    users = [
        User(username='alpha', email='alpha@example.com', age=25),
        User(username='beta', email='beta@example.com', age=None),
        User(username='gamma', email='gamma@example.com', age=35)
    ]
    for user in users:
        user.save()

    # Create orders with various characteristics for each user
    status_map = {
        'alpha': [('ORD-A1', 'pending', '150.00'), ('ORD-A2', 'paid', '250.00')],
        'beta': [('ORD-B1', 'shipped', '350.00'), ('ORD-B2', 'pending', '450.00')],
        'gamma': [('ORD-C1', 'paid', '550.00')]
    }

    for user in users:
        for order_num, status, amount in status_map[user.username]:
            order = Order(
                user_id=user.id,
                order_number=order_num,
                status=status,
                total_amount=Decimal(amount)
            )
            order.save()

            # Create multiple order items for each order
            for i in range(2):
                item = OrderItem(
                    order_id=order.id,
                    product_name=f'Product {order_num}-{i + 1}',
                    quantity=i + 1,
                    unit_price=Decimal('100.00'),
                    subtotal=Decimal('100.00') * (i + 1)
                )
                item.save()

    # Complex join query combining multiple conditions
    results = Order.query() \
        .select(
        f'{Order.__table_name__}.*',
        f'{User.__table_name__}.username',
        f'{OrderItem.__table_name__}.quantity'
    ) \
        .join(f"""
            INNER JOIN {User.__table_name__}
            ON {Order.__table_name__}.user_id = {User.__table_name__}.id
        """) \
        .join(f"""
            LEFT JOIN {OrderItem.__table_name__}
            ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
        """) \
        .start_or_group() \
        .between(f'{Order.__table_name__}.total_amount',
                 Decimal('200.00'), Decimal('500.00')) \
        .like(f'{Order.__table_name__}.order_number', 'ORD-A%') \
        .end_or_group() \
        .start_or_group() \
        .is_not_null(f'{User.__table_name__}.age') \
        .not_like(f'{Order.__table_name__}.order_number', 'ORD-B%') \
        .end_or_group() \
        .order_by(f'{Order.__table_name__}.total_amount DESC') \
        .all()

    # Verify results
    assert len(results) > 0
    for result in results:
        # Get related user for verification
        user = User.find_one(result.user_id)

        # Check that each result matches either:
        # (amount between 200-500 AND order number starts with 'ORD-A')
        # OR
        # (user age is not null AND order number doesn't start with 'ORD-B')
        assert (
                (Decimal('200.00') <= result.total_amount <= Decimal('500.00')
                 and result.order_number.startswith('ORD-A'))
                or
                (user.age is not None and not result.order_number.startswith('ORD-B'))
        )

    # Additional complex join query
    results = Order.query() \
        .join(f"""
            INNER JOIN {User.__table_name__}
            ON {Order.__table_name__}.user_id = {User.__table_name__}.id
        """) \
        .join(f"""
            INNER JOIN {OrderItem.__table_name__}
            ON {Order.__table_name__}.id = {OrderItem.__table_name__}.order_id
        """) \
        .not_between(f'{Order.__table_name__}.total_amount',
                     Decimal('300.00'), Decimal('600.00')) \
        .start_or_group() \
        .is_null(f'{User.__table_name__}.age') \
        .not_like(f'{OrderItem.__table_name__}.product_name', '%1') \
        .end_or_group() \
        .all()

    # Verify the second query results
    for result in results:
        user = User.find_one(result.user_id)
        items = OrderItem.query().where('order_id = ?', (result.id,)).all()

        # Amount should be outside 300-600 range
        assert not (Decimal('300.00') <= result.total_amount <= Decimal('600.00'))
        # If user age is null, no order items should have product names ending in 1
        if user.age is None:
            assert all(not item.product_name.endswith('1') for item in items)