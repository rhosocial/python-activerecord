# Testing Strategy Guide

This guide covers comprehensive testing strategies for RhoSocial ActiveRecord applications, with examples from both social media and e-commerce domains.

## Test Setup

### Basic Configuration

```python
import pytest
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig

@pytest.fixture
def db_config():
    """Create test database configuration."""
    return ConnectionConfig(
        database=':memory:',
        options={
            'foreign_keys': True,
            'journal_mode': 'WAL'
        }
    )

@pytest.fixture
def setup_models(db_config):
    """Configure models for testing."""
    models = [User, Post, Comment]  # Social media models
    # models = [User, Order, Product, OrderItem]  # E-commerce models
    
    for model in models:
        model.configure(db_config, SQLiteBackend)
    
    yield models

@pytest.fixture
def test_data():
    """Create test data."""
    return {
        'users': create_test_users(10),
        'posts': create_test_posts(50),
        'comments': create_test_comments(100)
    }
```

### Test Data Factories

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

@dataclass
class UserFactory:
    """Factory for creating test users."""
    
    @staticmethod
    def create(**kwargs) -> User:
        """Create test user."""
        data = {
            'username': f"user_{datetime.now().timestamp()}",
            'email': f"user_{datetime.now().timestamp()}@example.com",
            'created_at': datetime.now(),
            **kwargs
        }
        user = User(**data)
        user.save()
        return user
    
    @staticmethod
    def create_batch(count: int, **kwargs) -> List[User]:
        """Create multiple test users."""
        return [UserFactory.create(**kwargs) for _ in range(count)]

@dataclass
class OrderFactory:
    """Factory for creating test orders."""
    
    @staticmethod
    def create(user: Optional[User] = None, **kwargs) -> Order:
        """Create test order."""
        if user is None:
            user = UserFactory.create()
        
        data = {
            'user_id': user.id,
            'total': Decimal('100.00'),
            'status': 'pending',
            'created_at': datetime.now(),
            **kwargs
        }
        order = Order(**data)
        order.save()
        return order
```

## Unit Testing

### Model Tests

```python
class TestUser:
    """Test user model."""
    
    def test_create_user(self, setup_models):
        """Test user creation."""
        user = User(
            username='testuser',
            email='test@example.com'
        )
        user.save()
        
        assert user.id is not None
        assert user.username == 'testuser'
    
    def test_validate_email(self, setup_models):
        """Test email validation."""
        with pytest.raises(ValidationError):
            User(
                username='testuser',
                email='invalid'
            ).save()
    
    def test_unique_username(self, setup_models):
        """Test username uniqueness."""
        User(username='testuser').save()
        
        with pytest.raises(IntegrityError):
            User(username='testuser').save()

class TestOrder:
    """Test order model."""
    
    def test_create_order(self, setup_models):
        """Test order creation."""
        user = UserFactory.create()
        order = OrderFactory.create(user=user)
        
        assert order.id is not None
        assert order.user_id == user.id
    
    def test_order_total(self, setup_models):
        """Test order total calculation."""
        order = OrderFactory.create()
        
        # Add items
        OrderItem(
            order_id=order.id,
            product_id=1,
            quantity=2,
            price=Decimal('10.00')
        ).save()
        
        assert order.calculate_total() == Decimal('20.00')
```

### Query Tests

```python
class TestUserQueries:
    """Test user queries."""
    
    def test_find_by_username(self, setup_models, test_data):
        """Test finding user by username."""
        user = User.query()\
            .where('username = ?', ('testuser',))\
            .one()
        
        assert user is not None
        assert user.username == 'testuser'
    
    def test_active_users(self, setup_models, test_data):
        """Test querying active users."""
        users = User.query()\
            .where('status = ?', ('active',))\
            .all()
        
        assert len(users) > 0
        assert all(user.status == 'active' for user in users)

class TestOrderQueries:
    """Test order queries."""
    
    def test_pending_orders(self, setup_models, test_data):
        """Test querying pending orders."""
        orders = Order.query()\
            .where('status = ?', ('pending',))\
            .all()
        
        assert len(orders) > 0
        assert all(order.status == 'pending' for order in orders)
    
    def test_order_with_items(self, setup_models, test_data):
        """Test eager loading order items."""
        order = Order.query()\
            .with_('items.product')\
            .find_one(1)
        
        assert order is not None
        assert len(order.items) > 0
        assert all(item.product is not None for item in order.items)
```

## Integration Testing

### Transaction Tests

```python
class TestOrderProcessing:
    """Test order processing workflow."""
    
    def test_process_order(self, setup_models):
        """Test complete order processing."""
        # Create order
        order = OrderFactory.create()
        
        # Add items
        product = Product(name='Test', price=Decimal('10.00'))
        product.save()
        
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=2
        ).save()
        
        # Process order
        with Order.transaction():
            order.process()
            
            # Verify status
            assert order.status == 'processing'
            
            # Verify inventory
            product.refresh()
            assert product.stock == 8

    def test_failed_payment(self, setup_models):
        """Test order processing with failed payment."""
        order = OrderFactory.create()
        
        with pytest.raises(PaymentError):
            with Order.transaction():
                order.process()
                raise PaymentError("Payment failed")
        
        # Verify order status
        order.refresh()
        assert order.status == 'payment_failed'
```

### Relationship Tests

```python
class TestUserRelationships:
    """Test user relationships."""
    
    def test_user_posts(self, setup_models):
        """Test user-posts relationship."""
        user = UserFactory.create()
        posts = [Post(user_id=user.id, content=f"Post {i}") 
                for i in range(3)]
        
        for post in posts:
            post.save()
        
        assert len(user.posts) == 3
        assert all(post.author.id == user.id for post in user.posts)
    
    def test_post_comments(self, setup_models):
        """Test post-comments relationship."""
        post = Post(user_id=1, content="Test post")
        post.save()
        
        comments = [Comment(post_id=post.id, user_id=1, content=f"Comment {i}")
                   for i in range(3)]
        
        for comment in comments:
            comment.save()
        
        assert len(post.comments) == 3
        assert all(comment.post.id == post.id for comment in post.comments)

class TestOrderRelationships:
    """Test order relationships."""
    
    def test_order_items(self, setup_models):
        """Test order-items relationship."""
        order = OrderFactory.create()
        items = [
            OrderItem(
                order_id=order.id,
                product_id=1,
                quantity=i + 1
            )
            for i in range(3)
        ]
        
        for item in items:
            item.save()
        
        assert len(order.items) == 3
        assert all(item.order.id == order.id for item in order.items)
```

## Performance Testing

### Query Performance

```python
class TestQueryPerformance:
    """Test query performance."""
    
    def test_query_timing(self, setup_models, test_data):
        """Test query execution time."""
        start = time.perf_counter()
        
        users = User.query()\
            .with_('posts.comments')\
            .all()
        
        duration = time.perf_counter() - start
        assert duration < 0.1  # Less than 100ms
    
    def test_batch_processing(self, setup_models, test_data):
        """Test batch processing performance."""
        start = time.perf_counter()
        
        batch_size = 100
        processed = 0
        
        while True:
            users = User.query()\
                .limit(batch_size)\
                .offset(processed)\
                .all()
            
            if not users:
                break
            
            for user in users:
                process_user(user)
            
            processed += len(users)
        
        duration = time.perf_counter() - start
        assert duration < 1.0  # Less than 1 second
```

### Memory Testing

```python
class TestMemoryUsage:
    """Test memory usage."""
    
    def test_memory_efficiency(self, setup_models):
        """Test memory-efficient queries."""
        import tracemalloc
        
        tracemalloc.start()
        start_snapshot = tracemalloc.take_snapshot()
        
        # Execute query
        users = User.query()\
            .select('id', 'username')\  # Select only needed fields
            .all()
        
        end_snapshot = tracemalloc.take_snapshot()
        
        # Compare memory usage
        stats = end_snapshot.compare_to(start_snapshot, 'lineno')
        
        # Verify memory usage
        total_memory = sum(stat.size_diff for stat in stats)
        assert total_memory < 1024 * 1024  # Less than 1MB
```

## Mock Testing

### Database Mocks

```python
class TestWithMocks:
    """Test using mocks."""
    
    def test_database_error(self, setup_models, mocker):
        """Test database error handling."""
        # Mock database execution
        mocker.patch.object(
            SQLiteBackend,
            'execute',
            side_effect=DatabaseError("Test error")
        )
        
        with pytest.raises(DatabaseError):
            User(username='test').save()
    
    def test_connection_retry(self, setup_models, mocker):
        """Test connection retry behavior."""
        connect_mock = mocker.patch.object(
            SQLiteBackend,
            'connect'
        )
        connect_mock.side_effect = [
            ConnectionError("First attempt"),
            None  # Second attempt succeeds
        ]
        
        User(username='test').save()
        assert connect_mock.call_count == 2
```

### Service Mocks

```python
class TestOrderServices:
    """Test order-related services."""
    
    def test_payment_processing(self, setup_models, mocker):
        """Test payment processing with mocked service."""
        # Mock payment service
        payment_mock = mocker.patch('services.payment.process_payment')
        payment_mock.return_value = {
            'id': 'payment123',
            'status': 'success'
        }
        
        # Process order
        order = OrderFactory.create()
        order.process()
        
        # Verify payment was called
        payment_mock.assert_called_once_with(
            amount=order.total,
            currency='USD'
        )
        assert order.status == 'processing'
```

## Best Practices

1. **Test Organization**
   - Group related tests
   - Use descriptive names
   - Follow naming conventions
   - Maintain test isolation

2. **Test Data**
   - Use factories for test data
   - Create realistic test cases
   - Clean up test data
   - Avoid dependencies

3. **Performance Testing**
   - Test query performance
   - Monitor memory usage
   - Test batch operations
   - Set performance criteria

4. **Mock Testing**
   - Mock external services
   - Test error conditions
   - Verify interactions
   - Use appropriate mocks

5. **Test Coverage**
   - Test core functionality
   - Include edge cases
   - Test error handling
   - Maintain coverage metrics

## Next Steps

1. Study [Performance Optimization](performance_optimization.md)
2. Review [Error Handling](error_handling.md)
3. Learn about [Transaction Usage](transaction_usage.md)