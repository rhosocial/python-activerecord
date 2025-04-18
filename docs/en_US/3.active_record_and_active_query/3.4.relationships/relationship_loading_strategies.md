# Relationship Loading Strategies

When working with related data in rhosocial ActiveRecord, the way relationships are loaded can significantly impact your application's performance. This document explains the different relationship loading strategies available in rhosocial ActiveRecord and provides guidance on when to use each strategy.

## Overview

rhosocial ActiveRecord supports two main strategies for loading related data:

1. **Lazy Loading**: Related data is loaded only when explicitly accessed
2. **Eager Loading**: Related data is loaded upfront in a single query or a minimal number of queries

Each strategy has its advantages and disadvantages, and choosing the right strategy depends on your specific use case.

## Lazy Loading

Lazy loading is the default loading strategy in rhosocial ActiveRecord. With lazy loading, related data is loaded only when you explicitly access it through the relationship method.

### How Lazy Loading Works

When you define a relationship using `HasOne`, `HasMany`, or `BelongsTo`, rhosocial ActiveRecord creates a method that, when called, executes a query to load the related data.

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    
    id: Optional[int] = None
    username: str
    email: str
    
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )

class Post(IntegerPKMixin, ActiveRecord):
    __table_name__ = "posts"
    
    id: Optional[int] = None
    user_id: int
    title: str
    content: str
    
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )
```

With lazy loading, the related data is loaded only when you call the relationship method:

```python
# Load a user
user = User.find_by(username="example_user")

# At this point, no posts are loaded

# Now the posts are loaded when we call the posts() method
posts = user.posts()

# Each post's user is loaded only when accessed
for post in posts:
    # This triggers another query to load the user
    post_author = post.user()
    print(f"Post '{post.title}' by {post_author.username}")
```

### Advantages of Lazy Loading

- **Simplicity**: Lazy loading is simple to use and understand
- **Memory Efficiency**: Only loads data that is actually needed
- **Flexibility**: Works well when you don't know in advance which relationships you'll need

### Disadvantages of Lazy Loading

- **N+1 Query Problem**: Can lead to a large number of database queries, especially when iterating through collections
- **Performance Impact**: Multiple small queries can be slower than a single larger query

## Eager Loading

Eager loading is a strategy where related data is loaded upfront in a single query or a minimal number of queries. This is done using the `with_` method in rhosocial ActiveRecord.

### How Eager Loading Works

When you use eager loading, rhosocial ActiveRecord loads the related data in a separate query and then associates it with the appropriate records in memory.

```python
# Eager load posts when fetching users
users = User.find_all().with_("posts").all()

# Now you can access posts without additional queries
for user in users:
    print(f"User: {user.username}")
    for post in user.posts():
        print(f"  Post: {post.title}")
```

### Nested Eager Loading

You can also eager load nested relationships by using dot notation:

```python
# Eager load posts and each post's comments
users = User.find_all().with_("posts.comments").all()

# Now you can access posts and comments without additional queries
for user in users:
    print(f"User: {user.username}")
    for post in user.posts():
        print(f"  Post: {post.title}")
        for comment in post.comments():
            print(f"    Comment: {comment.content}")
```

### Multiple Relationship Eager Loading

You can eager load multiple relationships by passing a list to the `with_` method:

```python
# Eager load both posts and profile
users = User.find_all().with_(["posts", "profile"]).all()

# Now you can access both posts and profile without additional queries
for user in users:
    profile = user.profile()
    posts = user.posts()
    print(f"User: {user.username}, Bio: {profile.bio}")
    print(f"Number of posts: {len(posts)}")
```

### Advantages of Eager Loading

- **Performance**: Reduces the number of database queries, especially when working with collections
- **Predictable Load**: Makes database load more predictable
- **Solves N+1 Problem**: Avoids the N+1 query problem by loading related data in bulk

### Disadvantages of Eager Loading

- **Memory Usage**: Loads data that might not be used, potentially increasing memory usage
- **Complexity**: Requires more planning to determine which relationships to eager load
- **Potential Overhead**: For small datasets or rarely accessed relationships, eager loading might be unnecessary

## Choosing the Right Loading Strategy

The choice between lazy loading and eager loading depends on your specific use case. Here are some guidelines:

### Use Lazy Loading When:

- You're working with a single record or a small number of records
- You're not sure which relationships will be accessed
- Memory usage is a concern
- The relationship is rarely accessed

### Use Eager Loading When:

- You're working with collections of records
- You know in advance which relationships will be accessed
- You're displaying related data in a list or table
- Performance is a priority

## The N+1 Query Problem

The N+1 query problem is a common performance issue in ORM frameworks. It occurs when you load a collection of N records and then access a relationship for each record, resulting in N additional queries (hence N+1 queries in total).

### Example of N+1 Problem

```python
# Load all users (1 query)
users = User.find_all().all()

# For each user, load their posts (N additional queries)
for user in users:
    posts = user.posts()  # This executes a query for each user
    print(f"User: {user.username}, Posts: {len(posts)}")
```

### Solving the N+1 Problem with Eager Loading

```python
# Load all users with their posts (2 queries total)
users = User.find_all().with_("posts").all()

# No additional queries needed
for user in users:
    posts = user.posts()  # This uses the already loaded data
    print(f"User: {user.username}, Posts: {len(posts)}")
```

## Caching and Relationship Loading

rhosocial ActiveRecord includes a caching mechanism for relationship loading. When you access a relationship, the result is cached for the duration of the request, so subsequent accesses to the same relationship don't trigger additional queries.

### Relationship Caching Configuration

You can configure caching behavior for relationships using the `CacheConfig` class:

```python
from rhosocial.activerecord.relation import HasMany, CacheConfig

class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    
    id: Optional[int] = None
    username: str
    email: str
    
    # Configure caching for the posts relationship
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='user',
        cache_config=CacheConfig(enabled=True, ttl=300)  # Cache for 5 minutes
    )
```

### Global Cache Configuration

You can also set global cache configuration for all relationships:

```python
from rhosocial.activerecord.relation import GlobalCacheConfig

# Enable caching for all relationships with a 10-minute TTL
GlobalCacheConfig.enabled = True
GlobalCacheConfig.ttl = 600
```

## Best Practices

1. **Profile Your Application**: Use database query logging and profiling tools to identify N+1 query problems and other performance issues.

2. **Be Strategic with Eager Loading**: Only eager load relationships that you know you'll need. Eager loading relationships that aren't used can waste memory and database resources.

3. **Consider Batch Size**: For very large collections, consider processing records in batches to balance memory usage and query efficiency.

4. **Use Relationship Caching**: Configure appropriate caching for frequently accessed relationships to reduce database load.

5. **Optimize Queries**: Use query scopes and conditions to limit the amount of data loaded.

6. **Denormalize When Appropriate**: For read-heavy applications, consider denormalizing some data to reduce the need for relationship loading.

## Conclusion

Choosing the right relationship loading strategy is crucial for building performant applications with rhosocial ActiveRecord. By understanding the trade-offs between lazy loading and eager loading, and by using techniques like caching and batch processing, you can optimize your application's database interactions and provide a better experience for your users.