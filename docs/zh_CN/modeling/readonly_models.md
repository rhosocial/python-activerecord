# 只读模型

有些关系永远不允许写入：查询跑在只读副本上、报表读取数据仓库、审计日志只允许追加。
`ReadOnlyMixin` 用来声明这一点，框架会在自己掌握的所有写入路径上强制执行。

> 💡 **AI 提示语：** "我需要一个连接分析数据库的模型类，如果有人不小心尝试写入就报错。该怎么做？"

---

## 1. 声明只读模型

把 `ReadOnlyMixin` 混入任意模型：

```python
from typing import Optional
from rhosocial.activerecord.field import ReadOnlyMixin
from rhosocial.activerecord.model import ActiveRecord

class UserAnalytics(ReadOnlyMixin, ActiveRecord):
    """users 表在分析副本上的只读视图。"""
    __table_name__ = "users"
    id: Optional[int] = None
    name: str
    email: str
```

声明到此为止。`__read_only__` 被置为 `True`，框架在准备任何 SQL 之前就拒绝写入：

```python
# ✅ 读取照常工作
analysts = UserAnalytics.query().where(UserAnalytics.c.name == "Alice").all()
count = UserAnalytics.query().count()

# ❌ 被拒绝——不会发出任何语句
UserAnalytics(name="Alice", email="alice@example.com").save()
# ReadOnlyError: save is not allowed on read-only model 'UserAnalytics'. ...
```

`ReadOnlyError` 是 `DatabaseError` 的子类，因此已有的 `except DatabaseError`
也能捕获它。

### 被拦截的范围

| 被拦截 | 可用 |
| --- | --- |
| `save()`、`delete()` | `query()`、`all()`、`one()`、`where()`、`order_by()`、`group_by()` |
| `bulk_create()`、`bulk_update()`、`bulk_delete()` | `count()`、`exists()`、`aggregate()`、`avg()`、`sum_()`、`max_()`、`min_()` |
| `update_all()`、`delete_all()` | `with_()` 预加载、关联、`find_all()` |

读取不受影响。模型自己声明的字段也不受影响——`ReadOnlyMixin` 只是*语义*，
与 `SoftDeleteMixin`、`TimestampMixin` 的约定一致。

### 退出这个门禁

设置 `__read_only__ = False` 即可写入：

```python
class Maintenance(ReadOnlyMixin, ActiveRecord):
    __table_name__ = "users"
    __read_only__ = False   # 逃生口，供确实需要写入的脚本使用
```

---

## 2. 为什么判断放在模型上

`ReadOnlyMixin` 实现了 `IReadOnlyBehavior`，它是 `interface/update.py` 中四个行为接口之一，
与 `IUpdateBehavior`、`IDeleteBehavior`、`IDataPreparationBehavior` 并列：

```python
class ReadOnlyMixin(IReadOnlyBehavior):
    __read_only__: ClassVar[bool] = True

    @classmethod
    def read_only(cls) -> bool:
        return bool(getattr(cls, "__read_only__", False))
```

框架询问 `read_only()` 并依据**返回值**行动，而不是依据类型：

```python
@classmethod
def refuse_read_only(cls, operation: str) -> None:
    read_only = getattr(cls, "read_only", None)
    if callable(read_only) and read_only():
        raise ReadOnlyError(cls.__name__, operation)
```

属于 `IReadOnlyBehavior` 只说明存在一个 `read_only` 方法——模型可以满足该接口却依然可写。
若改为判断类型，这些模型会被误拦，所以刻意不这样做。同样的理由让 `read_only()`
返回 `bool` 而不是 `None`：`None` 会诱导人用 `is None` 当类型判断。

**这个特性是可选的。** 没有混入该接口的模型连 `read_only()` 都不会回答，
因此既有行为完全不变——没有为不需要它的模型付出任何代价。

**一份实现同时服务同步与异步。** `read_only()` 是零 IO 的类方法，而 `field/` 的约定是
只有当方法会发出 SQL 时才需要异步版本（`SoftDeleteMixin` 为 `restore()` 提供了）。
`AsyncActiveRecord` 模型混入同一个 `ReadOnlyMixin`。

任何类都可以单独实现 `IReadOnlyBehavior`——普通 dataclass、非 ActiveRecord 的领域对象——
从而获得同样的声明能力。

---

## 3. 连接到只读副本

把只读模型配置到独立的后端：

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

# 主库——可写模型
User.configure(SQLiteConnectionConfig(database="primary.db"), SQLiteBackend)

# 分析副本——只读模型
UserAnalytics.configure(SQLiteConnectionConfig(database="analytics.db"), SQLiteBackend)
```

---

## 4. 与共享字段混入类模式结合

字段只定义一次，在可写模型与只读副本之间共享：

```python
from pydantic import BaseModel

class UserFields(BaseModel):
    id: Optional[int] = None
    name: str
    email: str

class User(UserFields, ActiveRecord):
    __table_name__ = "users"

class UserAnalytics(ReadOnlyMixin, UserFields, ActiveRecord):
    __table_name__ = "users"

User.configure(primary_config, SQLiteBackend)
UserAnalytics.configure(analytics_config, SQLiteBackend)
```

字段集中在一处，字段变更时两个模型自动保持同步。

---

## 5. 无主键是另一个维度

只读与"是否有主键"互相独立。只读副本通常保留主键，无主键的关系也依然可以写入：

```python
class AuditLog(ActiveRecord):          # 无主键，但可写（只追加表）
    __primary_key__ = None
    event: str

class EventView(ReadOnlyMixin, ActiveRecord):
    __primary_key__ = None             # 既无主键，又只读
    event: str
```

`__primary_key__ = None` 的含义以及被排除的 API 见 [无主键模型](keyless_models.md)。

---

## 6. 值得知道的边界

**它守护的是框架的写入路径，而不是数据库。** `backend.expression` 是公开导出的，
任何人都可以手工构造并执行一条 UPDATE：

```python
from rhosocial.activerecord.backend.expression import UpdateExpression

UpdateExpression(dialect, table="users", data={"name": "x"}, where=...).to_sql()
```

真正的保障是数据库凭据——只给账号授予 `SELECT`。用混入类防止手滑，
用权限来强制策略。

**与写入型行为的混入类组合会被拒绝。** `SoftDeleteMixin`、`TimestampMixin`、
`OptimisticLockMixin` 会注册 `BEFORE_INSERT` / `BEFORE_UPDATE` / `BEFORE_DELETE` 处理器，
而在只读模型上它们永远不会被执行，因为写入总是先被拒绝。该组合在**类定义时**
抛出 `TypeError`：

```python
class Broken(ReadOnlyMixin, SoftDeleteMixin, ActiveRecord):
    ...  # TypeError: Broken is read-only but also implements IDeleteBehavior ...
```

检查从 `__init_subclass__` 触发，因此在类定义时就会报错，而不是等到首次实例化。

---

## 检查清单

- [ ] 混入 `ReadOnlyMixin`，而不是手写 `save()` / `delete()` 覆写
- [ ] 测试断言 `ReadOnlyError`，而不是笼统的异常
- [ ] 若意图是只读副本，后端配置指向副本
- [ ] 数据库账号仅授予只读权限——混入类不是边界
- [ ] 没有与写入型行为的混入类组合

---

## 可运行示例

见 [`docs/examples/chapter_03_modeling/readonly_models.py`](../../examples/chapter_03_modeling/readonly_models.py)。

---

## 相关文档

- [无主键模型](keyless_models.md) —— `__primary_key__ = None` 及其影响
- [把视图写成查询](views_as_queries.md) —— 用封装查询表达数据库视图
- [Mixin](mixins.md) —— 其他内置混入类
- [批量处理](batch_processing.md) —— 高效读取大数据集
