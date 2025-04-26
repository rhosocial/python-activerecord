# 跨数据库关系

跨数据库关系允许您定义存储在不同数据库中的模型之间的关联。rhosocial ActiveRecord提供了跨多个数据库连接处理相关数据的支持，实现更灵活和可扩展的应用程序架构。

## 概述

跨数据库关系在各种场景中都很有用，包括：

- 微服务架构，其中不同的服务有自己的数据库
- 遗留系统集成，数据分布在多个数据库中
- 分片策略，数据分区到多个数据库中
- 多租户应用程序，每个租户有单独的数据库

在rhosocial ActiveRecord中，跨数据库关系的工作方式与常规关系类似，但需要额外的配置来指定每个模型的数据库连接。

## 设置多个数据库连接

在使用跨数据库关系之前，您需要在应用程序中配置多个数据库连接：

```python
from rhosocial.activerecord import ConnectionManager

# 配置主数据库连接
ConnectionManager.configure({
    'default': {
        'driver': 'mysql',
        'host': 'localhost',
        'database': 'primary_db',
        'username': 'user',
        'password': 'password'
    },
    'secondary': {
        'driver': 'postgresql',
        'host': 'localhost',
        'database': 'secondary_db',
        'username': 'user',
        'password': 'password'
    }
})
```

## 定义使用不同数据库连接的模型

要使用跨数据库关系，您需要指定每个模型应该使用哪个数据库连接：

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    __connection__ = "default"  # 使用默认数据库连接
    
    id: Optional[int] = None
    username: str
    email: str
    
    # 定义与secondary数据库中Post模型的关系
    posts: ClassVar[HasMany['Post']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )

class Post(IntegerPKMixin, ActiveRecord):
    __table_name__ = "posts"
    __connection__ = "secondary"  # 使用secondary数据库连接
    
    id: Optional[int] = None
    user_id: int
    title: str
    content: str
    
    # 定义与default数据库中User模型的关系
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )
```

## 使用跨数据库关系

### 基本用法

一旦您使用适当的数据库连接设置了模型，您就可以像使用常规关系一样使用跨数据库关系：

```python
# 在默认数据库中查找用户
user = User.find_by(username="example_user")

# 从secondary数据库获取帖子
posts = user.posts()

for post in posts:
    print(f"帖子标题: {post.title}")
    
    # 这将查询默认数据库以获取用户
    post_author = post.user()
    print(f"作者: {post_author.username}")
```

### 创建相关记录

在跨数据库创建相关记录时，您需要注意事务不会跨多个数据库：

```python
# 在默认数据库中查找用户
user = User.find_by(username="example_user")

# 在secondary数据库中创建新帖子
new_post = Post(
    user_id=user.id,
    title="跨数据库关系示例",
    content="这个帖子存储在与用户不同的数据库中。"
)
new_post.save()
```

## 跨数据库关系的预加载

预加载适用于跨数据库关系，但它将为每个数据库执行单独的查询：

```python
# 获取用户时预加载帖子
users = User.find_all().with_("posts").all()

# 这将执行两个查询：
# 1. 一个查询到默认数据库以获取用户
# 2. 另一个查询到secondary数据库以获取帖子

for user in users:
    posts = user.posts()  # 不执行额外的查询
    print(f"用户: {user.username}, 帖子数量: {len(posts)}")
```

## 限制和注意事项

### 事务限制

跨数据库关系最显著的限制是事务不能跨多个数据库。这意味着如果您需要更新不同数据库中的相关记录，您不能确保两个操作的原子性：

```python
# 此事务仅影响默认数据库
with User.transaction():
    user = User.find_by(username="example_user")
    user.username = "new_username"
    user.save()
    
    # 此操作在不同的数据库中，不会成为事务的一部分
    post = Post.find_by(user_id=user.id)
    post.title = "更新的标题"
    post.save()
```

为了处理这个限制，您可能需要实现应用程序级别的补偿机制或使用最终一致性模式。

### 性能考虑

跨数据库关系可能会由于需要连接到多个数据库而引入额外的延迟。考虑以下性能优化：

1. **使用预加载**：通过在适当时预加载相关数据，最小化数据库往返次数。

2. **缓存频繁访问的数据**：使用缓存减少对频繁访问数据的跨数据库查询需求。

3. **考虑反规范化**：在某些情况下，跨数据库反规范化数据可能有益，以减少跨数据库查询的需求。

### 数据库同步

在使用跨数据库关系时，您需要确保相关数据在数据库之间保持一致。这可能涉及：

1. **外键约束**：即使外键约束不能跨数据库，您也应该实现应用程序级别的验证以确保引用完整性。

2. **计划同步**：对于某些用例，您可能需要实现计划任务来同步数据库之间的数据。

3. **基于事件的同步**：使用事件或消息队列在数据库之间传播更改。

## 高级模式

### 仓库模式

对于复杂的跨数据库场景，您可能想要实现仓库模式来抽象数据访问的细节：

```python
class UserRepository:
    @classmethod
    def get_user_with_posts(cls, user_id):
        user = User.find_by(id=user_id)
        if user:
            posts = Post.find_all().where(user_id=user_id).all()
            # 手动将帖子与用户关联
            user._posts = posts
        return user
```

### 读取副本

如果您使用读取副本进行扩展，可以为读取和写入操作配置不同的连接：

```python
class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    __connection__ = "default"  # 用于写操作
    __read_connection__ = "default_replica"  # 用于读操作
    
    # ...
```

## 最佳实践

1. **最小化跨数据库关系**：虽然跨数据库关系功能强大，但它们有限制。尝试设计数据库架构以最小化跨数据库查询的需求。

2. **记录数据库依赖关系**：清楚地记录哪些模型存储在哪些数据库中以及它们如何相互关联。

3. **实现应用程序级别的验证**：由于外键约束不能跨数据库，请实现应用程序级别的验证以确保数据完整性。

4. **考虑最终一致性**：在具有多个数据库的分布式系统中，最终一致性可能比尝试维持严格一致性更合适。

5. **监控性能**：定期监控跨数据库查询的性能并根据需要进行优化。

6. **使用连接池**：为每个数据库配置连接池，以最小化建立新连接的开销。

## 结论

rhosocial ActiveRecord中的跨数据库关系提供了一种强大的方式来处理跨多个数据库的相关数据。虽然它们有一定的限制，特别是在事务方面，但它们实现了更灵活和可扩展的应用程序架构。通过理解这些限制并遵循最佳实践，您可以在应用程序中有效地使用跨数据库关系。