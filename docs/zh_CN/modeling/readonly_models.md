# 只读分析模型 (Read-Only Analytics Models)

在数据分析、报表和只读副本场景中，往往需要**只能查询、绝对不能写入**的模型类。
本文介绍如何安全地定义、配置和使用只读模型。

> 💡 **AI 提示词：** "我想要一个连接分析数据库的模型类，一旦有人不小心尝试写入就立即报错。
> 怎么做？"

---

## 1. 为什么需要只读模型

| 使用场景 | 说明 |
| --- | --- |
| **只读副本** | 查询走副本，写入只能到主库 |
| **数据分析 / BI** | 报表查询数据仓库，不允许修改 |
| **多租户审计** | 某租户的模型可以读取另一租户的数据，但不能写入 |
| **历史快照** | 归档表只读，不允许任何变更 |

---

## 2. 声明只读模型

添加 `__readonly__` 类属性，并覆盖 `save()` 和 `delete()` 使其立即报错：

```python
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord

class ReadOnlyMixin:
    """混入任意 ActiveRecord 子类，使其成为只读模型。"""

    __readonly__: bool = True

    def save(self, *args, **kwargs):
        raise TypeError(
            f"{type(self).__name__} 是只读模型，不能保存。"
            "请使用对应的可写模型类。"
        )

    def delete(self, *args, **kwargs):
        raise TypeError(
            f"{type(self).__name__} 是只读模型，不能删除。"
        )

    @classmethod
    def bulk_create(cls, *args, **kwargs):
        raise TypeError(f"{cls.__name__} 是只读模型。")
```

应用到任意模型：

```python
class UserAnalytics(ReadOnlyMixin, ActiveRecord):
    """只读视图——连接分析副本上的 users 表。"""
    __table_name__ = "users"
    id: Optional[int] = None
    name: str
    email: str
    created_at: Optional[str] = None
```

---

## 3. 连接只读副本

将只读模型配置到独立的后端——通常是只读副本或分析数据库：

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

# 主库——可写模型
primary_config = SQLiteConnectionConfig(database="primary.db")
User.configure(primary_config, SQLiteBackend)

# 分析副本——只读模型
analytics_config = SQLiteConnectionConfig(database="analytics_replica.db")
UserAnalytics.configure(analytics_config, SQLiteBackend)
```

查询走副本；任何意外写入操作会在到达数据库之前立即抛出 `TypeError`：

```python
# ✅ 安全：读操作正常工作
analysts = UserAnalytics.query().where(UserAnalytics.c.created_at >= "2024-01-01").all()

# ✅ 安全：聚合查询
count = UserAnalytics.query().count()

# ❌ 立即阻断——不会产生任何数据库调用
user = UserAnalytics(name="Alice", email="alice@example.com")
user.save()  # 抛出：TypeError: UserAnalytics 是只读模型，不能保存。
```

---

## 4. 与共享字段 Mixin 模式结合

最易维护的方式是将 `ReadOnlyMixin` 与[共享字段 Mixin](best_practices.md#8-多个独立连接-multiple-independent-connections) 模式结合：
字段定义一处，由可写模型和只读分析模型共享。

```python
from pydantic import BaseModel

# 共享字段定义
class UserFields(BaseModel):
    id: Optional[int] = None
    name: str
    email: str
    created_at: Optional[str] = None

# 可写业务模型——主库
class User(UserFields, ActiveRecord):
    __table_name__ = "users"

# 只读分析模型——分析副本
class UserAnalytics(ReadOnlyMixin, UserFields, ActiveRecord):
    __table_name__ = "users"

# 各自独立配置
User.configure(primary_config, SQLiteBackend)
UserAnalytics.configure(analytics_config, SQLiteBackend)
```

字段定义集中在 `UserFields` 一处。添加或修改字段时，两个模型自动保持同步。

---

## 5. 派生 / 计算字段

分析模型通常需要从存储数据派生出指标。对不需要入库的值使用 `@property`：

```python
from datetime import datetime

class UserAnalytics(ReadOnlyMixin, UserFields, ActiveRecord):
    __table_name__ = "users"
    signup_days_ago: Optional[int] = None  # 由数据库查询或注解填充

    @property
    def is_new_user(self) -> bool:
        """注册不超过 30 天的用户视为新用户。"""
        return (self.signup_days_ago or 0) <= 30

    @property
    def tier(self) -> str:
        """按注册时长对用户分层。"""
        days = self.signup_days_ago or 0
        if days <= 30:
            return "new"
        if days <= 365:
            return "regular"
        return "veteran"
```

`@property` 字段在 Python 中计算，永远不会存入数据库，无需任何 Schema 变更即可添加。

---

## 6. 只读模型检查清单

- [ ] `ReadOnlyMixin`（或等价实现）覆盖了 `save()`、`delete()` 和 `bulk_create()`
- [ ] 只读模型配置到副本 / 分析后端，而非主库
- [ ] 字段定义通过 `BaseModel` Mixin 共享，避免重复
- [ ] 计算指标通过 `@property` 表达，而非存储列
- [ ] 单元测试验证 `save()` 和 `delete()` 会抛出 `TypeError`

---

## 可运行示例

参见 [`docs/examples/chapter_03_modeling/readonly_models.py`](../../../examples/chapter_03_modeling/readonly_models.py)，
该脚本自包含，完整演示了上述四种模式。

---

## 另请参阅

- [多个独立连接](best_practices.md#8-多个独立连接-multiple-independent-connections) — 子类继承 vs. Mixin 模式的连接分离方案
- [大批量数据处理](batch_processing.md) — 从分析数据库高效读取大型数据集
- [Mixins](mixins.md) — 内置 Mixin 及模型行为组合模式
