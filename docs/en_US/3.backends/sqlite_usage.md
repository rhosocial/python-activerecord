# SQLite Usage Guide

This guide covers how to effectively use the built-in SQLite backend in RhoSocial ActiveRecord.

## Basic Setup

### Installation

SQLite support is included by default:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.typing import ConnectionConfig
```

### Configuration Options

```python
# Basic file-based database
config = ConnectionConfig(
    database='app.db'  # File path
)

# In-memory database
config = ConnectionConfig(
    database=':memory:'  # Special identifier for in-memory
)

# Advanced configuration
config = ConnectionConfig(
    database='app.db',
    options={
        'timeout': 30,              # Connection timeout
        'journal_mode': 'WAL',      # Write-Ahead Logging
        'synchronous': 'NORMAL',    # Synchronization mode
        'cache_size': -2000,        # Cache size in KB
        'foreign_keys': True        # Foreign key constraints
    }
)
```

## Use Cases

### Development Database

```python
# Social Media Models
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    user_id: int
    content: str

# Development configuration
def configure_development():
    config = ConnectionConfig(
        database='development.db',
        options={
            'journal_mode': 'WAL',
            'foreign_keys': True
        }
    )
    
    for model in [User, Post]:
        model.configure(config, SQLiteBackend)
```

### Testing Database

```python
# E-commerce Models
class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: int
    name: str
    price: Decimal

class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    total: Decimal
    status: str

# Testing configuration using in-memory database
def configure_testing():
    config = ConnectionConfig(
        database=':memory:',
        options={
            'foreign_keys': True
        }
    )
    
    for model in [Product, Order]:
        model.configure(config, SQLiteBackend)
```

## Advanced Features

### Write-Ahead Logging (WAL)

```python
# Enable WAL mode for better concurrency
config = ConnectionConfig(
    database='app.db',
    options={
        'journal_mode': 'WAL',
        'synchronous': 'NORMAL',
        'wal_autocheckpoint': 1000
    }
)

# Usage with models
class User(ActiveRecord):
    @classmethod
    def bulk_insert(cls, users: List[dict]) -> None:
        with cls.transaction():
            for user_data in users:
                user = cls(**user_data)
                user.save()
```

### Foreign Key Support

```python
# Enable foreign key constraints
config = ConnectionConfig(
    database='app.db',
    options={
        'foreign_keys': True
    }
)

class Order(ActiveRecord):
    __table_name__ = 'orders'
    
    id: int
    user_id: int
    total: Decimal

class OrderItem(ActiveRecord):
    __table_name__ = 'order_items'
    
    id: int
    order_id: int  # Foreign key to orders.id
    product_id: int
    quantity: int

# Foreign key constraint will be enforced
try:
    item = OrderItem(order_id=999, product_id=1, quantity=1)
    item.save()
except IntegrityError:
    print("Referenced order does not exist")
```

### Memory Management

```python
# Configure cache size and temp store
config = ConnectionConfig(
    database='app.db',
    options={
        'cache_size': -2000,  # 2MB page cache
        'temp_store': 'MEMORY',  # Use memory for temp storage
        'mmap_size': 2**26     # 64MB mmap size
    }
)

# Bulk operations with memory optimization
def bulk_process_orders(orders: List[dict]) -> None:
    with Order.transaction():
        # Process in batches to manage memory
        batch_size = 1000
        for i in range(0, len(orders), batch_size):
            batch = orders[i:i + batch_size]
            for order_data in batch:
                order = Order(**order_data)
                order.save()
```

### Concurrency Control

```python
# Configure for concurrent access
config = ConnectionConfig(
    database='app.db',
    options={
        'journal_mode': 'WAL',
        'busy_timeout': 5000,  # 5 second timeout
        'locking_mode': 'NORMAL'
    }
)

# Concurrent operations
async def process_user_data():
    try:
        with User.transaction():
            user = User.find_one_or_fail(1)
            user.process_data()
            user.save()
    except OperationalError as e:
        if "database is locked" in str(e):
            # Handle concurrent access
            await asyncio.sleep(1)
            return await process_user_data()
```

## Performance Optimization

### Index Usage

```python
# Create indexes for better performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_orders_user_status ON orders(user_id, status);

# Query using indexes
users = User.query()\
    .where('email = ?', ('john@example.com',))\
    .all()

orders = Order.query()\
    .where('user_id = ?', (1,))\
    .where('status = ?', ('pending',))\
    .all()
```

### Query Optimization

```python
# Use explain query plan
query = Order.query()\
    .where('status = ?', ('pending',))\
    .order_by('created_at DESC')

plan = query.explain()
print(plan)

# Optimize complex queries
def get_user_statistics(user_id: int) -> dict:
    stats = User.query()\
        .select(
            'users.id',
            'COUNT(DISTINCT orders.id) as order_count',
            'SUM(orders.total) as total_spent'
        )\
        .join('LEFT JOIN orders ON orders.user_id = users.id')\
        .where('users.id = ?', (user_id,))\
        .group_by('users.id')\
        .one()
    
    return stats
```

### Batch Processing

```python
def process_large_dataset(items: List[dict]) -> None:
    # Process in batches to optimize memory usage
    batch_size = 1000
    
    with Order.transaction():
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # Process batch
            values = []
            for item in batch:
                values.append((
                    item['order_id'],
                    item['product_id'],
                    item['quantity']
                ))
            
            # Bulk insert
            Order.backend().execute_many(
                "INSERT INTO order_items (order_id, product_id, quantity) VALUES (?, ?, ?)",
                values
            )
```

## Best Practices

1. **Development Setup**
   - Use WAL mode for better concurrency
   - Enable foreign key constraints
   - Configure appropriate cache size

2. **Testing Setup**
   - Use in-memory database for tests
   - Reset database between tests
   - Enable foreign key checks

3. **Performance**
   - Create appropriate indexes
   - Use batch processing for bulk operations
   - Monitor and optimize queries

4. **Concurrency**
   - Use WAL mode in multi-user scenarios
   - Configure appropriate busy timeout
   - Handle database locks properly

5. **Memory Management**
   - Process large datasets in batches
   - Configure appropriate cache size
   - Use memory-efficient queries

## Next Steps

1. Study [SQLite Implementation](sqlite_impl.md) for internal details
2. Learn about [Custom Backends](custom_backend.md)
3. Explore backend-agnostic features in [Core Documentation](../1.core/index.md)