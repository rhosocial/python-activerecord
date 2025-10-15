# 创建、读取、更新、删除操作

本文档涵盖了rhosocial ActiveRecord中的基本CRUD（创建、读取、更新、删除）操作。这些操作构成了应用程序中数据库交互的基础。

## 创建记录

rhosocial ActiveRecord提供了几种创建新记录的方法：

### 方法1：实例化并保存

最常见的方法是创建模型的实例，然后调用`save()`方法：

```python
# 创建新用户
user = User(username="johndoe", email="john@example.com", age=30)
user.save()  # 将记录插入数据库

# 保存后主键会自动设置
print(user.id)  # 输出新ID
```

### 方法2：从字典创建

您也可以从属性字典创建模型实例：

```python
user_data = {
    "username": "janedoe",
    "email": "jane@example.com",
    "age": 28
}
user = User(**user_data)
user.save()
```

### 创建过程中的验证

当您保存记录时，验证会自动进行。如果验证失败，会抛出`DBValidationError`异常：

```python
try:
    user = User(username="a", email="invalid-email")
    user.save()
except DBValidationError as e:
    print(f"验证失败：{e}")
```

### 生命周期事件

在创建过程中，会触发几个您可以挂钩的事件：

- `BEFORE_VALIDATE`：在执行验证前触发
- `AFTER_VALIDATE`：在验证成功后触发
- `BEFORE_SAVE`：在保存操作前触发
- `AFTER_SAVE`：在保存操作后触发
- `AFTER_INSERT`：在插入新记录后触发

## 读取记录

rhosocial ActiveRecord提供了多种查询记录的方法：

### 通过主键查找

最常见的查询是通过主键查找单个记录：

```python
# 通过ID查找用户
user = User.find_one(1)  # 返回ID为1的用户或None

# 如果记录不存在则抛出异常
try:
    user = User.find_one_or_fail(999)  # 如果ID为999的用户不存在，抛出RecordNotFound异常
except RecordNotFound:
    print("用户不存在")
```

### 使用条件查询

您可以使用条件查询来查找记录：

```python
# 通过条件查找单个记录
user = User.find_one(1)  # 通过主键查找

# 查找所有记录
all_users = User.find_all()
```

### 使用ActiveQuery进行高级查询

对于更复杂的查询，您可以使用ActiveQuery：

```python
# 查找年龄大于25的活跃用户，按创建时间排序
users = User.query()\
    .where("status = ?", ("active",))\
    .where("age > ?", (25,))\
    .order_by("created_at DESC")\
    .all()
```

### 使用OR条件查询

当您需要使用OR逻辑连接多个条件时，可以使用`or_where`方法：

```python
# 查找状态为活跃或VIP的用户
users = User.query()\
    .where("status = ?", ("active",))\
    .or_where("status = ?", ("vip",))\
    .all()
# 等同于: SELECT * FROM users WHERE status = 'active' OR status = 'vip'

# 组合AND和OR条件
users = User.query()\
    .where("status = ?", ("active",))\
    .where("age > ?", (25,))\
    .or_where("vip_level > ?", (0,))\
    .all()
# 等同于: SELECT * FROM users WHERE (status = 'active' AND age > 25) OR vip_level > 0
```

您还可以使用条件组来创建更复杂的逻辑组合：

```python
# 使用条件组创建复杂查询
users = User.query()\
    .where("status = ?", ("active",))\
    .start_or_group()\
    .where("age > ?", (25,))\
    .or_where("vip_level > ?", (0,))\
    .end_or_group()\
    .all()
# 等同于: SELECT * FROM users WHERE status = 'active' AND (age > 25 OR vip_level > 0)
```

> **注意**：查询条件必须使用SQL表达式和参数占位符，不支持直接传入字典。参数值必须以元组形式传递，即使只有一个参数也需要加逗号：`(value,)`。

## 更新记录

### 更新单个记录

要更新现有记录，首先获取记录，修改其属性，然后保存：

```python
# 查找并更新用户
user = User.find_one(1)
if user:
    user.email = "newemail@example.com"
    user.age += 1
    user.save()  # 更新数据库中的记录
```

### 批量更新

> **❌ 未实现**：批量更新功能未实现。这是计划中的功能，仅用于未来参考。当前用户应单独更新记录。此功能可能会在未来版本中开发，但没有保证的时间表。

理论上，批量更新将允许您使用查询构建器一次更新多条记录：

```python
# 将所有不活跃用户的状态更新为已归档（示例代码，目前不可用）
affected_rows = User.query()\
    .where("status = ?", ("inactive",))\
    .update({"status": "archived"})

print(f"已更新{affected_rows}条记录")
```

### 更新过程中的生命周期事件

更新过程中会触发以下事件：

- `BEFORE_VALIDATE`：在执行验证前触发
- `AFTER_VALIDATE`：在验证成功后触发
- `BEFORE_SAVE`：在保存操作前触发
- `AFTER_SAVE`：在保存操作后触发
- `AFTER_UPDATE`：在更新现有记录后触发

## 删除记录

### 删除单个记录

要删除记录，首先获取记录，然后调用`delete()`方法：

```python
# 查找并删除用户
user = User.find_one(1)
if user:
    affected_rows = user.delete()  # 从数据库中删除记录
    print(f"已删除{affected_rows}条记录")
```

### 批量删除

对于批量删除，可以使用查询构建器：

```python
# 删除所有不活跃用户
affected_rows = User.query()\
    .where({"status": "inactive"})\
    .delete()

print(f"已删除{affected_rows}条记录")
```

### 软删除

如果您的模型使用了`SoftDeleteMixin`，`delete()`方法不会真正从数据库中删除记录，而是将其标记为已删除：

```python
# 对于使用SoftDeleteMixin的模型
user = User.find_one(1)
user.delete()  # 标记为已删除，但记录仍保留在数据库中

# 默认查询会排除已删除的记录
active_users = User.find_all()  # 只返回未删除的记录

# 包括已删除的记录
all_users = User.query().with_deleted().all()

# 只查询已删除的记录
deleted_users = User.query().only_deleted().all()
```

> **重要**：即使记录被删除后，实例对象依然存在于内存中，您仍然可以修改其属性并调用`save()`方法将其恢复或更新到数据库。对于软删除的记录，这将自动恢复记录；对于硬删除的记录，这将创建一个具有相同属性的新记录（可能具有新的主键）。

### 删除过程中的生命周期事件

删除过程中会触发以下事件：

- `BEFORE_DELETE`：在删除操作前触发
- `AFTER_DELETE`：在删除操作后触发

## 刷新记录

如果您需要从数据库重新加载记录的最新状态，可以使用`refresh()`方法：

```python
user = User.find_one(1)
# ... 其他代码可能修改了数据库中的记录 ...
user.refresh()  # 从数据库重新加载记录
```

## 检查记录状态

ActiveRecord提供了几个有用的属性来检查记录的状态：

```python
user = User.find_one(1)

# 检查是否为新记录（尚未保存到数据库）
if user.is_new_record:
    print("这是一个新记录")

# 检查记录是否已被修改
user.email = "changed@example.com"
if user.is_dirty:
    print("记录已被修改")
    print(f"已修改的属性: {user.dirty_attributes}")
```

## 总结

rhosocial ActiveRecord提供了直观且强大的API来执行CRUD操作。通过这些基本操作，您可以轻松地与数据库交互，同时利用生命周期事件和验证来确保数据的完整性和一致性。