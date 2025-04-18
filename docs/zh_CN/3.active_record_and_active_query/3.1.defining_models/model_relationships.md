# 模型关系定义

本文档介绍如何在ActiveRecord模型中定义和使用关系。模型关系是数据库表之间关联的表示，允许您以面向对象的方式处理相关数据。

## 关系类型概述

rhosocial ActiveRecord支持以下主要关系类型：

- **BelongsTo**：表示HasMany或HasOne的反向关系，当前模型包含引用另一个模型的外键
- **HasMany（一对多）**：表示另一个模型中的多条记录包含引用当前模型的外键
- **HasOne（一对一）**：表示另一个模型中的一条记录包含引用当前模型的外键

## 定义关系

### BelongsTo关系

BelongsTo关系表示当前模型包含引用另一个模型的外键。例如，评论属于文章：

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import BelongsTo

class Comment(IntegerPKMixin, ActiveRecord):
    __table_name__ = "comments"
    
    id: Optional[int] = None
    post_id: int  # 外键
    content: str
    
    # 定义与Post模型的关系
    post: ClassVar[BelongsTo['Post']] = BelongsTo(
        foreign_key='post_id',  # 当前模型中的外键字段
        inverse_of='comments'   # Post模型中对应的关系名
    )
```

### HasMany关系

HasMany关系表示另一个模型中的多条记录包含引用当前模型的外键。例如，文章有多条评论：

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany

class Post(IntegerPKMixin, ActiveRecord):
    __table_name__ = "posts"
    
    id: Optional[int] = None
    title: str
    content: str
    
    # 定义与Comment模型的关系
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='post_id',  # Comment模型中的外键字段
        inverse_of='post'       # Comment模型中对应的关系名
    )
```

### 双向关系

通过使用`inverse_of`参数，您可以定义双向关系，这有助于维护数据一致性并提高性能：

```python
# Post模型
comments: ClassVar[HasMany['Comment']] = HasMany(
    foreign_key='post_id',
    inverse_of='post'  # 指向Comment模型中的post关系
)

# Comment模型
post: ClassVar[BelongsTo['Post']] = BelongsTo(
    foreign_key='post_id',
    inverse_of='comments'  # 指向Post模型中的comments关系
)
```

## 关系配置选项

### 基本配置参数

所有关系类型都支持以下配置参数：

- `foreign_key`：外键字段名
- `inverse_of`：反向关系名
- `cache_config`：关系缓存配置

### 缓存配置

您可以使用`CacheConfig`类配置关系缓存：

```python
from rhosocial.activerecord.relation import HasMany, CacheConfig

orders: ClassVar[HasMany['Order']] = HasMany(
    foreign_key='user_id',
    cache_config=CacheConfig(
        ttl=300,       # 缓存生存时间（秒）
        max_size=100   # 最大缓存项数
    )
)
```

## 使用关系

### 自动生成的方法

当您定义一个关系时，rhosocial ActiveRecord会自动为每个关系生成两个方法：

1. **relation_name()** - 用于访问相关记录的方法
2. **relation_name_query()** - 用于访问关系的预配置查询构建器的方法

### 访问关系

一旦定义了关系，您可以通过调用关系方法来访问它们：

```python
# 获取用户的所有订单
user = User.find(1)
orders = user.orders()  # 返回Order对象列表

# 获取订单的用户
order = Order.find(1)
user = order.user()  # 返回User对象
```

### 关系查询

每个关系都提供对预配置查询构建器的直接访问，通过自动生成的查询方法：

```python
# 获取用户的活跃订单
active_orders = user.orders_query().where('status = ?', ('active',)).all()

# 获取用户的订单数量
order_count = user.orders_query().count()

# 使用条件查询
active_orders = user.orders_query().where('status = ?', ('active',)).all()

# 使用聚合函数
total_amount = user.orders_query().sum('amount')
```

### 关系缓存管理

rhosocial ActiveRecord为关系提供实例级缓存。关系描述符实现了`__delete__`方法，用于清除缓存而非删除关系本身：

```python
# 清除特定关系的缓存
user.orders.clear_cache()  # 使用关系方法的clear_cache()函数

# 或者使用实例的清除缓存方法
user.clear_relation_cache('orders')

# 使用Python的del关键字（利用__delete__方法）
del user.orders  # 等同于上面的方法，只会清除缓存而不会删除关系

# 清除所有关系的缓存
user.clear_relation_cache()
```

## 完整示例

以下是一个完整的示例，演示了如何设置和使用关系：

```python
from typing import ClassVar, Optional, List
from pydantic import Field, EmailStr
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin, TimestampMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    __table_name__ = "users"

    id: Optional[int] = None
    username: str
    email: EmailStr
    
    # 定义与Post的一对多关系
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )
    
    # 定义与Comment的一对多关系
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )

class Post(IntegerPKMixin, TimestampMixin, ActiveRecord):
    __table_name__ = "posts"

    id: Optional[int] = None
    user_id: int
    title: str
    content: str
    
    # 定义与User的多对一关系
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )
    
    # 定义与Comment的一对多关系
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='post_id',
        inverse_of='post'
    )

class Comment(IntegerPKMixin, TimestampMixin, ActiveRecord):
    __table_name__ = "comments"

    id: Optional[int] = None
    user_id: int
    post_id: int
    content: str
    
    # 定义与Post的BelongsTo关系
    post: ClassVar[BelongsTo['Post']] = BelongsTo(
        foreign_key='post_id',
        inverse_of='comments'
    )
    
    # 定义与User的BelongsTo关系
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='comments'
    )
```

使用这些关系：

```python
# 创建用户
user = User(username="test_user", email="test@example.com")
user.save()

# 创建文章
post = Post(user_id=user.id, title="Test Post", content="This is a test post")
post.save()

# 创建评论
comment = Comment(user_id=user.id, post_id=post.id, content="Great post!")
comment.save()

# 访问关系
user_posts = user.posts()  # 获取用户的所有文章
post_comments = post.comments()  # 获取文章的所有评论
comment_user = comment.user()  # 获取评论的用户

# 使用关系查询
recent_posts = user.posts_query().where('created_at > ?', (last_week,)).all()
active_comments = post.comments_query().where('status = ?', ('active',)).all()
```

## 关系加载策略

### 延迟加载

默认情况下，关系使用延迟加载策略，这意味着只有在访问关系时才会加载相关数据：

```python
user = User.find(1)
# 此时还没有加载posts

posts = user.posts  # 现在才执行查询加载posts
```

### 预加载

为了避免N+1查询问题，您可以使用预加载功能：

```python
# 预加载用户的文章
users = User.with_relation('posts').all()

# 预加载嵌套关系
users = User.with_relation(['posts', 'posts.comments']).all()

# 对预加载的关系应用条件
users = User.with_relation('posts', lambda q: q.where(status='published')).all()
```

## 总结

rhosocial ActiveRecord的关系系统提供了一种直观且类型安全的方式来定义和使用数据库关系。通过适当地使用关系，您可以创建更加清晰和高效的代码，同时避免常见的性能陷阱。