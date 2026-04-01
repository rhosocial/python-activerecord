# 查询解释接口 (Query Explain Interface)

`explain()` 接口提供了一种结构化的方式，对数据库后端执行 `EXPLAIN` 语句，并获得带类型、针对具体后端的结果对象。它主要用于查询分析、性能调试和索引使用验证。

## 概述

解释系统通过 `backend.explain(expression, options)` 直接访问，提供：

- **字节码分析**（SQLite）：检查 SQLite 为查询编译的虚拟机程序
- **查询计划分析**：获取查询策略的人类可读描述
- **索引使用检测**：自动判断查询是否进行全表扫描、使用回表索引，或受益于覆盖索引
- **类型化结果**：后端专属的 `pydantic.BaseModel` 结果对象，而非原始字典
- **同步/异步对等**：同步与异步后端具有完全相同的 API 形态

## 架构设计

### 模块结构

```
backend/explain/
├── __init__.py          # 模块导出
├── types.py             # BaseExplainResult 基类
├── protocols.py         # 同步和异步协议定义
└── backend_mixin.py     # SyncExplainBackendMixin / AsyncExplainBackendMixin

backend/impl/sqlite/explain/
├── __init__.py          # SQLite explain 导出
└── types.py             # SQLite 专属结果行和结果类
```

### 同步/异步分离

解释系统遵循项目的同步/异步对等原则，协议和混入类严格分离：

| 类 | 作用 |
|----|------|
| `SyncExplainBackendProtocol` | 同步后端的运行时可检查协议 |
| `AsyncExplainBackendProtocol` | 异步后端的运行时可检查协议 |
| `SyncExplainBackendMixin` | 通过 `fetch_all()` 实现同步 `explain()` 的混入类 |
| `AsyncExplainBackendMixin` | 通过 `await fetch_all()` 实现异步 `explain()` 的混入类 |
| `_ExplainMixinBase` | 共享非 I/O 逻辑：SQL 构建和 `_parse_explain_result()` 钩子 |

### 结果基类

所有解释结果均继承自 `BaseExplainResult`，它是普通的 `pydantic.BaseModel`（而非 `ActiveRecord`）：

```python
class BaseExplainResult(BaseModel):
    raw_rows: List[Dict[str, Any]]  # 来自 fetch_all() 的原始行数据
    sql: str                         # 实际执行的 EXPLAIN SQL
    duration: float                  # 执行耗时（秒）
```

使用 `pydantic.BaseModel` 可避免后端层对 ActiveRecord 模型层的反向依赖。

## 基本用法

### 解释一条查询（同步）

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteExplainResult
from rhosocial.activerecord.backend.expression import RawSQLExpression
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

dialect = SQLiteDialect()
backend = SQLiteBackend(database="mydb.sqlite3")
backend.connect()

# 获取查询的字节码解释
expr = RawSQLExpression(dialect, "SELECT * FROM users WHERE id = 1")
result = backend.explain(expr)

assert isinstance(result, SQLiteExplainResult)
print(f"SQL:  {result.sql}")
print(f"耗时: {result.duration * 1000:.2f} ms")
for row in result.rows:
    print(f"  {row.addr:>4}  {row.opcode:<18}  {row.p1:>4}  {row.p2:>4}  {row.comment or ''}")
```

### 使用表达式构建器

可以传入任何 `BaseExpression`（`ExplainExpression` 本身除外）：

```python
from rhosocial.activerecord.backend.expression.core import (
    TableExpression, WildcardExpression,
)
from rhosocial.activerecord.backend.expression.statements import QueryExpression

query = QueryExpression(
    dialect,
    select=[WildcardExpression(dialect)],
    from_=TableExpression(dialect, "users"),
)
result = backend.explain(query)
```

### EXPLAIN QUERY PLAN

传入 `ExplainOptions(type=ExplainType.QUERY_PLAN)` 可获取查询策略而非字节码：

```python
from rhosocial.activerecord.backend.expression.statements import (
    ExplainOptions, ExplainType,
)
from rhosocial.activerecord.backend.impl.sqlite import SQLiteExplainQueryPlanResult

opts = ExplainOptions(type=ExplainType.QUERY_PLAN)
result = backend.explain(query, opts)

assert isinstance(result, SQLiteExplainQueryPlanResult)
for row in result.rows:
    print(f"  {row.detail}")
```

### 异步 API

```python
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

backend = AsyncSQLiteBackend(database="mydb.sqlite3")
await backend.connect()

result = await backend.explain(query)           # 字节码
result = await backend.explain(query, opts)     # 查询计划
```

## SQLite 结果类型

SQLite 根据 EXPLAIN 模式的不同，输出的列格式完全不同。后端为每种模式返回专属的类型化对象。

### SQLiteExplainResult（字节码）

由普通 `EXPLAIN <stmt>` 返回。每行代表一条 VDBE（Virtual DataBase Engine，虚拟数据库引擎）指令：

```python
class SQLiteExplainRow(BaseModel):
    addr: int           # 程序计数器地址
    opcode: str         # 指令名称（如 "OpenRead"、"SeekGE"、"Column"）
    p1: int             # 第一操作数（通常是游标编号）
    p2: int             # 第二操作数（通常是 B 树页号或跳转目标）
    p3: int             # 第三操作数
    p4: Optional[str]   # 可选的字符串或 blob 操作数
    p5: int             # 标志位掩码
    comment: Optional[str]  # 人类可读的注释
```

```python
class SQLiteExplainResult(BaseExplainResult):
    rows: List[SQLiteExplainRow]
```

#### 核心操作码说明

对查询分析最重要的操作码：

| 操作码 | 含义 |
|--------|------|
| `OpenRead` | 在 B 树（表或索引）上打开一个游标 |
| `Rewind` | 将游标移到第一行（全表扫描的开始） |
| `Next` | 将游标推进到下一行 |
| `SeekGE` / `SeekGT` / `SeekLE` / `SeekLT` / `SeekEQ` | 使用键比较在索引上定位游标 |
| `DeferredSeek` | 延迟移动主表游标，直到实际需要某列时才访问 |
| `IdxRowid` | 从当前索引游标读取 rowid |
| `Column` | 从游标读取列值 |

### SQLiteExplainQueryPlanResult（查询计划）

由 `EXPLAIN QUERY PLAN <stmt>` 返回。每行描述查询策略中的一个步骤：

```python
class SQLiteExplainQueryPlanRow(BaseModel):
    id: int       # 行标识符（用于构建树形结构）
    parent: int   # 父行 id（0 表示顶层）
    notused: int  # 保留字段（当前 SQLite 版本始终为 0）
    detail: str   # 该步骤的人类可读描述
```

```python
class SQLiteExplainQueryPlanResult(BaseExplainResult):
    rows: List[SQLiteExplainQueryPlanRow]
```

`detail` 文本中使用 `SCAN`、`SEARCH`、`USING (COVERING) INDEX` 等关键词，直接反映查询策略。

## 索引使用分析

`SQLiteExplainResult` 和 `SQLiteExplainQueryPlanResult` 均内置了索引使用检测工具。

### `analyze_index_usage()`

返回以下四个字符串标签之一：

| 标签 | 含义 |
|------|------|
| `"full_scan"` | 未使用索引，扫描所有行 |
| `"index_with_lookup"` | 使用索引定位行，但仍需访问主表获取非索引列（回表） |
| `"covering_index"` | 覆盖索引满足查询，无需任何主表访问 |
| `"unknown"` | 无法识别的模式（复杂多表查询或未来的 SQLite 版本） |

### 便捷属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `is_full_scan` | `bool` | 未使用索引时为 `True` |
| `is_index_used` | `bool` | 使用了任意索引时为 `True` |
| `is_covering_index` | `bool` | 使用覆盖索引（无主表访问）时为 `True` |

### 示例：诊断索引使用情况

```python
from rhosocial.activerecord.backend.expression import RawSQLExpression
from rhosocial.activerecord.backend.expression.statements import ExplainOptions, ExplainType

dialect = SQLiteDialect()
backend = SQLiteBackend(database="mydb.sqlite3")
backend.connect()

queries = {
    "全表扫描":   "SELECT * FROM orders",
    "索引回表":   "SELECT * FROM orders WHERE status = 'pending'",
    "覆盖索引":   "SELECT sku FROM order_items WHERE order_id = 1",
}

for label, sql in queries.items():
    # 字节码分析
    result = backend.explain(RawSQLExpression(dialect, sql))
    print(f"{label}: {result.analyze_index_usage()}")
    print(f"  is_full_scan={result.is_full_scan}, "
          f"is_index_used={result.is_index_used}, "
          f"is_covering_index={result.is_covering_index}")

    # 查询计划分析（具备相同属性）
    plan = backend.explain(
        RawSQLExpression(dialect, sql),
        ExplainOptions(type=ExplainType.QUERY_PLAN),
    )
    for row in plan.rows:
        print(f"  plan: {row.detail}")
```

#### 解读字节码模式

**全表扫描** — 主表上只有一个 `OpenRead` 游标，没有任何 seek 操作码：

```
OpenRead  p1=0  p2=<table root>   # 打开表 B 树
Rewind    p1=0                     # 从头开始
Ne        ...                      # 逐行比较
Next      p1=0                     # 移到下一行
```

**索引回表** — 两个 `OpenRead` 游标（主表 + 索引），存在 seek 操作码：

```
OpenRead  p1=0  p2=<table root>          # 主表游标
OpenRead  p1=1  p2=<index root>  p5=2    # 索引游标（OPFLAG_SEEKEQ）
SeekGE    p1=1  ...                       # 在索引上定位
IdxGT     p1=1  ...                       # 范围边界检查
DeferredSeek p1=1                         # 延迟主表访问
IdxRowid  p1=1                            # 从索引获取 rowid
Column    p1=0  ...                       # 从主表读取剩余列（回表）
```

**覆盖索引** — 只有一个 `OpenRead` 游标指向索引，所有 `Column` 读取均使用索引游标：

```
OpenRead  p1=1  p2=<index root>  p4=k(n,,)  # 只打开索引游标
SeekGE    p1=1  ...                           # 在索引上定位
IdxGT     p1=1  ...                           # 范围边界
Column    p1=1  p2=<col>                      # 直接从索引读取
```

## 协议检查

可在运行时验证后端是否满足 explain 协议：

```python
from rhosocial.activerecord.backend.explain import (
    SyncExplainBackendProtocol,
    AsyncExplainBackendProtocol,
)

assert isinstance(backend, SyncExplainBackendProtocol)
assert isinstance(async_backend, AsyncExplainBackendProtocol)
```

## 在自定义后端中实现 `explain()`

1. **根据后端类型导入对应的混入类**（同步或异步）。
2. **将其加入类的 MRO**，放在存储后端基类之前。
3. **覆写 `_parse_explain_result()`**，返回您的后端专属结果类。

```python
from rhosocial.activerecord.backend.explain import SyncExplainBackendMixin
from rhosocial.activerecord.backend.base import StorageBackend
from pydantic import BaseModel
from typing import List, Dict, Any

class MyExplainRow(BaseModel):
    # 定义与您的数据库 EXPLAIN 输出匹配的字段
    ...

class MyExplainResult(BaseExplainResult):
    rows: List[MyExplainRow]

class MyBackend(SyncExplainBackendMixin, StorageBackend):
    def _parse_explain_result(
        self,
        raw_rows: List[Dict[str, Any]],
        sql: str,
        duration: float,
    ) -> MyExplainResult:
        rows = [MyExplainRow(**r) for r in raw_rows]
        return MyExplainResult(raw_rows=raw_rows, sql=sql, duration=duration, rows=rows)
```

如果您的数据库使用非标准 EXPLAIN 语法，还需要在 Dialect 中覆写 `format_explain_statement()`。

## API 参考

### `backend.explain(expression, options=None)`

| 参数 | 类型 | 说明 |
|------|------|------|
| `expression` | `BaseExpression` | 除 `ExplainExpression` 以外的任意表达式 |
| `options` | `ExplainOptions \| None` | 可选的解释选项（类型、格式、analyze） |

**返回值**：后端专属的 `BaseExplainResult` 子类。

### `ExplainOptions`

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `type` | `ExplainType \| None` | `None` | `ExplainType.QUERY_PLAN` 表示查询计划模式 |
| `format` | `ExplainFormat \| None` | `None` | 输出格式（后端相关） |
| `analyze` | `bool` | `False` | 实际执行查询并包含运行时统计（PostgreSQL） |

### `SQLiteExplainResult` 方法

| 方法 / 属性 | 返回类型 | 说明 |
|-------------|----------|------|
| `analyze_index_usage()` | `str` | `"full_scan"`、`"index_with_lookup"`、`"covering_index"` 或 `"unknown"` |
| `is_full_scan` | `bool` | 未使用索引时为 `True` |
| `is_index_used` | `bool` | 使用了任意索引时为 `True` |
| `is_covering_index` | `bool` | 使用覆盖索引（无主表访问）时为 `True` |

### `SQLiteExplainQueryPlanResult` 方法

与上表相同的 `analyze_index_usage()`、`is_full_scan`、`is_index_used`、`is_covering_index`，基于 `EXPLAIN QUERY PLAN` 返回的 `detail` 文本进行分析。
