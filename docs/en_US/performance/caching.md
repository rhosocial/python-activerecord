# Caching Mechanism

The library includes multi-level caching optimizations:

1.  **Metadata Cache**: Field mappings and column information are parsed only once.
2.  **Relation Cache**: `user.posts()` caches the result after the first call, unless explicitly refreshed or expired.

## Clearing Relation Cache

```python
# Force re-querying the database
user.clear_relation_cache('posts')
# Or
user.posts.clear_cache()
```

## Batch Loading Cache

When using `batch_load` or `with_`, the ORM intelligently populates these caches to avoid triggering queries in subsequent accesses.
