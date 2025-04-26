# Relationship Caching

Relationship caching is a specialized form of caching that stores the results of relationship queries between models. This technique is particularly effective at preventing the N+1 query problem and improving application performance when working with related data. This document explores how to implement and manage relationship caching in rhosocial ActiveRecord applications.

## Introduction

When working with related models in an ORM, applications often encounter the N+1 query problem: loading a collection of N records and then accessing a relationship for each record, resulting in N additional queries. Relationship caching addresses this by storing the results of relationship queries, significantly reducing database load.

## The N+1 Query Problem

To understand the value of relationship caching, first consider the N+1 query problem:

```python
# Without caching or eager loading - N+1 problem
users = User.objects.all()  # 1 query to get all users

for user in users:  # N additional queries, one per user
    orders = user.orders  # Each access triggers a separate database query
```

This pattern can lead to performance issues as the number of records increases.

## Basic Relationship Caching

rhosocial ActiveRecord provides built-in caching for model relationships:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.relation import HasMany, CacheConfig

class User(ActiveRecord):
    __table_name__ = 'users'
    
    # Configure relationship caching
    orders: ClassVar[HasMany['Order']] = HasMany(
                    foreign_key='user_id',
                    cache_config=CacheConfig(enabled=True, ttl=300))  # Cache for 5 minutes
```

With this configuration, when you access the `orders` relationship on a `User` instance, the result is cached for 5 minutes. Subsequent accesses to the same relationship on the same instance will use the cached result instead of querying the database.

## Cache Configuration Options

The `CacheConfig` class provides several options for configuring relationship caching:

```python
from rhosocial.activerecord.relation import CacheConfig

cache_config = CacheConfig(
    enabled=True,     # Enable caching for this relationship
    ttl=300,          # Cache time-to-live in seconds
    max_size=100,     # Maximum number of items to cache (for collection relationships)
    version=1         # Cache version (increment to invalidate all caches)
)
```

## Global Cache Configuration

You can also configure caching globally for all relationships:

```python
from rhosocial.activerecord.relation import GlobalCacheConfig

# Enable caching for all relationships
GlobalCacheConfig.enabled = True
GlobalCacheConfig.ttl = 600  # 10 minutes default TTL
GlobalCacheConfig.max_size = 100  # Default maximum size for collections
```

Individual relationship configurations will override the global configuration.

## Cache Management

rhosocial ActiveRecord provides methods to manage relationship caches:

```python
# Clear cache for a specific relationship
user = User.objects.get(id=1)
user.clear_relation_cache('orders')

# Clear cache for all relationships on an instance
user.clear_relation_cache()
```

## Automatic Cache Invalidation

Relationship caches are automatically invalidated in certain scenarios:

```python
# When the related model is updated
order = Order.objects.get(id=1)
order.update(status='shipped')  # Invalidates the orders cache for the related user

# When a relationship is modified
user = User.objects.get(id=1)
new_order = Order(product='New Product')
user.orders.add(new_order)  # Invalidates the orders cache for this user
```

## Combining with Eager Loading

Relationship caching works well with eager loading for optimal performance:

```python
# Eager load relationships and cache the results
users = User.objects.prefetch_related('orders').all()

# First access loads from the eager-loaded data and caches it
for user in users:
    orders = user.orders  # Uses eager-loaded data, then caches

# Later accesses use the cache
user = users[0]
orders_again = user.orders  # Uses cached data, no database query
```

## Implementation Details

Under the hood, rhosocial ActiveRecord uses the `InstanceCache` system to store relationship data directly on model instances:

```python
from rhosocial.activerecord.relation.cache import InstanceCache

# Manually interact with the cache (advanced usage)
user = User.objects.get(id=1)

# Get cached relationship
cached_orders = InstanceCache.get(user, 'orders', cache_config)

# Set relationship in cache
orders = Order.objects.filter(user_id=user.id).all()
InstanceCache.set(user, 'orders', orders, cache_config)

# Delete from cache
InstanceCache.delete(user, 'orders')
```

## Cache Storage

By default, relationship caches are stored in memory. For production applications, you can configure a distributed cache backend:

```python
from rhosocial.activerecord.cache import configure_cache
import redis

# Configure Redis as the cache backend
redis_client = redis.Redis(host='localhost', port=6379, db=0)
configure_cache(backend='redis', client=redis_client)

# Now relationship caching will use Redis
```

## Performance Considerations

### Benefits

- **Eliminates N+1 Query Problem**: Cached relationships prevent multiple database queries
- **Reduces Database Load**: Fewer queries hitting the database
- **Improves Response Times**: Faster access to related data

### Memory Usage

Relationship caching stores data in memory, which can be a concern for large relationships:

```python
# Limit memory usage for large collections
class User(ActiveRecord):
    __table_name__ = 'users'
    
    # Limit cache size for potentially large collections
    orders: ClassVar[HasMany['Order']] = HasMany(
                    foreign_key='user_id',
                    cache_config=CacheConfig(enabled=True, ttl=300, max_size=50))
```

## Best Practices

1. **Enable Caching for Frequently Accessed Relationships**: Focus on relationships that are accessed often

2. **Set Appropriate TTLs**: Balance freshness with performance
   - Short TTLs for frequently changing relationships
   - Longer TTLs for stable relationships

3. **Combine with Eager Loading**: For optimal performance, use both eager loading and caching

4. **Monitor Memory Usage**: Be mindful of memory consumption, especially for large collections

5. **Use Cache Versioning**: Increment the cache version when your model structure changes

6. **Clear Caches When Appropriate**: Implement proper cache invalidation strategies

## Debugging Relationship Caching

rhosocial ActiveRecord provides tools to debug relationship caching:

```python
from rhosocial.activerecord.cache import CacheStats
from rhosocial.activerecord import set_log_level
import logging

# Enable debug logging for cache operations
set_log_level(logging.DEBUG)

# Get cache statistics
stats = CacheStats.get_relation_stats()
print(f"Hits: {stats.hits}")
print(f"Misses: {stats.misses}")
print(f"Hit ratio: {stats.hit_ratio:.2f}")
```

## Conclusion

Relationship caching is a powerful technique for improving the performance of rhosocial ActiveRecord applications, especially when working with related data. By caching the results of relationship queries, you can eliminate the N+1 query problem and significantly reduce database load.

When implementing relationship caching, carefully consider which relationships to cache, how long to cache them, and how to handle cache invalidation to ensure data consistency while maximizing performance benefits.