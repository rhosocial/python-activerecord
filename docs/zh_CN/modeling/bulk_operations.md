# 模型层批量操作

除了后端底层的批量 DML/DQL 接口，本库还在模型（ActiveRecord）层面提供了高级批量操作 API，包括 `bulk_create`、`bulk_update` 和 `bulk_delete`。这些方法在单个 SQL 语句中处理多条记录，同时保留模型层的验证（validation）、事件（event）和自动填充（如主键、时间戳）功能。

## 前置条件

要使用批量操作，模型需要混入 `BulkOperationsMixin`（同步）或 `AsyncBulkOperationsMixin`（异步）：

```python
from typing import List
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base.bulk_operations import BulkOperationsMixin

class User(BulkOperationsMixin, ActiveRecord):
    __table_name__ = "users"
    id: int
    name: str
    email: str
```

## 批量创建 (`bulk_create`)

一次性插入多条记录，自动填充主键和触发事件。

```python
users = [
    User(name="Alice", email="alice@example.com"),
    User(name="Bob", email="bob@example.com"),
    User(name="Charlie", email="charlie@example.com"),
]

created = User.bulk_create(users, batch_size=50)
print(f"成功创建 {len(created)} 条记录")
for user in created:
    print(f"  ID: {user.id}, Name: {user.name}")
```

> **提示**：`batch_size` 参数控制每批处理多少条记录。未指定时使用默认值。

## 批量更新 (`bulk_update`)

批量更新指定字段，使用 `CASE WHEN` 模式在单条 SQL 中完成更新。

```python
# 修改一些用户数据
users = User.find_all().all()[:5]
for i, user in enumerate(users):
    user.name = f"Updated_{i}"

# 批量更新 name 字段
updated = User.bulk_update(users, fields=["name"])
print(f"成功更新 {len(updated)} 条记录")
```

> **注意**：必须指定 `fields` 参数，明确需要更新的字段列表。该方法不会自动检测脏字段。

## 批量删除 (`bulk_delete`)

批量删除记录，支持软删除（软删除模型会自动调用 `prepare_delete`）。

```python
# 删除所有测试用户
admin_users = User.query().where(User.c.role == "admin").all()
deleted_count = User.bulk_delete(admin_users)
print(f"成功删除 {deleted_count} 条管理员记录")
```

## 事务行为

所有批量操作默认在事务中执行。如果某个批次失败，整个操作将回滚（`WHOLE` 提交模式）。

```python
from rhosocial.activerecord.backend.result import BatchCommitMode

# 每批次独立提交
User.bulk_create(users, batch_size=20, commit_mode=BatchCommitMode.PER_BATCH)
```

## 异步支持

异步版本的 API 签名与同步完全一致，仅需 `await`：

```python
from rhosocial.activerecord.base.bulk_operations import AsyncBulkOperationsMixin

class AsyncUser(AsyncBulkOperationsMixin, ActiveRecord):
    __table_name__ = "users"
    id: int
    name: str
    email: str

async def create_users_async():
    users = [
        AsyncUser(name="Alice", email="alice@example.com"),
        AsyncUser(name="Bob", email="bob@example.com"),
    ]
    created = await AsyncUser.bulk_create(users)
    return created
```

## 错误处理

| 异常类型 | 说明 |
|---------|------|
| `BulkStateError` | 记录状态不合法（如尝试创建已有 ID 的记录，或更新/删除未持久化的记录） |
| `BulkValidationError` | 记录未通过模型验证 |

```python
from rhosocial.activerecord.base.bulk_operations import BulkStateError, BulkValidationError

try:
    User.bulk_create(invalid_users)
except BulkValidationError as e:
    print(f"验证失败: {e}")
except BulkStateError as e:
    print(f"状态错误: {e}")
```

## 与后端批量操作的区别

本库提供**两层**批量操作接口，各有侧重：

| 层面 | API | 特点 |
|------|-----|------|
| **模型层**（Model） | `bulk_create` / `bulk_update` / `bulk_delete` | 支持验证、事件、字段映射，面向 ActiveRecord 实例 |
| **后端层**（Backend） | `execute_batch_dml` / `execute_batch_dql` | 直接操作 SQL 表达式，更高的灵活性和性能，面向表达式构建 |

> 后端层批量操作的详细说明见 [性能与优化 - 批量操作](../performance/batch_operations.md)。
