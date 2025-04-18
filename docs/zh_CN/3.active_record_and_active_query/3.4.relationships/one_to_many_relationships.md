# 一对多关系

一对多关系是数据库中最常见的关系类型之一，它表示一个模型的单个实例可以与另一个模型的多个实例相关联。在rhosocial ActiveRecord中，这种关系通过`HasMany`和`BelongsTo`关系类型来实现。

## 概述

一对多关系的典型例子包括：

- 一个用户可以有多个帖子
- 一个部门可以有多个员工
- 一个产品可以有多个评论

在这些例子中，"一"方（用户、部门、产品）通过`HasMany`关系与"多"方（帖子、员工、评论）相关联，而"多"方通过`BelongsTo`关系与"一"方相关联。

## 定义一对多关系

### 使用HasMany和BelongsTo

在rhosocial ActiveRecord中，一对多关系通过在两个模型之间定义`HasMany`和`BelongsTo`关系来实现：

```python
from typing import ClassVar, Optional, List
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    
    id: Optional[int] = None
    username: str
    email: str
    
    # 定义与Post模型的一对多关系
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',  # Post模型中的外键字段
        inverse_of='user'       # Post模型中的反向关系属性名
    )

class Post(IntegerPKMixin, ActiveRecord):
    __table_name__ = "posts"
    
    id: Optional[int] = None
    user_id: int  # 外键字段，引用User模型的id
    title: str
    content: str
    
    # 定义与User模型的多对一关系
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',  # 当前模型中的外键字段
        inverse_of='posts'      # User模型中的反向关系属性名
    )
```

### 关系配置选项

`HasMany`和`BelongsTo`关系支持以下配置选项：

#### 共同选项

- `foreign_key`：指定外键字段名（必填）
- `inverse_of`：指定关联模型中的反向关系属性名（可选，但强烈建议设置）
- `loader`：自定义加载器实现（可选）
- `validator`：自定义验证器实现（可选）
- `cache_config`：缓存配置（可选）

这些选项在`RelationDescriptor`基类中定义，并被`HasMany`和`BelongsTo`类继承。例如：

```python
# HasMany示例
posts: ClassVar[HasMany['Post']] = HasMany(
    foreign_key='user_id',  # Post模型中的外键字段
    inverse_of='user',      # Post模型中的反向关系属性名
    cache_config=CacheConfig(ttl=300)  # 可选的缓存配置
)

# BelongsTo示例
user: ClassVar[BelongsTo['User']] = BelongsTo(
    foreign_key='user_id',  # 当前模型中的外键字段
    inverse_of='posts'      # User模型中的反向关系属性名
)
```

## 使用一对多关系

### 访问关联记录

一旦定义了一对多关系，您可以使用以下方式访问关联记录：

```python
# 获取用户
user = User.query().where('username = ?', ("example_user",)).one()

# 获取用户的所有帖子
posts = user.posts()

# 遍历帖子
for post in posts:
    print(f"标题: {post.title}")
    print(f"内容: {post.content}")

# 从帖子获取用户
post = Post.query().where('title = ?', ("示例帖子",)).one()
post_author = post.user()
print(f"作者: {post_author.username}")
```

### 创建关联记录

rhosocial ActiveRecord提供了多种方式来创建关联记录：

```python
# 获取用户
user = User.query().where('username = ?', ("example_user",)).one()

# 方法1：直接创建并设置外键
new_post = Post(
    user_id=user.id,
    title="新帖子",
    content="这是一个新帖子的内容。"
)
new_post.save()

# 方法2：使用关系创建
new_post = Post(
    title="另一个新帖子",
    content="这是另一个新帖子的内容。"
)
user.posts().create(new_post)

# 方法3：使用build方法（创建但不保存）
new_post = user.posts().build(
    title="未保存的帖子",
    content="这个帖子尚未保存到数据库。"
)
# 稍后保存
new_post.save()
```

### 查询关联记录

您可以在关联记录上执行查询：

```python
# 获取用户
user = User.query().where('username = ?', ("example_user",)).one()

# 查询用户的特定帖子
recent_posts = user.posts().where(created_at__gt=datetime.now() - timedelta(days=7)).all()

# 计算用户的帖子数量
post_count = user.posts().count()

# 查找包含特定关键字的帖子
keyword_posts = user.posts().where(content__contains="Python").all()
```

### 预加载关联记录

为了避免N+1查询问题，您可以使用预加载（eager loading）：

```python
# 获取所有用户及其帖子（单个查询）
users = User.query().with_("posts").all()

# 现在可以访问每个用户的帖子，而不会触发额外的查询
for user in users:
    print(f"用户: {user.username}")
    posts = user.posts()  # 不执行额外查询
    print(f"帖子数量: {len(posts)}")
```

## 高级用法

### 手动处理级联操作

在处理一对多关系时，您可能需要手动实现级联操作，例如当删除父记录时删除所有关联记录：

```python
# 删除用户及其所有帖子
user = User.query().where('username = ?', ("example_user",)).one()

# 首先删除所有帖子
Post.query().where('user_id = ?', (user.id,)).delete().execute()

# 然后删除用户
user.delete()
```

您也可以在应用程序中实现其他级联策略：

- **级联删除**：删除父记录时删除所有关联记录
- **设置为NULL**：删除父记录时将关联记录的外键设置为NULL
- **阻止删除**：如果存在关联记录，则阻止删除父记录
```

### 排序关系

您可以为关系指定默认排序：

```python
class User(IntegerPKMixin, ActiveRecord):
    # ...
    
    # 按创建时间降序排列帖子
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        order=['-created_at']
    )
```

## 最佳实践

### 命名约定

- 使用描述性名称命名关系
- 对于`HasMany`关系，使用复数名称（如`posts`、`comments`）
- 对于`BelongsTo`关系，使用单数名称（如`user`、`author`）

### 性能考虑

- 为外键字段创建数据库索引
- 使用预加载避免N+1查询问题
- 对于大型集合，考虑分页或限制结果集大小

### 数据完整性

- 在数据库级别设置外键约束
- 使用适当的依赖选项确保数据一致性
- 在模型中实现验证规则

## 示例：完整的博客系统

以下是一个更完整的博客系统示例，展示了多个一对多关系：

```python
from typing import ClassVar, Optional, List
from datetime import datetime
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    
    id: Optional[int] = None
    username: str
    email: str
    created_at: datetime = datetime.now()
    
    # 用户可以有多个帖子
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='author',
        dependent='cascade'
    )
    
    # 用户可以发表多个评论
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='user_id',
        inverse_of='author',
        dependent='cascade'
    )

class Post(IntegerPKMixin, ActiveRecord):
    __table_name__ = "posts"
    
    id: Optional[int] = None
    user_id: int
    title: str
    content: str
    published: bool = False
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    # 帖子属于一个用户
    author: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )
    
    # 帖子可以有多个评论
    comments: ClassVar[HasMany['Comment']] = HasMany(
        foreign_key='post_id',
        inverse_of='post',
        dependent='cascade',
        order=['-created_at']
    )

class Comment(IntegerPKMixin, ActiveRecord):
    __table_name__ = "comments"
    
    id: Optional[int] = None
    post_id: int
    user_id: int
    content: str
    created_at: datetime = datetime.now()
    
    # 评论属于一个帖子
    post: ClassVar[BelongsTo['Post']] = BelongsTo(
        foreign_key='post_id',
        inverse_of='comments'
    )
    
    # 评论属于一个用户
    author: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='comments'
    )
```

使用这个系统：

```python
# 创建用户
user = User(username="john_doe", email="john@example.com")
user.save()

# 创建帖子
post = Post(
    user_id=user.id,
    title="rhosocial ActiveRecord简介",
    content="这是一个关于rhosocial ActiveRecord的帖子。",
    published=True
)
post.save()

# 添加评论
comment = Comment(
    post_id=post.id,
    user_id=user.id,
    content="这是一个自评论！"
)
comment.save()

# 获取帖子及其评论和作者
post_with_relations = Post.query().where('id = ?', (post.id,)).with_("author", "comments.author").one()

print(f"帖子: {post_with_relations.title}")
print(f"作者: {post_with_relations.author().username}")
print("评论:")
for comment in post_with_relations.comments():
    print(f" - {comment.author().username}: {comment.content}")
```

## 结论

一对多关系是数据库设计中的基础关系类型，rhosocial ActiveRecord提供了强大而灵活的API来处理这些关系。通过正确定义和使用`HasMany`和`BelongsTo`关系，您可以构建复杂的数据模型，同时保持代码的可读性和可维护性。

记住要考虑性能影响，特别是在处理大型数据集时，并使用预加载和其他优化技术来确保应用程序的高效运行。