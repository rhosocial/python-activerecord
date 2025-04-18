# Model Relationships

This document explains how to define and use relationships in ActiveRecord models. Model relationships represent associations between database tables, allowing you to work with related data in an object-oriented way.

## Relationship Types Overview

rhosocial ActiveRecord supports the following main relationship types:

- **BelongsTo**: Represents the inverse relationship of HasMany or HasOne, where the current model contains a foreign key referencing another model
- **HasMany (One-to-Many)**: Indicates that multiple records in another model contain foreign keys referencing the current model
- **HasOne (One-to-One)**: Indicates that a single record in another model contains a foreign key referencing the current model

## Defining Relationships

### BelongsTo Relationship

A BelongsTo relationship indicates that the current model contains a foreign key referencing another model. For example, a comment belongs to a post:

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import BelongsTo

class Comment(IntegerPKMixin, ActiveRecord):
    __table_name__ = "comments"
    
    id: Optional[int] = None
    post_id: int  # Foreign key
    content: str
    
    # Define relationship with Post model
    post: ClassVar[BelongsTo['Post']] = BelongsTo(
        foreign_key='post_id',  # Foreign key field in current model
        inverse_of='comments'   # Corresponding relationship name in Post model
    )
```

### HasMany Relationship

A HasMany relationship indicates that multiple records in another model contain foreign keys referencing the current model. For example, a post has many comments:

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany

class Post(IntegerPKMixin, ActiveRecord):
    __table_name__ = "posts"
    
    id: Optional[int] = None
    title: str
    content: str
    
    # Define relationship with Comment model
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='post_id',  # Foreign key field in Comment model
        inverse_of='post'       # Corresponding relationship name in Comment model
    )
```

### Bidirectional Relationships

By using the `inverse_of` parameter, you can define bidirectional relationships, which helps maintain data consistency and improve performance:

```python
# Post model
comments: ClassVar[HasMany['Comment']] = HasMany(
    foreign_key='post_id',
    inverse_of='post'  # Points to post relationship in Comment model
)

# Comment model
post: ClassVar[BelongsTo['Post']] = BelongsTo(
    foreign_key='post_id',
    inverse_of='comments'  # Points to comments relationship in Post model
)
```

## Relationship Configuration Options

### Basic Configuration Parameters

All relationship types support the following configuration parameters:

- `foreign_key`: The name of the foreign key field
- `inverse_of`: The name of the inverse relationship
- `cache_config`: Configuration for relationship caching

### Cache Configuration

You can configure relationship caching using the `CacheConfig` class:

```python
from rhosocial.activerecord.relation import HasMany, CacheConfig

orders: ClassVar[HasMany['Order']] = HasMany(
    foreign_key='user_id',
    cache_config=CacheConfig(
        ttl=300,       # Cache time-to-live in seconds
        max_size=100   # Maximum number of cached items
    )
)
```

## Using Relationships

### Automatically Generated Methods

When you define a relationship, rhosocial ActiveRecord automatically generates two methods for each relationship:

1. **relation_name()** - A method to access the related record(s)
2. **relation_name_query()** - A method to access a pre-configured query builder for the relationship

### Accessing Relationships

Once relationships are defined, you can access them like regular attributes:

```python
# Get all orders for a user
user = User.find(1)
orders = user.orders  # Returns a list of Order objects

# Get the user for an order
order = Order.find(1)
user = order.user  # Returns a User object
```

### Relationship Queries

Each relationship provides direct access to a pre-configured query builder:

```python
# Get active orders for a user
active_orders = user.orders.where(status='active').all()

# Get the count of user's orders
order_count = user.orders.count()

# Using the automatically generated query method
active_orders = user.orders_query().where(status='active').all()
```

### Relationship Cache Management

rhosocial ActiveRecord provides instance-level caching for relationships. The relationship descriptor implements the `__delete__` method, which clears the cache rather than deleting the relationship itself:

```python
# Clear cache for a specific relationship
user.orders.clear_cache()  # Using the clear_cache() method of the relationship

# Or use the instance's clear cache method
user.clear_relation_cache('orders')

# Using Python's del keyword (leveraging the __delete__ method)
del user.orders  # Equivalent to the methods above, only clears cache without deleting the relationship

# Clear cache for all relationships
user.clear_relation_cache()
```

## Complete Example

Here's a complete example demonstrating how to set up and use relationships:

```python
from typing import ClassVar, Optional, List
from pydantic import Field, EmailStr
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    __table_name__ = "users"

    id: Optional[int] = None
    username: str
    email: EmailStr
    
    # Define one-to-many relationship with Post
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )
    
    # Define one-to-many relationship with Comment
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )

class Post(IntegerPKMixin, TimestampMixin, ActiveRecord):
    __table_name__ = "posts"

    id: Optional[int] = None
    user_id: int
    title: str
    content: str
    
    # Define many-to-one relationship with User
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )
    
    # Define one-to-many relationship with Comment
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='post_id',
        inverse_of='post'
    )

class Comment(IntegerPKMixin, TimestampMixin, ActiveRecord):
    __table_name__ = "comments"

    id: Optional[int] = None
    user_id: int
    post_id: int
    content: str
    
    # Define many-to-one relationship with Post
    post: ClassVar[BelongsTo['Post']] = BelongsTo(
        foreign_key='post_id',
        inverse_of='comments'
    )
    
    # Define many-to-one relationship with User
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='comments'
    )
```

Using these relationships:

```python
# Create a user
user = User(username="test_user", email="test@example.com")
user.save()

# Create a post
post = Post(user_id=user.id, title="Test Post", content="This is a test post")
post.save()

# Create a comment
comment = Comment(user_id=user.id, post_id=post.id, content="Great post!")
comment.save()

# Access relationships
user_posts = user.posts  # Get all posts for the user
post_comments = post.comments  # Get all comments for the post
comment_user = comment.user  # Get the user for the comment
```

## Relationship Loading Strategies

### Lazy Loading

By default, relationships use a lazy loading strategy, which means related data is only loaded when the relationship is accessed:

```python
user = User.find(1)
# Posts are not loaded yet

posts = user.posts  # Query is executed now to load posts
```

### Eager Loading

To avoid N+1 query problems, you can use eager loading:

```python
# Eager load posts for users
users = User.with_relation('posts').all()

# Eager load nested relationships
users = User.with_relation(['posts', 'posts.comments']).all()

# Apply conditions to eager loaded relationships
users = User.with_relation('posts', lambda q: q.where(status='published')).all()
```

## Summary

rhosocial ActiveRecord's relationship system provides an intuitive and type-safe way to define and use database relationships. By using relationships appropriately, you can create clearer and more efficient code while avoiding common performance pitfalls.