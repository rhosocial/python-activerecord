---
name: user-relationships
description: Complete guide to defining and using relationships in rhosocial-activerecord - belongs_to, has_one, has_many, has_many_through with eager loading and caching strategies
license: MIT
compatibility: opencode
metadata:
  category: relationships
  level: intermediate
  audience: users
  order: 5
  prerequisites:
    - user-modeling-guide
---

## What I do

Master relationship management in rhosocial-activerecord:
- Define relationships (belongs_to, has_one, has_many, has_many_through)
- Eager loading to avoid N+1 queries
- Relation caching strategies
- Common anti-patterns and solutions

## When to use me

- Setting up foreign key relationships
- Optimizing query performance (eager vs lazy loading)
- Debugging relationship issues
- Understanding relationship lifecycle

## Relationship Types

### belongs_to (Child → Parent)

```python
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import BelongsTo

class Comment(ActiveRecord):
    __table_name__ = 'comments'
    
    content: str
    user_id: int  # Foreign key
    post_id: int
    
    c: ClassVar = FieldProxy()
    
    # Define relationship - Comment belongs to User
    author: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='comments'
    )
    
    # Comment belongs to Post
    post: ClassVar[BelongsTo['Post']] = BelongsTo(
        foreign_key='post_id',
        inverse_of='comments'
    )
```

### has_one (Parent → Child, one-to-one)

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    name: str
    c: ClassVar = FieldProxy()
    
    # User has one Profile
    profile: ClassVar[HasOne['Profile']] = HasOne(
        foreign_key='user_id',
        inverse_of='owner'
    )

class Profile(ActiveRecord):
    __table_name__ = 'profiles'
    
    bio: str
    user_id: int  # Foreign key
    c: ClassVar = FieldProxy()
    
    # Profile belongs to User
    owner: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='profile'
    )
```

### has_many (Parent → Child, one-to-many)

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    name: str
    c: ClassVar = FieldProxy()
    
    # User has many Posts
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='author'
    )
    
    # User has many Comments
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='user_id',
        inverse_of='author'
    )

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    title: str
    user_id: int
    c: ClassVar = FieldProxy()
    
    # Post belongs to User
    author: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )
```

### has_many_through (Many-to-many via join table)

```python
class Student(ActiveRecord):
    __table_name__ = 'students'
    
    name: str
    c: ClassVar = FieldProxy()
    
    # Students enroll in many Courses through Enrollments
    courses: ClassVar[HasManyThrough['Course']] = HasManyThrough(
        through='Enrollment',
        source_foreign_key='student_id',
        target_foreign_key='course_id'
    )

class Course(ActiveRecord):
    __table_name__ = 'courses'
    
    name: str
    c: ClassVar = FieldProxy()
    
    # Courses have many Students through Enrollments
    students: ClassVar[HasManyThrough['Student']] = HasManyThrough(
        through='Enrollment',
        source_foreign_key='course_id',
        target_foreign_key='student_id'
    )

class Enrollment(ActiveRecord):
    __table_name__ = 'enrollments'
    
    student_id: int
    course_id: int
    enrolled_at: datetime
    c: ClassVar = FieldProxy()
    
    # Enrollment belongs to both Student and Course
    student: ClassVar[BelongsTo['Student']] = BelongsTo(
        foreign_key='student_id',
        inverse_of='courses'
    )
    
    course: ClassVar[BelongsTo['Course']] = BelongsTo(
        foreign_key='course_id',
        inverse_of='students'
    )
```

## Loading Strategies

### Lazy Loading (Default)

```python
# Each access triggers a database query (N+1 problem)
for user in User.query().limit(10):
    for post in user.posts():  # Queries database each time!
        print(post.title)
```

### Eager Loading with with_()

```python
# Single query with JOINs
for user in User.query().with_('posts').limit(10):
    for post in user.posts():  # Already loaded!
        print(post.title)
```

### Multiple Eager Loading

```python
# Load users with their posts AND comments
users = User.query().with_('posts', 'comments').all()

# Nested eager loading
# Load posts with their author AND comments
posts = Post.query().with_('author', 'comments.author').all()

for post in posts:
    print(post.author.name)  # Loaded!
    for comment in post.comments:
        print(comment.content)  # Loaded!
```

### When to Use Each Strategy

| Strategy | Use Case |
|-----------|----------|
| Lazy (default) | Single record, rarely accessing relationship |
| Eager (`with_()`) | Iterating over multiple records |
| Nested eager | Multi-level relationships |
| Pre-fetch | Batch processing with relationships |

## Relation Caching

### Automatic Request-Lifecycle Cache

```python
# First access - queries database
user = User.find_one(1)
posts = user.posts()  # Queries DB, caches result

# Same request - uses cache
comments = user.comments  # Uses cached posts!

# Cache cleared on save/delete
user.save()  # Clears user.posts() cache
```

### Manual Cache Management

```python
# Clear specific relation cache
user.clear_relation_cache('posts')

# Clear all relation caches
user.clear_all_relation_caches()

# Check if cached
if user.has_cached_relation('posts'):
    posts = user.posts
```

## Common Anti-patterns

### ❌ N+1 Query Problem

```python
# BAD - queries database for EACH user
for user in User.query().all():
    for post in user.posts():  # N queries!
        print(post.title)

# GOOD - single query with JOIN
for user in User.query().with_('posts').all():
    for post in user.posts():  # Already loaded!
        print(post.title)
```

### ❌ Circular Imports

```python
# BAD - circular import at module level
from .post import Post

class User(ActiveRecord):
    posts = HasMany('Post')  # Triggers import!

# GOOD - use string reference
class User(ActiveRecord):
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='author'
    )
```

### ❌ Missing Inverse Of

```python
# BAD - relationship without inverse
class User(ActiveRecord):
    posts = HasMany('Post')  # Missing inverse_of

class Post(ActiveRecord):
    author = BelongsTo('User')  # No link to User.posts

# GOOD - properly linked
class User(ActiveRecord):
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='author'
    )

class Post(ActiveRecord):
    author: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )
```

### ❌ Wrong Foreign Key

```python
# BAD - wrong foreign key column
class Comment(ActiveRecord):
    author_id: int
    
    # Should reference author_id, not wrong column
    author = BelongsTo('User', foreign_key='wrong_column')

# GOOD - correct foreign key
class Comment(ActiveRecord):
    author_id: int
    
    author: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='author_id'  # Matches column name!
    )
```

## Performance Tips

### Index Foreign Keys

```sql
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_user_id ON comments(user_id);
```

### Use Eager Loading for Reports

```python
# BAD for reports - many queries
users = User.query().all()
for user in users:
    print(f"{user.name}: {len(user.posts)} posts, {len(user.comments)} comments")

# GOOD for reports - single query
users = User.query().with_('posts', 'comments').all()
for user in users:
    print(f"{user.name}: {len(user.posts)} posts, {len(user.comments)} comments")
```

### Batch Loading for Large Datasets

```python
# For very large datasets, use pagination
BATCH_SIZE = 1000
offset = 0

while True:
    users = User.query().limit(BATCH_SIZE).offset(offset).with_('posts').all()
    
    if not users:
        break
    
    process_users(users)
    offset += BATCH_SIZE
```

## Full Documentation

- **Relationships Guide:** `docs/en_US/relationships/`
- **Query Optimization:** `docs/en_US/performance/`
- **Eager Loading:** `docs/en_US/querying/eager_loading.md`
