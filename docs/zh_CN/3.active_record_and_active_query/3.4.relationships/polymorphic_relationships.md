# 多态关系

多态关系允许一个模型通过单一关联属于多种类型的模型。在rhosocial ActiveRecord中，多态关系使您能够创建灵活和可重用的代码，允许一个模型使用单一组外键与多个其他模型相关联。

## 概述

当您有一个可以与多个其他模型相关联的模型时，多态关系非常有用。常见的例子包括：

- 可以属于不同类型内容的评论（帖子、视频、产品）
- 可以与各种模型相关联的附件（用户、消息、文章）
- 可以应用于不同类型项目的标签（产品、文章、事件）

在多态关系中，可以属于不同类型的模型通常有两个特殊字段：

1. 存储相关记录ID的外键字段
2. 存储相关模型的类或类型的类型字段

## 实现多态关系

### 示例：不同内容类型的评论

让我们实现一个系统，其中评论可以与帖子或视频相关联：

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
    
    # 定义与Comment模型的关系
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
    
    # 定义与Comment模型的关系
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
    commentable_id: int      # 指向相关模型的外键
    commentable_type: str    # 相关模型的类型（"Post"或"Video"）
    
    # 定义多态关系
    commentable: ClassVar[BelongsTo[Union['Post', 'Video']]] = BelongsTo(
        foreign_key='commentable_id',
        polymorphic_type='commentable_type',
        inverse_of='comments'
    )
    
    # 获取实际可评论对象的辅助方法
    def get_commentable(self):
        if self.commentable_type == 'Post':
            from .post import Post
            return Post.find_by(id=self.commentable_id)
        elif self.commentable_type == 'Video':
            from .video import Video
            return Video.find_by(id=self.commentable_id)
        return None
```

在这个例子中：

- `Post`和`Video`模型与`Comment`有`HasMany`关系
- `Comment`模型与`Post`或`Video`有`BelongsTo`关系
- `commentable_type`字段存储相关模型的类型（"Post"或"Video"）
- `commentable_id`字段存储相关记录的ID

## 使用多态关系

### 为不同内容类型创建评论

```python
# 创建一个帖子并添加评论
post = Post(title="我的第一篇帖子", content="这是我的第一篇帖子内容")
post.save()

post_comment = Comment(
    content="好文章！",
    commentable_id=post.id,
    commentable_type="Post"
)
post_comment.save()

# 创建一个视频并添加评论
video = Video(title="我的第一个视频", url="https://example.com/video1", duration=120)
video.save()

video_comment = Comment(
    content="不错的视频！",
    commentable_id=video.id,
    commentable_type="Video"
)
video_comment.save()
```

### 检索评论

```python
# 获取帖子的所有评论
post = Post.find_by(title="我的第一篇帖子")
post_comments = post.comments()

for comment in post_comments:
    print(f"帖子评论: {comment.content}")

# 获取视频的所有评论
video = Video.find_by(title="我的第一个视频")
video_comments = video.comments()

for comment in video_comments:
    print(f"视频评论: {comment.content}")
```

### 检索可评论对象

```python
# 获取评论及其相关对象
comment = Comment.find_by(content="好文章！")
commentable = comment.get_commentable()

if commentable:
    if comment.commentable_type == "Post":
        print(f"帖子评论: {commentable.title}")
    elif comment.commentable_type == "Video":
        print(f"视频评论: {commentable.title}")
```

## 高级用法：多态多对多关系

您还可以实现多态多对多关系。例如，让我们创建一个标签系统，其中标签可以应用于不同类型的项目：

```python
from typing import ClassVar, Optional, Union
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class Tag(IntegerPKMixin, ActiveRecord):
    __table_name__ = "tags"
    
    id: Optional[int] = None
    name: str
    
    # 定义与Tagging模型的关系
    taggings: ClassVar[HasMany['Tagging']] = HasMany(
        foreign_key='tag_id',
        inverse_of='tag'
    )
    
    # 获取特定类型的所有可标记对象的辅助方法
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
    
    # 定义关系
    tag: ClassVar[BelongsTo['Tag']] = BelongsTo(
        foreign_key='tag_id',
        inverse_of='taggings'
    )
    
    # 获取可标记对象的辅助方法
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
    
    # 定义与Tagging模型的关系
    taggings: ClassVar[HasMany['Tagging']] = HasMany(
        foreign_key='taggable_id',
        polymorphic_type='taggable_type',
        polymorphic_value='Product',
        inverse_of='taggable'
    )
    
    # 获取此产品的所有标签的辅助方法
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
    
    # 定义与Tagging模型的关系
    taggings: ClassVar[HasMany['Tagging']] = HasMany(
        foreign_key='taggable_id',
        polymorphic_type='taggable_type',
        polymorphic_value='Article',
        inverse_of='taggable'
    )
    
    # 获取此文章的所有标签的辅助方法
    def tags(self):
        from .tag import Tag
        taggings = self.taggings()
        tag_ids = [tagging.tag_id for tagging in taggings]
        return Tag.find_all().where(id__in=tag_ids).all()
```

## 最佳实践

1. **为多态字段使用有意义的名称**：不要使用像"type"和"id"这样的通用名称，而是使用更具描述性的名称，如"commentable_type"和"commentable_id"。

2. **实现辅助方法**：在模型中添加辅助方法，使多态关系的使用更加直观，如上面的示例所示。

3. **考虑使用类型注册表**：对于具有多种多态类型的大型应用程序，考虑实现类型注册表，以在模型类和类型字符串之间进行映射。

4. **注意类型安全**：由于多态关系可以返回不同类型的对象，请注意代码中的类型安全。使用适当的类型提示和运行时检查。

5. **添加数据库索引**：在多态关系中为外键和类型字段添加索引，以提高查询性能。

## 结论

多态关系提供了一种强大的方式，在rhosocial ActiveRecord中创建模型之间的灵活关联。通过使用多态关系，您可以减少代码重复，创建更易于维护和扩展的应用程序。虽然它们比标准关系需要更多的设置，但对于复杂的应用程序来说，它们提供的灵活性通常值得额外的努力。