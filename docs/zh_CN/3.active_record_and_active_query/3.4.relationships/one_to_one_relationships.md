# 一对一关系

一对一关系表示两个模型之间的连接，其中第一个模型中的每条记录恰好与第二个模型中的一条记录相关联，反之亦然。在rhosocial ActiveRecord中，一对一关系可以使用`HasOne`或`BelongsTo`描述符实现，具体取决于哪个模型持有外键。

## 一对一关系的类型

在rhosocial ActiveRecord中实现一对一关系有两种方式：

1. **HasOne**：当关联模型包含外键时使用
2. **BelongsTo**：当当前模型包含外键时使用

## HasOne关系

`HasOne`关系表示另一个模型包含引用当前模型的外键。例如，用户有一个个人资料：

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasOne

class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    
    id: Optional[int] = None
    username: str
    email: str
    
    # 定义与Profile模型的关系
    profile: ClassVar[HasOne['Profile']] = HasOne(
        foreign_key='user_id',  # Profile模型中的外键字段
        inverse_of='user'       # Profile模型中对应的关系名
    )
```

## BelongsTo关系

`BelongsTo`关系表示当前模型包含引用另一个模型的外键。例如，个人资料属于用户：

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import BelongsTo

class Profile(IntegerPKMixin, ActiveRecord):
    __table_name__ = "profiles"
    
    id: Optional[int] = None
    user_id: int  # 外键
    bio: str
    avatar_url: str
    
    # 定义与User模型的关系
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',  # 当前模型中的外键字段
        inverse_of='profile'    # User模型中对应的关系名
    )
```

## 使用一对一关系

### 访问关联记录

一旦定义了一对一关系，您可以像访问模型实例的属性一样访问关联记录：

```python
# 获取用户
user = User.find_one(1)

# 访问用户的个人资料
profile = user.profile()

# 访问个人资料的用户
profile = Profile.find_one(1)
user = profile.user()
```

### 创建关联记录

要创建关联记录，首先需要创建父记录，然后创建具有适当外键的关联记录：

```python
# 创建用户
user = User(username="john_doe", email="john@example.com")
user.save()

# 为用户创建个人资料
profile = Profile(user_id=user.id, bio="Python开发者", avatar_url="/avatars/john.jpg")
profile.save()
```

## 预加载

为了在访问关联记录时优化性能，您可以使用预加载在同一查询中加载关联记录：

```python
# 查询用户时预加载个人资料
user = User.query().with_("profile").find_one(1)

# 现在访问个人资料不会触发额外的查询
profile = user.profile()
```

## 反向关系

当您在关系定义中设置`inverse_of`参数时，会自动设置反向关系。这确保了关系在两个方向上都正确链接。

## 级联操作

默认情况下，rhosocial ActiveRecord不会自动将删除操作级联到关联记录。如果您希望在删除父记录时删除关联记录，需要手动实现此行为：

```python
class User(IntegerPKMixin, ActiveRecord):
    # ... 其他代码 ...
    
    def before_delete(self) -> None:
        # 当用户被删除时删除用户的个人资料
        profile = self.profile()
        if profile:
            profile.delete()
        super().before_delete()
```

## 最佳实践

1. **始终定义反向关系**：这有助于维护数据完整性并启用双向导航。
2. **使用有意义的关系名称**：选择能清楚表明关系目的的名称。
3. **考虑使用事务**：在创建或更新关联记录时，使用事务确保数据一致性。
4. **使用预加载**：当您知道需要关联记录时，使用预加载减少数据库查询次数。
5. **验证外键**：确保外键引用有效记录以维护数据完整性。

## 常见问题及解决方案

### 循环依赖

在定义具有相互关系的模型时，可能会遇到循环导入依赖。要解决此问题，请使用基于字符串的前向引用：

```python
from typing import ClassVar, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .profile import Profile

class User(IntegerPKMixin, ActiveRecord):
    # ... 其他代码 ...
    
    profile: ClassVar[HasOne['Profile']] = HasOne(
        foreign_key='user_id',
        inverse_of='user'
    )
```

### N+1查询问题

N+1查询问题发生在加载记录列表然后为每条记录访问关联记录时，导致N+1次数据库查询。要避免这种情况，请使用预加载：

```python
# 不好：N+1次查询
users = User.find_all()
for user in users:
    profile = user.profile()  # 为每个用户触发单独的查询

# 好：2次查询
users = User.query().with_("profile").find_all()
for user in users:
    profile = user.profile()  # 使用已加载的数据，无额外查询
```

## 结论

rhosocial ActiveRecord中的一对一关系提供了一种强大的方式来模型化相关实体之间的连接。通过理解`HasOne`和`BelongsTo`关系之间的区别，并遵循关系定义和使用的最佳实践，您可以为应用程序构建高效且可维护的数据模型。