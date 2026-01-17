# Many-to-Many Relationships

This library currently does not have a built-in implicit `ManyToMany` descriptor, but encourages explicitly defining an **Intermediate Model**. This approach requires a few more lines of code but allows you to store additional data on the relationship (e.g., when a tag was added).

## Scenario: Post and Tag

A post has multiple tags, and a tag can be used for multiple posts. We need a `PostTag` intermediate table.

### 1. Define Intermediate Model

```python
from typing import ClassVar
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.relation import BelongsTo

class PostTag(ActiveRecord):
    post_id: str
    tag_id: str
    created_at: int  # Extra info: when the tag was added

    # Define BelongsTo to both ends
    post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id', inverse_of='post_tags')
    tag: ClassVar[BelongsTo['Tag']] = BelongsTo(foreign_key='tag_id', inverse_of='post_tags')
```

### 2. Define Models at Both Ends

```python
from rhosocial.activerecord.relation import HasMany

class Post(ActiveRecord):
    # Point to the intermediate table
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='post_id', inverse_of='post')

class Tag(ActiveRecord):
    # Point to the intermediate table
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='tag_id', inverse_of='tag')
```

### 3. Usage

To query all tags for a post, we usually join via the intermediate table (detailed in the Querying chapter), or traverse at the application layer:

```python
post = Post.find_one(1)
# Get intermediate records
links = post.post_tags()
# Get actual tags (causes N+1 query, eager loading recommended)
tags = [link.tag() for link in links]
```
