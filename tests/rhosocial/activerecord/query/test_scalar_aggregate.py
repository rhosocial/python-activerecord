"""Test scalar aggregate calculations without grouping."""
from decimal import Decimal
from .utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()

def test_scalar_count(order_fixtures):
    """Test basic COUNT aggregation"""
    User, Order, OrderItem = order_fixtures

    # Create test user
    user = User(
        username='test_user',
        email='test@example.com',
        age=30
    )
    user.save()

    # Create multiple orders
    for i in range(5):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1:03d}',
            total_amount=Decimal('100.00')
        )
        order.save()

    # Test total count
    count = Order.query().count()
    assert count == 5

    # Test count with condition
    count = Order.query().where('total_amount > ?', (Decimal('50.00'),)).count()
    assert count == 5

    # Test count with limit (should not affect count)
    count = Order.query().limit(2).count()
    assert count == 5

    # Test distinct count
    count = Order.query().count('user_id', distinct=True)
    assert count == 1

def test_scalar_sum(order_fixtures):
    """Test basic SUM aggregation"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1:03d}',
            total_amount=amount
        )
        order.save()

    # Test total sum
    total = Order.query().sum('total_amount')
    assert total == Decimal('600.00')

    # Test sum with condition
    total = Order.query().where('total_amount > ?', (Decimal('150.00'),)).sum('total_amount')
    assert total == Decimal('500.00')

def test_scalar_avg(order_fixtures):
    """Test basic AVG aggregation"""
    User, Order, OrderItem = order_fixtures

    # Create users with different ages
    ages = [25, 30, 35]
    for i, age in enumerate(ages):
        user = User(
            username=f'user{i+1}',
            email=f'user{i+1}@example.com',
            age=age
        )
        user.save()

    # Test average age
    avg_age = User.query().avg('age')
    assert avg_age == 30.0

    # Test average with condition
    avg_age = User.query().where('age > ?', (27,)).avg('age')
    assert avg_age == 32.5

def test_scalar_min_max(order_fixtures):
    """Test basic MIN and MAX aggregations"""
    User, Order, OrderItem = order_fixtures

    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    # Create orders with different amounts
    amounts = [Decimal('100.00'), Decimal('200.00'), Decimal('300.00')]
    for i, amount in enumerate(amounts):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1:03d}',
            total_amount=amount
        )
        order.save()

    # Test min and max
    min_amount = Order.query().min('total_amount')
    max_amount = Order.query().max('total_amount')
    assert min_amount == Decimal('100.00')
    assert max_amount == Decimal('300.00')

    # Test with condition
    min_amount = Order.query().where('total_amount > ?', (Decimal('150.00'),)).min('total_amount')
    max_amount = Order.query().where('total_amount < ?', (Decimal('250.00'),)).max('total_amount')
    assert min_amount == Decimal('200.00')
    assert max_amount == Decimal('200.00')

def test_aggregate_with_complex_conditions(order_fixtures):
    """Test aggregations with complex query conditions"""
    User, Order, OrderItem = order_fixtures

    # Create users and orders
    for i in range(3):
        user = User(
            username=f'user{i+1}',
            email=f'user{i+1}@example.com',
            age=25 + i * 5
        )
        user.save()

        # Create orders for each user
        for j in range(2):
            order = Order(
                user_id=user.id,
                order_number=f'ORD-{i+1}-{j+1}',
                total_amount=Decimal(f'{(i+1)*100}.00'),
                status='paid' if j % 2 == 0 else 'pending'
            )
            order.save()

    # Test count with OR conditions
    count = (Order.query()
            .start_or_group()
            .where('total_amount > ?', (Decimal('150.00'),))
            .or_where('status = ?', ('pending',))
            .end_or_group()
            .count())
    assert count == 5  # Orders with amount > 150 OR status = pending

    # Test sum with complex conditions
    total = (Order.query()
             .where('status = ?', ('paid',))
             .where('total_amount < ?', (Decimal('250.00'),))
             .sum('total_amount'))
    assert total == Decimal('300.00')  # Only first user's paid order

    # Test average with BETWEEN
    avg_amount = (Order.query()
                 .between('total_amount', Decimal('150.00'), Decimal('250.00'))
                 .avg('total_amount'))
    assert avg_amount == Decimal('200.00')

def test_aggregate_with_ordering_and_limit(order_fixtures):
    """Test aggregations with ORDER BY and LIMIT clauses (which should be ignored)"""
    User, Order, OrderItem = order_fixtures

    # Create test data
    user = User(username='test_user', email='test@example.com', age=30)
    user.save()

    for i in range(5):
        order = Order(
            user_id=user.id,
            order_number=f'ORD-{i+1:03d}',
            total_amount=Decimal(f'{(i+1)*100}.00')
        )
        order.save()

    # These clauses should not affect the aggregate results
    total = (Order.query()
             .order_by('total_amount DESC')
             .limit(2)
             .sum('total_amount'))
    assert total == Decimal('1500.00')  # Should sum all records


    # Basic aggregation, should always return the correct result
    total = Order.query().sum('total_amount')
    assert total == Decimal('1500.00')  # 100+200+300+400+500

    # With limit, should still give same result
    total_with_limit = Order.query().limit(2).sum('total_amount')
    assert total_with_limit == Decimal('1500.00')  # Still sums all records

    # With offset, returns None because single result is skipped
    total_with_offset = Order.query().limit(1).offset(1).sum('total_amount')
    assert total_with_offset is None  # Offset skips the only result

    # With order by, should still give same result
    avg = Order.query().order_by('total_amount DESC').avg('total_amount')
    assert avg == Decimal('300.00')  # (1500/5)

    # Additional verifications
    count = Order.query().limit(1).count()
    assert count == 5  # Counts all records regardless of limit

    min_amount = Order.query().order_by('total_amount DESC').min('total_amount')
    assert min_amount == Decimal('100.00')  # Still finds global minimum

    # With both limit and offset
    max_amount = Order.query().limit(2).offset(1).max('total_amount')
    assert max_amount is None  # Single result is skipped due to offset