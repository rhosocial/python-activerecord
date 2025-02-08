# Common Issues and Solutions

This guide covers common issues encountered when using RhoSocial ActiveRecord and their solutions, with examples from both social media and e-commerce applications.

## Installation Issues

### SQLite Version Issues

**Issue**: SQLite version compatibility errors.

**Solution**:
```python
# Check SQLite version
import sqlite3
print(sqlite3.sqlite_version)  # Should be 3.35.0 or higher

# If version is too old:
# 1. Upgrade SQLite
# 2. Or use different Python SQLite package:
pip install pysqlite3-binary
```

### Database Backend Issues

**Issue**: Missing database backend dependencies.

**Solution**:
```bash
# Install specific backend
pip install rhosocial-activerecord[mysql]     # MySQL support
pip install rhosocial-activerecord[pgsql]     # PostgreSQL support

# Install all backends
pip install rhosocial-activerecord[databases]
```

## Configuration Issues

### Database Connection

**Issue**: Unable to connect to database.

**Solution**:
```python
# Verify connection configuration
config = ConnectionConfig(
    database='app.db',
    host='localhost',
    username='user',
    password='pass',
    # Add debug options
    options={
        'debug': True,
        'trace': True
    }
)

# Test connection
try:
    User.configure(config, SQLiteBackend)
    User.query().one()  # Test query
except ConnectionError as e:
    print(f"Connection failed: {e}")
    # Check connection parameters
```

### Model Configuration

**Issue**: Models not properly configured.

**Solution**:
```python
# Ensure proper model configuration
class User(ActiveRecord):
    __table_name__ = 'users'  # Must set table name
    
    # Define all fields
    id: int
    username: str
    email: str

# Configure before use
User.configure(config, SQLiteBackend)

# Common error: Using model before configuration
try:
    user = User(username='test')
    user.save()
except DatabaseError:
    print("Model not configured")
    User.configure(config, SQLiteBackend)
```

## Query Issues

### N+1 Query Problem

**Issue**: Multiple queries executed for related records.

**Solution**:
```python
# Bad: N+1 queries
posts = Post.query().all()
for post in posts:
    author = post.author  # Extra query per post

# Good: Use eager loading
posts = Post.query()\
    .with_('author')\
    .all()

# E-commerce example
# Bad
orders = Order.query().all()
for order in orders:
    items = order.items  # Extra query
    for item in items:
        product = item.product  # Extra query

# Good
orders = Order.query()\
    .with_('items.product')\
    .all()
```

### Memory Issues

**Issue**: Out of memory with large result sets.

**Solution**:
```python
# Bad: Loading all records at once
users = User.query().all()

# Good: Batch processing
def process_users(batch_size: int = 1000):
    offset = 0
    while True:
        users = User.query()\
            .limit(batch_size)\
            .offset(offset)\
            .all()
        
        if not users:
            break
        
        for user in users:
            process_user(user)
        
        offset += batch_size
```

## Relationship Issues

### Circular Dependencies

**Issue**: Circular relationship imports.

**Solution**:
```python
# Bad: Direct imports
from .user import User
from .post import Post

# Good: Use string references
class User(ActiveRecord):
    posts: List['Post'] = HasMany('Post', foreign_key='user_id')

class Post(ActiveRecord):
    author: 'User' = BelongsTo('User', foreign_key='user_id')
```

### Missing Relationships

**Issue**: Relationship not found errors.

**Solution**:
```python
# Ensure proper relationship definition
class Order(ActiveRecord):
    # Define both sides of relationship
    user: 'User' = BelongsTo('User', foreign_key='user_id')
    items: List['OrderItem'] = HasMany('OrderItem', foreign_key='order_id')

class OrderItem(ActiveRecord):
    # Define inverse relationship
    order: 'Order' = BelongsTo('Order', foreign_key='order_id')
    product: 'Product' = BelongsTo('Product', foreign_key='product_id')

# Test relationships
order = Order.find_one(1)
try:
    items = order.items
except AttributeError:
    print("Relationship not defined properly")
```

## Transaction Issues

### Deadlocks

**Issue**: Deadlocks in concurrent transactions.

**Solution**:
```python
from functools import wraps
from time import sleep

def with_retry(max_attempts: int = 3, delay: float = 1.0):
    """Retry decorator for deadlocks."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except DeadlockError as e:
                    last_error = e
                    if attempt + 1 < max_attempts:
                        sleep(delay * (2 ** attempt))
                    continue
            
            raise last_error
        
        return wrapper
    return decorator

# Usage
@with_retry()
def process_order(order: Order):
    with Order.transaction():
        order.process()
```

### Transaction Isolation

**Issue**: Inconsistent data due to improper isolation.

**Solution**:
```python
from rhosocial.activerecord.transaction import IsolationLevel

# Use appropriate isolation level
with Order.transaction(isolation_level=IsolationLevel.SERIALIZABLE):
    order = Order.find_one_or_fail(1)
    order.process()

# Consider using optimistic locking
class Order(OptimisticLockMixin, ActiveRecord):
    version: int  # Version field for locking
```

## Validation Issues

### Data Validation

**Issue**: Invalid data not caught before save.

**Solution**:
```python
from pydantic import validator

class User(ActiveRecord):
    username: str
    email: str
    age: int
    
    @validator('username')
    def username_valid(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username too short")
        return v
    
    @validator('email')
    def email_valid(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError("Invalid email")
        return v
    
    @validator('age')
    def age_valid(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Age cannot be negative")
        return v

# Test validation
try:
    user = User(username='a', email='invalid', age=-1)
    user.save()
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Relationship Validation

**Issue**: Invalid relationship data.

**Solution**:
```python
class Order(ActiveRecord):
    user_id: int
    items: List['OrderItem']
    
    def validate_items(self):
        """Validate order items."""
        if not self.items:
            raise ValidationError("Order must have items")
        
        total = sum(item.quantity * item.price for item in self.items)
        if total <= 0:
            raise ValidationError("Order total must be positive")
    
    def save(self) -> None:
        """Save with validation."""
        self.validate_items()
        super().save()
```

## Performance Issues

### Slow Queries

**Issue**: Queries taking too long to execute.

**Solution**:
```python
# Use query profiling
query = User.query()\
    .with_('posts.comments')\
    .where('status = ?', ('active',))

# Get execution plan
plan = query.explain()
print(plan)

# Monitor query time
start = time.perf_counter()
result = query.all()
duration = time.perf_counter() - start

print(f"Query took {duration:.3f} seconds")
```

### Memory Leaks

**Issue**: Memory usage growing over time.

**Solution**:
```python
import gc
from typing import Iterator

def process_large_dataset() -> Iterator[User]:
    """Process dataset with memory management."""
    batch_size = 1000
    offset = 0
    
    while True:
        # Get batch
        users = User.query()\
            .limit(batch_size)\
            .offset(offset)\
            .all()
        
        if not users:
            break
        
        # Process batch
        for user in users:
            yield user
        
        # Clear references
        users = None
        gc.collect()
        
        offset += batch_size

# Usage
for user in process_large_dataset():
    process_user(user)
```

## Best Practices

1. **Installation**
   - Check dependencies
   - Verify versions
   - Use virtual environments
   - Document requirements

2. **Configuration**
   - Test connections
   - Validate settings
   - Use environment variables
   - Document configuration

3. **Query Optimization**
   - Use eager loading
   - Batch process
   - Monitor performance
   - Use indexes

4. **Error Handling**
   - Implement retries
   - Log errors
   - Validate data
   - Clean up resources

5. **Testing**
   - Write unit tests
   - Test edge cases
   - Monitor performance
   - Document examples

## Next Steps

1. Read [Debugging Guide](debugging_guide.md)
2. Study [Performance Problems](performance_problems.md)
3. Learn about [Error Resolution](error_resolution.md)