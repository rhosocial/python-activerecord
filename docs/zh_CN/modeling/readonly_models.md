# 只读模型 (Read-Only Models)

在数据分析、报表和只读副本场景中，往往需要**只能查询、绝对不能写入**的模型类。
`ReadOnlyMixin` 把这件事变成一个声明，而不是一组覆写方法：框架的每条写路径都会在发出
任何 SQL 之前拒绝操作。

> **AI 提示词：** "我想要一个连接分析数据库的模型类，一旦有人不小心尝试写入就立即报错。
> 怎么做？"

---

## 1. 为什么需要只读模型

| 使用场景 | 说明 |
| --- | --- |
| **只读副本** | 查询走副本，写入只能到主库 |
| **数据分析 / BI** | 报表查询数据仓库，不允许修改 |
| **多租户审计** | 某租户的模型可以读取另一租户的数据，但不能写入 |
| **历史快照** | 归档表只读，不允许任何变更 |
| **视图映射** | 模型映射的是视图或物化视图，而不是可写表 |

---

## 2. 声明只读模型

把 `ReadOnlyMixin` 混入普通模型：

```python
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import ReadOnlyMixin

class UserAnalytics(ActiveRecord, ReadOnlyMixin):
    """只读视图——连接分析副本上的 users 表。"""
    @classmethod
    def table_name(cls):
        return "users"

    id: Optional[int] = None
    name: str
    email: str
    created_at: Optional[str] = None
```

该 Mixin 不声明任何字段。它设置 `__read_only__ = True`，并提供框架询问的唯一判定点：

```python
UserAnalytics.read_only()  # True
```

没有混入的模型根本不会回答 `read_only()`，因此该能力始终是显式启用的。

---

## 3. 哪些操作会被拒绝

所有框架写路径都会在构造语句之前调用 `refuse_read_only()`：

| 路径 | 同步 / 异步 |
| --- | --- |
| `save()`、`delete()` | 两者 |
| `_insert_internal()`、`_update_internal()` | 两者 |
| `bulk_create()`、`bulk_update()`、`bulk_delete()` | 两者 |
| `query().update_all()`、`query().delete_all()` | 两者 |

被拒绝的写入抛出 `ReadOnlyError`：

```python
from rhosocial.activerecord.backend.errors import ReadOnlyError

user = UserAnalytics(name="Alice", email="alice@example.com")
try:
    user.save()
except ReadOnlyError as exc:
    print(exc.model_name, exc.operation)  # UserAnalytics save
```

`ReadOnlyError` 继承 `DatabaseError`，现有的 `except DatabaseError` 处理逻辑继续有效。
异常携带 `model_name` 与 `operation`。

读操作永远不会被拒绝：

```python
UserAnalytics.query().where(UserAnalytics.c.created_at >= "2024-01-01").all()
UserAnalytics.query().count()
UserAnalytics.find_one({"email": "alice@example.com"})
```

> **保证边界：** 这保护的是框架自身的写路径。表达式层是公开的，手工构造的 UPDATE /
> DELETE 仍可执行。真正的保证来自数据库账号权限；本 Mixin 只防止误操作。

---

## 4. 退出与自定义行为

显式设置 `__read_only__ = False` 可以关闭门禁：

```python
class SometimesWritable(ActiveRecord, ReadOnlyMixin):
    @classmethod
    def table_name(cls):
        return "records"

    @classmethod
    def read_only(cls):
        return False

```

门禁读取的是 `read_only()` 的**返回值**，而不是接收者的类型。模型可以实现
`IReadOnlyBehavior` 却仍然可写：

```python
from rhosocial.activerecord.interface import IReadOnlyBehavior

class PolicyDriven(ActiveRecord, IReadOnlyBehavior):
    @classmethod
    def read_only(cls) -> bool:
        return False  # 真实判定，而不是类型测试

PolicyDriven.refuse_read_only("save")  # 允许
```

这正是不能用 `isinstance(model, IReadOnlyBehavior)` 做门禁的原因：它只说明存在一个
`read_only` 方法。

---

## 5. 视图与物化视图声明

只读模型经常映射的不是表。可以在 DDL 来源上声明对象类型：

```python
from rhosocial.activerecord.base import ObjectDeclaration

class UserAnalytics(ActiveRecord, ReadOnlyMixin):
    @classmethod
    def table_name(cls):
        return "user_analytics_view"

    id: Optional[int] = None
    name: str

    @classmethod
    def object_type(cls) -> ObjectDeclaration:
        return ObjectDeclaration.VIEW
```

`ObjectDeclaration` 包含 `TABLE`（默认）、`VIEW` 和 `MATERIALIZED_VIEW`。这只是声明：
DDL 层据此选择要构造的语句，再由 dialect 的能力门禁决定该语句是否可表达。数据库里是否
真的存在同名视图，是内省要回答的问题，不是模型元数据要回答的问题。

---

## 6. 与写事件 Mixin 的冲突

`SoftDeleteMixin` 注册 `BEFORE_DELETE` 并发出 UPDATE；`TimestampMixin` 与
`OptimisticLockMixin` 注册 `BEFORE_UPDATE`。在只读模型上这些处理器永远无法执行，因为
所有写入都会先被拒绝。因此该组合在类定义时直接报错：

```python
class Conflict(ActiveRecord, ReadOnlyMixin, TimestampMixin):
    ...
# TypeError: Conflict is read-only but also implements
# IUpdateBehavior (e.g. TimestampMixin, OptimisticLockMixin).
```

检测基于接口（`IUpdateBehavior` / `IDeleteBehavior`），第三方行为 Mixin 也会被捕获。
如果模型确实可写，请设置 `__read_only__ = False`。

---

## 7. 只读与主键正交

只读表可以有自增主键；无主键表也可以可写。`ReadOnlyMixin` 对两者都没有意见。参见
[无主键模型](keyless_models.md) 中的 `__primary_key__ = None`。

---

## 8. 检查清单

- [ ] 模型混入了 `ReadOnlyMixin`
- [ ] 写路径会捕获或允许 `ReadOnlyError` 向上抛出
- [ ] 只读模型配置到副本 / 分析后端，而非主库
- [ ] 重复字段通过 `BaseModel` Mixin 共享
- [ ] 计算指标通过 `@property` 表达，而非存储列
- [ ] 模型映射视图时覆写 `object_type()`

---

## 可运行示例

参见 [`docs/examples/chapter_03_modeling/readonly_models.py`](../../../examples/chapter_03_modeling/readonly_models.py)，
该脚本自包含。

## 另请参阅

- [无主键模型](keyless_models.md) —— `__primary_key__ = None` 与无身份访问
- [多个独立连接](best_practices.md#8-多个独立连接-multiple-independent-connections) —— 子类继承 vs. Mixin 模式的连接分离方案
- [Mixins](mixins.md) —— 内置 Mixin 及模型行为组合模式
