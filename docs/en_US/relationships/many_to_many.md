# Many-to-Many Relationships

This library currently does not have a built-in implicit `ManyToMany` descriptor, but encourages explicitly defining an **Intermediate Model**. This approach requires a few more lines of code but allows you to store additional data on the relationship (e.g., when a tag was added).

> 💡 **AI Prompt Example**: "How to implement many-to-many relationships in ActiveRecord? Why not provide a ManyToMany descriptor directly?"

## Scenario: Post and Tag

A post has multiple tags, and a tag can be used for multiple posts. We need a `PostTag` intermediate table to establish this many-to-many relationship.

### 1. Define Intermediate Model

The intermediate model is the core of many-to-many relationships. It not only connects two entities but can also store additional information about the relationship itself.

```python
# Import necessary modules
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import BelongsTo
from rhosocial.activerecord.field import TimestampMixin

# PostTag class represents the association relationship between posts and tags
# Inheriting TimestampMixin automatically adds creation time field
class PostTag(TimestampMixin, ActiveRecord):
    # Foreign key column linking to Post table's id column
    post_id: str
    # Foreign key column linking to Tag table's id column
    tag_id: str
    # Extra information: tagging time (inherited from TimestampMixin)
    # created_at: datetime  # Automatically added timestamp field
    
    # Define subordinate relationship to Post
    # BelongsTo descriptor defines the subordinate relationship
    # foreign_key='post_id' refers to the foreign key column name in this table
    # inverse_of='post_tags' specifies the name of the reverse relationship, i.e., the corresponding relationship name in the Post class
    post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id', inverse_of='post_tags')
    
    # Define subordinate relationship to Tag
    # BelongsTo descriptor defines the subordinate relationship
    # foreign_key='tag_id' refers to the foreign key column name in this table
    # inverse_of='post_tags' specifies the name of the reverse relationship, i.e., the corresponding relationship name in the Tag class
    tag: ClassVar[BelongsTo['Tag']] = BelongsTo(foreign_key='tag_id', inverse_of='post_tags')

    # Return table name
    @classmethod
    def table_name(cls) -> str:
        return 'post_tags'
```

> 💡 **AI Prompt Example**: "What role does the intermediate model play in many-to-many relationships? Why is it better than implicit many-to-many?"

### 2. Define Models at Both Ends

Define the two entity models participating in the many-to-many relationship.

```python
# Import necessary modules
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany

# Post class represents blog posts
class Post(ActiveRecord):
    # Post title
    title: str
    # Post content
    content: str
    
    # Point to intermediate table relationship (one-to-many)
    # One post can be associated with multiple tag relationship records through the intermediate table
    # HasMany descriptor defines the one-to-many ownership relationship
    # foreign_key='post_id' refers to the foreign key column name in the PostTag table
    # inverse_of='post' specifies the name of the reverse relationship, i.e., the corresponding relationship name in the PostTag class
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='post_id', inverse_of='post')

    # Return table name
    @classmethod
    def table_name(cls) -> str:
        return 'posts'

# Tag class represents post tags
class Tag(ActiveRecord):
    # Tag name
    name: str
    # Tag description
    description: str
    
    # Point to intermediate table relationship (one-to-many)
    # One tag can be associated with multiple post relationship records through the intermediate table
    # HasMany descriptor defines the one-to-many ownership relationship
    # foreign_key='tag_id' refers to the foreign key column name in the PostTag table
    # inverse_of='tag' specifies the name of the reverse relationship, i.e., the corresponding relationship name in the PostTag class
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='tag_id', inverse_of='tag')

    # Return table name
    @classmethod
    def table_name(cls) -> str:
        return 'tags'
```

> 💡 **AI Prompt Example**: "How should the models at both ends of a many-to-many relationship be defined? What similarities does it have with one-to-many relationships?"

### 3. Using Many-to-Many Relationships

Access many-to-many relationship data through the intermediate model.

```python
# Create post
post = Post(title="Python Programming Introduction", content="Python is a powerful programming language...")
post.save()

# Create tags
tag1 = Tag(name="Python", description="Python programming language related")
tag1.save()
tag2 = Tag(name="Programming", description="Programming technology related")
tag2.save()

# Create association relationships
post_tag1 = PostTag(post_id=post.id, tag_id=tag1.id)
post_tag1.save()
post_tag2 = PostTag(post_id=post.id, tag_id=tag2.id)
post_tag2.save()

# Query all tags for a post
# Method 1: Traverse through intermediate table (causes N+1 query, not recommended)
post = Post.find_one(post.id)
# Get intermediate records
links = post.post_tags()  # First query: get all association records
# Get actual tags (causes N+1 query, each call to tag() executes one query)
tags = [link.tag() for link in links]  # Multiple queries: get each tag
print(f"Post tags: {[tag.name for tag in tags]}")

# Method 2: Use eager loading (recommended, avoids N+1 problem)
# Load associated data along with the query
post_with_tags = Post.query().with_('post_tags').all()
for post in post_with_tags:
    links = post.post_tags()  # Get from cache, no query execution
    tags = [link.tag() for link in links]  # Get from cache, no query execution
    print(f"Tags for post '{post.title}': {[tag.name for tag in tags]}")
```

> 💡 **AI Prompt Example**: "How to efficiently query many-to-many relationship data? How to avoid the N+1 query problem?"

### 4. Advanced Usage: Direct Access to Associated Objects

For more convenient use of many-to-many relationships, you can add convenience methods:

```python
# Extend Post class, add convenience methods for accessing tags
class Post(ActiveRecord):
    title: str
    content: str
    
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='post_id', inverse_of='post')

    @classmethod
    def table_name(cls) -> str:
        return 'posts'
    
    # Convenience method: directly get all tags
    def tags(self):
        """Get all tags for the post"""
        # Get all association records through intermediate table, then get corresponding tags
        links = self.post_tags()
        return [link.tag() for link in links]
    
    # Convenience method: add tag
    def add_tag(self, tag):
        """Add tag to the post"""
        # Check if association already exists
        existing = PostTag.query().where(
            (PostTag.c.post_id == self.id) & (PostTag.c.tag_id == tag.id)
        ).first()
        
        if not existing:
            post_tag = PostTag(post_id=self.id, tag_id=tag.id)
            post_tag.save()
            return post_tag
        return existing

# Extend Tag class, add convenience methods for accessing posts
class Tag(ActiveRecord):
    name: str
    description: str
    
    post_tags: ClassVar[HasMany[PostTag]] = HasMany(foreign_key='tag_id', inverse_of='tag')

    @classmethod
    def table_name(cls) -> str:
        return 'tags'
    
    # Convenience method: directly get all posts
    def posts(self):
        """Get all posts using this tag"""
        # Get all association records through intermediate table, then get corresponding posts
        links = self.post_tags()
        return [link.post() for link in links]
```

> 💡 **AI Prompt Example**: "How to add convenient access methods for many-to-many relationships? What are the benefits of doing so?"