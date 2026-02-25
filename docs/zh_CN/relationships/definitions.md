# 基础关系 (1:1, 1:N)

`rhosocial-activerecord` 使用三个核心描述符：`BelongsTo`, `HasOne`, `HasMany`。这些描述符提供了类型安全的关联关系定义方式。

> 💡 **AI提示词示例**: "ActiveRecord中的关联关系有哪些类型？它们之间有什么区别？"

## 一对一 (One-to-One): User 与 Profile

每个用户有一个资料页。这种关系表示两个实体之间的一对一映射关系。

```python
# 导入必要的模块
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasOne, BelongsTo

# User类代表系统中的用户
class User(ActiveRecord):
    # 用户名字段
    username: str
    
    # User 拥有一个 Profile (一对一关系)
    # HasOne描述符定义了拥有关系
    # foreign_key='user_id' 指的是 Profile 表中的外键字段名
    # inverse_of='user' 指定了反向关系的名称，即在Profile类中对应的关联关系名
    profile: ClassVar[HasOne['Profile']] = HasOne(foreign_key='user_id', inverse_of='user')

    # 返回表名
    @classmethod
    def table_name(cls) -> str:
        return 'users'

# Profile类代表用户的详细资料
class Profile(ActiveRecord):
    # 外键字段，关联到User表的id字段
    # 这个字段在数据库中实际存在
    user_id: str
    
    # 用户的个人简介
    bio: str
    # 用户的头像URL
    avatar_url: str
    
    # Profile 属于一个 User (一对一反向关系)
    # BelongsTo描述符定义了从属关系
    # foreign_key='user_id' 指的是本表中的外键字段名
    # inverse_of='profile' 指定了反向关系的名称，即在User类中对应的关联关系名
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='profile')

    # 返回表名
    @classmethod
    def table_name(cls) -> str:
        return 'profiles'
```

> 💡 **AI提示词示例**: "在一对一关系中，外键应该放在哪张表中？HasOne和BelongsTo有什么区别？"

## 一对多 (One-to-Many): User 与 Post

一个用户可以发布多篇文章。这种关系表示一个实体可以拥有多个相关实体。

```python
# 导入必要的模块
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany, BelongsTo

# User类代表系统中的用户
class User(ActiveRecord):
    # 用户名字段
    username: str
    # 邮箱字段
    email: str
    
    # User 拥有多个 Post (一对多关系)
    # HasMany描述符定义了一对多的拥有关系
    # foreign_key='user_id' 指的是 Post 表中的外键字段名
    # inverse_of='author' 指定了反向关系的名称，即在Post类中对应的关联关系名
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')

    # 返回表名
    @classmethod
    def table_name(cls) -> str:
        return 'users'

# Post类代表用户发布的文章
class Post(ActiveRecord):
    # 文章标题
    title: str
    # 文章内容
    content: str
    # 外键字段，关联到User表的id字段
    # 这个字段在数据库中实际存在
    user_id: str
    
    # Post 属于一个 User (多对一关系，文章的作者)
    # BelongsTo描述符定义了从属关系
    # foreign_key='user_id' 指的是本表中的外键字段名
    # inverse_of='posts' 指定了反向关系的名称，即在User类中对应的关联关系名
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')

    # 返回表名
    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

> 💡 **AI提示词示例**: "一对多关系在数据库中如何表示？如何通过代码访问关联的数据？"

## 关系使用示例

定义好关系后，可以通过以下方式使用：

```python
# 创建用户
user = User(username="张三", email="zhangsan@example.com")
user.save()

# 创建用户的资料
profile = Profile(bio="我是张三，一个程序员", avatar_url="http://example.com/avatar.jpg", user_id=user.id)
profile.save()

# 创建用户的文章
post1 = Post(title="我的第一篇文章", content="这是文章内容...", user_id=user.id)
post1.save()
post2 = Post(title="我的第二篇文章", content="这是另一篇文章内容...", user_id=user.id)
post2.save()

# 访问关联数据
# 获取用户的资料 (一对一关系)
user_profile = user.profile()  # 这会执行一次数据库查询
print(f"用户简介: {user_profile.bio}")

# 获取用户的所有文章 (一对多关系)
user_posts = user.posts()  # 这会执行一次数据库查询
print(f"用户发布了 {len(user_posts)} 篇文章")

# 获取文章的作者 (多对一关系)
post_author = post1.author()  # 这会执行一次数据库查询
print(f"文章作者: {post_author.username}")
```

> 💡 **AI提示词示例**: "访问关联关系时会执行数据库查询吗？如何避免N+1查询问题？"

## 重要注意事项

**注意**: 所有的关系描述符必须声明为 `ClassVar`，以避免干扰 Pydantic 的字段验证。

如果不使用 `ClassVar`，Pydantic 会将这些关系当作模型字段处理，导致：
1. 数据验证时出现错误
2. 序列化时包含不必要的关系数据
3. 内存使用增加

```python
# ❌ 错误的做法 - 没有使用ClassVar
class User(ActiveRecord):
    # 这会被Pydantic当作字段处理，导致问题
    profile = HasOne(foreign_key='user_id', inverse_of='user')

# ✅ 正确的做法 - 使用ClassVar
class User(ActiveRecord):
    # 这不会被Pydantic当作字段处理
    profile: ClassVar[HasOne['Profile']] = HasOne(foreign_key='user_id', inverse_of='user')
```

> 💡 **AI提示词示例**: "为什么关系描述符必须使用ClassVar声明？不这样做会有什么后果？"