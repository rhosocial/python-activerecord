# Polymorphic Relationships

Polymorphic relationships allow a model to belong to more than one type of model through a single association. In rhosocial ActiveRecord, polymorphic relationships enable you to create flexible and reusable code by allowing a model to be associated with multiple other models using a single set of foreign keys.

## Overview

Polymorphic relationships are useful when you have a model that can be associated with multiple other models. Common examples include:

- Comments that can belong to different types of content (posts, videos, products)
- Attachments that can be associated with various models (users, messages, articles)
- Tags that can be applied to different types of items (products, articles, events)

In a polymorphic relationship, the model that can belong to different types typically has two special fields:

1. A foreign key field that stores the ID of the related record
2. A type field that stores the class or type of the related model

## Implementing Polymorphic Relationships

### Example: Comments for Different Content Types

Let's implement a system where comments can be associated with either posts or videos:

```python
from typing import ClassVar, Optional, Union, Type
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import BelongsTo, HasMany

class Post(IntegerPKMixin, ActiveRecord):
    __table_name__ = "posts"
    
    id: Optional[int] = None
    title: str
    content: str
    
    # Define relationship with Comment model
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='commentable_id',
        polymorphic_type='commentable_type',
        polymorphic_value='Post',
        inverse_of='commentable'
    )

class Video(IntegerPKMixin, ActiveRecord):
    __table_name__ = "videos"
    
    id: Optional[int] = None
    title: str
    url: str
    duration: int
    
    # Define relationship with Comment model
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='commentable_id',
        polymorphic_type='commentable_type',
        polymorphic_value='Video',
        inverse_of='commentable'
    )

class Comment(IntegerPKMixin, ActiveRecord):
    __table_name__ = "comments"
    
    id: Optional[int] = None
    content: str
    commentable_id: int      # Foreign key to the related model
    commentable_type: str    # Type of the related model ("Post" or "Video")
    
    # Define polymorphic relationship
    commentable: ClassVar[BelongsTo[Union['Post', 'Video']]] = BelongsTo(
        foreign_key='commentable_id',
        polymorphic_type='commentable_type',
        inverse_of='comments'
    )
    
    # Helper method to get the actual commentable object
    def get_commentable(self):
        if self.commentable_type == 'Post':
            from .post import Post
            return Post.find_by(id=self.commentable_id)
        elif self.commentable_type == 'Video':
            from .video import Video
            return Video.find_by(id=self.commentable_id)
        return None
```

In this example:

- `Post` and `Video` models have a `HasMany` relationship with `Comment`
- `Comment` model has a `BelongsTo` relationship with either `Post` or `Video`
- The `commentable_type` field stores the type of the related model ("Post" or "Video")
- The `commentable_id` field stores the ID of the related record

## Using Polymorphic Relationships

### Creating Comments for Different Content Types

```python
# Create a post and add a comment
post = Post(title="My First Post", content="This is my first post content")
post.save()

post_comment = Comment(
    content="Great post!",
    commentable_id=post.id,
    commentable_type="Post"
)
post_comment.save()

# Create a video and add a comment
video = Video(title="My First Video", url="https://example.com/video1", duration=120)
video.save()

video_comment = Comment(
    content="Nice video!",
    commentable_id=video.id,
    commentable_type="Video"
)
video_comment.save()
```

### Retrieving Comments

```python
# Get all comments for a post
post = Post.find_by(title="My First Post")
post_comments = post.comments()

for comment in post_comments:
    print(f"Comment on post: {comment.content}")

# Get all comments for a video
video = Video.find_by(title="My First Video")
video_comments = video.comments()

for comment in video_comments:
    print(f"Comment on video: {comment.content}")
```

### Retrieving the Commentable Object

```python
# Get a comment and its related object
comment = Comment.find_by(content="Great post!")
commentable = comment.get_commentable()

if commentable:
    if comment.commentable_type == "Post":
        print(f"Comment on post: {commentable.title}")
    elif comment.commentable_type == "Video":
        print(f"Comment on video: {commentable.title}")
```

## Advanced Usage: Polymorphic Many-to-Many Relationships

You can also implement polymorphic many-to-many relationships. For example, let's create a tagging system where tags can be applied to different types of items:

```python
from typing import ClassVar, Optional, Union
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class Tag(IntegerPKMixin, ActiveRecord):
    __table_name__ = "tags"
    
    id: Optional[int] = None
    name: str
    
    # Define relationship with Tagging model
    taggings: ClassVar[HasMany['Tagging']] = HasMany(
        foreign_key='tag_id',
        inverse_of='tag'
    )
    
    # Helper method to get all taggable objects of a specific type
    def taggables(self, taggable_type):
        taggings = self.taggings().where(taggable_type=taggable_type).all()
        taggable_ids = [tagging.taggable_id for tagging in taggings]
        
        if taggable_type == 'Product':
            from .product import Product
            return Product.find_all().where(id__in=taggable_ids).all()
        elif taggable_type == 'Article':
            from .article import Article
            return Article.find_all().where(id__in=taggable_ids).all()
        
        return []

class Tagging(IntegerPKMixin, ActiveRecord):
    __table_name__ = "taggings"
    
    id: Optional[int] = None
    tag_id: int
    taggable_id: int
    taggable_type: str
    
    # Define relationships
    tag: ClassVar[BelongsTo['Tag']] = BelongsTo(
        foreign_key='tag_id',
        inverse_of='taggings'
    )
    
    # Helper method to get the taggable object
    def get_taggable(self):
        if self.taggable_type == 'Product':
            from .product import Product
            return Product.find_by(id=self.taggable_id)
        elif self.taggable_type == 'Article':
            from .article import Article
            return Article.find_by(id=self.taggable_id)
        return None

class Product(IntegerPKMixin, ActiveRecord):
    __table_name__ = "products"
    
    id: Optional[int] = None
    name: str
    price: float
    
    # Define relationship with Tagging model
    taggings: ClassVar[HasMany['Tagging']] = HasMany(
        foreign_key='taggable_id',
        polymorphic_type='taggable_type',
        polymorphic_value='Product',
        inverse_of='taggable'
    )
    
    # Helper method to get all tags for this product
    def tags(self):
        from .tag import Tag
        taggings = self.taggings()
        tag_ids = [tagging.tag_id for tagging in taggings]
        return Tag.find_all().where(id__in=tag_ids).all()

class Article(IntegerPKMixin, ActiveRecord):
    __table_name__ = "articles"
    
    id: Optional[int] = None
    title: str
    content: str
    
    # Define relationship with Tagging model
    taggings: ClassVar[HasMany['Tagging']] = HasMany(
        foreign_key='taggable_id',
        polymorphic_type='taggable_type',
        polymorphic_value='Article',
        inverse_of='taggable'
    )
    
    # Helper method to get all tags for this article
    def tags(self):
        from .tag import Tag
        taggings = self.taggings()
        tag_ids = [tagging.tag_id for tagging in taggings]
        return Tag.find_all().where(id__in=tag_ids).all()
```

## Best Practices

1. **Use meaningful names for polymorphic fields**: Instead of generic names like "type" and "id", use more descriptive names like "commentable_type" and "commentable_id".

2. **Implement helper methods**: Add helper methods to your models to make working with polymorphic relationships more intuitive, as shown in the examples above.

3. **Consider using a type registry**: For large applications with many polymorphic types, consider implementing a type registry to map between model classes and type strings.

4. **Be careful with type safety**: Since polymorphic relationships can return different types of objects, be mindful of type safety in your code. Use appropriate type hints and runtime checks.

5. **Add database indexes**: Add indexes to both the foreign key and type fields in polymorphic relationships to improve query performance.

## Conclusion

Polymorphic relationships provide a powerful way to create flexible associations between models in rhosocial ActiveRecord. By using polymorphic relationships, you can reduce code duplication and create more maintainable and extensible applications. While they require a bit more setup than standard relationships, the flexibility they provide is often worth the extra effort for complex applications.