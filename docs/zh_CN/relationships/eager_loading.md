# 预加载 (Eager Loading)

预加载通过 `with_()` 方法在主查询中一并加载关联数据，是解决 N+1 查询问题的标准方案。

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

## 嵌套预加载

使用点号（`.`）语法预加载深层关联：

```python
users = User.query().with_("posts.comments").all()
for user in users:
    for post in user.posts():
        # post.comments() 也不会触发额外查询
        print(f"  {post.title}: {len(post.comments())} 条评论")
```

## 带修饰器的预加载

对预加载的关联进行过滤或排序：

```python
users = User.query().with_(
    ("posts", lambda q: q.where(Post.c.published == True).order_by(Post.c.created_at.desc()))
).all()
```

修饰器接受查询对象 `q`（`ActiveQuery`），可以链式调用 `.where()`、`.order_by()`、`.limit()` 等方法。

## 预加载多个关联

```python
# 同时预加载多个关系
users = User.query().with_("profile").with_("posts").with_("roles").all()

# 也可在一个 with_ 中传入多个参数（如果支持）
users = User.query().with_("profile", "posts", "roles").all()
```

## 异步用法

异步模型使用 `AsyncRelationalQueryMixin`，API 与同步完全一致：

```python
async_users = await AsyncUser.query().with_("posts").all()
for user in async_users:
    posts = await user.posts()  # 不触发额外查询
```

## 路径验证

`with_()` 会自动验证关联路径的有效性。如果指定的关系不存在，会抛出异常：

```python
from rhosocial.activerecord.query.relational import RelationNotFoundError

try:
    users = User.query().with_("nonexistent_relation").all()
except RelationNotFoundError as e:
    print(f"关系不存在: {e}")
```

## 参数展开规则

当参数中包含嵌套路径时，系统会自动展开：

```python
# 自动展开为：
# - 'posts' -> None（posts 本身，无修饰器）
# - 'posts.comments' -> modifier（posts 下的 comments，附带修饰器）
users = User.query().with_(("posts.comments", lambda q: q.where(...))).all()
```

## 性能建议

| 场景 | 策略 |
|------|------|
| 确定需要大部分关联数据 | 使用 `with_()` 预加载 |
| 只需要少量对象的关联 | 使用延迟加载（默认） |
| 需要过滤关联数据 | 使用修饰器参数 |
| 深层嵌套（超过 3 层） | 考虑是否拆分为多次查询 |
