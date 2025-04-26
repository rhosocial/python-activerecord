# 第一个模型示例

本指南将引导您创建第一个ActiveRecord模型并执行基本的数据库操作。

## 定义您的第一个模型

在rhosocial ActiveRecord中，模型是继承自`ActiveRecord`的Python类，它们定义了数据库表的结构。

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.typing import ConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from datetime import datetime
from typing import Optional

# 定义一个User模型
class User(ActiveRecord):
    __table_name__ = 'users'  # 指定表名
    
    # 使用类型注解定义字段
    id: int                   # 主键
    name: str                 # 用户名
    email: str                # 用户邮箱
    created_at: datetime      # 创建时间戳
    updated_at: Optional[datetime] = None  # 最后更新时间戳

# 配置数据库连接
User.configure(
    ConnectionConfig(database='database.sqlite3'),
    backend_class=SQLiteBackend
)
```

### 模型的关键组成部分

- **类继承**：您的模型继承自`ActiveRecord`
- **表名**：`__table_name__`属性指定数据库表名
- **字段**：使用Python类型注解定义

## 使用数据库表

rhosocial ActiveRecord可以与与您的模型定义匹配的现有数据库表一起工作。目前，该框架不支持迁移功能，因此在使用模型之前，您需要使用SQL或其他数据库管理工具创建数据库表。

## 基本CRUD操作

现在您已经有了模型和表，可以执行创建（Create）、读取（Read）、更新（Update）和删除（Delete）操作。

### 创建记录

```python
# 创建一个新用户
user = User(
    name='张三',
    email='zhangsan@example.com',
    created_at=datetime.now()
    # 注意：不要指定自增主键（id）
    # 数据库会自动生成它
)

# 将用户保存到数据库
user.save()

# 保存后自动设置ID，并刷新模型实例
print(f"创建的用户ID：{user.id}")
```

### 读取记录

```python
# 通过主键查找用户
user = User.find_one(1)
if user:
    print(f"找到用户：{user.name}")

# 查询所有用户
# 注意：这与Query.find_all()效果相同，会返回所有记录而不进行任何筛选
# 对于大型数据集，请谨慎使用，因为它可能会导致性能问题
all_users = User.query().all()
for user in all_users:
    print(f"用户：{user.name}，邮箱：{user.email}")

# 带条件的查询
# 注意：最好使用能命中索引的条件以获得更好的性能
# 如果没有适当的索引，像LIKE这样的字符串搜索可能会很慢
zhang_users = User.query().where("name LIKE ?", "%张%").all()
for user in zhang_users:
    print(f"找到张姓用户：{user.name}")
```

### 更新记录

```python
# 查找并更新用户
user = User.find_one(1)
if user:
    user.name = "李四"  # 更新名称
    user.updated_at = datetime.now()  # 更新时间戳
    user.save()  # 将更改保存到数据库
    print(f"用户已更新：{user.name}")
```

### 删除记录

```python
# 查找并删除用户
user = User.find_one(1)
if user:
    user.delete()  # 从数据库中删除
    print("用户已删除")
    
    # 注意：删除后，实例仍然存在于内存中
    # 它变为一个新记录状态，属性已被清除
    # 您可以再次将其保存为具有不同ID的新记录
    user.name = "删除后的新用户"
    user.save()  # 这将创建一个具有新ID的新记录
    print(f"删除后创建的新用户ID：{user.id}")
```

> **重要提示**：当您使用`delete()`方法删除记录时，只有数据库中的记录被移除。实例对象仍然存在于内存中，并变为新记录状态。您可以修改其属性并调用`save()`方法将其作为新记录保存到数据库中，此时会获得一个新的自增主键值。

## 使用查询构建器

rhosocial ActiveRecord包含一个强大的查询构建器，用于更复杂的查询：

```python
# 复杂查询示例
recent_users = User.query()\
    .where("created_at > ?", datetime.now() - timedelta(days=7))\
    .order_by("created_at DESC")\
    .limit(10)\
    .all()

print(f"找到 {len(recent_users)} 个最近的用户")

# 计数查询
user_count = User.query().count()
print(f"总用户数：{user_count}")

# 使用参数化查询进行条件查询，防止SQL注入
young_users = User.query().where('age < ?', (22,)).all()
print(f"找到 {len(young_users)} 个年轻用户")
```

> **重要安全提示**：始终对所有用户输入使用带有占位符（`?`）的参数化查询，以防止SQL注入攻击。将实际值作为元组传递给`where()`方法的第二个参数。切勿将用户输入直接拼接到SQL字符串中。这对安全性至关重要，除非您能保证终端用户无法接触到原始查询语句。

## 事务

对于需要原子性的操作，使用事务：

```python
# 开始一个事务
with User.transaction():
    # 在单个事务中创建多个用户
    for i in range(5):
        user = User(
            name=f"用户 {i}",
            email=f"user{i}@example.com",
            created_at=datetime.now()
        )
        user.save()
    # 如果任何操作失败，所有更改都将回滚
```

## 完整示例

这是一个演示模型完整生命周期的示例：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend.typing import ConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from datetime import datetime
from typing import Optional

# 定义模型
class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int
    name: str
    email: str
    created_at: datetime
    updated_at: Optional[datetime] = None

# 配置数据库
User.configure(
    ConnectionConfig(database='example.sqlite3'),
    backend_class=SQLiteBackend
)

# 创建用户
user = User(
    name='张三',
    email='zhangsan@example.com',
    created_at=datetime.now()
)
user.save()
print(f"创建的用户ID：{user.id}")

# 查找并更新用户
found_user = User.find_one(user.id)
if found_user:
    found_user.name = "李四"
    found_user.updated_at = datetime.now()
    found_user.save()
    print(f"更新用户名为：{found_user.name}")

# 查询所有用户
all_users = User.query().all()
print(f"总用户数：{len(all_users)}")
for u in all_users:
    print(f"用户 {u.id}：{u.name}，{u.email}，创建时间：{u.created_at}")

# 删除用户
found_user.delete()
print("用户已删除")

# 验证删除
remaining = User.query().count()
print(f"剩余用户数：{remaining}")
```

## 下一步

现在您已经创建了第一个模型并执行了基本操作，请查看[常见问题解答](faq.md)了解常见问题和解决方案，或探索文档中更高级的主题。