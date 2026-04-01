# 大批量数据处理 (Batch Data Processing)

一次性将百万行数据加载到内存中会耗尽进程的 RAM，很可能直接导致应用崩溃。
本文介绍高效处理大数据集的模式——无论是 ETL 管道、数据迁移还是分析任务。

> 💡 **AI 提示词：** "我需要处理一张有一千万行数据的表，但不能撑爆内存。
> rhosocial-activerecord 推荐什么方案？"

---

## 1. 核心问题：内存

```python
# ❌ 将整张表加载到 RAM——对大表极度危险
all_users = User.query().all()
for user in all_users:
    process(user)
```

对于百万行级别的表，`all()` 会占用数 GB 内存并触发 OOM。
解决方案是**分块处理数据**。

---

## 2. 使用偏移量分页分块读取

最简单的分块策略是 `limit` + `offset`：

```python
def iter_users_by_page(page_size: int = 500):
    """每次产出一页用户数据。"""
    offset = 0
    while True:
        page = User.query().order_by("id").limit(page_size).offset(offset).all()
        if not page:
            break
        yield from page
        offset += page_size

# 逐个处理用户，不把所有行加载到内存
for user in iter_users_by_page(page_size=500):
    process(user)
```

> ⚠️ **稳定性要求**：偏移量分页只在迭代过程中数据不发生变化时才能产出一致结果。
> 对于写入频繁的活跃表，建议使用游标分块（见下文）或从快照中读取。

---

## 3. 游标分块（适合活跃表）

使用最后一条记录的主键作为游标，替代 `offset`。
这可以避免在迭代过程中插入或删除行导致的"数据漂移"问题：

```python
def iter_users_by_cursor(page_size: int = 500):
    """使用游标按主键顺序稳定地产出用户数据。"""
    last_id = 0
    while True:
        page = (
            User.query()
            .where(User.c.id > last_id)
            .order_by("id")
            .limit(page_size)
            .all()
        )
        if not page:
            break
        yield from page
        last_id = page[-1].id

for user in iter_users_by_cursor():
    process(user)
```

---

## 4. 框架级批量 DQL

框架提供了 `execute_batch_dql` 作为后端实例的方法，在内部自动处理分页，以同步生成器的形式逐页产出 `BatchDQLResult`：

```python
from rhosocial.activerecord.backend.expression.statements import QueryExpression
from rhosocial.activerecord.backend.expression import WildcardExpression, TableExpression
from rhosocial.activerecord.backend.expression.query_parts import OrderByClause
from rhosocial.activerecord.backend.expression import Column

# 构建 SELECT * FROM users ORDER BY id 表达式
dialect = User.backend().dialect
query_expr = QueryExpression(
    dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, "users"),
    order_by=OrderByClause(dialect, expressions=[(Column(dialect, "id"), "ASC")]),
)

# execute_batch_dql 是后端实例的方法，不是独立函数
for page in User.backend().execute_batch_dql(query_expr, page_size=500):
    for row in page.data:   # page.data 是 dict 列表
        process(row)
    if not page.has_more:
        break
```

完整 API 文档参见[批量操作](../performance/batch_operations.md)。

---

## 5. 批量写入——避免 N+1 写入陷阱

### 陷阱

```python
# ❌ N+1 次插入——每行数据一次数据库往返
for row in source_data:
    User(name=row["name"], email=row["email"]).save()
```

对于 10,000 行数据，这会发出 10,000 条独立的 `INSERT` 语句。
按每次往返 1ms 计算，需要约 10 秒——而批量插入可以在 100ms 以内完成。

### 正确做法：`execute_batch_dml`

```python
# ✅ 通过后端实例的 execute_batch_dml 方法批量插入
from rhosocial.activerecord.backend.expression import (
    InsertExpression, ValuesSource, Literal,
)
from rhosocial.activerecord.backend.result import BatchCommitMode

dialect = User.backend().dialect
exprs = [
    InsertExpression(
        dialect,
        into="users",
        columns=["name", "email"],
        source=ValuesSource(
            dialect,
            values_list=[[Literal(dialect, row["name"]), Literal(dialect, row["email"])]],
        ),
    )
    for row in source_data
]

# execute_batch_dml 是后端实例的方法，不是独立函数
for batch_result in User.backend().execute_batch_dml(exprs, batch_size=500):
    pass   # 消耗生成器；WHOLE 模式在迭代完成时自动提交
```

---

## 6. 大批量任务的事务策略

### 全局事务（要么全部成功，要么全部回滚）

```python
from rhosocial.activerecord.backend.expression import (
    InsertExpression, ValuesSource, Literal,
)
from rhosocial.activerecord.backend.result import BatchCommitMode

dialect = User.backend().dialect
with User.transaction():
    for chunk in chunked(source_data, size=500):
        exprs = [
            InsertExpression(
                dialect, into="users", columns=["name", "email"],
                source=ValuesSource(dialect, values_list=[
                    [Literal(dialect, row["name"]), Literal(dialect, row["email"])]
                ]),
            )
            for row in chunk
        ]
        for _ in User.backend().execute_batch_dml(exprs, batch_size=500):
            pass
```

**适用场景**：数据完整性要求严格，必须全部成功或全部回滚。

**缺点**：在整个执行期间持有写锁，可能阻塞其他写入操作。

### 逐批提交（可断点续传）

```python
from rhosocial.activerecord.backend.result import BatchCommitMode

for _ in User.backend().execute_batch_dml(
    exprs,
    batch_size=500,
    commit_mode=BatchCommitMode.PER_BATCH,
):
    pass
```

**适用场景**：任务可能被中断并重启（数据具有幂等性，或通过进度表记录哪些批次已提交）。

**缺点**：中途失败会留下部分已提交的数据，需要设计幂等性保障。

---

## 7. 只查询需要的列

当你只需要两列时，获取宽行会浪费带宽和 Pydantic 验证时间：

```python
# ❌ 获取所有列并验证所有字段
users = User.query().all()
emails = [u.email for u in users]

# ✅ 只获取 id 和 email
rows = User.query().select("id", "email").all()
emails = [r["email"] for r in rows]
```

---

## 8. 批量处理检查清单

- [ ] 不对大表使用无限制的 `.all()` 查询
- [ ] 活跃表使用游标分块；静态快照可使用偏移量分页
- [ ] 批量写入使用 `execute_batch_dml`（或 `insert_many`），而非逐行 `save()`
- [ ] 完整性要求严格的任务使用全局事务；可续传的任务使用逐批提交
- [ ] 通过 `query().select(...)` 只查询实际需要的列
- [ ] 在开发阶段使用接近生产量级的数据验证内存占用

---

## 可运行示例

参见 [`docs/examples/chapter_03_modeling/batch_processing.py`](../../../examples/chapter_03_modeling/batch_processing.py)，
该脚本自包含，完整演示了上述五种模式。

---

## 另请参阅

- [批量操作 API](../performance/batch_operations.md) — `execute_batch_dml` 和 `execute_batch_dql` 参考文档
- [只读分析模型](readonly_models.md) — 从分析数据库高效读取数据
- [性能模式](../performance/modes.md) — Raw 模式用于高吞吐量聚合查询
