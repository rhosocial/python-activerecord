# Query Result Caching

Query result caching is an effective performance optimization technique that stores the results of database queries in a cache, allowing them to be reused without executing the same query multiple times. This document explores how to implement and manage query result caching in rhosocial ActiveRecord applications.

## Introduction

Database queries, especially complex ones involving joins, aggregations, or large datasets, can be resource-intensive. Query result caching addresses this by storing the results of these queries in a fast cache store, significantly reducing database load for frequently executed queries.

## Basic Implementation

rhosocial ActiveRecord provides a `QueryCache` class that handles query result caching:

```python
from rhosocial.activerecord.models import Article
from rhosocial.activerecord.cache import QueryCache

# Define a potentially expensive query
query = Article.objects.filter(status='published')\
                     .order_by('-published_at')\
                     .limit(10)

# Execute the query and cache the results (with a 5-minute TTL)
results = query.all()
QueryCache.set('recent_articles', results, ttl=300)

# Later, retrieve the results from cache
cached_results = QueryCache.get('recent_articles')
if cached_results is None:
    # Cache miss - execute query and update cache
    cached_results = query.all()
    QueryCache.set('recent_articles', cached_results, ttl=300)
```

## Simplified Caching with get_or_set

For convenience, rhosocial ActiveRecord provides a `get_or_set` method that combines cache retrieval and query execution:

```python
from rhosocial.activerecord.cache import QueryCache

# Define the query
query = Article.objects.filter(status='published')\
                     .order_by('-published_at')\
                     .limit(10)

# Get from cache or execute query and cache results
results = QueryCache.get_or_set(
    'recent_articles',     # Cache key
    lambda: query.all(),   # Function to execute if cache miss
    ttl=300                # Cache TTL in seconds
)
```

## Cache Key Generation

Consistent cache key generation is important for effective caching:

```python
from rhosocial.activerecord.cache import generate_query_cache_key

# Generate a cache key based on the query
query = Article.objects.filter(status='published')\
                     .order_by('-published_at')\
                     .limit(10)

# Generate a unique key based on the query's SQL and parameters
cache_key = generate_query_cache_key(query)
print(cache_key)  # Output: "query:hash_of_sql_and_params:v1"

# Use the generated key
results = QueryCache.get_or_set(cache_key, lambda: query.all(), ttl=300)
```

The key format typically includes:
- A prefix (`query:`)
- A hash of the SQL query and its parameters
- A version number (for cache invalidation)

## Automatic Query Caching

rhosocial ActiveRecord can be configured to automatically cache query results:

```python
from rhosocial.activerecord.cache import enable_query_cache

# Enable automatic query caching globally
enable_query_cache(ttl=300)

# Now query results will be automatically cached
results = Article.objects.filter(status='published').all()
# Subsequent identical queries will use the cache
```

## Query-specific Cache Configuration

You can configure caching for specific queries:

```python
from rhosocial.activerecord.models import Article

# Execute a query with specific cache settings
results = Article.objects.filter(status='published')\
                       .cache(ttl=600)\
                       .all()

# Disable caching for a specific query
results = Article.objects.filter(status='draft')\
                       .no_cache()\
                       .all()
```

## Cache Invalidation

Proper cache invalidation is crucial to prevent stale data:

```python
from rhosocial.activerecord.cache import QueryCache

# Invalidate a specific query cache
QueryCache.delete('recent_articles')

# Invalidate all query caches for a model
QueryCache.invalidate_for_model(Article)

# Invalidate caches matching a pattern
QueryCache.delete_pattern('article:*')

# Invalidate all query caches
QueryCache.clear()

# Automatic invalidation on model updates
article = Article.objects.get(id=1)
article.update(title="New Title")  # Can trigger invalidation of related query caches
```

## Time-based Invalidation

Time-based invalidation uses TTL (Time To Live) to automatically expire cached results:

```python
# Cache results for 5 minutes
QueryCache.set('recent_articles', results, ttl=300)

# Cache results for 1 hour
QueryCache.set('category_list', categories, ttl=3600)

# Cache results indefinitely (until manual invalidation)
QueryCache.set('site_configuration', config, ttl=None)
```

## Conditional Caching

Sometimes you may want to cache query results only under certain conditions:

```python
from rhosocial.activerecord.cache import QueryCache

def get_articles(status, cache=True):
    query = Article.objects.filter(status=status).order_by('-published_at')
    
    if not cache or status == 'draft':  # Don't cache draft articles
        return query.all()
    
    cache_key = f"articles:{status}"
    return QueryCache.get_or_set(cache_key, lambda: query.all(), ttl=300)
```

## Caching with Query Parameters

When caching queries with variable parameters, include the parameters in the cache key:

```python
from rhosocial.activerecord.cache import QueryCache

def get_articles_by_category(category_id):
    cache_key = f"articles:category:{category_id}"
    
    return QueryCache.get_or_set(
        cache_key,
        lambda: Article.objects.filter(category_id=category_id).all(),
        ttl=300
    )
```

## Caching Aggregation Results

Aggregation queries are excellent candidates for caching:

```python
from rhosocial.activerecord.cache import QueryCache

def get_article_counts_by_status():
    cache_key = "article:counts_by_status"
    
    return QueryCache.get_or_set(
        cache_key,
        lambda: Article.objects.group_by('status')\
                             .select('status', 'COUNT(*) as count')\
                             .all(),
        ttl=600  # Cache for 10 minutes
    )
```

## Distributed Caching

For production applications, a distributed cache like Redis or Memcached is recommended:

```python
from rhosocial.activerecord.cache import configure_cache
import redis

# Configure Redis as the cache backend
redis_client = redis.Redis(host='localhost', port=6379, db=0)
configure_cache(backend='redis', client=redis_client)

# Now all query caching operations will use Redis
QueryCache.set('recent_articles', results, ttl=300)  # Stored in Redis
```

## Monitoring Cache Performance

Monitoring cache performance helps optimize your caching strategy:

```python
from rhosocial.activerecord.cache import CacheStats

# Get query cache statistics
stats = CacheStats.get_query_stats()
print(f"Hits: {stats.hits}")
print(f"Misses: {stats.misses}")
print(f"Hit ratio: {stats.hit_ratio:.2f}")

# Get statistics for a specific model's queries
model_stats = CacheStats.get_query_stats(Article)
print(f"Article query cache hit ratio: {model_stats.hit_ratio:.2f}")
```

## Best Practices

1. **Cache Selectively**: Not all queries benefit from caching. Focus on:
   - Frequently executed queries
   - Queries that are expensive to execute (complex joins, aggregations)
   - Queries whose results don't change frequently

2. **Set Appropriate TTLs**: Balance freshness with performance
   - Short TTLs for frequently changing data
   - Longer TTLs for stable data

3. **Use Consistent Cache Keys**: Ensure cache keys are consistent and include all relevant query parameters

4. **Handle Cache Failures Gracefully**: Your application should work correctly even if the cache is unavailable

5. **Consider Query Variations**: Be aware that even small changes to a query (like order or parameter values) will result in different cache keys

6. **Implement Proper Invalidation**: Ensure caches are invalidated when the underlying data changes

## Performance Considerations

### Benefits

- **Reduced Database Load**: Fewer queries hitting the database
- **Lower Latency**: Faster response times for cached queries
- **Consistent Performance**: More predictable response times, especially for complex queries

### Potential Issues

- **Memory Usage**: Caching large result sets can consume significant memory
- **Cache Invalidation Complexity**: Ensuring cache consistency can be challenging
- **Stale Data**: Improperly invalidated caches can lead to stale data

## Conclusion

Query result caching is a powerful technique for improving the performance of rhosocial ActiveRecord applications. By caching the results of frequently executed or expensive queries, you can significantly reduce database load and improve response times.

When implementing query result caching, carefully consider which queries to cache, how long to cache them, and how to handle cache invalidation to ensure data consistency while maximizing performance benefits.