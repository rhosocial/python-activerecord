# 谓词表达式 (Predicates)

本文档描述了定义在 `src/rhosocial/activerecord/backend/expression/predicates.py` 中的谓词表达式类。这些类表示用于 `WHERE`、`HAVING` 和 `ON` 子句中的 SQL 条件。

## 概述

谓词是计算结果为布尔值（TRUE、FALSE 或 UNKNOWN/NULL）的表达式。它们是 SQL 查询中过滤逻辑的构建块。所有谓词类都继承自 `bases.SQLPredicate`。

## 类说明

### ComparisonPredicate

表示两个表达式之间的标准比较操作。

```python
class ComparisonPredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", op: str, left: "SQLValueExpression", right: "SQLValueExpression"): ...
```

**参数:**
- `dialect`: SQL 方言实例。
- `op`: 比较运算符 (例如 `=`, `>`, `<`, `>=`, `<=`, `<>`)。
- `left`: 左侧表达式。
- `right`: 右侧表达式。

**示例:**
```python
# users.age >= 18
    pred = ComparisonPredicate(dialect, ">=", Column(dialect, "age"), Literal(dialect, 18))
    # -> ('"age" >= ?', (18,))
```

### LogicalPredicate

表示组合其他谓词的逻辑操作。

```python
class LogicalPredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", op: str, *predicates: "bases.SQLPredicate"): ...
```

**参数:**
- `dialect`: SQL 方言实例。
- `op`: 逻辑运算符 (例如 `AND`, `OR`, `NOT`)。
- `*predicates`: 一个或多个要组合的谓词。

**示例:**
```python
# (age >= 18) AND (status = 'active')
    pred1 = ComparisonPredicate(dialect, ">=", Column(dialect, "age"), Literal(dialect, 18))
    pred2 = ComparisonPredicate(dialect, "=", Column(dialect, "status"), Literal(dialect, "active"))
    combined = LogicalPredicate(dialect, "AND", pred1, pred2)
    # -> ('"age" >= ? AND "status" = ?', (18, 'active'))
```

### LikePredicate

表示模式匹配操作 (`LIKE`, `ILIKE`)。

```python
class LikePredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", op: str, expr: "SQLValueExpression", pattern: "SQLValueExpression"): ...
```

**参数:**
- `dialect`: SQL 方言实例。
- `op`: 运算符 (`LIKE`, `ILIKE`, `NOT LIKE` 等)。
- `expr`: 要测试的表达式。
- `pattern`: 要匹配的模式。

**示例:**
```python
# name LIKE 'User%'
    pred = LikePredicate(dialect, "LIKE", Column(dialect, "name"), Literal(dialect, "User%"))
    # -> ('"name" LIKE ?', ('User%',))
```

### InPredicate

表示集合成员测试 (`IN`)。

```python
class InPredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", expr: "SQLValueExpression", values: "bases.BaseExpression"): ...
```

**参数:**
- `dialect`: SQL 方言实例。
- `expr`: 要测试的表达式。
- `values`: 包含集合（列表/元组）的 `Literal` 或子查询表达式。

**示例:**
```python
# status IN ('active', 'pending')
pred = InPredicate(dialect, Column(dialect, "status"), Literal(dialect, ["active", "pending"]))
```

### BetweenPredicate

表示范围测试 (`BETWEEN`)。

```python
class BetweenPredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", low: "bases.BaseExpression", high: "bases.BaseExpression"): ...
```

**参数:**
- `dialect`: SQL 方言实例。
- `expr`: 要测试的表达式。
- `low`: 下界。
- `high`: 上界。

**示例:**
```python
# age BETWEEN 18 AND 65
pred = BetweenPredicate(dialect, Column(dialect, "age"), Literal(dialect, 18), Literal(dialect, 65))
```

### IsNullPredicate

表示 NULL 测试 (`IS NULL`, `IS NOT NULL`)。

```python
class IsNullPredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", is_not: bool = False): ...
```

**参数:**
- `dialect`: SQL 方言实例。
- `expr`: 要测试的表达式。
- `is_not`: 如果为 `True`，创建 `IS NOT NULL`。默认为 `False` (`IS NULL`)。

**示例:**
```python
# email IS NOT NULL
    pred = IsNullPredicate(dialect, Column(dialect, "email"), is_not=True)
    # -> ('"email" IS NOT NULL', ())
```
