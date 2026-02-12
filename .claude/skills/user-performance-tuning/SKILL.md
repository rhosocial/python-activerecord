---
name: user-performance-tuning
description: Performance optimization guide for rhosocial-activerecord - query optimization, eager loading, batch operations, caching strategies, and database-specific optimizations
license: MIT
compatibility: opencode
metadata:
  category: performance
  level: intermediate
  audience: users
  order: 8
  prerequisites:
    - user-activerecord-pattern
    - user-query-advanced
    - user-relationships
---

# Performance Optimization Guide

This guide covers performance optimization techniques for rhosocial-activerecord applications, including query optimization, eager loading, batch operations, caching strategies, and database-specific optimizations.

## Query Optimization

### Select Only Required Fields

By default, queries retrieve all fields. Use `select()` to retrieve only the columns you need.

```python
# ❌ Inefficient - retrieves all columns
users = User.query().all()
for user in users:
    print(user.id, user.name)

# ✅ Efficient - retrieves only id and name
users = User.query().select('id', 'name').all()
for user in users:
    print(user.id, user.name)
```

### Use Where Clauses Early

Apply filtering as early as possible to reduce the dataset early in the query pipeline.

```python
# ❌ Inefficient - filters after retrieving all users
all_users = User.query().all()
active_users = [u for u in all_users if u.is_active]

# ✅ Efficient - filters at database level
active_users = User.query().where(User.c.is_active == True).all()
```

### Avoid N+1 Queries

The N+1 problem occurs when you retrieve a list of records and then query related records for each one.

```python
# ❌ N+1 Problem - queries for orders for each user
users = User.query().all()
for user in users:
    orders = Order.query().where(Order.c.user_id == user.id).all()
    print(f"User {user.name} has {len(orders)} orders")

# ✅ Solution 1: Use eager loading with includes
users = User.query().includes('orders').all()
for user in users:
    orders = user.orders  # Already loaded
    print(f"User {user.name} has {len(orders)} orders")

# ✅ Solution 2: Use JOIN to fetch all data at once
results = User.query().join(
    Order, User.c.id == Order.c.user_id
).select(
    User.c.id, User.c.name, Order.c.id, Order.c.total
).all()

for row in results:
    print(f"User {row.User.name} has order {row.Order.id}")
```

### Use Indexes Wisely

Ensure your database has appropriate indexes for frequently queried columns.

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int = Field(primary_key=True)
    email: str = Field(max_length=255)
    status: str = Field(default='active')
    created_at: datetime = Field()
    
    # Define indexes in mapping
    __mapping__ = {
        'id': 'INTEGER PRIMARY KEY',
        'email': 'VARCHAR(255) NOT NULL UNIQUE',
        'status': 'VARCHAR(20) DEFAULT "active"',
        'created_at': 'TEXT',
    }

# Create additional indexes manually
# SQLite example:
# CREATE INDEX idx_users_status ON users(status);
# CREATE INDEX idx_users_created_at ON users(created_at);
```

## Eager Loading

Use eager loading to fetch related records in a single query instead of multiple queries.

### Includes with Select

```python
# Load users with their orders (1-to-many)
users = User.query().includes('orders').all()

for user in users:
    # Orders are pre-loaded
    for order in user.orders:
        print(order.total)
```

### Includes with Filters

```python
# Load users with only their recent orders
users = User.query().includes({
    'orders': lambda q: q.where(Order.c.created_at > '2024-01-01')
}).all()

for user in users:
    recent_orders = user.orders
    print(f"User {user.name} has {len(recent_orders)} recent orders")
```

### Multiple Includes

```python
# Load orders with their items and the user who placed them
orders = Order.query().includes('items', 'user').all()

for order in orders:
    print(f"Order {order.id} by {order.user.name}")
    for item in order.items:
        print(f"  - {item.product_name}: {item.quantity}")
```

### Nested Includes

```python
# Load authors with their books and book categories
authors = Author.query().includes({
    'books': {
        'categories': True
    }
}).all()

for author in authors:
    for book in author.books:
        for category in book.categories:
            print(f"{author.name}: {book.title} [{category.name}]")
```

## Batch Operations

### Bulk Insert

Insert multiple records efficiently using `insert_many()`.

```python
# ❌ Inefficient - individual inserts
users = []
for i in range(1000):
    user = User(name=f"User {i}", email=f"user{i}@example.com")
    user.save()
    users.append(user)

# ✅ Efficient - bulk insert
users_data = [
    {'name': f"User {i}", 'email': f"user{i}@example.com"}
    for i in range(1000)
]
User.insert_many(users_data)
```

### Bulk Update

Update multiple records efficiently.

```python
# ❌ Inefficient - individual updates
for user in users:
    user.status = 'active'
    user.updated_at = datetime.utcnow()
    user.save()

# ✅ Efficient - bulk update
user_ids = [u.id for u in users]
User.query().where(
    User.c.id.is_in(user_ids)
).update({
    'status': 'active',
    'updated_at': datetime.utcnow()
})
```

### Bulk Delete

Delete multiple records efficiently.

```python
# ❌ Inefficient - individual deletes
for user in inactive_users:
    user.delete()

# ✅ Efficient - bulk delete
User.query().where(
    User.c.status == 'inactive'
).delete()
```

### Chunking Large Result Sets

Process large datasets in chunks to avoid memory issues.

```python
# Process users in chunks of 1000
chunk_size = 1000
last_id = 0

while True:
    users = (
        User.query()
        .where(User.c.id > last_id)
        .order_by(User.c.id)
        .limit(chunk_size)
        .all()
    )
    
    if not users:
        break
    
    for user in users:
        process_user(user)
    
    last_id = users[-1].id
```

## Caching Strategies

### Query Result Caching

Cache expensive query results to avoid repeated database access.

```python
from functools import lru_cache
import hashlib
import json


class UserRepository:
    """Repository with caching for User queries."""
    
    @staticmethod
    @lru_cache(maxsize=128)
    def get_active_users_cached():
        """Get active users with caching."""
        return User.query().where(
            User.c.status == 'active'
        ).all()
    
    @staticmethod
    def clear_cache():
        """Clear the query cache."""
        UserRepository.get_active_users_cached.cache_clear()


# Usage
active_users = UserRepository.get_active_users_cached()
```

### Model Instance Caching

Cache frequently accessed model instances by their primary key.

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int = Field(primary_key=True)
    name: str = Field()
    email: str = Field()
    
    _cache = {}
    
    @classmethod
    def find_by_id_cached(cls, id: int) -> Optional['User']:
        """Find user by ID with instance caching."""
        if id in cls._cache:
            return cls._cache[id]
        
        user = cls.find_one(cls.c.id == id)
        if user:
            cls._cache[id] = user
        return user
    
    def save(self) -> int:
        """Save and update cache."""
        result = super().save()
        self._cache[self.id] = self
        return result
    
    def delete(self) -> int:
        """Delete and remove from cache."""
        result = super().delete()
        if self.id in self._cache:
            del self._cache[self.id]
        return result
```

### Cache Invalidation

Implement proper cache invalidation strategies.

```python
class Product(ActiveRecord):
    __table_name__ = 'products'
    
    id: int = Field(primary_key=True)
    name: str = Field()
    price: float = Field()
    category_id: int = Field()
    
    @classmethod
    def get_by_category_cached(cls, category_id: int) -> List['Product']:
        """Get products by category with caching."""
        cache_key = f"products:category:{category_id}"
        
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        
        products = cls.query().where(
            cls.c.category_id == category_id
        ).all()
        
        cache.set(cache_key, products, timeout=300)  # 5 minutes
        return products
    
    @classmethod
    def invalidate_category_cache(cls, category_id: int):
        """Invalidate category cache when products change."""
        cache_key = f"products:category:{category_id}"
        cache.delete(cache_key)
    
    def save(self) -> int:
        """Save and invalidate relevant caches."""
        result = super().save()
        
        # Invalidate category cache
        self.invalidate_category_cache(self.category_id)
        return result
    
    def delete(self) -> int:
        """Delete and invalidate caches."""
        category_id = self.category_id
        result = super().delete()
        self.invalidate_category_cache(category_id)
        return result
```

## Database-Specific Optimizations

### SQLite Optimizations

```python
# Enable WAL mode for better concurrency
backend.execute("PRAGMA journal_mode=WAL")

# Increase cache size
backend.execute("PRAGMA cache_size=-64000")  # 64MB

# Enable foreign keys
backend.execute("PRAGMA foreign_keys=ON")

# Use indexed columns for WHERE clauses
# Create indexes for frequently filtered columns
backend.execute("CREATE INDEX IF NOT EXISTS idx_user_status ON users(status)")
backend.execute("CREATE INDEX IF NOT EXISTS idx_order_user ON orders(user_id)")
```

### Connection Pooling

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

class OptimizedSQLiteBackend(SQLiteBackend):
    """SQLite backend with optimized settings."""
    
    def connect(self):
        super().connect()
        
        # Optimizations
        self.execute("PRAGMA journal_mode=WAL")
        self.execute("PRAGMA synchronous=NORMAL")
        self.execute("PRAGMA cache_size=-64000")
        self.execute("PRAGMA temp_store=MEMORY")
        self.execute("PRAGMA mmap_size=268435456")  # 256MB
        
        # Enable foreign keys
        self.execute("PRAGMA foreign_keys=ON")
    
    def execute(self, sql: str, params=None):
        """Execute with retry on lock."""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                return super().execute(sql, params)
            except DatabaseLockedError:
                if attempt == max_retries - 1:
                    raise
                import time
                time.sleep(0.01 * (2 ** attempt))  # Exponential backoff
```

### Prepared Statements

Use prepared statements for frequently executed queries.

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int = Field(primary_key=True)
    email: str = Field(max_length=255)
    status: str = Field(default='active')
    
    # Pre-compiled query for finding by email
    FIND_BY_EMAIL = None
    
    @classmethod
    def find_by_email(cls, email: str) -> Optional['User']:
        """Find user by email using prepared statement."""
        if cls.FIND_BY_EMAIL is None:
            cls.FIND_BY_EMAIL = cls.query().where(
                cls.c.email == BindParam('email')
            ).compile()
        
        result = cls.FIND_BY_EMAIL.execute(email=email)
        return result[0] if result else None
```

## Query Analysis

### Explain Queries

Use EXPLAIN to analyze query execution plans.

```python
def explain_query(query: ActiveQuery) -> str:
    """Get EXPLAIN output for a query."""
    sql = query.explain()
    return backend.execute(sql).fetchall()


# Analyze a query
query = User.query().where(User.c.status == 'active').order_by(User.c.name)
plan = explain_query(query)
print(plan)
```

### Query Timing

Measure query execution time.

```python
import time
from contextlib import contextmanager


@contextmanager
def query_timer():
    """Context manager for timing queries."""
    start = time.perf_counter()
    yield
    elapsed = time.perf_counter() - start
    print(f"Query took: {elapsed*1000:.2f}ms")


# Usage
with query_timer():
    users = User.query().includes('orders').all()
```

## Async Optimization

### Concurrent Query Execution

Execute independent queries concurrently in async code.

```python
import asyncio


async def load_user_data(user_id: int):
    """Load user data with concurrent queries."""
    # These queries can run in parallel
    user, orders, preferences = await asyncio.gather(
        User.find_by_id(user_id),
        Order.query().where(Order.c.user_id == user_id).all(),
        UserPreference.query().where(
            UserPreference.c.user_id == user_id
        ).first(),
    )
    
    return {
        'user': user,
        'orders': orders,
        'preferences': preferences,
    }
```

### Batch Async Operations

Process multiple async operations efficiently.

```python
async def bulk_create_users(users_data: List[Dict]) -> List[User]:
    """Create multiple users concurrently."""
    async def create_one(data):
        user = User(**data)
        await user.save()
        return user
    
    # Create all users concurrently
    users = await asyncio.gather(
        *[create_one(data) for data in users_data]
    )
    return users
```

## Monitoring and Profiling

### Query Logging

Log queries for analysis.

```python
import logging


class QueryLogger:
    """Query logging middleware."""
    
    def __init__(self):
        self.logger = logging.getLogger('queries')
        self.logger.setLevel(logging.DEBUG)
        
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(message)s')
        )
        self.logger.addHandler(handler)
    
    def log_query(self, sql: str, params: tuple, duration: float):
        """Log query execution."""
        self.logger.debug(
            f"Query ({duration*1000:.2f}ms): {sql} | Params: {params}"
        )


# Integrate with backend
class LoggedSQLiteBackend(SQLiteBackend):
    """SQLite backend with query logging."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = QueryLogger()
    
    def execute(self, sql: str, params=None):
        start = time.perf_counter()
        result = super().execute(sql, params)
        duration = time.perf_counter() - start
        
        self.logger.log_query(sql, params, duration)
        return result
```

### Slow Query Detection

Identify and optimize slow queries.

```python
SLOW_QUERY_THRESHOLD_MS = 100


class SlowQueryDetector:
    """Detect and report slow queries."""
    
    def __init__(self):
        self.slow_queries = []
    
    def record_query(self, sql: str, duration: float):
        """Record query if it's slow."""
        if duration * 1000 > SLOW_QUERY_THRESHOLD_MS:
            self.slow_queries.append({
                'sql': sql,
                'duration': duration,
                'timestamp': datetime.utcnow(),
            })
    
    def report(self):
        """Generate slow query report."""
        if not self.slow_queries:
            return "No slow queries detected."
        
        sorted_queries = sorted(
            self.slow_queries,
            key=lambda q: q['duration'],
            reverse=True
        )
        
        report = f"Slow Query Report ({len(self.slow_queries)} queries):\n"
        for i, q in enumerate(sorted_queries[:10], 1):
            report += f"{i}. {q['duration']*1000:.2f}ms: {q['sql']}\n"
        
        return report
```

## Best Practices Summary

1. **Use `select()`** to retrieve only needed fields
2. **Apply filters early** with `where()` clauses
3. **Avoid N+1 queries** with eager loading (`includes()`)
4. **Use bulk operations** (`insert_many()`, `update()`, `delete()`)
5. **Implement caching** for frequently accessed data
6. **Create appropriate indexes** for query columns
7. **Process large datasets** in chunks
8. **Use async concurrency** for independent queries
9. **Monitor query performance** with logging and timing
10. **Profile and optimize** slow queries proactively

## Performance Checklist

- [ ] Review all queries and add `select()` for specific fields
- [ ] Add eager loading (`includes()`) to eliminate N+1 queries
- [ ] Replace loops with bulk operations
- [ ] Implement caching for read-heavy data
- [ ] Create database indexes for filtered/sorted columns
- [ ] Configure connection pooling and query timeouts
- [ ] Set up query logging and slow query detection
- [ ] Profile application to identify bottlenecks
- [ ] Optimize slow queries using EXPLAIN
- [ ] Test performance under realistic load
