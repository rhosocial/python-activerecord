# Model-level Caching

Model-level caching is a powerful performance optimization technique that stores entire model instances in a cache, allowing them to be retrieved without executing database queries. This document explores how to implement and manage model-level caching in rhosocial ActiveRecord applications.

## Introduction

Database queries, especially those that retrieve complex model instances with relationships, can be resource-intensive. Model-level caching addresses this by storing serialized model instances in a fast cache store, significantly reducing database load for frequently accessed models.

## Basic Implementation

rhosocial ActiveRecord provides a `ModelCache` class that handles model-level caching:

```python
from rhosocial.activerecord.models import User
from rhosocial.activerecord.cache import ModelCache

# Fetch a user from the database
user = User.objects.get(id=1)

# Cache the user instance (with a 5-minute TTL)
ModelCache.set(User, 1, user, ttl=300)

# Later, retrieve the user from cache
cached_user = ModelCache.get(User, 1)
if cached_user is None:
    # Cache miss - fetch from database and update cache
    cached_user = User.objects.get(id=1)
    ModelCache.set(User, 1, cached_user, ttl=300)
```

## Automatic Model Caching

For convenience, rhosocial ActiveRecord can be configured to automatically cache model instances:

```python
from rhosocial.activerecord.models import User
from rhosocial.activerecord.cache import enable_model_cache

# Enable automatic caching for the User model with a 5-minute TTL
enable_model_cache(User, ttl=300)

# Now model fetches will automatically use the cache
user = User.objects.get(id=1)  # Checks cache first, then database if needed

# Model updates will automatically invalidate the cache
user.name = "New Name"
user.save()  # Updates database and refreshes cache
```

## Model Cache Configuration

You can configure model caching at the class level:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.cache import ModelCacheConfig

class User(ActiveRecord):
    __table_name__ = 'users'
    
    # Configure caching for this model
    __cache_config__ = ModelCacheConfig(
        enabled=True,
        ttl=300,           # Cache TTL in seconds
        version=1,         # Cache version (increment to invalidate all caches)
        include_relations=False  # Whether to cache related models
    )
```

## Cache Key Generation

rhosocial ActiveRecord uses a consistent strategy for generating cache keys:

```python
from rhosocial.activerecord.cache import generate_model_cache_key

# Generate a cache key for a specific model instance
user = User.objects.get(id=1)
cache_key = generate_model_cache_key(User, 1)
print(cache_key)  # Output: "model:User:1:v1" (if version=1)
```

The key format includes:
- A prefix (`model:`)
- The model class name
- The primary key value
- A version number (for cache invalidation)

## Cache Invalidation

Proper cache invalidation is crucial to prevent stale data:

```python
from rhosocial.activerecord.cache import ModelCache

# Invalidate a specific model instance
ModelCache.delete(User, 1)

# Invalidate all cached instances of a model
ModelCache.clear(User)

# Invalidate all model caches
ModelCache.clear_all()

# Automatic invalidation on model updates
user = User.objects.get(id=1)
user.update(name="New Name")  # Automatically invalidates cache
```

## Caching with Relationships

You can control whether related models are included in the cache:

```python
from rhosocial.activerecord.cache import ModelCache

# Cache a user with their related orders
user = User.objects.prefetch_related('orders').get(id=1)
ModelCache.set(User, 1, user, ttl=300, include_relations=True)

# Later, retrieve the user with their orders from cache
cached_user = ModelCache.get(User, 1)
if cached_user:
    # Access orders without additional queries
    orders = cached_user.orders
```

## Cache Serialization

Model instances must be serializable to be cached. rhosocial ActiveRecord handles this automatically for most cases, but you may need to customize serialization for complex models:

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    def __prepare_for_cache__(self):
        """Prepare the model for caching"""
        # Custom serialization logic
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            # Exclude sensitive or non-serializable data
        }
    
    @classmethod
    def __restore_from_cache__(cls, data):
        """Restore a model instance from cached data"""
        # Custom deserialization logic
        instance = cls()
        instance.id = data['id']
        instance.name = data['name']
        instance.email = data['email']
        return instance
```

## Distributed Caching

For production applications, a distributed cache like Redis or Memcached is recommended:

```python
from rhosocial.activerecord.cache import configure_cache
import redis

# Configure Redis as the cache backend
redis_client = redis.Redis(host='localhost', port=6379, db=0)
configure_cache(backend='redis', client=redis_client)

# Now all model caching operations will use Redis
ModelCache.set(User, 1, user, ttl=300)  # Stored in Redis
```

## Monitoring Cache Performance

Monitoring cache performance helps optimize your caching strategy:

```python
from rhosocial.activerecord.cache import CacheStats

# Get model cache statistics
stats = CacheStats.get_model_stats(User)
print(f"Hits: {stats.hits}")
print(f"Misses: {stats.misses}")
print(f"Hit ratio: {stats.hit_ratio:.2f}")
```

## Best Practices

1. **Cache Selectively**: Not all models benefit from caching. Focus on:
   - Frequently accessed models
   - Models that are expensive to load (with complex relationships)
   - Models that don't change frequently

2. **Set Appropriate TTLs**: Balance freshness with performance
   - Short TTLs for frequently changing data
   - Longer TTLs for stable data

3. **Be Mindful of Cache Size**: Large model instances can consume significant memory

4. **Handle Cache Failures Gracefully**: Your application should work correctly even if the cache is unavailable

5. **Use Cache Versioning**: Increment the cache version when your model structure changes

6. **Consider Partial Caching**: For large models, consider caching only frequently accessed attributes

## Performance Considerations

### Benefits

- **Reduced Database Load**: Fewer queries hitting the database
- **Lower Latency**: Faster response times for cached models
- **Reduced Network Traffic**: Less data transferred between application and database

### Potential Issues

- **Memory Usage**: Caching large models can consume significant memory
- **Cache Invalidation Complexity**: Ensuring cache consistency can be challenging
- **Serialization Overhead**: Converting models to/from cache format adds some overhead

## Conclusion

Model-level caching is a powerful technique for improving the performance of rhosocial ActiveRecord applications. By caching frequently accessed model instances, you can significantly reduce database load and improve response times.

When implementing model-level caching, carefully consider which models to cache, how long to cache them, and how to handle cache invalidation to ensure data consistency while maximizing performance benefits.