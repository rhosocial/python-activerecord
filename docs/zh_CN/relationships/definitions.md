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

## 复合主键与关联关系

当模型使用复合主键（`CompositePKMixin`）时，外键列的数量必须匹配目标 PK 中
的列数。`foreign_key` 参数支持传入 **列名字符串元组**，每个外键列将按**位置**
映射到对应的 PK 列。

```python
from typing import ClassVar
from rhosocial.activerecord.field import CompositePKMixin
from rhosocial.activerecord.relation import BelongsTo, HasMany

class Order(ActiveRecord):
    __primary_key__ = ("order_id",)

    order_id: int
    items: ClassVar[HasMany['OrderItem']] = HasMany(
        foreign_key="order_id",
        inverse_of="order",
    )

class OrderItem(CompositePKMixin, ActiveRecord):
    __primary_key__ = ("order_id", "product_id")

    order_id: int
    product_id: int
    quantity: int

    # BelongsTo 按位置将外键列映射到 PK 列
    order: ClassVar[BelongsTo['Order']] = BelongsTo(
        foreign_key=("order_id",),
        inverse_of="items",
    )

# ("order_id",) 中的第一个外键列映射到第一个 PK 列 "order_id"
# 剩余的 PK 列 "product_id" 不被映射——它们构成中间表的复合唯一性。
# 这与单列场景等价，但当拥有侧本身使用复合 PK 时需要使用元组形式。
```

**规则**：

- `foreign_key` 可以是 `str`（单列）或 `tuple[str, ...]`（多列）。
- 外键列按**索引顺序**（位置映射）匹配目标 PK 列。
- 外键列数量不需要等于完整 PK 列数量。
  例如，在多对多中间表 `("order_id", "product_id")` 中，
  `BelongsTo(foreign_key=("order_id",))` 只映射第一个 PK 列。
- 异步描述符（`AsyncBelongsTo`、`AsyncHasOne`、`AsyncHasMany`）也支持相同的
  `foreign_key` 元组语法。

> 💡 **AI提示词示例**: "如何在复合主键模型上定义 BelongsTo？foreign_key 元组需要包含所有 PK 列吗？"

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
## 异步关系

当使用 `AsyncActiveRecord` 时，需要使用对应的异步关系描述符：

| 同步关系 | 异步关系 | 用途 |
|---------|---------|------|
| `HasOne` | `AsyncHasOne` | 一对一 |
| `HasMany` | `AsyncHasMany` | 一对多 |
| `BelongsTo` | `AsyncBelongsTo` | 多对一/反向 |

### 定义异步关系

```python
from typing import ClassVar
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.relation import AsyncHasMany, AsyncBelongsTo

class AsyncUser(AsyncActiveRecord):
    username: str
    
    # 异步一对多关系
    posts: ClassVar[AsyncHasMany['AsyncPost']] = AsyncHasMany(
        foreign_key='user_id', 
        inverse_of='author'
    )

class AsyncPost(AsyncActiveRecord):
    title: str
    user_id: int
    
    # 异步反向关系
    author: ClassVar[AsyncBelongsTo['AsyncUser']] = AsyncBelongsTo(
        foreign_key='user_id', 
        inverse_of='posts'
    )
```

### 访问异步关系

异步关系的访问需要使用 `await`：

```python
# 获取用户的所有文章
user = await AsyncUser.find_one(1)
posts = await user.posts()  # 注意：需要 await

# 预加载异步关系
users = await AsyncUser.query().with_("posts").all()
```

> 💡 **AI提示词示例**: "同步和异步模型的关系定义有什么区别？如何正确使用异步关系？"

### 禁止同步/异步描述符混用

同步描述符（`BelongsTo`、`HasOne`、`HasMany`）只能用于 `ActiveRecord` 模型，异步描述符（`AsyncBelongsTo`、`AsyncHasOne`、`AsyncHasMany`）只能用于 `AsyncActiveRecord` 模型。混用会在类创建时抛出 `TypeError`。

```python
# ❌ 错误：同步描述符用于异步模型 → TypeError
class AsyncUser(AsyncActiveRecord):
    username: str
    # 抛出 TypeError: Sync relation descriptor `posts` cannot be used on async model `AsyncUser`
    posts: ClassVar[HasMany['AsyncPost']] = HasMany(foreign_key='user_id', inverse_of='user')

# ❌ 错误：异步描述符用于同步模型 → TypeError
class User(ActiveRecord):
    username: str
    # 抛出 TypeError: Async relation descriptor `posts` cannot be used on sync model `User`
    posts: ClassVar[AsyncHasMany['Post']] = AsyncHasMany(foreign_key='user_id', inverse_of='user')

# ✅ 正确：同步描述符用于同步模型
class User(ActiveRecord):
    username: str
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='user')

# ✅ 正确：异步描述符用于异步模型
class AsyncUser(AsyncActiveRecord):
    username: str
    posts: ClassVar[AsyncHasMany['AsyncPost']] = AsyncHasMany(foreign_key='user_id', inverse_of='user')
```

> 💡 **AI提示词示例**: "同步和异步描述符混用会怎样？如何避免关系定义的类型错误？"

## inverse_of 参数说明

`inverse_of` 参数用于指定双向关系的另一端名称。正确设置这个参数可以：

1. **验证关系一致性**：框架会检查双向关系是否正确对应
2. **优化预加载**：帮助 ORM 正确关联预加载的数据

**常见错误**：

- 如果 `inverse_of` 指定的关系名不存在，会抛出验证错误
- 如果双向关系的 `inverse_of` 不匹配，可能导致预加载数据无法正确关联

> 💡 **AI提示词示例**: "inverse_of 参数有什么作用？如果设置错误会有什么后果？如何调试关系定义问题？"

## 类型解析与前向引用

关系描述符支持**字符串前向引用**，允许在定义时引用尚未定义的模型类。类型解析机制在类创建时自动完成：

```python
# 前向引用：Post 类在之后才定义
class User(ActiveRecord):
    username: str
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')

class Post(ActiveRecord):
    title: str
    user_id: int
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')
```

从 v1.0.0.dev28 开始，类型解析已集中到 `type_resolver` 模块，统一处理以下场景：

- **`__set_name__` 中的 Python < 3.12 兼容性**：`RuntimeError` 自动解包，确保在 Python 3.8–3.11 上正常工作。
- **方法内定义的模型类**：支持在函数或方法内部定义模型类时正确解析前向引用。
- **描述符兼容性校验**：同步/异步描述符混用检测从 `__set_name__` 提升到元类，失败时在类创建瞬间抛出 `TypeError`。
