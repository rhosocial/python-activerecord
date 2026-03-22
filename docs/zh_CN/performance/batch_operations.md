# 批量操作

在处理大量数据时，逐条执行查询会因重复的数据库往返开销而效率低下。批量执行接口提供了流式处理方式，支持自动事务管理和内存高效迭代。

## 概述

后端提供两种批量执行方法：

- **`execute_batch_dml`**：批量执行 DML 操作（INSERT、UPDATE、DELETE）
- **`execute_batch_dql`**：批量执行 DQL 操作（SELECT），支持分页

两种方法均支持同步和异步变体，API 完全一致。

## 批量 DML 操作

### 基本用法

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.expression import InsertExpression, ValuesSource, Literal

backend = SQLiteBackend(database=":memory:")
backend.connect()

# 创建 INSERT 表达式列表
expressions = []
for i in range(100):
    source = ValuesSource(backend.dialect, values_list=[
        [Literal(backend.dialect, f"user{i}"),
         Literal(backend.dialect, f"user{i}@example.com")]
    ])
    expr = InsertExpression(
        backend.dialect,
        into="users",
        columns=["name", "email"],
        source=source
    )
    expressions.append(expr)

# 以每批 20 条执行
for batch_result in backend.execute_batch_dml(expressions, batch_size=20):
    print(f"批次 {batch_result.batch_index}: 影响 {batch_result.total_affected_rows} 行")

backend.disconnect()
```

### 提交模式

批量 DML 支持两种提交模式：

#### WHOLE 模式（默认）

整个批量操作包装在单个事务中。如果发生错误，所有更改都会回滚。

```python
from rhosocial.activerecord.backend.result import BatchCommitMode

# 全有或全无：要么所有批次成功，要么全部回滚
for batch in backend.execute_batch_dml(
    expressions,
    batch_size=50,
    commit_mode=BatchCommitMode.WHOLE
):
    process_batch(batch)
```

**行为特性：**
- 所有批次在单个事务中执行
- 如果批次中途发生错误，所有之前的批次都会回滚
- 生成器退出（break/异常）会触发整个操作的回滚

#### PER_BATCH 模式

每个批次在执行后立即提交。如果发生错误，已提交的批次保留其更改。

```python
# 每个批次独立提交
for batch in backend.execute_batch_dml(
    expressions,
    batch_size=50,
    commit_mode=BatchCommitMode.PER_BATCH
):
    process_batch(batch)
```

**行为特性：**
- 每个批次在独立事务中执行
- 已提交的批次即使后续批次失败也会保留
- 生成器退出不会回滚已提交的批次

### RETURNING 子句支持

对于支持 RETURNING 子句的后端（PostgreSQL、SQLite 3.35+），可以获取受影响行的数据：

```python
# 获取插入的 ID 和名称
for batch in backend.execute_batch_dml(
    expressions,
    batch_size=10,
    returning_columns=["id", "name"]
):
    for result in batch.results:
        print(f"已插入: id={result.data[0]['id']}, name={result.data[0]['name']}")
```

**注意：** 使用 `returning_columns` 会将执行路径从高效的 `executemany()` 切换为逐行 `execute()` 调用。请谨慎在大型批次中使用此功能。

### 表达式要求

批量 DML 要求**同质表达式**：

1. 所有表达式必须是相同类型（全为 INSERT、全为 UPDATE 或全为 DELETE）
2. 表达式必须生成相同的 SQL 模板（相同表、相同列）

```python
# 有效：所有 INSERT 表达式针对同一张表
expressions = [
    make_insert("user1", "user1@example.com"),
    make_insert("user2", "user2@example.com"),
    make_insert("user3", "user3@example.com"),
]

# 无效：混合表达式类型
expressions = [
    make_insert("user1", "user1@example.com"),
    make_update(1, "new_name"),  # TypeError: 异质表达式
]
```

## 批量 DQL 操作

### 延迟加载分页

`execute_batch_dql` 为大型结果集提供内存高效的分页：

```python
from rhosocial.activerecord.backend.expression import QueryExpression, TableExpression, WildcardExpression

query = QueryExpression(
    backend.dialect,
    select=[WildcardExpression(backend.dialect)],
    from_=TableExpression(backend.dialect, "large_table"),
)

# 逐页处理 1000 行
for page in backend.execute_batch_dql(query, page_size=1000):
    print(f"第 {page.page_index} 页: {page.page_size} 行")
    for row in page.data:
        process_row(row)
    # 此页的内存在获取下一页前可以释放
```

### 页面元数据

每个批次结果提供有用的元数据：

```python
for page in backend.execute_batch_dql(query, page_size=100):
    print(f"页索引: {page.page_index}")
    print(f"页大小: {page.page_size}")
    print(f"还有更多页: {page.has_more}")
    print(f"本页总行数: {len(page.data)}")
```

### 表达式类型

`execute_batch_dql` 支持所有 DQL 表达式类型：

- `QueryExpression`：基本 SELECT 查询
- `WithQueryExpression`：公用表表达式（CTE）
- `SetOperationExpression`：UNION、INTERSECT、EXCEPT 操作

```python
# CTE 示例
from rhosocial.activerecord.backend.expression.query_sources import WithQueryExpression, CTEExpression

cte_query = QueryExpression(
    backend.dialect,
    select=[WildcardExpression(backend.dialect)],
    from_=TableExpression(backend.dialect, "orders"),
    where=WhereClause(backend.dialect, condition=...),
)
cte = CTEExpression(backend.dialect, name="recent_orders", query=cte_query)

main_query = QueryExpression(
    backend.dialect,
    select=[WildcardExpression(backend.dialect)],
    from_=TableExpression(backend.dialect, "recent_orders"),
)

with_query = WithQueryExpression(backend.dialect, ctes=[cte], main_query=main_query)

for page in backend.execute_batch_dql(with_query, page_size=50):
    process_orders(page.data)
```

## 异步支持

两种批量方法都有语义完全相同的异步版本：

```python
# 异步批量 DML
async for batch in async_backend.execute_batch_dml(expressions, batch_size=20):
    await process_batch(batch)

# 异步批量 DQL
async for page in async_backend.execute_batch_dql(query, page_size=1000):
    await process_page(page)
```

## 事务交互

### 外部事务

当已在事务中时，批量操作会遵循现有事务：

```python
with backend.transaction():
    # 批量操作使用现有事务
    for batch in backend.execute_batch_dml(expressions, batch_size=50):
        process_batch(batch)
    # 更改在上下文管理器退出前不会提交
```

### 错误处理

```python
try:
    for batch in backend.execute_batch_dml(
        expressions,
        batch_size=50,
        commit_mode=BatchCommitMode.WHOLE
    ):
        process_batch(batch)
except IntegrityError:
    # WHOLE 模式：所有更改已回滚
    # PER_BATCH 模式：之前的批次可能已提交
    handle_error()
```

## 性能考量

1. **批次大小选择**：
   - 较小批次：内存占用低，进度粒度细
   - 较大批次：往返次数少，吞吐量高
   - 建议：大多数场景使用 100-1000 行

2. **RETURNING 子句权衡**：
   - 不使用 RETURNING：使用高效的 `executemany()`
   - 使用 RETURNING：逐行使用 `execute()`
   - 如需 RETURNING 数据，考虑单独查询

3. **内存效率**：
   - DQL 分页在每页后释放内存
   - DML 批次增量处理
   - 避免在内存中累积所有结果

## 后端支持

| 后端 | 批量 DML | 批量 DQL | RETURNING |
|------|----------|----------|-----------|
| SQLite | 支持 | 支持 | 3.35+ |
| MySQL | 支持 | 支持 | 不支持 |
| PostgreSQL | 支持 | 支持 | 支持 |
