# Model Testing Guide

This guide covers approaches and best practices for testing RhoSocial ActiveRecord models in backend implementations.

## Test Setup

### Base Test Configuration

```python
import pytest
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig

class TestBase:
    """Base class for model tests."""
    
    @pytest.fixture
    def db_config(self):
        """Create test database configuration."""
        return ConnectionConfig(
            database=':memory:',  # Use in-memory database for tests
            options={
                'foreign_keys': True,
                'journal_mode': 'WAL'
            }
        )
    
    @pytest.fixture
    def setup_models(self, db_config):
        """Configure models for testing."""
        # Define test models
        test_models = [User, Post, Comment]  # Social media models
        # test_models = [User, Order, Product, OrderItem]  # E-commerce models
        
        # Configure each model
        for model in test_models:
            model.configure(db_config, SQLiteBackend)
        
        yield test_models
```

### Test Data Factories

```python
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

@dataclass
class TestDataFactory:
    """Factory for creating test data."""
    
    @staticmethod
    def create_user(**kwargs) -> User:
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
    def create_post(user: Optional[User] = None, **kwargs) -> Post:
        """Create test post."""
        if user is None:
            user = TestDataFactory.create_user()
        
        data = {
            'user_id': user.id,
            'content': f"Test post {datetime.now().timestamp()}",
            'created_at': datetime.now(),
            **kwargs
        }
        post = Post(**data)
        post.save()
        return post
    
    @staticmethod
    def create_order(user: Optional[User] = None, **kwargs) -> Order:
        """Create test order."""
        if user is None:
            user = TestDataFactory.create_user()
        
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

## Model Tests

### Basic Model Tests

```python
class TestUser(TestBase):
    """Test user model."""
    
    def test_create_user(self, setup_models):
        """Test user creation."""
        user = TestDataFactory.create_user()
        assert user.id is not None
        assert '@' in user.email
    
    def test_validate_username(self, setup_models):
        """Test username validation."""
        with pytest.raises(ValidationError):
            TestDataFactory.create_user(username='')
    
    def test_update_user(self, setup_models):
        """Test user update."""
        user = TestDataFactory.create_user()
        user.username = 'updated_username'
        user.save()
        
        updated = User.find_one(user.id)
        assert updated.username == 'updated_username'
    
    def test_delete_user(self, setup_models):
        """Test user deletion."""
        user = TestDataFactory.create_user()
        user.delete()
        
        assert User.find_one(user.id) is None

class TestOrder(TestBase):
    """Test order model."""
    
    def test_create_order(self, setup_models):
        """Test order creation."""
        order = TestDataFactory.create_order()
        assert order.id is not None
        assert order.status == 'pending'
    
    def test_validate_total(self, setup_models):
        """Test order total validation."""
        with pytest.raises(ValidationError):
            TestDataFactory.create_order(total=Decimal('-100.00'))
```

### Relationship Tests

```python
class TestUserRelationships(TestBase):
    """Test user relationships."""
    
    def test_user_posts(self, setup_models):
        """Test user-posts relationship."""
        user = TestDataFactory.create_user()
        posts = [TestDataFactory.create_post(user=user) 
                for _ in range(3)]
        
        assert len(user.posts) == 3
        assert all(post.author.id == user.id for post in user.posts)
    
    def test_user_comments(self, setup_models):
        """Test user-comments relationship."""
        user = TestDataFactory.create_user()
        post = TestDataFactory.create_post()
        comments = [TestDataFactory.create_comment(user=user, post=post) 
                   for _ in range(3)]
        
        assert len(user.comments) == 3
        assert all(comment.author.id == user.id for comment in user.comments)

class TestOrderRelationships(TestBase):
    """Test order relationships."""
    
    def test_order_items(self, setup_models):
        """Test order-items relationship."""
        order = TestDataFactory.create_order()
        items = [TestDataFactory.create_order_item(order=order) 
                for _ in range(3)]
        
        assert len(order.items) == 3
        assert all(item.order.id == order.id for item in order.items)
```

### Query Tests

```python
class TestUserQueries(TestBase):
    """Test user queries."""
    
    def test_find_by_username(self, setup_models):
        """Test finding user by username."""
        user = TestDataFactory.create_user(username='testuser')
        found = User.query()\
            .where('username = ?', ('testuser',))\
            .one()
        
        assert found.id == user.id
    
    def test_active_users(self, setup_models):
        """Test querying active users."""
        active_users = [
            TestDataFactory.create_user(status='active')
            for _ in range(3)
        ]
        inactive_user = TestDataFactory.create_user(status='inactive')
        
        users = User.query()\
            .where('status = ?', ('active',))\
            .all()
        
        assert len(users) == 3
        assert all(user.status == 'active' for user in users)

class TestOrderQueries(TestBase):
    """Test order queries."""
    
    def test_pending_orders(self, setup_models):
        """Test querying pending orders."""
        pending_orders = [
            TestDataFactory.create_order(status='pending')
            for _ in range(3)
        ]
        completed_order = TestDataFactory.create_order(status='completed')
        
        orders = Order.query()\
            .where('status = ?', ('pending',))\
            .all()
        
        assert len(orders) == 3
        assert all(order.status == 'pending' for order in orders)
```

### Transaction Tests

```python
class TestTransactions(TestBase):
    """Test transaction handling."""
    
    def test_successful_transaction(self, setup_models):
        """Test successful transaction."""
        with User.transaction():
            user = TestDataFactory.create_user()
            post = TestDataFactory.create_post(user=user)
        
        # Verify changes persisted
        assert User.find_one(user.id) is not None
        assert Post.find_one(post.id) is not None
    
    def test_failed_transaction(self, setup_models):
        """Test failed transaction rollback."""
        user = TestDataFactory.create_user()
        
        with pytest.raises(ValueError):
            with User.transaction():
                post = TestDataFactory.create_post(user=user)
                raise ValueError("Test error")
        
        # Verify changes rolled back
        assert Post.find_one(post.id) is None
```

### Performance Tests

```python
class TestModelPerformance(TestBase):
    """Test model performance."""
    
    def test_batch_creation(self, setup_models):
        """Test batch record creation."""
        start = time.perf_counter()
        
        with User.transaction():
            users = [TestDataFactory.create_user() 
                    for _ in range(100)]
        
        duration = time.perf_counter() - start
        assert duration < 1.0  # Less than 1 second
    
    def test_query_performance(self, setup_models):
        """Test query performance."""
        # Create test data
        users = [TestDataFactory.create_user() 
                for _ in range(100)]
        for user in users:
            [TestDataFactory.create_post(user=user) 
             for _ in range(5)]
        
        start = time.perf_counter()
        
        # Test eager loading
        posts = Post.query()\
            .with_('author')\
            .all()
        
        duration = time.perf_counter() - start
        assert duration < 0.1  # Less than 100ms
```

## Mock Testing

### Backend Mocks

```python
class TestWithMocks(TestBase):
    """Test using mocks."""
    
    def test_database_error(self, setup_models, mocker):
        """Test database error handling."""
        mocker.patch.object(
            SQLiteBackend,
            'execute',
            side_effect=DatabaseError("Test error")
        )
        
        with pytest.raises(DatabaseError):
            TestDataFactory.create_user()
    
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
        
        TestDataFactory.create_user()
        assert connect_mock.call_count == 2
```

## Best Practices

1. **Test Organization**
   - Group related tests
   - Use descriptive names
   - Follow naming conventions
   - Maintain test isolation

2. **Test Data**
   - Use test factories
   - Create test fixtures
   - Clean up test data
   - Keep tests independent

3. **Test Coverage**
   - Test CRUD operations
   - Test relationships
   - Test validation rules
   - Test error conditions

4. **Test Performance**
   - Monitor test speed
   - Test batch operations
   - Test query efficiency
   - Test resource usage

5. **Test Documentation**
   - Document test purpose
   - Explain test scenarios
   - Document assumptions
   - Maintain examples

## Next Steps

1. Study [Implementation Guide](implementation_guide.md)
2. Learn about [Custom Backend](custom_backend.md)
3. Review [SQLite Implementation](sqlite_impl.md