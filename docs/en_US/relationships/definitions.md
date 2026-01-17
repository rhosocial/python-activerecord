# Relationship Definitions (1:1, 1:N)

`rhosocial-activerecord` uses three core descriptors: `BelongsTo`, `HasOne`, `HasMany`.

## One-to-One: User and Profile

Each user has one profile page.

```python
from typing import ClassVar
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.relation import HasOne, BelongsTo

class User(ActiveRecord):
    # User has one Profile
    # foreign_key='user_id' refers to the column in the Profile table
    profile: ClassVar[HasOne['Profile']] = HasOne(foreign_key='user_id', inverse_of='user')

class Profile(ActiveRecord):
    user_id: str  # The foreign key column actually exists here
    
    # Profile belongs to a User
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='profile')
```

## One-to-Many: User and Post

A user can publish multiple posts.

```python
from rhosocial.activerecord.relation import HasMany

class User(ActiveRecord):
    # User has many Posts
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')

class Post(ActiveRecord):
    user_id: str
    
    # Post belongs to a User (author)
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')
```

> **Note**: All relationship descriptors must be declared as `ClassVar` to avoid interfering with Pydantic's field validation.
