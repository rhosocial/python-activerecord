# 表达式系统 (Expression System)

表达式系统提供了一种与数据库无关的方式，使用 Python 对象构建 SQL 查询。它处理 SQL 生成、参数绑定和方言特定的差异。

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
