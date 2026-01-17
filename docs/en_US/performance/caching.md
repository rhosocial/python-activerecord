# Caching Mechanism

The library includes multi-level caching optimizations designed to improve application performance and reduce database load.

1.  **Metadata Cache**: Field mappings and column information are parsed only once and reused for subsequent operations.
2.  **Relation Cache**: Relation data on model instances (e.g., `user.posts()`) is cached after the first access or eager loading.

## N+1 Query Problem and Solution

### What is the N+1 Problem?

The N+1 problem is a common performance pitfall in ORMs. When you query N objects and then iterate over them accessing their relationships, if each access triggers a database query, you end up executing N+1 queries in total (1 query for the list + N queries for the relationships).

**Inefficient Code Example (N+1)**:

```python
# 1 Query: Get first 10 users
users = User.query().limit(10).all()

for user in users:
    # N Queries: Each iteration triggers a DB query to fetch profile
    # Note: Accessing the relation method user.profile() triggers query (if not cached)
    print(user.profile().bio)

# Total queries: 1 + 10 = 11 queries
```

### Solution: Eager Loading

Use the `with_` method to eager load required relationship data in one go. The ORM automatically populates the fetched relationship data into the model instances' **relation cache**.

**Efficient Code Example (Eager Loading)**:

```python
# 1 Query: Get users and fetch profiles simultaneously
# The ORM performs optimization, typically requiring only 1-2 SQL queries to load all data
users = User.query().with_("profile").limit(10).all()

for user in users:
    # 0 Queries: Data is already in cache, direct memory access
    print(user.profile().bio)
```

### How Caching Works

When using `with_`:
1.  The main query executes, fetching the `users` list.
2.  The ORM collects all user IDs.
3.  The ORM executes a batch query to fetch `profile` data for these users.
4.  The ORM maps `profile` data back to corresponding `user` instances and stores it in the internal dictionary (relation cache).
5.  Subsequent calls to `user.profile()` check the cache, find existing data, and return it directly without accessing the database.

## Clearing Relation Cache

Sometimes you need to force a reload of the latest data from the database (e.g., if relation data was modified elsewhere). You can clear the cache using the following methods:

```python
user = User.find(1)
posts = user.posts()  # Triggers query and caches result

# ... posts updated elsewhere ...

# Method 1: Clear cache for a specific relation
user.clear_relation_cache('posts')

# Method 2: Clear cache for all relations on the instance
user.clear_relation_cache()

# Method 3: Via helper method on the relation accessor
user.posts.clear_cache()
```

> **Note**: Relation cache is **instance-level**. Different model instances (even if representing the same database record) have their own independent caches.
