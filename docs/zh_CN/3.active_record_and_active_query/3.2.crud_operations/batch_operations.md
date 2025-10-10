# 批量操作

> **❌ 未实现**：本文档中描述的批量操作功能**未实现**。此文档描述了计划中的功能，仅用于未来参考。当前用户应仅依赖单个记录操作。此功能可能会在未来版本中开发，但没有保证的时间表。本文档中描述的API可能与实际实现有显著差异。

> **⚠️ 非实现文档**：这些内容是关于rhosocial ActiveRecord中批量操作的计划功能，允许您一次高效地对多条记录执行操作。**此功能当前不可用。**

本文档涵盖了rhosocial ActiveRecord中的批量操作，这些操作允许您一次高效地对多条记录执行操作。

## 批量创建

当您需要一次插入多条记录时，批量创建可以通过减少数据库查询次数显著提高性能。

### 创建多条记录

```python
# 准备多个用户记录
users = [
    User(username="user1", email="user1@example.com"),
    User(username="user2", email="user2@example.com"),
    User(username="user3", email="user3@example.com")
]

# 在单个批量操作中插入所有记录
User.batch_insert(users)

# 批量插入后，每个模型实例都会设置其主键
for user in users:
    print(f"用户 {user.username} 的ID为: {user.id}")
```

### 使用字典进行批量创建

您也可以使用字典进行批量创建：

```python
user_data = [
    {"username": "user4", "email": "user4@example.com"},
    {"username": "user5", "email": "user5@example.com"},
    {"username": "user6", "email": "user6@example.com"}
]

# 从字典插入所有记录
User.batch_insert_from_dicts(user_data)
```

### 批量创建中的验证

默认情况下，批量创建过程中会对每条记录进行验证。如果需要，您可以跳过验证：

```python
# 在批量插入过程中跳过验证
User.batch_insert(users, validate=False)
```

### 性能考虑

- 对于大型数据集，批量操作比单独插入要快得多
- 处理非常大的集合时，请考虑内存使用情况
- 对于极大的数据集，考虑将数据分成更小的批次处理

```python
# 将大型数据集分成每批1000条记录处理
chunk_size = 1000
for i in range(0, len(large_dataset), chunk_size):
    chunk = large_dataset[i:i+chunk_size]
    User.batch_insert(chunk)
```

## 批量更新

批量更新允许您通过单个查询更新多条记录。

### 使用相同值更新多条记录

```python
# 将所有状态为'inactive'的用户更新为'archived'
affected_rows = User.query()\
    .where({"status": "inactive"})\
    .update({"status": "archived"})

print(f"已更新{affected_rows}条记录")
```

### 条件批量更新

您可以使用更复杂的条件进行批量更新：

```python
# 更新所有30天内未登录的用户
from datetime import datetime, timedelta
inactive_date = datetime.now() - timedelta(days=30)

affected_rows = User.query()\
    .where("last_login < ?", inactive_date)\
    .update({"status": "inactive"})
```

### 使用表达式更新

您可以使用表达式基于现有值更新值：

```python
# 为所有活跃用户增加登录次数
from rhosocial.activerecord.query.expression import Expression

User.query()\
    .where({"status": "active"})\
    .update({"login_count": Expression("login_count + 1")})
```

## 批量删除

批量删除允许您通过单个查询删除多条记录。

### 删除多条记录

```python
# 删除所有状态为'temporary'的用户
affected_rows = User.query()\
    .where({"status": "temporary"})\
    .delete()

print(f"已删除{affected_rows}条记录")
```

### 条件批量删除

您可以使用复杂条件进行批量删除：

```python
# 删除所有创建时间超过一年的不活跃用户
old_date = datetime.now() - timedelta(days=365)

affected_rows = User.query()\
    .where({"status": "inactive"})\
    .where("created_at < ?", old_date)\
    .delete()
```

### 批量操作中的软删除

如果您的模型使用了`SoftDeleteMixin`，批量删除将标记记录为已删除，而不是将其移除：

```python
# 将所有不活跃用户标记为已删除
User.query()\
    .where({"status": "inactive"})\
    .delete()  # 记录被软删除

# 即使使用SoftDeleteMixin也强制实际删除
User.query()\
    .where({"status": "inactive"})\
    .hard_delete()  # 记录被永久移除
```

## 优化批量操作

### 在事务中使用批量操作

将批量操作包装在事务中可以提高性能并确保原子性：

```python
from rhosocial.activerecord.backend.transaction import Transaction

# 在单个事务中执行多个批量操作
with Transaction():
    # 删除旧记录
    User.query().where("created_at < ?", old_date).delete()
    
    # 更新现有记录
    User.query().where({"status": "trial"}).update({"status": "active"})
    
    # 插入新记录
    User.batch_insert(new_users)
```

### 禁用触发器和约束

对于非常大的批量操作，您可能考虑临时禁用触发器或约束：

```python
# 为大型批量操作禁用触发器的示例
# （实现取决于特定的数据库后端）
from rhosocial.activerecord.backend import get_connection

conn = get_connection()
with conn.cursor() as cursor:
    # 禁用触发器（PostgreSQL示例）
    cursor.execute("ALTER TABLE users DISABLE TRIGGER ALL")
    
    try:
        # 执行批量操作
        User.batch_insert(huge_dataset)
    finally:
        # 重新启用触发器
        cursor.execute("ALTER TABLE users ENABLE TRIGGER ALL")
```

## 总结

rhosocial ActiveRecord中的批量操作提供了高效的方式来对多条记录执行操作。通过使用这些功能，您可以在处理大型数据集时显著提高应用程序的性能。