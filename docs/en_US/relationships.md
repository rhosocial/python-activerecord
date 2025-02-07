# Relationships

## Overview

RhoSocial ActiveRecord supports three types of relationship definitions:
- `BelongsTo`: Many-to-one relationship
- `HasOne`: One-to-one relationship
- `HasMany`: One-to-many relationship

Each relationship must be properly paired with its inverse relationship using the `inverse_of` parameter.

## Important Note
Currently, direct relationship creation (e.g., through association proxy) is under development and not yet available. All relationships must be managed through foreign keys.

## Basic Relationships

### One-to-One Relationships

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.relation import BelongsTo, HasOne
from typing import Optional

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    email: str
    
    # One-to-one with Profile
    profile: 'Profile' = HasOne(
        foreign_key='user_id',
        inverse_of='user'
    )

class Profile(ActiveRecord):
    __table_name__ = 'profiles'
    
    id: int
    user_id: int
    bio: str
    avatar_url: Optional[str]
    
    # Inverse one-to-one with User
    user: User = BelongsTo(
        foreign_key='user_id',
        inverse_of='profile'
    )
```

### One-to-Many Relationships

```python
from typing import List

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    email: str
    
    # One-to-many with Post
    posts: List['Post'] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    user_id: int
    title: str
    content: str
    
    # Many-to-one with User
    user: User = BelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )
```

## Accessing Relationships

### Loading Related Records

```python
# One-to-one relationships
user = User.find_one(1)
profile = user.profile()              # Call method to get profile
user_from_profile = profile.user()    # Call method to get user

# One-to-many relationships
posts = user.posts()                  # Call method to get all posts
for post in posts:
    print(f"Post by {post.user().name}")  # Call method to get user
```

### Relationship Queries

Each relationship provides a query method that allows you to build custom queries:

```python
# Query user's posts
user = User.find_one(1)
recent_posts = user.posts_query()
    .where('status = ?', ('published',))
    .order_by('created_at DESC')
    .limit(5)
    .all()

# Query post's user with specific conditions
post = Post.find_one(1)
active_user = post.user_query()
    .where('status = ?', ('active',))
    .one()
```

## Eager Loading

### Basic Eager Loading

```python
# Load user with profile
user = User.query()
    .with_('profile')
    .where('id = ?', (1,))
    .one()

# Load user with posts
user = User.query()
    .with_('posts')
    .one()
```

### Customized Eager Loading

```python
# Load only published posts
user = User.query()
    .with_(('posts', lambda q: q.where('status = ?', ('published',))))
    .one()

# Load recent posts with specific columns
user = User.query()
    .with_(('posts', lambda q: q
        .select('id', 'title', 'created_at')
        .order_by('created_at DESC')
        .limit(5)
    ))
    .one()
```

## Creating and Updating Related Records

Note: Currently, records must be created and linked manually using foreign keys.

```python
# Create related records manually
user = User(name='John Doe', email='john@example.com')
user.save()

# Create profile by setting foreign key
profile = Profile(
    user_id=user.id,  # Set foreign key manually
    bio='Python Developer'
)
profile.save()

# Create post by setting foreign key
post = Post(
    user_id=user.id,  # Set foreign key manually
    title='First Post',
    content='Hello World!'
)
post.save()
```

## Caching

Relationship results can be cached for better performance:

```python
from rhosocial.activerecord.relation import CacheConfig

class User(ActiveRecord):
    # Cache profile query results for 5 minutes
    profile: Profile = HasOne(
        foreign_key='user_id',
        inverse_of='user',
        cache_config=CacheConfig(ttl=300)
    )
```

## Clearing Relationship Cache

```python
user = User.find_one(1)

# Clear specific relationship cache
user.clear_relation_cache('profile')

# Clear all relationship caches
user.clear_relation_cache()
```

## Best Practices

1. **Use Relationship Methods**
   - Always use `relation_name()` to access related records
   - Use `relation_name_query()` for custom queries

2. **Eager Loading**
   - Use `with_()` to avoid N+1 query problems
   - Only load needed relationships and fields

3. **Caching**
   - Configure caching for frequently accessed relationships
   - Clear cache when related data changes

4. **Foreign Keys**
   - Ensure foreign keys are correctly set when creating records
   - Maintain referential integrity at the database level

## Known Limitations

1. Direct relationship creation through association proxy is not yet available
2. Automatic foreign key management is under development
3. Many-to-many relationships must be managed manually through junction tables

## Coming Soon

Future releases will include:
- Association proxy for easier relationship creation
- Automatic foreign key management
- Direct many-to-many relationship support
- Relationship callbacks and events
- Cascading deletes