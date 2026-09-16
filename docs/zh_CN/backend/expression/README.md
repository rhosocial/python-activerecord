# 表达式系统 (Expression System)

表达式系统提供了一种与数据库无关的方式，使用 Python 对象构建 SQL。它处理 SQL 生成、参数绑定和方言特定的差异。

## 设计目标：封装所有 SQL 语义

表达式系统的根本目标是**用 Python 对象完整封装 SQL 的所有语义**——从最简单的 `SELECT`、`INSERT`，到窗口函数、CTE、JSON 操作、属性图查询（PGQ），再到各类数据类型与后端私有语法。

`to_sql()` 是唯一的生产入口：任何表达式都可以独立调用 `to_sql()` 生成 `(SQL 字符串, 参数元组)`，无需经过完整查询编译。这意味着：

- 每个表达式对象都是**自包含**的：它持有构建该 SQL 片段所需的全部信息
- 表达式可以自由**组合**（嵌套、按位运算符、链式调用）
- 表达式可以脱离任何后端独立测试，也可以在绑定方言后直接生成可执行 SQL

## 设计哲学：通用与特定后端

表达式系统是**通用（core）与特定后端（backend-specific）两层结构**。

### 原则一：广泛覆盖，节省后端工作量

通用层（`rhosocial.activerecord.backend.expression` 与 `backend.dialect`）力求**尽可能广泛地覆盖 SQL 标准语义**。对于绝大多数数据库都能以标准方式表达的语法，框架在通用层一次性实现，后端包**无需重复实现**即可获得这些能力。

这带来的直接收益是：

- 后端作者只需关注**方言差异**，而非重新实现通用语义
- 新后端接入成本大幅降低——大部分表达式能力开箱即用
- 用户学习成本低：通用 API 在所有后端的用法一致

### 原则二：尊重后端实际

通用覆盖不是「一刀切」。每个数据库都有自身独有的语法与能力边界，通用层**绝不强加**统一语义：

- **严格忠实渲染**：方言只渲染它原生支持的声明，遇到不支持的情况**直接报错并给出指引**，绝不静默替换为近似语义（例如在 PostgreSQL 上声明通用自增类型会报错并指向 `PostgresSerialType`）
- **能力协商**：方言通过协议（Protocols）与能力查询方法暴露自身支持范围（如 `supports_graph_match()`），用户可在运行时检测
- **特定后端扩展**：通用层无法覆盖的私有语法，由后端包提供**以后端名为前缀**的特定表达式（见下）

### 原则三：特定后端表达式以后端名为前缀

后端特定表达式（以及特定协议、混入、类型）**必须以该后端名称作为前缀**，例如：

| 后端 | 特定表达式/类型示例 |
|------|--------------------|
| MySQL | `MySQLVectorType`、`MySQLEnumType` |
| PostgreSQL | `PostgresSerialType`、`PostgresTSVectorType` |
| SQLite | `SQLiteIntegerType`、`SQLiteBlobType` |

命名约定保障了可读性、可发现性与隔离性：用户一眼即可分辨「这是通用能力还是某后端的私有能力」，且不同后端的扩展不会相互冲突。

> **相关约定**：方言协议的命名遵循相同原则——通用协议（如 `WindowFunctionSupport`）无前缀，后端特定协议（如 `PostgresPartitionSupport`、`MySQLFullTextSearchSupport`）必须有后端前缀。详见[自定义后端](custom_backend.md)。

## 主要特性

- **逐节点方言绑定**: 每个表达式单独绑定方言——方言是约定俗成的第一个构造参数（可选，默认 `None`，允许推迟赋值）。`dialect` setter 只影响被赋值的节点本身，不会向子表达式传播
- **无状态渲染**: `to_sql()` 无参数，读取节点自身绑定的方言、就地渲染现有的树——没有重建、没有副本。未绑定方言即渲染会抛出 `ValueError`（fail-fast 护栏）
- **直接 SQL 生成**: 从表达式到 SQL 只需 2 步——在绑定的方言上解析该类声明的 `format_method` 并调用格式化器——避免了多层编译架构
- **灵活的片段生成**: 任何表达式都可以独立调用 `to_sql()` 生成 SQL 片段，不像某些系统需要完整查询编译
- **用户控制**: 用户完全控制何时以及如何生成 SQL，没有隐藏的自动行为
- **显式优于隐式**: 没有隐藏的状态管理、自动编译或复杂的对象生命周期跟踪
- **无隐藏行为**: 没有自动刷新或隐藏的数据库操作，不像某些系统有自动会话管理

## 序列化与反序列化

由于**所有表达式都是类定义**，且在实例化时**收集了全部参数**，因此表达式对象天然具备**序列化 / 反序列化**的能力——这是「自包含」设计原则的直接推论。

表达式可序列化为三种形态，并可从这些形态还原为等价的表达式对象：

| 形态 | 入口 | 说明 |
|------|------|------|
| 字典（spec） | `serialize(expr)` / `deserialize(spec, dialect)` | JSON 兼容字典结构 |
| JSON 字符串 | `serialize_json(expr)` / `deserialize_json(s, dialect)` | 便于网络传输与存储 |
| XML | `serialize_xml(expr)` / `deserialize_xml(x, dialect)` | 便于跨语言系统互操作 |

要点：

- **方言不参与序列化**：方言必须在反序列化时提供（`dialect` 参数），因为 SQL 生成取决于方言
- 嵌套表达式、元组、`cast()` 链、dataclass 值、非 JSON 原生标量均通过预留的保留键（`__expr__`、`__tuple__`、`__cast__`、`__vdc__`、`__value__`）完整往返
- 序列化使表达式可以**跨进程、跨机器、跨语言**传递，为查询模板化、缓存与分布式场景提供基础

> 序列化的完整规范（spec 格式、嵌套/元组标记、安全考虑与注册表机制）见 [表达式序列化](serialization.md)，自定义表达式接入序列化见[扩展指南](extending.md)。

## 模块 (Modules)

- [**核心 (Core)**](core.md): 基类、协议、混入 (Mixins) 和基础运算符。
- [**语句 (Statements)**](statements.md): 顶层 SQL 语句 (SELECT, INSERT, UPDATE, DELETE, MERGE 等)。
- [**子句 (Clauses)**](clauses.md): 查询组件，如 WHERE, JOIN, GROUP BY, ORDER BY。
- [**谓词 (Predicates)**](predicates.md): 用于过滤的布尔表达式 (比较, 逻辑运算, LIKE, IN 等)。
- [**函数 (Functions)**](functions.md): SQL 函数构建器 (COUNT, SUM, 字符串函数等)。
- [**数据类型 (Data Types)**](types.md): 通用与后端特定数据类型，及二者的配合关系。
- [**高级功能 (Advanced)**](advanced.md): 高级特性，如窗口函数, CTE, JSON 操作和图查询。

## 使用概览 (Usage Overview)

表达式系统允许您以编程方式组合查询：

```python
from rhosocial.activerecord.backend.expression import (
    QueryExpression, TableExpression, Column, Literal
)

# SELECT name, age FROM users WHERE age >= 18
query = QueryExpression(
    dialect,
    select=[Column(dialect, "name"), Column(dialect, "age")],
    from_=TableExpression(dialect, "users"),
    where=Column(dialect, "age") >= Literal(dialect, 18)
)
sql, params = query.to_sql()
# sql: 'SELECT "name", "age" FROM "users" WHERE "age" >= ?'
# params: (18,)
```