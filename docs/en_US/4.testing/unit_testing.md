# Unit Testing

This guide covers unit testing approaches for RhoSocial ActiveRecord applications. We'll use both social media and e-commerce examples to demonstrate testing strategies.

## Test Setup

### Basic Test Configuration

```python
import pytest
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig

@pytest.fixture
def db_config():
    """Create in-memory database configuration."""
    return ConnectionConfig(
        database=':memory:',
        options={'foreign_keys': True}
    )

@pytest.fixture
def setup_models(db_config):
    """Configure models with test database."""
    models = [User, Post, Comment]  # Your models
    for model in models:
        model.configure(db_config, SQLiteBackend)
    yield models
```

### Test Data Fixtures

```python
@pytest.fixture
def sample_user():
    """Create sample user for testing."""
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'created_at': datetime.now()
    }

@pytest.fixture
def sample_post(sample_user):
    """Create sample post for testing."""
    return {
        'user_id': sample_user['id'],
        'content': 'Test post content',
        'created_at': datetime.now()
    }
```

## Model Testing

### Testing Model Creation

```python
def test_user_creation(setup_models, sample_user):
    """Test creating a new user."""
    user = User(**sample_user)
    user.save()
    
    assert user.id is not None
    assert user.username == sample_user['username']
    assert user.email == sample_user['email']

def test_post_with_relations(setup_models, sample_user):
    """Test creating post with relations."""
    # Create user
    user = User(**sample_user)
    user.save()
    
    # Create post
    post = Post(
        user_id=user.id,
        content='Test content'
    )
    post.save()
    
    # Verify relationships
    assert post.author.id == user.id
    assert post in user.posts
```

### Testing Validation

```python
def test_user_validation(setup_models):
    """Test user model validation."""
    with pytest.raises(ValidationError):
        User(username='', email='invalid').save()

def test_order_validation(setup_models):
    """Test order total validation."""
    with pytest.raises(ValidationError) as exc:
        Order(
            user_id=1,
            total=Decimal('100'),
            items=[
                {'product_id': 1, 'quantity': 2, 'price': Decimal('20')}
            ]
        ).save()
    assert "Total does not match items" in str(exc.value)
```

## Query Testing

### Testing Basic Queries

```python
def test_find_one(setup_models, sample_user):
    """Test finding single record."""
    user = User(**sample_user)
    user.save()
    
    found = User.find_one(user.id)
    assert found.id == user.id
    assert found.username == user.username

def test_find_by_condition(setup_models):
    """Test finding records by condition."""
    # Create test data
    User(username='user1', status='active').save()
    User(username='user2', status='active').save()
    User(username='user3', status='inactive').save()
    
    # Test query
    active_users = User.find_all({'status': 'active'})
    assert len(active_users) == 2
```

### Testing Complex Queries

```python
def test_order_with_items_query(setup_models):
    """Test complex order query with items."""
    # Create test data
    order = create_test_order()
    
    # Test query
    result = Order.query()\
        .with_('items.product')\
        .where('total > ?', (Decimal('100'),))\
        .one()
    
    assert result.id == order.id
    assert len(result.items) > 0
    assert all(item.product is not None for item in result.items)

def test_user_post_comments_query(setup_models):
    """Test nested relationship query."""
    # Create test data
    user = create_test_user_with_posts()
    
    # Test query
    result = User.query()\
        .with_('posts.comments.author')\
        .find_one(user.id)
    
    assert result.posts
    assert result.posts[0].comments
    assert result.posts[0].comments[0].author
```

## Transaction Testing

### Testing Basic Transactions

```python
def test_basic_transaction(setup_models):
    """Test basic transaction commit/rollback."""
    user = User(username='test')
    
    with User.transaction():
        user.save()
        assert User.find_one(user.id) is not None
    
    # Transaction committed
    assert User.find_one(user.id) is not None

def test_transaction_rollback(setup_models):
    """Test transaction rollback on error."""
    user = User(username='test')
    
    try:
        with User.transaction():
            user.save()
            raise ValueError("Test error")
    except ValueError:
        pass
    
    # Transaction rolled back
    assert User.find_one(user.id) is None
```

### Testing Nested Transactions

```python
def test_nested_transaction(setup_models):
    """Test nested transaction behavior."""
    with Order.transaction() as tx1:
        order = create_test_order()
        
        with Order.transaction() as tx2:
            # Update items
            for item in order.items:
                item.quantity += 1
                item.save()
            
            # Create savepoint
            tx2.create_savepoint('updated_quantities')
            
            try:
                # This will fail
                order.total = Decimal('-1')
                order.save()
            except ValidationError:
                # Rollback to savepoint
                tx2.rollback_to_savepoint('updated_quantities')
        
        # Outer transaction still valid
        assert Order.find_one(order.id) is not None
```

## Mock Testing

### Mocking Database Calls

```python
def test_database_error(setup_models, mocker):
    """Test handling of database errors."""
    # Mock database execution
    mocker.patch.object(
        SQLiteBackend,
        'execute',
        side_effect=DatabaseError("Test error")
    )
    
    with pytest.raises(DatabaseError):
        User(username='test').save()

def test_connection_retry(setup_models, mocker):
    """Test connection retry behavior."""
    connect_mock = mocker.patch.object(SQLiteBackend, 'connect')
    connect_mock.side_effect = [
        ConnectionError("First attempt"),
        None  # Second attempt succeeds
    ]
    
    User(username='test').save()
    assert connect_mock.call_count == 2
```

### Mocking External Services

```python
def test_order_processing(setup_models, mocker):
    """Test order processing with mocked payment service."""
    # Mock payment service
    payment_mock = mocker.patch('services.payment.process_payment')
    payment_mock.return_value = {'id': 'payment123', 'status': 'success'}
    
    # Create and process order
    order = create_test_order()
    order.process()
    
    # Verify payment was called
    payment_mock.assert_called_once_with(
        amount=order.total,
        currency='USD'
    )
    assert order.status == 'processing'
```

## Integration Testing

### Testing Model Interactions

```python
def test_order_product_integration(setup_models):
    """Test order and product stock interaction."""
    # Create test data
    product = Product(name='Test', stock=10, price=Decimal('10'))
    product.save()
    
    # Create order
    order = Order(user_id=1, status='pending')
    order.save()
    
    # Add item
    item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        quantity=2,
        price=product.price
    )
    
    with Order.transaction():
        item.save()
        product.stock -= item.quantity
        product.save()
    
    # Verify stock updated
    updated_product = Product.find_one(product.id)
    assert updated_product.stock == 8
```

## Best Practices

1. **Use Fixtures**: Create reusable test fixtures
2. **Test Isolation**: Each test should run independently
3. **Mock External Services**: Mock external dependencies
4. **Test Edge Cases**: Include error conditions
5. **Transaction Testing**: Test transaction boundaries

## Next Steps

1. Learn about [Performance Testing](performance_testing.md)
2. Explore [Mock Testing](mock_testing.md)
3. Study [Integration Testing](integration_testing.md)