# One-to-Many Relationships

One-to-many relationships represent a connection between two models where a record in the first model can be associated with multiple records in the second model, but each record in the second model is associated with only one record in the first model. In rhosocial ActiveRecord, one-to-many relationships are implemented using the `HasMany` descriptor on the "one" side and the `BelongsTo` descriptor on the "many" side.

## Overview

A one-to-many relationship is one of the most common relationship types in database design. Examples include:

- A user has many posts
- A department has many employees
- A product has many reviews

In rhosocial ActiveRecord, these relationships are defined using descriptors that create a seamless API for accessing related records.

## Defining One-to-Many Relationships

### The "One" Side (HasMany)

The model that represents the "one" side of the relationship uses the `HasMany` descriptor to define its relationship with the "many" side:

```python
from typing import ClassVar, Optional, List
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany

class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    
    id: Optional[int] = None
    username: str
    email: str
    
    # Define relationship with Post model
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',  # Foreign key field in Post model
        inverse_of='user'       # Corresponding relationship name in Post model
    )
```

### Relationship Configuration Options

Both `HasMany` and `BelongsTo` relationships support the following configuration options:

- `foreign_key`: Specifies the foreign key field name (required)
- `inverse_of`: Specifies the name of the inverse relationship in the related model (optional but highly recommended)
- `loader`: Custom loader implementation (optional)
- `validator`: Custom validation implementation (optional)
- `cache_config`: Cache configuration (optional)

These options are defined in the `RelationDescriptor` base class and inherited by both `HasMany` and `BelongsTo` classes. For example:

```python
# HasMany example
posts: ClassVar[HasMany['Post']] = HasMany(
    foreign_key='user_id',  # Foreign key field in Post model
    inverse_of='user',      # Corresponding relationship name in Post model
    cache_config=CacheConfig(ttl=300)  # Optional cache configuration
)
```

### The "Many" Side (BelongsTo)

The model that represents the "many" side of the relationship uses the `BelongsTo` descriptor to define its relationship with the "one" side:

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import BelongsTo

class Post(IntegerPKMixin, ActiveRecord):
    __table_name__ = "posts"
    
    id: Optional[int] = None
    user_id: int  # Foreign key
    title: str
    content: str
    
    # Define relationship with User model
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',  # Foreign key field in this model
        inverse_of='posts'      # Corresponding relationship name in User model
    )
```

## Using One-to-Many Relationships

### Accessing Related Records

#### From the "One" Side

To access all posts belonging to a user:

```python
user = User.query().where('username = ?', ("example_user",)).one()

# Get all posts for this user
posts = user.posts()

# Iterate through the posts
for post in posts:
    print(f"Post title: {post.title}")
```

#### From the "Many" Side

To access the user who owns a post:

```python
post = Post.query().where('title = ?', ("Example Post",)).one()

# Get the user who owns this post
user = post.user()

print(f"Post author: {user.username}")
```

### Creating Related Records

#### Creating a Post for a User

```python
user = User.query().where('username = ?', ("example_user",)).one()

# Create a new post associated with this user
new_post = Post(
    user_id=user.id,
    title="New Post",
    content="This is a new post content"
)
new_post.save()
```

### Querying with Relationships

#### Finding Users with Posts

```python
# Find all users who have at least one post
users_with_posts = User.query().join('JOIN posts ON users.id = posts.user_id').all()
```

#### Finding Posts by a Specific User

```python
# Find all posts by a specific user
posts_by_user = Post.query().where('user_id = ?', (user.id,)).all()
```

## Eager Loading

To optimize performance when accessing related records, you can use eager loading to load the related records in a single query:

```python
# Eager load posts when fetching users
users_with_posts = User.query().with_("posts").all()

# Now you can access posts without additional queries
for user in users_with_posts:
    print(f"User: {user.username}")
    for post in user.posts():
        print(f"  Post: {post.title}")
```

## Cascading Operations

When working with one-to-many relationships, you often need to handle cascading operations such as deleting related records when a parent record is deleted. rhosocial ActiveRecord doesn't automatically handle cascading operations, so you need to implement them manually:

```python
# Delete a user and all their posts
user = User.query().where('username = ?', ("example_user",)).one()

# First delete all posts
Post.delete_all().where('user_id = ?', (user.id,)).execute()

# Then delete the user
user.delete()
```

## Best Practices

1. **Always define inverse relationships**: Define both sides of the relationship with matching `inverse_of` parameters to ensure consistency and enable bidirectional navigation.

2. **Use eager loading for collections**: When you know you'll need to access related records, use eager loading to avoid N+1 query problems.

3. **Consider using transactions**: When creating or updating related records, use transactions to ensure data consistency.

4. **Validate foreign keys**: Ensure that foreign keys reference valid records to maintain data integrity.

5. **Handle cascading operations explicitly**: Implement cascading operations (like cascading deletes) explicitly in your application code or database constraints.

## Conclusion

One-to-many relationships are a fundamental part of database design and are well-supported in rhosocial ActiveRecord. By using the `HasMany` and `BelongsTo` descriptors, you can create intuitive and type-safe relationships between your models, making it easy to work with related data in your application.