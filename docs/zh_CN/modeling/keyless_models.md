# 无主键模型 (Keyless Models)

关系并不总是有唯一的单行主键。只增审计日志、聚合投影，或身份仅由读取它的查询提供的表，
都是真实存在的形状。`__primary_key__ = None` 把这种形状显式声明出来。

> **AI 提示词：** "我需要映射一张没有主键的表。查询和插入要能用，但 `find_one(id)`
> 应该明确告诉我没有 id 可找。"

---

## 1. 声明无主键模型

```python
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord

class AuditLog(ActiveRecord):
    __table_name__ = "audit_log"
    __primary_key__ = None

    event: str
    level: str
```

`__primary_key__ = None` 不是漏配，而是被接受的声明。模型通过唯一的判定点回答：

```python
AuditLog.addressable()          # False
AuditLog.primary_key_columns()  # ()
AuditLog.primary_key_fields()   # ()
```

空元组很重要：调用方可以无条件迭代，永远不会拿到 `(None,)`。

---

## 2. 哪些能力保持可用

身份只是读取的一种方式。以下操作全部继续可用：

```python
AuditLog(event="a").save()                                  # INSERT
AuditLog.query().all()
AuditLog.query().where(AuditLog.c.level == "warn").one()
AuditLog.query().order_by(AuditLog.c.event).limit(10).all()
AuditLog.query().count()
AuditLog.query().select(AuditLog.c.level).aggregate()
AuditLog.find_all({"level": "warn"})
AuditLog.find_one({"event": "a"})
```

`is_new_record` 也有诚实的答案。没有主键就没有身份可查，因此由来源标记决定：从数据库
加载的行不是新记录，Python 中构造的都是新记录。

```python
AuditLog(event="x").is_new_record             # True
loaded = AuditLog.query().where(...).one()
loaded.is_new_record                          # False
```

---

## 3. 哪些操作会被拒绝

按主键寻址需要主键。以下操作抛出 `UnaddressableRecordError`，而不是泄漏
`TypeError: attribute name must be string, not 'NoneType'`：

| 操作 | 抛出的异常 |
| --- | --- |
| `find_one(pk_value)` | `UnaddressableRecordError` |
| `find_all([pk1, pk2])` | `UnaddressableRecordError` |
| `refresh()` | `UnaddressableRecordError` |
| `_get_pk_value()` | `UnaddressableRecordError` |
| `_build_pk_where_predicate(...)` | `UnaddressableRecordError` |

异常会指出模型与操作，并给出替代方案：

```python
from rhosocial.activerecord.backend.errors import UnaddressableRecordError

try:
    AuditLog.find_one(1)
except UnaddressableRecordError as exc:
    print(exc.model_name, exc.operation)  # AuditLog find_one
```

当一行由其它条件唯一确定时，使用 `where(...).one()`：

```python
record = AuditLog.query().where(AuditLog.c.event == "only").one()
```

只有**裸主键**条件会被拒绝。dict 或谓词条件不是身份查找，仍然可以执行：

```python
AuditLog.find_one({"event": "a"})
AuditLog.find_one(AuditLog.c.event == "a")
```

`UnaddressableRecordError` 继承 `DatabaseError`。

---

## 4. 无主键与只读正交

这两个维度互不干涉：

```python
class KeylessWritable(ActiveRecord):
    __primary_key__ = None
    ...

class ReadOnlyWithKey(ActiveRecord, ReadOnlyMixin):
    __table_name__ = "records"
    ...

class KeylessReadOnly(ActiveRecord, ReadOnlyMixin):
    __primary_key__ = None
    ...
```

- `KeylessWritable.addressable()` 为 `False`；写入仍然可用。
- `ReadOnlyWithKey.addressable()` 为 `True`；写入被拒绝。
- `KeylessReadOnly` 两者兼有；写入被拒绝，且身份访问不可用。

---

## 5. 检查清单

- [ ] `__primary_key__ = None` 是刻意声明，而不是遗漏
- [ ] 身份操作改用 `where(...).one()`
- [ ] 插入与查询都有测试覆盖
- [ ] 复合主键仍保持元组；`None` 不是复合主键

---

## 另请参阅

- [只读模型](readonly_models.md) —— 通过模型 API 拒绝写入
- [DDLSource 声明收集](ddl_source.md) —— `object_type()` 与 DDL 元数据
- [Active Query](../querying/active_query.md) —— 谓词、排序、聚合
