# Function Factories

This document describes the factory functions defined in `src/rhosocial/activerecord/backend/expression/functions.py`. These functions provide a convenient way to create aggregate and scalar function expressions.

## Overview

The `functions` module provides factory functions that simplify the creation of SQL function calls. Instead of manually instantiating `FunctionCall` or `AggregateFunctionCall` objects, you can use these helpers which handle type conversion and provide a more Pythonic interface.

## Aggregate Functions

### AggregateFunctionCall

Represents a call to a SQL aggregate function. Supports `FILTER` (WHERE) clauses.

```python
class AggregateFunctionCall(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", func_name: str, *args, is_distinct: bool = False, alias: Optional[str] = None): ...

    def filter(self, predicate: "SQLPredicate") -> 'AggregateFunctionCall':
        """Applies a FILTER (WHERE ...) clause to the aggregate expression."""
        ...
```

**Example:**
```python
# COUNT with FILTER
active_count = count(dialect, "*", alias="active_count").filter(
    Column(dialect, "status") == Literal(dialect, "active")
)
sql, params = active_count.to_sql()
# sql: 'COUNT(*) FILTER (WHERE "status" = ?) AS "active_count"'
# params: ("active",)

# SUM with multiple chained filters
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

Creates a `COUNT` aggregate function call.

```python
def count(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"] = "*", is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

**Usage Rules:**
- `count(dialect, "*")` -> `COUNT(*)`
- `count(dialect, Column(dialect, "id"))` -> `COUNT(id)`
- `count(dialect, "val")` -> `COUNT('val')` (Literal)

**Example:**
```python
# Basic COUNT(*)
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

Creates a `SUM` aggregate function call. Note the trailing underscore to avoid conflict with Python's built-in `sum`.

```python
def sum_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

**Example:**
```python
s = sum_(dialect, Column(dialect, "amount"))
sql, params = s.to_sql()
# sql: 'SUM("amount")'
# params: ()
```

### avg

Creates an `AVG` aggregate function call.

```python
def avg(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

**Example:**
```python
a = avg(dialect, Column(dialect, "score"), is_distinct=True, alias="avg_score")
sql, params = a.to_sql()
# sql: 'AVG(DISTINCT "score") AS "avg_score"'
# params: ()
```

### min_

Creates a `MIN` aggregate function call. Note the trailing underscore.

```python
def min_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

**Example:**
```python
m = min_(dialect, Column(dialect, "price"))
sql, params = m.to_sql()
# sql: 'MIN("price")'
# params: ()
```

### max_

Creates a `MAX` aggregate function call. Note the trailing underscore.

```python
def max_(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

**Example:**
```python
m = max_(dialect, Column(dialect, "price"))
sql, params = m.to_sql()
# sql: 'MAX("price")'
# params: ()
```

## String Functions

### concat

Creates a `CONCAT` scalar function call.

```python
def concat(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
c = concat(dialect, Column(dialect, "first_name"), " ", Column(dialect, "last_name"))
sql, params = c.to_sql()
# sql: 'CONCAT("first_name", ?, "last_name")'
# params: (" ",)
```

### coalesce

Creates a `COALESCE` scalar function call.

```python
def coalesce(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
c = coalesce(dialect, Column(dialect, "nickname"), Column(dialect, "real_name"), "Anonymous")
sql, params = c.to_sql()
# sql: 'COALESCE("nickname", "real_name", ?)'
# params: ("Anonymous",)
```

### length

Creates a `LENGTH` scalar function call.

```python
def length(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
l = length(dialect, Column(dialect, "description"))
sql, params = l.to_sql()
# sql: 'LENGTH("description")'
# params: ()
```

### substring

Creates a `SUBSTRING` scalar function call.

```python
def substring(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], start: Union[int, "bases.BaseExpression"], length: Optional[Union[int, "bases.BaseExpression"]] = None) -> "core.FunctionCall": ...
```

**Example:**
```python
# With length
s1 = substring(dialect, Column(dialect, "text"), 1, 5)
sql, params = s1.to_sql()
# sql: 'SUBSTRING("text", ?, ?)'
# params: (1, 5)

# Without length
s2 = substring(dialect, Column(dialect, "text"), 5)
sql, params = s2.to_sql()
# sql: 'SUBSTRING("text", ?)'
# params: (5,)
```

### trim

Creates a `TRIM` scalar function call.

```python
def trim(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], chars: Optional[Union[str, "bases.BaseExpression"]] = None, direction: str = "BOTH") -> "operators.RawSQLExpression": ...
```

**Example:**
```python
# Default trim (spaces from both sides)
t1 = trim(dialect, Column(dialect, "name"))
sql, params = t1.to_sql()
# sql: 'TRIM(BOTH FROM "name")'
# params: ()

# Custom trim
t2 = trim(dialect, Column(dialect, "name"), chars=".", direction="LEADING")
sql, params = t2.to_sql()
# sql: 'TRIM(LEADING ? FROM "name")'
# params: (".",)
```

### replace

Creates a `REPLACE` scalar function call.

```python
def replace(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], pattern: Union[str, "bases.BaseExpression"], replacement: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
r = replace(dialect, Column(dialect, "content"), "http", "https")
sql, params = r.to_sql()
# sql: 'REPLACE("content", ?, ?)'
# params: ("http", "https")
```

### upper

Creates an `UPPER` scalar function call.

```python
def upper(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
u = upper(dialect, Column(dialect, "email"))
sql, params = u.to_sql()
# sql: 'UPPER("email")'
# params: ()
```

### lower

Creates a `LOWER` scalar function call.

```python
def lower(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
l = lower(dialect, Column(dialect, "email"))
sql, params = l.to_sql()
# sql: 'LOWER("email")'
# params: ()
```

### initcap

Creates an `INITCAP` scalar function call (title case).

```python
def initcap(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
i = initcap(dialect, Column(dialect, "title"))
sql, params = i.to_sql()
# sql: 'INITCAP("title")'
# params: ()
```

### left

Creates a `LEFT` scalar function call.

```python
def left(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], n: int) -> "core.FunctionCall": ...
```

**Example:**
```python
l = left(dialect, Column(dialect, "code"), 3)
sql, params = l.to_sql()
# sql: 'LEFT("code", ?)'
# params: (3,)
```

### right

Creates a `RIGHT` scalar function call.

```python
def right(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], n: int) -> "core.FunctionCall": ...
```

**Example:**
```python
r = right(dialect, Column(dialect, "code"), 4)
sql, params = r.to_sql()
# sql: 'RIGHT("code", ?)'
# params: (4,)
```

### lpad

Creates an `LPAD` scalar function call.

```python
def lpad(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], length: int, pad: Optional[str] = None) -> "core.FunctionCall": ...
```

**Example:**
```python
p = lpad(dialect, Column(dialect, "id"), 5, "0")
sql, params = p.to_sql()
# sql: 'LPAD("id", ?, ?)'
# params: (5, "0")
```
