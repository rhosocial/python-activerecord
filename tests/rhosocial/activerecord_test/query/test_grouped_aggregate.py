"""Test aggregate calculations with grouping."""
from decimal import Decimal
from .utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_single_group_aggregates(order_fixtures):
    """Test basic grouped aggregations with single group by"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    statuses = ['pending', 'paid', 'shipped']
    for i, status in enumerate(statuses):
        user = User(
            username=f'user{i + 1}',
            email=f'user{i + 1}@example.com',
            age=30
        )
        user.save()

        # Create multiple orders for each status
        for j in range(2):
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{status}-{j + 1}',
                total_amount=Decimal(f'{(j + 1) * 100}.00'),
                status=status
            )
            order.save()

    # Test single aggregate with group by
    results = (Order.query()
               .group_by('status')
               .count('*', 'order_count')
               .aggregate())

    assert len(results) == 3
    for result in results:
        assert result['order_count'] == 2

    # Test multiple aggregates with group by
    results = (Order.query()
               .group_by('status')
               .count('*', 'order_count')
               .sum('total_amount', 'sum_amount')  # SQLite allows the alias and original name of an expression to be the same,
               # but if columns with the same name continue to appear, the query results may be different from other databases.
               .avg('total_amount', 'avg_amount')
               .aggregate())

    assert len(results) == 3
    for result in results:
        assert result['order_count'] == 2
        assert result['sum_amount'] == Decimal('300.00')
        assert result['avg_amount'] == Decimal('150.00')


def test_group_with_conditions(order_fixtures):
    """Test grouped aggregations with WHERE and HAVING conditions"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    users = []
    for i in range(3):
        user = User(
            username=f'user{i + 1}',
            email=f'user{i + 1}@example.com',
            age=25 + i * 5
        )
        user.save()
        users.append(user)

    # Create orders with different statuses and amounts
    statuses = ['pending', 'paid', 'shipped']
    for user in users:
        for status in statuses:
            for amount in [Decimal('100.00'), Decimal('200.00')]:
                order = Order(
                    user_id=user.id,
                    order_number=f'ORD-{user.id}-{status}',
                    total_amount=amount,
                    status=status
                )
                order.save()

    # Test group by with where condition
    results = (Order.query()
               .where('total_amount > ?', (Decimal('150.00'),))
               .group_by('status')
               .count('*', 'order_count')
               .sum('total_amount', 'sum_amount')  # SQLite allows the alias and original name of an expression to be the same,
               # but if columns with the same name continue to appear, the query results may be different from other databases.
               .aggregate())

    assert len(results) == 3
    for result in results:
        assert result['order_count'] == 3  # 3 users * 1 order (200.00) per status
        assert result['sum_amount'] == Decimal('600.00')  # 3 * 200.00

    # TODO: Test group by with having condition
    # results = (Order.query()
    #            .group_by('status')
    #            .having('SUM(total_amount) > ?', (Decimal('500.00'),))
    #            .count('*', 'order_count')
    #            .sum('total_amount', 'total_amount')
    #            .aggregate())
    #
    # assert len(results) == 3
    # for result in results:
    #     assert result['total_amount'] > Decimal('500.00')


def test_multiple_group_by(order_fixtures):
    """Test aggregations with multiple group by columns"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    users = []
    for i in range(2):
        user = User(
            username=f'user{i + 1}',
            email=f'user{i + 1}@example.com',
            age=30
        )
        user.save()
        users.append(user)

    statuses = ['pending', 'paid']
    for user in users:
        for status in statuses:
            for amount in [Decimal('100.00'), Decimal('200.00')]:
                order = Order(
                    user_id=user.id,
                    order_number=f'ORD-{user.id}-{status}',
                    total_amount=amount,
                    status=status
                )
                order.save()

    # Test multiple group by columns
    results = (Order.query()
               .group_by('user_id', 'status')
               .count('*', 'order_count')
               .sum('total_amount', 'sum_amount')  # SQLite allows the alias and original name of an expression to be the same,
               # but if columns with the same name continue to appear, the query results may be different from other databases.
               .aggregate())

    assert len(results) == 4  # 2 users * 2 statuses
    for result in results:
        assert result['order_count'] == 2  # 2 orders per user-status combination
        assert result['sum_amount'] == Decimal('300.00')  # 100 + 200 per group


def test_aggregate_ordering(order_fixtures):
    """Test ordering by aggregate expressions"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    statuses = ['pending', 'paid', 'shipped']
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    for status in statuses:
        for amount in amounts:
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{status}',
                total_amount=amount,
                status=status
            )
            order.save()

    # Test ordering by aggregate alias
    results = (Order.query()
               .group_by('status')
               .count('*', 'order_count')
               .sum('total_amount', 'sum_amount')  # SQLite allows the alias and original name of an expression to be the same,
               # but if columns with the same name continue to appear, the query results may be different from other databases.
               .order_by('sum_amount DESC')
               .aggregate())

    assert len(results) == 3
    previous_amount = None
    for result in results:
        if previous_amount is not None:
            assert result['sum_amount'] <= previous_amount
        previous_amount = result['sum_amount']


def test_complex_aggregates(order_fixtures):
    """Test complex aggregate queries combining multiple features"""
    User, Order, OrderItem = order_fixtures

    # Create extensive test data
    users = []
    for i in range(3):
        user = User(
            username=f'user{i + 1}',
            email=f'user{i + 1}@example.com',
            age=25 + i * 5
        )
        user.save()
        users.append(user)

    statuses = ['pending', 'paid', 'shipped']
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]

    for user in users:
        for status in statuses:
            for amount in amounts:
                order = Order(
                    user_id=user.id,
                    order_number=f'ORD-{user.id}-{status}',
                    total_amount=amount,
                    status=status
                )
                order.save()

    # Complex query combining multiple features
    results = (Order.query()
               .where('total_amount >= ?', (Decimal('200.00'),))
               .group_by('user_id', 'status')
               .having('COUNT(*) > ?', (1,))
               .count('*', 'order_count')
               .sum('total_amount', 'sum_amount')  # SQLite allows the alias and original name of an expression to be the same,
               # but if columns with the same name continue to appear, the query results may be different from other databases.
               .avg('total_amount', 'avg_amount')
               .min('total_amount', 'min_amount')
               .max('total_amount', 'max_amount')
               .order_by('total_amount DESC')
               .limit(5)
               .aggregate())

    # Verify results
    assert len(results) <= 5  # Respects limit
    for result in results:
        # Verify counts and amounts
        assert result['order_count'] > 1  # From HAVING clause
        assert result['min_amount'] >= Decimal('200.00')  # From WHERE clause
        assert result['sum_amount'] == result['order_count'] * result['avg_amount']
        assert result['min_amount'] <= result['max_amount']

    # Verify ordering
    previous_amount = None
    for result in results:
        if previous_amount is not None:
            assert result['sum_amount'] <= previous_amount
        previous_amount = result['sum_amount']