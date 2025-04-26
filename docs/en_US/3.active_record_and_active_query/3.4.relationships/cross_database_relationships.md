# Cross-database Relationships

Cross-database relationships allow you to define associations between models that are stored in different databases. rhosocial ActiveRecord provides support for working with related data across multiple database connections, enabling more flexible and scalable application architectures.

## Overview

Cross-database relationships are useful in various scenarios, including:

- Microservice architectures where different services have their own databases
- Legacy systems integration where data is spread across multiple databases
- Sharding strategies where data is partitioned across multiple databases
- Multi-tenant applications where each tenant has a separate database

In rhosocial ActiveRecord, cross-database relationships work similarly to regular relationships but require additional configuration to specify the database connection for each model.

## Setting Up Multiple Database Connections

Before you can use cross-database relationships, you need to configure multiple database connections in your application:

```python
from rhosocial.activerecord import ConnectionManager

# Configure primary database connection
ConnectionManager.configure({
    'default': {
        'driver': 'mysql',
        'host': 'localhost',
        'database': 'primary_db',
        'username': 'user',
        'password': 'password'
    },
    'secondary': {
        'driver': 'postgresql',
        'host': 'localhost',
        'database': 'secondary_db',
        'username': 'user',
        'password': 'password'
    }
})
```

## Defining Models with Different Database Connections

To use cross-database relationships, you need to specify which database connection each model should use:

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    __connection__ = "default"  # Use the default database connection
    
    id: Optional[int] = None
    username: str
    email: str
    
    # Define relationship with Post model in secondary database
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )

class Post(IntegerPKMixin, ActiveRecord):
    __table_name__ = "posts"
    __connection__ = "secondary"  # Use the secondary database connection
    
    id: Optional[int] = None
    user_id: int
    title: str
    content: str
    
    # Define relationship with User model in default database
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )
```

## Using Cross-database Relationships

### Basic Usage

Once you've set up your models with the appropriate database connections, you can use cross-database relationships just like regular relationships:

```python
# Find a user in the default database
user = User.find_by(username="example_user")

# Get posts from the secondary database
posts = user.posts()

for post in posts:
    print(f"Post title: {post.title}")
    
    # This will query the default database to get the user
    post_author = post.user()
    print(f"Author: {post_author.username}")
```

### Creating Related Records

When creating related records across databases, you need to be aware that transactions won't span multiple databases:

```python
# Find a user in the default database
user = User.find_by(username="example_user")

# Create a new post in the secondary database
new_post = Post(
    user_id=user.id,
    title="Cross-database Relationship Example",
    content="This post is stored in a different database than the user."
)
new_post.save()
```

## Eager Loading with Cross-database Relationships

Eager loading works with cross-database relationships, but it will execute separate queries for each database:

```python
# Eager load posts when fetching users
users = User.find_all().with_("posts").all()

# This will execute two queries:
# 1. One query to the default database to fetch users
# 2. Another query to the secondary database to fetch posts

for user in users:
    posts = user.posts()  # No additional query is executed
    print(f"User: {user.username}, Posts: {len(posts)}")
```

## Limitations and Considerations

### Transaction Limitations

The most significant limitation of cross-database relationships is that transactions cannot span multiple databases. This means that if you need to update related records in different databases, you cannot ensure atomicity across both operations:

```python
# This transaction only affects the default database
with User.transaction():
    user = User.find_by(username="example_user")
    user.username = "new_username"
    user.save()
    
    # This operation is in a different database and won't be part of the transaction
    post = Post.find_by(user_id=user.id)
    post.title = "Updated Title"
    post.save()
```

To handle this limitation, you may need to implement application-level compensation mechanisms or use eventual consistency patterns.

### Performance Considerations

Cross-database relationships can introduce additional latency due to the need to connect to multiple databases. Consider the following performance optimizations:

1. **Use eager loading**: Minimize the number of database round-trips by eager loading related data when appropriate.

2. **Cache frequently accessed data**: Use caching to reduce the need to query across databases for frequently accessed data.

3. **Consider denormalization**: In some cases, it might be beneficial to denormalize data across databases to reduce the need for cross-database queries.

### Database Synchronization

When working with cross-database relationships, you need to ensure that related data remains consistent across databases. This might involve:

1. **Foreign key constraints**: Even though foreign key constraints cannot span databases, you should implement application-level validation to ensure referential integrity.

2. **Scheduled synchronization**: For some use cases, you might need to implement scheduled jobs to synchronize data between databases.

3. **Event-based synchronization**: Use events or message queues to propagate changes across databases.

## Advanced Patterns

### Repository Pattern

For complex cross-database scenarios, you might want to implement the Repository pattern to abstract away the details of data access:

```python
class UserRepository:
    @classmethod
    def get_user_with_posts(cls, user_id):
        user = User.find_by(id=user_id)
        if user:
            posts = Post.find_all().where(user_id=user_id).all()
            # Manually associate posts with user
            user._posts = posts
        return user
```

### Read Replicas

If you're using read replicas for scaling, you can configure different connections for read and write operations:

```python
class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    __connection__ = "default"  # For write operations
    __read_connection__ = "default_replica"  # For read operations
    
    # ...
```

## Best Practices

1. **Minimize cross-database relationships**: While cross-database relationships are powerful, they come with limitations. Try to design your database schema to minimize the need for cross-database queries.

2. **Document database dependencies**: Clearly document which models are stored in which databases and how they relate to each other.

3. **Implement application-level validation**: Since foreign key constraints cannot span databases, implement application-level validation to ensure data integrity.

4. **Consider eventual consistency**: In distributed systems with multiple databases, eventual consistency might be more appropriate than trying to maintain strict consistency.

5. **Monitor performance**: Regularly monitor the performance of cross-database queries and optimize as needed.

6. **Use connection pooling**: Configure connection pooling for each database to minimize the overhead of establishing new connections.

## Conclusion

Cross-database relationships in rhosocial ActiveRecord provide a powerful way to work with related data across multiple databases. While they come with certain limitations, particularly around transactions, they enable more flexible and scalable application architectures. By understanding these limitations and following best practices, you can effectively use cross-database relationships in your applications.