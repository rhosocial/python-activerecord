# Relationship Management

rhosocial ActiveRecord offers a versatile and type-safe relationship management system that enables developers to define
and work with database relationships in an intuitive way. The relationship system is designed to handle common
relationship types while providing flexible querying and eager loading capabilities.

## Core Relationship Types

rhosocial ActiveRecord supports three primary relationship types:

### 1. BelongsTo (Many-to-One)

The `BelongsTo` relationship indicates that the current model contains a foreign key referencing another model:

```python
from activerecord import ActiveRecord
from activerecord.relations import BelongsTo
from typing import Optional, ClassVar

class Comment(ActiveRecord):
    __table_name__ = 'comments'
    
    id: Optional[int] = None
    content: str
    post_id: int
    
    # Comment belongs to a Post
    post: ClassVar['Post'] = BelongsTo('post_id')
```

### 2. HasOne (One-to-One)

The `HasOne` relationship indicates that another model contains a foreign key referencing the current model, with
a constraint that there can only be one related record:

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: Optional[int] = None
    name: str
    
    # User has one profile
    profile: ClassVar['Profile'] = HasOne('user_id')
```

### 3. HasMany (One-to-Many)

The `HasMany` relationship indicates that multiple records in another model contain foreign keys referencing the current model:

```python
from typing import List, ClassVar

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: Optional[int] = None
    title: str
    
    # Post has many comments
    comments: ClassVar[List['Comment']] = HasMany('post_id')
```

## Relationship Configuration

Each relationship type provides configuration options:

```python
class User(ActiveRecord):
    # Basic relationship
    profile: ClassVar[HasOne['Profile']] = HasOne('user_id')
    
    # With inverse relationship specified
    posts: ClassVar[HasMany['Post']] = HasMany('user_id', inverse_of='author')
    
    # With custom cache configuration
    orders: ClassVar[HasMany['Order']] = HasMany('user_id', cache_config=CacheConfig(ttl=600, max_size=500))
```

## Bidirectional Relationships

rhosocial ActiveRecord supports bidirectional relationships through the `inverse_of` parameter, which helps maintain
consistency and enables validation:

```python
class Post(ActiveRecord):
    # Post has many comments
    comments: ClassVar[List['Comment']] = HasMany('post_id', inverse_of='post')
    # Post belongs to an author (User)
    author: ClassVar['User'] = BelongsTo('user_id', inverse_of='posts')

class Comment(ActiveRecord):
    # Comment belongs to a post
    post: ClassVar['Post'] = BelongsTo('post_id', inverse_of='comments')
```

## Eager Loading

The relationship system includes powerful eager loading capabilities to avoid N+1 query problems:

```python
# Load users with their profiles and posts in just 3 queries
users = User.query().with_('profile', 'posts').all()

# Nested eager loading with dot notation
users = User.query().with_('posts.comments').all()

# Custom query conditions for relationship loading
users = User.query().with_(
    ('posts', lambda q: q.where('published = ?', (True,)))
).all()
```

## Relationship Queries

Each relationship provides direct access to a pre-configured query builder:

```python
# Get a query builder for a user's posts
user = User.find_one(1)
recent_posts = user.posts_query().where('created_at > ?', (last_week,)).all()

# Filter and manipulate the relationship query
active_orders = user.orders_query().where('status = ?', ('active',)).order_by('created_at DESC').all()
```

## Relationship Caching

rhosocial ActiveRecord provides instance-level caching for relationships, ensuring proper isolation and memory management:

```python
# Cached on first access
user = User.find_one(1)
user.posts()  # Loads from database
user.posts()  # Uses cached value

# Clear cache when needed
user.clear_relation_cache('posts')  # Clear specific relation
user.clear_relation_cache()  # Clear all relations
```

## Usage Examples

Here's a complete example demonstrating how to set up and use relationships:

```python
from activerecord import ActiveRecord
from activerecord.relations import BelongsTo, HasMany, HasOne
from typing import Optional, List, ClassVar

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: Optional[int] = None
    username: str
    email: str
    
    # User has many posts
    posts: ClassVar[List['Post']] = HasMany('user_id', inverse_of='author')
    
    # User has one profile
    profile: ClassVar['Profile'] = HasOne('user_id', inverse_of='user')

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: Optional[int] = None
    user_id: int
    title: str
    content: str
    
    # Post belongs to a user
    author: ClassVar['User'] = BelongsTo('user_id', inverse_of='posts')
    
    # Post has many comments
    comments: ClassVar[List['Comment']] = HasMany('post_id', inverse_of='post')

class Comment(ActiveRecord):
    __table_name__ = 'comments'
    
    id: Optional[int] = None
    post_id: int
    user_id: int
    content: str
    
    # Comment belongs to a post
    post: ClassVar['Post'] = BelongsTo('post_id', inverse_of='comments')
    
    # Comment belongs to a user
    author: ClassVar['User'] = BelongsTo('user_id', inverse_of='comments')

class Profile(ActiveRecord):
    __table_name__ = 'profiles'
    
    id: Optional[int] = None
    user_id: int
    bio: str
    avatar_url: str
    
    # Profile belongs to a user
    user: ClassVar['User'] = BelongsTo('user_id', inverse_of='profile')

# Create records with relationships
user = User(username="john_doe", email="john@example.com")
user.save()

profile = Profile(user_id=user.id, bio="Python developer", avatar_url="avatar.jpg")
profile.save()

post = Post(user_id=user.id, title="Introduction to ORMs", content="...")
post.save()

comment = Comment(post_id=post.id, user_id=user.id, content="Great article!")
comment.save()

# Access relationships
user = User.find_one(1)
user_profile = user.profile()  # Access the user's profile
user_posts = user.posts()      # Access the user's posts

# Access nested relationships with eager loading
posts_with_comments = Post.query().with_('author', 'comments.author').all()

for post in posts_with_comments:
    print(f"Post: {post.title} by {post.author().username}")
    for comment in post.comments():
        print(f"  Comment by {comment.author().username}: {comment.content}")
```

## Comparison with Other ORMs

### vs SQLAlchemy
SQLAlchemy offers a wider variety of relationship types, including many-to-many relationships and association objects. However, its relationship definition syntax is more complex and requires more boilerplate code. rhosocial ActiveRecord's relationship system is more intuitive and requires less code while still providing the most common relationship types.

```python
# SQLAlchemy relationship example
class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String)
    content = Column(Text)
    
    # Define relationships
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
```

### vs Django ORM
Django ORM's relationship API uses field objects in model definitions, which is slightly different from
rhosocial ActiveRecord's descriptor-based approach. Django also supports many-to-many relationships out of the box,
but its eager loading requires more verbose syntax with `prefetch_related` and `select_related`.

```python
# Django ORM relationship example
class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # Access posts with related authors and comments
    # Post.objects.select_related('author').prefetch_related('comment_set__author')
```

### vs Peewee
Peewee's relationship API is similar to rhosocial ActiveRecord but uses field objects in model definitions
rather than descriptors. It also supports eager loading but requires more manual setup for nested relationships.

```python
# Peewee relationship example
class Post(Model):
    author = ForeignKeyField(User, backref='posts')
    title = CharField()
    content = TextField()
    
    # Access posts with related objects
    # Post.select().join(User).switch(Post).join(Comment)
```

## Key Advantages of rhosocial ActiveRecord's Relationship System

1. **Type Safety**: Full type hinting with generics for better IDE support and runtime type checking
2. **Simplified Definition**: Clean descriptor-based syntax with minimal boilerplate
3. **Flexible Loading**: Intuitive eager loading with support for nested relationships and query customization
4. **Instance-Level Caching**: Efficient caching mechanism with proper isolation between instances
5. **Bidirectional Validation**: Automatic validation of inverse relationships for data consistency
6. **Query Builder Access**: Direct access to relationship-specific query builders for custom filtering
7. **Performance Optimization**: Optimized batch loading for excellent performance with large datasets