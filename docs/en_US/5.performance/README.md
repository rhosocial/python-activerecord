# Performance

This chapter covers performance optimization strategies for RhoSocial ActiveRecord applications. We'll use both social media and e-commerce examples to demonstrate various optimization techniques.

## Overview

RhoSocial ActiveRecord provides several performance features:

1. **Query Optimization**
   - Eager loading strategies
   - Index usage
   - Query caching
   - Batch processing

2. **Memory Management**
   - Resource handling
   - Batch operations
   - Caching strategies
   - Memory profiling

3. **Connection Pooling**
   - Pool configuration
   - Connection management
   - Resource limits
   - Connection reuse

## Common Performance Issues

### N+1 Query Problem

```python
# Bad: N+1 queries
users = User.find_all()
for user in users:
    print(f"{user.username}: {len(user.posts)}")  # Extra query per user

# Good: Eager loading
users = User.query()\
    .with_('posts')\
    .all()
for user in users:
    print(f"{user.username}: {len(user.posts)}")  # No extra queries
```

### Memory Usage

```python
# Bad: Loading all records at once
all_orders = Order.find_all()  # May consume too much memory

# Good: Batch processing
batch_size = 1000
offset = 0
while True:
    orders = Order.query()\
        .limit(batch_size)\
        .offset(offset)\
        .all()
    if not orders:
        break
    process_orders(orders)
    offset += batch_size
```

### Connection Management

```python
# Bad: Manual connection handling
connection = get_connection()
try:
    # Use connection
    pass
finally:
    connection.close()

# Good: Using connection pool
with Order.transaction():
    # Connection automatically managed
    process_order()
```

## Performance Monitoring

### Query Profiling

```python
from rhosocial.activerecord.profiler import QueryProfiler

profiler = QueryProfiler()
User.backend().set_profiler(profiler)

# Execute queries
users = User.query()\
    .with_('posts.comments')\
    .all()

# Analyze results
print(f"Total queries: {profiler.query_count}")
print(f"Total time: {profiler.total_time}ms")
for query in profiler.slow_queries:
    print(f"Slow query: {query.sql}")
```

### Memory Profiling

```python
from rhosocial.activerecord.profiler import MemoryProfiler

profiler = MemoryProfiler()
profiler.start()

# Execute operations
process_large_dataset()

# Get memory stats
stats = profiler.get_stats()
print(f"Peak memory: {stats.peak_memory}MB")
print(f"Current memory: {stats.current_memory}MB")
```

## Example Optimizations

### Social Media Feed

```python
class User(ActiveRecord):
    def get_feed(self, limit: int = 20) -> List[Post]:
        """Get user's feed with optimizations."""
        return Post.query()\
            .with_('author', 'comments.author')\  # Eager load
            .where('user_id IN (SELECT followed_id FROM follows WHERE follower_id = ?)',
                  (self.id,))\
            .order_by('created_at DESC')\
            .limit(limit)\
            .all()

# Usage with caching
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_feed(user_id: int) -> List[Post]:
    user = User.find_one(user_id)
    return user.get_feed()
```

### E-commerce Order Processing

```python
class Order(ActiveRecord):
    @classmethod
    def process_pending_orders(cls):
        """Process orders in batches."""
        batch_size = 100
        processed = 0
        
        while True:
            with cls.transaction():
                orders = cls.query()\
                    .with_('items.product')\
                    .where('status = ?', ('pending',))\
                    .limit(batch_size)\
                    .all()
                
                if not orders:
                    break
                
                for order in orders:
                    order.process()
                    processed += 1
        
        return processed
```

## Best Practices

1. **Query Optimization**
   - Use eager loading
   - Implement caching
   - Batch process large datasets

2. **Memory Management**
   - Monitor memory usage
   - Use batch operations
   - Clean up resources

3. **Connection Management**
   - Configure connection pools
   - Reuse connections
   - Monitor pool usage

## Performance Checklist

- [ ] Identify and fix N+1 queries
- [ ] Implement appropriate caching
- [ ] Configure connection pools
- [ ] Monitor memory usage
- [ ] Use batch processing
- [ ] Profile slow queries
- [ ] Optimize indexes
- [ ] Cleanup resources

## In This Chapter

1. [Query Optimization](query_optimization.md)
   - N+1 problem solutions
   - Eager loading strategies
   - Query caching
   - Index usage

2. [Memory Management](memory_management.md)
   - Resource handling
   - Batch operations
   - Memory profiling
   - Cleanup strategies

3. [Connection Pooling](connection_pooling.md)
   - Pool configuration
   - Connection lifecycle
   - Resource limits
   - Monitoring

## Next Steps

1. Learn about [Query Optimization](query_optimization.md)
2. Study [Memory Management](memory_management.md)
3. Explore [Connection Pooling](connection_pooling.md)