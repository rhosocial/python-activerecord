# 基础关系 (1:1, 1:N)

`rhosocial-activerecord` 使用三个核心描述符：`BelongsTo`, `HasOne`, `HasMany`。

## 一对一 (One-to-One): User 与 Profile

每个用户有一个资料页。

```python
from typing import ClassVar
from rhosocial.activerecord.relation import HasOne, BelongsTo

class User(ActiveRecord):
    # User 拥有一个 Profile
    # foreign_key='user_id' 指的是 Profile 表中的字段
    profile: ClassVar[HasOne['Profile']] = HasOne(foreign_key='user_id', inverse_of='user')

class Profile(ActiveRecord):
    user_id: str  # 外键字段实际存在于此
    
    # Profile 属于一个 User
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='profile')
```

## 一对多 (One-to-Many): User 与 Post

一个用户可以发布多篇文章。

```python
from rhosocial.activerecord.relation import HasMany

class User(ActiveRecord):
    # User 拥有多个 Post
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')

class Post(ActiveRecord):
    user_id: str
    
    # Post 属于一个 User (作者)
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')
```

> **注意**: 所有的关系描述符必须声明为 `ClassVar`，以避免干扰 Pydantic 的字段验证。
