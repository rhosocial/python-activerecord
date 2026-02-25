# 表达式系统 (Expression System)

表达式系统提供了一种与数据库无关的方式，使用 Python 对象构建 SQL 查询。它处理 SQL 生成、参数绑定和方言特定的差异。

## 主要特性

- **无状态设计**: 表达式对象是纯函数，没有内部状态，消除了复杂对象状态管理的需求
- **直接 SQL 生成**: 从表达式到 SQL 只需 2 步，避免了多层编译架构
- **灵活的片段生成**: 任何表达式都可以独立调用 `to_sql()` 生成 SQL 片段，不像某些系统需要完整查询编译
- **用户控制**: 用户完全控制何时以及如何生成 SQL，没有隐藏的自动行为
- **显式优于隐式**: 没有隐藏的状态管理、自动编译或复杂的对象生命周期跟踪
- **无隐藏行为**: 没有自动刷新或隐藏的数据库操作，不像某些系统有自动会话管理

## 重要说明

- [**限制与注意事项**](limitations.md): 关于表达式系统边界和责任的关键信息。

## 设计哲学：显式优于隐式

我们的表达式系统遵循显式控制优于隐式行为的原则：
- 没有隐藏的状态管理或对象生命周期跟踪
- 没有自动查询编译或缓存机制
- 没有复杂的对象状态转换
- 用户对 SQL 生成有完全的可见性和控制权
- 与具有复杂多阶段编译的系统不同，我们的方法直接且可预测

## 模块 (Modules)

- [**核心 (Core)**](core.md): 基类、协议、混入 (Mixins) 和基础运算符。
- [**语句 (Statements)**](statements.md): 顶层 SQL 语句 (SELECT, INSERT, UPDATE, DELETE, MERGE 等)。
- [**子句 (Clauses)**](clauses.md): 查询组件，如 WHERE, JOIN, GROUP BY, ORDER BY。
- [**谓词 (Predicates)**](predicates.md): 用于过滤的布尔表达式 (比较, 逻辑运算, LIKE, IN 等)。
- [**函数 (Functions)**](functions.md): SQL 函数构建器 (COUNT, SUM, 字符串函数等)。
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
