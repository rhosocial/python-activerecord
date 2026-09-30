# 无主键模型

关系并不总有一个唯一的单行主键。只追加的审计日志没有；聚合投影也没有——
"客户 42 那一行"可能根本不存在。`__primary_key__ = None` 用来声明这一点，
框架对此有明确的答案。

---

## 1. 声明无主键模型

```python
from rhosocial.activerecord.model import ActiveRecord

class AuditLog(ActiveRecord):
    __table_name__ = "audit_log"
    __primary_key__ = None      # 没有单行身份
    event: str
    level: str
```

```python
AuditLog.addressable()            # False
AuditLog.primary_key_columns()    # ()  —— 空元组，绝不是 (None,)
AuditLog.primary_key_fields()     # ()
AuditLog.is_composite_pk()        # False
```

`primary_key_columns()` 返回**空元组**而不是 `(None,)`，因此调用方可以无条件地迭代它。

`addressable()` 是唯一的判断点，命名与框架向模型询问的其他谓词（`read_only()`）保持一致。
它只回答一个问题：*能否按主键定位到单行？*

---

## 2. 不可用的部分

所有需要身份的操作：

| 不可用 | 替代方案 |
| --- | --- |
| `find_one(pk)` | `query().where(...).one()` |
| `find_all([pk, pk])` | `query().where(Model.c.id.in_([...]))` |
| `refresh()` | 显式重新查询 |
| 按主键更新或删除 | `where(...)` 配合 `update_all()` / `delete_all()` |
| 基于主键的关联缓存 | 关闭缓存，或自行指定 key |

每一处都会抛出 `UnaddressableRecordError`，并指出模型与操作：

```python
AuditLog.find_one(5)
# UnaddressableRecordError: find_one needs a primary key, but 'AuditLog' declares
# __primary_key__ = None and so has no single-row identity. Select with
# AuditLog.query().where(...).one() instead, or declare a primary key if the
# relation really has one.
```

`UnaddressableRecordError` 是 `DatabaseError` 的子类。

---

## 3. 仍然可用的部分

API 的大部分仍然可用，因为大部分并不需要身份：

```python
AuditLog(event="login", level="info").save()               # ✅ 插入
AuditLog.query().all()                                      # ✅
AuditLog.query().where(AuditLog.c.level == "info").all()    # ✅
AuditLog.query().order_by(AuditLog.c.event).limit(10).all()  # ✅
AuditLog.query().count()                                    # ✅
AuditLog.query().where(...).exists()                        # ✅
AuditLog.query().select(AuditLog.c.level).aggregate()       # ✅ 分组、求平均
AuditLog.find_all({"level": "warn"})                        # ✅ 字典条件
AuditLog.find_one(AuditLog.c.level == "warn")               # ✅ 谓词条件
```

关联同样可用。`belongs_to` 的预加载使用**目标方**的主键；`has_many` 使用**父方**的主键。
无主键模型放在任何一侧都没问题——它做不到的是为自己的关联缓存生成 key。

> **注意：** `ActiveQuery` 没有 `first()`、`last()`、`pluck()`。请使用 `limit(1).all()`、
> 反向 `order_by`，或 `.select(...).aggregate()`。

---

## 4. 没有主键时的 `is_new_record`

有主键时，`is_new_record` 判断主键是否已设置。没有主键时没有身份可供检查，
于是改为依据来源判断：

```python
AuditLog(event="x").is_new_record          # True  —— 在 Python 中构造

loaded = AuditLog.query().where(...).one()
loaded.is_new_record                       # False —— 来自数据库
```

这让 `save()` 的分派保持合理：构造出的无主键记录执行插入，而从数据库读回的记录
被识别为已持久化。

无主键模型会跳过插入后读取主键的步骤——数据库没有什么可生成的，也就没有什么可读回的。

---

## 5. 与只读相互独立

两个维度互相正交，两个方向都成立：

```python
class AuditLog(ActiveRecord):                    # 无主键，可写
    __primary_key__ = None

class EventSummary(ReadOnlyMixin, ActiveRecord): # 既无主键，又只读
    __primary_key__ = None

class UserReplica(ReadOnlyMixin, ActiveRecord):  # 只读，但可寻址
    __table_name__ = "users"
```

物化视图模型会同时需要两者。

---

## 6. 该选无主键模型还是视图

如果你想要的形状是"每个 X 一行，列由其他表派生"，那通常是一个**查询**而不是一张表。
见 [把视图写成查询](views_as_queries.md)——封装一个 `ActiveQuery` 是更直接的表达，
而且不需要模型。

只有在需要类型化实例、关联或对结果做预加载时，才值得用无主键*模型*。

---

## 检查清单

- [ ] 仅在关系确实没有唯一键时才写 `__primary_key__ = None`
- [ ] 调用方使用 `where(...).one()` 而非 `find_one(pk)`
- [ ] 该模型的关联缓存已关闭，或自行指定 key
- [ ] 测试断言 `UnaddressableRecordError`，而不是裸的 `TypeError`

---

## 相关文档

- [只读模型](readonly_models.md) —— 拒绝写入
- [把视图写成查询](views_as_queries.md) —— 何时查询优于表
- [推导字段](derived_fields.md) —— SELECT 列表中的计算列
