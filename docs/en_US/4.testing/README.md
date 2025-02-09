# Testing and Quality

This chapter covers comprehensive testing strategies and quality assurance practices for RhoSocial ActiveRecord applications. We'll use both social media and e-commerce examples to demonstrate testing approaches.

## Overview

RhoSocial ActiveRecord provides several testing features and tools:

1. **Unit Testing Support**
   - Model testing
   - Query testing
   - Transaction testing
   - Mock testing
   - Relationship testing

2. **Model Testing**
   - Validation testing
   - Relationship integrity
   - Event handling
   - Transaction boundaries

3. **Performance Testing**
   - Benchmark testing
   - Load testing
   - Profile tools
   - Memory analysis

## Testing Environment

### Basic Setup

```python
import pytest
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig

# Test configuration
def get_test_config():
    return ConnectionConfig(
        database=':memory:',  # Use in-memory database
        options={
            'foreign_keys': True,  # Enable constraints
            'journal_mode': 'WAL'  # Write-Ahead Logging
        }
    )

# Model setup
def configure_test_models(models: List[Type[ActiveRecord]]):
    config = get_test_config()
    for model in models:
        model.configure(config, SQLiteBackend)
```

### Test Models

```python
# Social Media Models
class User(ActiveRecord):
    __table_name__ = 'users'
    id: int
    username: str
    email: str
    created_at: datetime

class Post(ActiveRecord):
    __table_name__ = 'posts'
    id: int
    user_id: int
    content: str
    created_at: datetime

# E-commerce Models
class Order(ActiveRecord):
    __table_name__ = 'orders'
    id: int
    user_id: int
    total: Decimal
    status: str
    created_at: datetime

class Product(ActiveRecord):
    __table_name__ = 'products'
    id: int
    name: str
    price: Decimal
    stock: int
```

## Test Categories

### Unit Tests

Unit tests verify individual components:

```python
def test_user_creation():
    """Test user model creation."""
    user = User(username='test', email='test@example.com')
    user.save()
    assert user.id is not None

def test_order_validation():
    """Test order validation rules."""
    with pytest.raises(ValidationError):
        Order(total=Decimal('-1')).save()
```

### Model Tests

Model tests focus on business logic:

```python
def test_order_processing():
    """Test order processing workflow."""
    order = create_test_order()
    order.process()
    assert order.status == 'processing'
    assert all(item.processed for item in order.items)

def test_post_relationships():
    """Test post relationship integrity."""
    post = create_test_post()
    assert post.author is not None
    assert post in post.author.posts
```

### Performance Tests

Performance tests measure system behavior:

```python
def test_query_performance():
    """Test query performance."""
    start = time.perf_counter()
    
    results = User.query()\
        .with_('posts.comments')\
        .where('status = ?', ('active',))\
        .all()
    
    duration = time.perf_counter() - start
    assert duration < 0.1  # Under 100ms
```

## Testing Tools

1. **pytest**: Primary testing framework
   - Fixture support
   - Parameterized tests
   - Mock support

2. **Coverage.py**: Code coverage tool
   - Statement coverage
   - Branch coverage
   - Report generation

3. **Profile Tools**
   - Query profiling
   - Memory profiling
   - Performance metrics

## Best Practices

1. **Test Organization**
   - Group related tests
   - Use descriptive names
   - Follow naming conventions

2. **Data Management**
   - Use test fixtures
   - Clean up test data
   - Maintain isolation

3. **Performance Testing**
   - Regular benchmarks
   - Realistic data sets
   - Resource monitoring

4. **Quality Metrics**
   - Code coverage
   - Test coverage
   - Performance baselines

## In This Chapter

1. [Unit Testing](unit_testing.md)
   - Basic test setup
   - Model testing
   - Query testing
   - Mock testing

2. [Model Testing](model_testing.md)
   - Validation testing
   - Relationship testing
   - Event testing
   - Transaction testing

3. [Performance Testing](performance_testing.md)
   - Benchmark tests
   - Load tests
   - Profile tools

## Example Test Suite

Here's a complete example of a test suite:

```python
# test_social_media.py
import pytest
from datetime import datetime
from decimal import Decimal

# Fixtures
@pytest.fixture
def setup_models():
    """Configure test models."""
    models = [User, Post, Comment]
    configure_test_models(models)
    return models

@pytest.fixture
def sample_user():
    """Create sample user."""
    return User(
        username='testuser',
        email='test@example.com',
        created_at=datetime.now()
    )

# Unit Tests
def test_user_creation(setup_models, sample_user):
    """Test user creation."""
    sample_user.save()
    assert sample_user.id is not None

def test_post_creation(setup_models, sample_user):
    """Test post creation with relationships."""
    sample_user.save()
    
    post = Post(
        user_id=sample_user.id,
        content='Test post',
        created_at=datetime.now()
    )
    post.save()
    
    assert post.author.id == sample_user.id
    assert post in sample_user.posts

# Model Tests
def test_order_workflow(setup_models):
    """Test complete order workflow."""
    # Create order
    order = create_test_order()
    
    # Process order
    with Order.transaction():
        order.process()
        for item in order.items:
            item.product.stock -= item.quantity
            item.product.save()
    
    # Verify results
    assert order.status == 'processed'
    for item in order.items:
        product = Product.find_one(item.product_id)
        assert product.stock >= 0

# Performance Tests
def test_feed_performance(setup_models):
    """Test user feed performance."""
    # Create test data
    users = create_test_users(100)
    posts = create_test_posts(1000)
    
    # Test feed query
    start = time.perf_counter()
    
    feed = Post.query()\
        .with_('author', 'comments.author')\
        .order_by('created_at DESC')\
        .limit(20)\
        .all()
    
    duration = time.perf_counter() - start
    assert duration < 0.1  # Under 100ms
```

## Next Steps

1. Study [Unit Testing](unit_testing.md) for detailed testing strategies
2. Learn about [Model Testing](model_testing.md) for business logic testing
3. Explore [Performance Testing](performance_testing.md) for optimization