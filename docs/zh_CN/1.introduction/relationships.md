# 关系管理

rhosocial ActiveRecord 提供了一个多功能且类型安全的关系管理系统，使开发者能够以直观的方式定义和使用数据库关系。关系系统设计用于处理常见的关系类型，同时提供灵活的查询和预加载功能。

## 核心关系类型

rhosocial ActiveRecord 支持三种主要关系类型：

### 1. BelongsTo（多对一）

`BelongsTo` 关系表示当前模型包含引用另一个模型的外键：

```python
from activerecord import ActiveRecord
from activerecord.relations import BelongsTo
from typing import Optional, ClassVar

class Comment(ActiveRecord):
    __table_name__ = 'comments'
    
    id: Optional[int] = None
    content: str
    post_id: int
    
    # 评论属于一篇文章
    post: ClassVar['Post'] = BelongsTo('post_id')
```

### 2. HasOne（一对一）

`HasOne` 关系表示另一个模型包含引用当前模型的外键，并且只能有一条相关记录：

```python
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: Optional[int] = None
    name: str
    
    # 用户有一个资料
    profile: ClassVar['Profile'] = HasOne('user_id')
```

### 3. HasMany（一对多）

`HasMany` 关系表示另一个模型中的多条记录包含引用当前模型的外键：

```python
from typing import List, ClassVar

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: Optional[int] = None
    title: str
    
    # 文章有多条评论
    comments: ClassVar[List['Comment']] = HasMany('post_id')
```

## 关系配置

每种关系类型提供配置选项：

```python
class User(ActiveRecord):
    # 基本关系
    profile: ClassVar[HasOne['Profile']] = HasOne('user_id')
    
    # 指定反向关系
    posts: ClassVar[HasMany['Post']] = HasMany('user_id', inverse_of='author')
    
    # 自定义缓存配置
    orders: ClassVar[HasMany['Order']] = HasMany('user_id', cache_config=CacheConfig(ttl=600, max_size=500))
```

## 双向关系

rhosocial ActiveRecord 通过 `inverse_of` 参数支持双向关系，这有助于维护一致性并启用验证：

```python
class Post(ActiveRecord):
    # 文章有多条评论
    comments: ClassVar[List['Comment']] = HasMany('post_id', inverse_of='post')
    # 文章属于一个作者（用户）
    author: ClassVar['User'] = BelongsTo('user_id', inverse_of='posts')

class Comment(ActiveRecord):
    # 评论属于一篇文章
    post: ClassVar['Post'] = BelongsTo('post_id', inverse_of='comments')
```

## 预加载

关系系统包括强大的预加载功能，以避免 N+1 查询问题：

```python
# 仅使用 3 个查询加载用户及其资料和文章
users = User.query().with_('profile', 'posts').all()

# 使用点表示法进行嵌套预加载
users = User.query().with_('posts.comments').all()

# 为关系加载自定义查询条件
users = User.query().with_(
    ('posts', lambda q: q.where('published = ?', (True,)))
).all()
```

## 关系查询

每个关系都提供对预配置查询构建器的直接访问：

```python
# 获取用户文章的查询构建器
user = User.find_one(1)
recent_posts = user.posts_query().where('created_at > ?', (last_week,)).all()

# 过滤和操作关系查询
active_orders = user.orders_query().where('status = ?', ('active',)).order_by('created_at DESC').all()
```

## 关系缓存

rhosocial ActiveRecord 为关系提供实例级缓存，确保适当的隔离和内存管理：

```python
# 首次访问时缓存
user = User.find_one(1)
user.posts()  # 从数据库加载
user.posts()  # 使用缓存值

# 需要时清除缓存
user.clear_relation_cache('posts')  # 清除特定关系
user.clear_relation_cache()  # 清除所有关系
```

## 使用示例

以下是一个完整示例，演示如何设置和使用关系：

```python
from activerecord import ActiveRecord
from activerecord.relations import BelongsTo, HasMany, HasOne
from typing import Optional, List, ClassVar

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: Optional[int] = None
    username: str
    email: str
    
    # 用户有多篇文章
    posts: ClassVar[List['Post']] = HasMany('user_id', inverse_of='author')
    
    # 用户有一个资料
    profile: ClassVar['Profile'] = HasOne('user_id', inverse_of='user')

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: Optional[int] = None
    user_id: int
    title: str
    content: str
    
    # 文章属于一个用户
    author: ClassVar['User'] = BelongsTo('user_id', inverse_of='posts')
    
    # 文章有多条评论
    comments: ClassVar[List['Comment']] = HasMany('post_id', inverse_of='post')

class Comment(ActiveRecord):
    __table_name__ = 'comments'
    
    id: Optional[int] = None
    post_id: int
    user_id: int
    content: str
    
    # 评论属于一篇文章
    post: ClassVar['Post'] = BelongsTo('post_id', inverse_of='comments')
    
    # 评论属于一个用户
    author: ClassVar['User'] = BelongsTo('user_id', inverse_of='comments')

class Profile(ActiveRecord):
    __table_name__ = 'profiles'
    
    id: Optional[int] = None
    user_id: int
    bio: str
    avatar_url: str
    
    # 资料属于一个用户
    user: ClassVar['User'] = BelongsTo('user_id', inverse_of='profile')

# 创建带关系的记录
user = User(username="john_doe", email="john@example.com")
user.save()

profile = Profile(user_id=user.id, bio="Python developer", avatar_url="avatar.jpg")
profile.save()

post = Post(user_id=user.id, title="Introduction to ORMs", content="...")
post.save()

comment = Comment(post_id=post.id, user_id=user.id, content="Great article!")
comment.save()

# 访问关系
user = User.find_one(1)
user_profile = user.profile()  # 访问用户资料
user_posts = user.posts()      # 访问用户文章

# 使用预加载访问嵌套关系
posts_with_comments = Post.query().with_('author', 'comments.author').all()

for post in posts_with_comments:
    print(f"Post: {post.title} by {post.author().username}")
    for comment in post.comments():
        print(f"  Comment by {comment.author().username}: {comment.content}")
```

## 与其他 ORM 的比较

### vs SQLAlchemy
SQLAlchemy 提供更广泛的关系类型，包括多对多关系和关联对象。然而，其关系定义语法更复杂，需要更多样板代码。rhosocial ActiveRecord 的关系系统更直观，需要更少的代码，同时仍提供最常见的关系类型。

```python
# SQLAlchemy 关系示例
class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    title = Column(String)
    content = Column(Text)
    
    # 定义关系
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
```

### vs Django ORM
Django ORM 的关系 API 在模型定义中使用字段对象，这与 rhosocial ActiveRecord 基于描述符的方法略有不同。Django 也支持开箱即用的多对多关系，但其预加载需要更冗长的语法，使用 `prefetch_related` 和 `select_related`。

```python
# Django ORM 关系示例
class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    # 访问带相关作者和评论的文章
    # Post.objects.select_related('author').prefetch_related('comment_set__author')
```

### vs Peewee
Peewee 的关系 API 类似于 rhosocial ActiveRecord，但在模型定义中使用字段对象而非描述符。它也支持预加载，但对于嵌套关系需要更多手动设置。

```python
# Peewee 关系示例
class Post(Model):
    author = ForeignKeyField(User, backref='posts')
    title = CharField()
    content = TextField()
    
    # 访问带相关对象的文章
    # Post.select().join(User).switch(Post).join(Comment)
```

## rhosocial ActiveRecord 关系系统的主要优势

1. **类型安全**：完全类型提示与泛型，提供更好的 IDE 支持和运行时类型检查
2. **简化定义**：基于描述符的干净语法，最小样板代码
3. **灵活加载**：直观的预加载，支持嵌套关系和查询自定义
4. **实例级缓存**：高效的缓存机制，在实例之间适当隔离
5. **双向验证**：自动验证反向关系，确保数据一致性
6. **查询构建器访问**：直接访问特定关系的查询构建器，用于自定义过滤
7. **性能优化**：优化的批量加载，对大型数据集提供出色性能