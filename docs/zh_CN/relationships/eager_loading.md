# 预加载详解 (Eager Loading Deep Dive)

预加载通过 `with_()` 方法在主查询中一并加载关联数据，是解决 N+1 查询问题的标准方案。

本文是 `with_()` 的完整参考文档，涵盖嵌套路径、查询修饰器、参数展开与覆盖规则、路径验证以及底层加载机制。加载策略的整体对比见[加载策略](loading.md)。

## 基本用法

```python
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(ActiveRecord):
    __table_name__ = "users"
    id: int
    name: str

    posts: ClassVar = HasMany('Post', inverse_of='user')

class Post(ActiveRecord):
    __table_name__ = "posts"
    id: int
    title: str
    user_id: int

    user: ClassVar = BelongsTo('User', inverse_of='posts')

# 预加载所有用户的 posts
users = User.query().with_("posts").all()
for user in users:
    # 不会触发额外查询 — 数据已在缓存中
    posts = user.posts()
    print(f"{user.name}: {len(posts)} 篇文章")
```

`with_()` 接受**可变参数**，每个参数既可以是普通字符串路径，也可以是 `(路径, 修饰器)` 元组：

| 参数形式 | 说明 | 示例 |
|----------|------|------|
| `str` | 简单关系路径 | `with_('posts')`、`with_('posts.comments')` |
| `tuple` | 路径 + 查询修饰器 | `with_(('posts', modifier))` |

## 加载多个关联

可以一次性预加载多个关系，也可以多次调用 `with_()` 链式追加：

```python
# 一次传入多个参数
users = User.query().with_("profile", "posts", "roles").all()

# 链式调用（等价）
users = User.query().with_("profile").with_("posts").with_("roles").all()
```

## 嵌套预加载

使用点号（`.`）语法预加载深层关联。每个中间关系都会单独配置并逐层批量加载：

```python
users = User.query().with_("posts.comments").all()
for user in users:
    for post in user.posts():
        # post.comments() 也不会触发额外查询
        print(f"  {post.title}: {len(post.comments())} 条评论")
```

嵌套深度没有硬性限制，`with_("user.orders.items.detail")` 这样的路径会被拆解为 4 个层级依次加载。

## 查询修饰器 (Query Modifiers)

对预加载的关联进行过滤、排序或限制数量：

```python
users = User.query().with_(
    ("posts", lambda q: q.where(Post.c.published == True).order_by(Post.c.created_at.desc()))
).all()
```

修饰器接收一个 `ActiveQuery` 对象 `q`，返回修改后的查询对象，可以链式调用 `.where()`、`.order_by()`、`.limit()` 等方法。

### 复杂修饰器推荐具名函数

复杂修饰器建议使用具名函数而非 lambda。当修饰器被**覆盖**时，框架会记录 WARNING 日志，具名函数会显示完整的 `模块.函数名`，便于调试；lambda 则显示为 `<lambda>`：

```python
def filter_published(q):
    return q.where(Post.c.status == 'published')

users = User.query().with_(('posts', filter_published)).all()
```

## 参数展开规则

**修饰器只作用于目标关系（路径的最后一环）**，中间关系不会被修饰器过滤。例如：

```python
users = User.query().with_(("posts.comments", lambda q: q.where(...))).all()
```

该参数展开为两条配置：

```
'posts'           -> 修饰器: None   （中间关系，不应用修饰器）
'posts.comments'  -> 修饰器: func   （目标关系，应用修饰器）
```

## 覆盖规则与顺序

`with_()` 遵循「**后出现的参数优先**」的规则（Yii2 行为）：

```python
# m1 生效（正确顺序：长路径在前，短路径在后）
users = User.query().with_(
    ('posts.comments.user', m2),
    ('posts.comments', m1),
)

# m2 会覆盖 m1（m1 丢失）
users = User.query().with_(
    ('posts.comments', m1),
    ('posts.comments.user', m2),
)
```

展开时，后一个参数会覆盖前一个参数对**同一路径**的配置，包括嵌套关系和修饰器：

```python
# ('posts.comments', m1) + ('posts.comments.user', m2) 的结果：
# 'posts'              -> 修饰器: None  （由第 2 个参数写入，覆盖）
# 'posts.comments'     -> 修饰器: m2    （由第 2 个参数覆盖 m1）
# 'posts.comments.user' -> 修饰器: m2
```

> **规则**：如果不想让某个修饰器被覆盖，请把它放在参数列表**靠后**的位置。

## 路径验证

`with_()` 在配置任何加载之前**先验证全部路径**，验证失败则抛出异常且**不应用任何配置**（事务性行为）。

### 语法验证

格式非法的路径会抛出 `InvalidRelationPathError`：

| 非法情形 | 示例 |
|----------|------|
| 空字符串 | `""` |
| 前导点 | `".posts"` |
| 尾随点 | `"posts."` |
| 连续点 | `"posts..comments"` |

### 语义验证

路径中每一环关系都必须存在于对应模型上，否则抛出 `RelationNotFoundError`。例如 `with_('posts.comments')` 会依次校验：

1. `posts` 关系存在于 `User` 模型
2. 解析 `posts` 的关联模型（`Post`）
3. `comments` 关系存在于 `Post` 模型

```python
from rhosocial.activerecord.query.relational import InvalidRelationPathError, RelationNotFoundError

try:
    users = User.query().with_("posts.nonexistent").all()
except RelationNotFoundError as e:
    print(f"关系不存在: {e}")
```

## 加载机制

理解底层机制有助于预测查询次数与性能。

### 批量加载 (Batch Load)

主查询执行后，框架对每条配置路径执行**一次批量查询**，而不是为每个对象单独查询：

- **BelongsTo**：收集所有对象的外键值 → 用 `IN` 谓词查询关联模型 → 按主键映射回各对象
- **HasOne / HasMany**：收集所有对象的主键值 → 用 `IN` 谓词查询关联表（外键 IN 主键）→ 按外键分组；`HasOne` 取单个，`HasMany` 取列表
- **复合主键**：以元组形式收集/匹配主键与外键组合

```python
orders = Order.query().with_('user').all()
# 无论多少条订单，user 关系只执行 1 次 IN 查询
```

嵌套路径在每层递归执行一次批量查询。

### 缓存优先

批量加载结果写入实例级缓存（`InstanceCache`，默认 TTL 300 秒、容量 1000）。再次访问同一关系（包括后续通过 `user.posts()` 延迟访问）时优先读缓存，不触发查询。

> 使用 `clear_relation_cache()` 可清除实例上的关系缓存；批量更新实例后如需强制重新加载，也应先清除缓存。

### 返回类型语义

| 关系类型 | 返回值 |
|----------|--------|
| `BelongsTo` / `HasOne` | 单个关联实例，或无匹配时返回 `None` |
| `HasMany` | 关联实例列表，无匹配时返回空列表 `[]` |

## 异步用法

异步模型使用 `AsyncRelationalQueryMixin`，API 与同步完全一致：

```python
async_users = await AsyncUser.query().with_("posts").all()
for user in async_users:
    posts = await user.posts()  # 不触发额外查询
```

## 性能建议

| 场景 | 策略 |
|------|------|
| 确定需要大部分关联数据 | 使用 `with_()` 预加载 |
| 只需要少量对象的关联 | 使用延迟加载（默认） |
| 需要过滤关联数据 | 使用修饰器参数 |
| 循环中访问关联 | 必须预加载，避免 N+1 |
| 深层嵌套（超过 3 层） | 考虑是否拆分为多次查询 |