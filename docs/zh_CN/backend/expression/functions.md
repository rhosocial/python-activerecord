# 函数工厂 (Function Factories)

本文档描述了定义在 `src/rhosocial/activerecord/backend/expression/functions.py` 中的工厂函数。这些函数提供了一种创建聚合函数和标量函数表达式的便捷方式。

## 概述

`functions` 模块提供了简化 SQL 函数调用创建的工厂函数。您可以使用这些助手函数来代替手动实例化 `FunctionCall` 或 `AggregateFunctionCall` 对象，它们处理类型转换并提供更符合 Python 习惯的接口。

## 聚合函数 (Aggregate Functions)

### AggregateFunctionCall

表示 SQL 聚合函数调用。支持 `FILTER` (WHERE) 子句。

```python
class AggregateFunctionCall(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", func_name: str, *args, is_distinct: bool = False, alias: Optional[str] = None): ...

    def filter(self, predicate: "SQLPredicate") -> 'AggregateFunctionCall':
        """应用 FILTER (WHERE ...) 子句到聚合表达式。"""
        ...
```

**示例:**
```python
# 带 FILTER 的 COUNT
active_count = count(dialect, "*", alias="active_count").filter(
    Column(dialect, "status") == Literal(dialect, "active")
)
sql, params = active_count.to_sql()
# sql: 'COUNT(*) FILTER (WHERE "status" = ?) AS "active_count"'
# params: ("active",)

# 带多个链式过滤器的 SUM
high_value_sum = sum_(dialect, Column(dialect, "amount"), alias="high_value_sum").filter(
    Column(dialect, "category") == Literal(dialect, "sales")
).filter(
    Column(dialect, "priority") == Literal(dialect, True)
)
sql, params = high_value_sum.to_sql()
# sql: 'SUM("amount") FILTER (WHERE "category" = ? AND "priority" = ?) AS "high_value_sum"'
# params: ("sales", True)
```

### count

创建 `COUNT` 聚合函数调用。

```python
def count(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"] = "*", is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

**使用规则:**
- `count(dialect, "*")` -> `COUNT(*)`
- `count(dialect, Column(dialect, "id"))` -> `COUNT(id)`
- `count(dialect, "val")` -> `COUNT('val')` (字面量)

**示例:**
```python
# 基本 COUNT(*)
c1 = count(dialect, "*")
sql, params = c1.to_sql()
# sql: 'COUNT(*)'
# params: ()

# COUNT(DISTINCT col)
c2 = count(dialect, Column(dialect, "id"), is_distinct=True, alias="unique_users")
sql, params = c2.to_sql()
# sql: 'COUNT(DISTINCT "id") AS "unique_users"'
# params: ()
```

### sum_

创建 `SUM` 聚合函数调用。注意尾随下划线以避免与 Python 内置的 `sum` 冲突。

```python
def sum_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

**示例:**
```python
s = sum_(dialect, Column(dialect, "amount"))
sql, params = s.to_sql()
# sql: 'SUM("amount")'
# params: ()
```

### avg

创建 `AVG` 聚合函数调用。

```python
def avg(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

**示例:**
```python
a = avg(dialect, Column(dialect, "score"), is_distinct=True, alias="avg_score")
sql, params = a.to_sql()
# sql: 'AVG(DISTINCT "score") AS "avg_score"'
# params: ()
```

### min_

创建 `MIN` 聚合函数调用。注意尾随下划线。

```python
def min_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

**示例:**
```python
m = min_(dialect, Column(dialect, "price"))
sql, params = m.to_sql()
# sql: 'MIN("price")'
# params: ()
```

### max_

创建 `MAX` 聚合函数调用。注意尾随下划线。

```python
def max_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

**示例:**
```python
m = max_(dialect, Column(dialect, "price"))
sql, params = m.to_sql()
# sql: 'MAX("price")'
# params: ()
```

## 字符串函数 (String Functions)

### concat

创建 `CONCAT` 标量函数调用。

```python
def concat(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
c = concat(dialect, Column(dialect, "first_name"), " ", Column(dialect, "last_name"))
sql, params = c.to_sql()
# sql: 'CONCAT("first_name", ?, "last_name")'
# params: (" ",)
```

### coalesce

创建 `COALESCE` 标量函数调用。

```python
def coalesce(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
c = coalesce(dialect, Column(dialect, "nickname"), Column(dialect, "real_name"), "Anonymous")
sql, params = c.to_sql()
# sql: 'COALESCE("nickname", "real_name", ?)'
# params: ("Anonymous",)
```

### length

创建 `LENGTH` 标量函数调用。

```python
def length(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
l = length(dialect, Column(dialect, "description"))
sql, params = l.to_sql()
# sql: 'LENGTH("description")'
# params: ()
```

### substring

创建 `SUBSTRING` 标量函数调用。

```python
def substring(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], start: Union[int, "bases.BaseExpression"], length: Optional[Union[int, "bases.BaseExpression"]] = None) -> "core.FunctionCall": ...
```

**示例:**
```python
# 指定长度
s1 = substring(dialect, Column(dialect, "text"), 1, 5)
sql, params = s1.to_sql()
# sql: 'SUBSTRING("text", ?, ?)'
# params: (1, 5)

# 不指定长度
s2 = substring(dialect, Column(dialect, "text"), 5)
sql, params = s2.to_sql()
# sql: 'SUBSTRING("text", ?)'
# params: (5,)
```

### trim

创建 `TRIM` 标量函数调用。

```python
def trim(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], chars: Optional[Union[str, "bases.BaseExpression"]] = None, direction: str = "BOTH") -> "operators.RawSQLExpression": ...
```

**示例:**
```python
# 默认 TRIM (去除两侧空格)
t1 = trim(dialect, Column(dialect, "name"))
sql, params = t1.to_sql()
# sql: 'TRIM(BOTH FROM "name")'
# params: ()

# 自定义 TRIM
t2 = trim(dialect, Column(dialect, "name"), chars=".", direction="LEADING")
sql, params = t2.to_sql()
# sql: 'TRIM(LEADING ? FROM "name")'
# params: (".",)
```

### replace

创建 `REPLACE` 标量函数调用。

```python
def replace(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], pattern: Union[str, "bases.BaseExpression"], replacement: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
r = replace(dialect, Column(dialect, "content"), "http", "https")
sql, params = r.to_sql()
# sql: 'REPLACE("content", ?, ?)'
# params: ("http", "https")
```

### upper

创建 `UPPER` 标量函数调用。

```python
def upper(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
u = upper(dialect, Column(dialect, "email"))
sql, params = u.to_sql()
# sql: 'UPPER("email")'
# params: ()
```

### lower

创建 `LOWER` 标量函数调用。

```python
def lower(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
l = lower(dialect, Column(dialect, "email"))
sql, params = l.to_sql()
# sql: 'LOWER("email")'
# params: ()
```

### initcap

创建 `INITCAP` 标量函数调用 (首字母大写)。

```python
def initcap(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
i = initcap(dialect, Column(dialect, "title"))
sql, params = i.to_sql()
# sql: 'INITCAP("title")'
# params: ()
```

### left

创建 `LEFT` 标量函数调用。

```python
def left(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], n: int) -> "core.FunctionCall": ...
```

**示例:**
```python
l = left(dialect, Column(dialect, "code"), 3)
sql, params = l.to_sql()
# sql: 'LEFT("code", ?)'
# params: (3,)
```

### right

创建 `RIGHT` 标量函数调用。

```python
def right(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], n: int) -> "core.FunctionCall": ...
```

**示例:**
```python
r = right(dialect, Column(dialect, "code"), 4)
sql, params = r.to_sql()
# sql: 'RIGHT("code", ?)'
# params: (4,)
```

### lpad

创建 `LPAD` 标量函数调用。

```python
def lpad(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], length: int, pad: Optional[str] = None) -> "core.FunctionCall": ...
```

**示例:**
```python
p = lpad(dialect, Column(dialect, "id"), 5, "0")
sql, params = p.to_sql()
# sql: 'LPAD("id", ?, ?)'
# params: (5, "0")
```
