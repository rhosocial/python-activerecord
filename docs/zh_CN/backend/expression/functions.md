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

### rpad

创建 `RPAD` 标量函数调用。

```python
def rpad(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], length: int, pad: Optional[str] = None) -> "core.FunctionCall": ...
```

**示例:**
```python
p = rpad(dialect, Column(dialect, "id"), 5, " ")
sql, params = p.to_sql()
# sql: 'RPAD("id", ?, ?)'
# params: (5, " ")
```

### reverse

创建 `REVERSE` 标量函数调用。

```python
def reverse(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
r = reverse(dialect, Column(dialect, "text"))
sql, params = r.to_sql()
# sql: 'REVERSE("text")'
# params: ()
```

### strpos

创建 `STRPOS` 标量函数调用 (查找子字符串位置)。

```python
def strpos(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], substring: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
p = strpos(dialect, Column(dialect, "text"), "world")
sql, params = p.to_sql()
# sql: 'STRPOS("text", ?)'
# params: ("world",)
```

## 数学函数 (Math Functions)

### abs_

创建 `ABS` 标量函数调用。注意尾随下划线以避免与 Python 内置的 `abs` 冲突。

```python
def abs_(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
a = abs_(dialect, -5)
sql, params = a.to_sql()
# sql: 'ABS(?)'
# params: (-5,)
```

### round_

创建 `ROUND` 标量函数调用。注意尾随下划线。

```python
def round_(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"], decimals: Optional[int] = None) -> "core.FunctionCall": ...
```

**示例:**
```python
r = round_(dialect, 3.14159, 2)
sql, params = r.to_sql()
# sql: 'ROUND(?, ?)'
# params: (3.14159, 2)
```

### ceil

创建 `CEIL` 标量函数调用。

```python
def ceil(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
c = ceil(dialect, 3.14)
sql, params = c.to_sql()
# sql: 'CEIL(?)'
# params: (3.14,)
```

### floor

创建 `FLOOR` 标量函数调用。

```python
def floor(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
f = floor(dialect, 3.99)
sql, params = f.to_sql()
# sql: 'FLOOR(?)'
# params: (3.99,)
```

### sqrt

创建 `SQRT` 标量函数调用。

```python
def sqrt(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
s = sqrt(dialect, 16)
sql, params = s.to_sql()
# sql: 'SQRT(?)'
# params: (16,)
```

### power

创建 `POWER` 标量函数调用。

```python
def power(dialect: "SQLDialectBase", base: Union[int, float, "bases.BaseExpression"], exponent: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
p = power(dialect, 2, 3)
sql, params = p.to_sql()
# sql: 'POWER(?, ?)'
# params: (2, 3)
```

### exp

创建 `EXP` 标量函数调用。

```python
def exp(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
e = exp(dialect, 1)
sql, params = e.to_sql()
# sql: 'EXP(?)'
# params: (1,)
```

### log

创建 `LOG` 标量函数调用。

```python
def log(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"], base: Optional[Union[int, float, "bases.BaseExpression"]] = None) -> "core.FunctionCall": ...
```

**示例:**
```python
l = log(dialect, 100, 10)
sql, params = l.to_sql()
# sql: 'LOG(?, ?)'
# params: (100, 10)
```

### sin, cos, tan

创建三角函数调用。

```python
def sin(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def cos(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def tan(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
s = sin(dialect, 0)
c = cos(dialect, 0)
t = tan(dialect, 0)
```

## 日期时间函数 (Date/Time Functions)

### now

创建 `NOW` 标量函数调用。

```python
def now(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
```

**示例:**
```python
n = now(dialect)
sql, params = n.to_sql()
# sql: 'NOW()'
# params: ()
```

### current_date

创建 `CURRENT_DATE` 标量函数调用。

```python
def current_date(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
```

**示例:**
```python
d = current_date(dialect)
sql, params = d.to_sql()
# sql: 'CURRENT_DATE'
# params: ()
```

### current_time

创建 `CURRENT_TIME` 标量函数调用。

```python
def current_time(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
```

**示例:**
```python
t = current_time(dialect)
sql, params = t.to_sql()
# sql: 'CURRENT_TIME'
# params: ()
```

### year, month, day, hour, minute, second

创建提取日期部分的函数调用。

```python
def year(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def month(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def day(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def hour(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def minute(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def second(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
y = year(dialect, Column(dialect, "created_at"))
sql, params = y.to_sql()
# sql: 'YEAR("created_at")'
# params: ()
```

### date_part

创建 `DATE_PART` 标量函数调用。

```python
def date_part(dialect: "SQLDialectBase", field: str, expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
p = date_part(dialect, "year", Column(dialect, "created_at"))
sql, params = p.to_sql()
# sql: 'DATE_PART(?, "created_at")'
# params: ("year",)
```

### date_trunc

创建 `DATE_TRUNC` 标量函数调用。

```python
def date_trunc(dialect: "SQLDialectBase", precision: str, expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
t = date_trunc(dialect, "month", Column(dialect, "created_at"))
sql, params = t.to_sql()
# sql: 'DATE_TRUNC(?, "created_at")'
# params: ("month",)
```

## 条件函数 (Conditional Functions)

### case

创建 `CASE` 表达式。

```python
def case(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "core.CaseExpression": ...
```

**示例:**
```python
c = case(dialect).when(Column(dialect, "status") == "active", "Active").else_("Inactive")
sql, params = c.to_sql()
```

### nullif

创建 `NULLIF` 标量函数调用。

```python
def nullif(dialect: "SQLDialectBase", expr1: Union[str, "bases.BaseExpression"], expr2: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
n = nullif(dialect, Column(dialect, "value"), "N/A")
sql, params = n.to_sql()
# sql: 'NULLIF("value", ?)'
# params: ("N/A",)
```

### greatest

创建 `GREATEST` 标量函数调用。

```python
def greatest(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
g = greatest(dialect, Column(dialect, "a"), Column(dialect, "b"), Column(dialect, "c"))
sql, params = g.to_sql()
# sql: 'GREATEST("a", "b", "c")'
# params: ()
```

### least

创建 `LEAST` 标量函数调用。

```python
def least(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
l = least(dialect, Column(dialect, "a"), Column(dialect, "b"), Column(dialect, "c"))
sql, params = l.to_sql()
# sql: 'LEAST("a", "b", "c")'
# params: ()
```

## 窗口函数 (Window Functions)

### row_number

创建 `ROW_NUMBER` 窗口函数调用。

```python
def row_number(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
```

**示例:**
```python
r = row_number(dialect)
sql, params = r.to_sql()
# sql: 'ROW_NUMBER()'
# params: ()
```

### rank, dense_rank

创建 `RANK` 和 `DENSE_RANK` 窗口函数调用。

```python
def rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
def dense_rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
```

### lag, lead

创建 `LAG` 和 `LEAD` 窗口函数调用。

```python
def lag(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], offset: Optional[int] = 1, default: Optional[Union[str, "bases.BaseExpression"]] = None, alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
def lead(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], offset: Optional[int] = 1, default: Optional[Union[str, "bases.BaseExpression"]] = None, alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
```

### first_value, last_value, nth_value

创建值窗口函数调用。

```python
def first_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
def last_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
def nth_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], n: int, alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
```

## JSON 函数 (JSON Functions)

### json_extract, json_extract_text

创建 JSON 提取函数调用。

```python
def json_extract(dialect: "SQLDialectBase", expr: "bases.BaseExpression", path: str) -> "operators.BinaryExpression": ...
def json_extract_text(dialect: "SQLDialectBase", expr: "bases.BaseExpression", path: str) -> "operators.BinaryExpression": ...
```

**示例:**
```python
j = json_extract(dialect, Column(dialect, "data"), "$.name")
sql, params = j.to_sql()
# 使用 -> 操作符提取 JSON 值
```

### json_build_object

创建 `JSON_BUILD_OBJECT` 函数调用。

```python
def json_build_object(dialect: "SQLDialectBase", *args: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

### json_array_elements

创建 `JSON_ARRAY_ELEMENTS` 函数调用。

```python
def json_array_elements(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

### json_objectagg, json_arrayagg

创建 JSON 聚合函数调用。

```python
def json_objectagg(dialect: "SQLDialectBase", key_expr: Union[str, "bases.BaseExpression"], value_expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
def json_arrayagg(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

## 数组函数 (Array Functions)

### array_agg

创建 `ARRAY_AGG` 聚合函数调用。

```python
def array_agg(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

### unnest

创建 `UNNEST` 函数调用。

```python
def unnest(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

### array_length

创建 `ARRAY_LENGTH` 函数调用。

```python
def array_length(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], dimension: int = 1) -> "core.FunctionCall": ...
```

## 类型转换函数 (Type Conversion Functions)

### cast

创建类型转换表达式。

```python
def cast(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], type_name: str) -> "core.Column": ...
```

**示例:**
```python
c = cast(dialect, Column(dialect, "value"), "INTEGER")
sql, params = c.to_sql()
# sql: 'CAST("value" AS INTEGER)'
# params: ()
```

### to_char

创建 `TO_CHAR` 函数调用。

```python
def to_char(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], format: Optional[str] = None) -> "core.FunctionCall": ...
```

### to_number

创建 `TO_NUMBER` 函数调用。

```python
def to_number(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], format: Optional[str] = None) -> "core.FunctionCall": ...
```

### to_date

创建 `TO_DATE` 函数调用。

```python
def to_date(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], format: Optional[str] = None) -> "core.FunctionCall": ...
```

## 分组函数 (Grouping Functions)

### rollup

创建 `ROLLUP` 分组表达式。

```python
def rollup(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "query_parts.GroupingExpression": ...
```

**示例:**
```python
r = rollup(dialect, Column(dialect, "department"), Column(dialect, "region"))
sql, params = r.to_sql()
# sql: 'ROLLUP("department", "region")'
# params: ()
```

### cube

创建 `CUBE` 分组表达式。

```python
def cube(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "query_parts.GroupingExpression": ...
```

### grouping_sets

创建 `GROUPING SETS` 分组表达式。

```python
def grouping_sets(dialect: "SQLDialectBase", *sets: List[Union[str, "bases.BaseExpression"]]) -> "query_parts.GroupingExpression": ...
```

## 字符串连接操作符 (String Concatenation Operator)

### concat_op

使用 `||` 操作符创建字符串连接表达式。

```python
def concat_op(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "operators.BinaryExpression": ...
```

**示例:**
```python
# 连接两列
expr = concat_op(dialect, Column(dialect, "first_name"), Column(dialect, "last_name"))
sql, params = expr.to_sql()
# sql: '"first_name" || "last_name"'
# params: ()

# 连接多列和字面量
expr = concat_op(dialect, Column(dialect, "first_name"), " ", Column(dialect, "last_name"))
sql, params = expr.to_sql()
# sql: '"first_name" || ? || "last_name"'
# params: (" ",)
```

---

## SQL 标准新增函数 (Additional SQL Standard Functions)

以下函数是 SQL:2003 标准中定义但之前未实现的函数。

### mod

创建 `MOD` 函数调用 (取模运算)。

```python
def mod(dialect: "SQLDialectBase", dividend: Union[int, float, "bases.BaseExpression"], divisor: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
m = mod(dialect, 10, 3)
sql, params = m.to_sql()
# sql: 'MOD(?, ?)'
# params: (10, 3)
```

### sign

创建 `SIGN` 函数调用 (返回 -1, 0, 或 1)。

```python
def sign(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
s = sign(dialect, -42)
sql, params = s.to_sql()
# sql: 'SIGN(?)'
# params: (-42,)
```

### truncate

创建 `TRUNCATE` 函数调用 (截断数字)。

```python
def truncate(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"], precision: Optional[int] = None) -> "core.FunctionCall": ...
```

**示例:**
```python
t = truncate(dialect, 3.14159, 2)
sql, params = t.to_sql()
# sql: 'TRUNCATE(?, ?)'
# params: (3.14159, 2)
```

### chr_

创建 `CHR` 函数调用 (ASCII 码转字符)。注意尾随下划线。

```python
def chr_(dialect: "SQLDialectBase", code: Union[int, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
c = chr_(dialect, 65)  # 返回 'A'
sql, params = c.to_sql()
# sql: 'CHR(?)'
# params: (65,)
```

### ascii

创建 `ASCII` 函数调用 (字符转 ASCII 码)。

```python
def ascii(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
a = ascii(dialect, "A")
sql, params = a.to_sql()
# sql: 'ASCII(?)'
# params: ("A",)
```

### octet_length

创建 `OCTET_LENGTH` 函数调用 (返回字节长度)。

```python
def octet_length(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
o = octet_length(dialect, Column(dialect, "text"))
sql, params = o.to_sql()
# sql: 'OCTET_LENGTH("text")'
# params: ()
```

### bit_length

创建 `BIT_LENGTH` 函数调用 (返回位长度)。

```python
def bit_length(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
b = bit_length(dialect, Column(dialect, "text"))
sql, params = b.to_sql()
# sql: 'BIT_LENGTH("text")'
# params: ()
```

### position

创建 `POSITION` 函数调用 (查找子字符串位置，1-based)。

```python
def position(dialect: "SQLDialectBase", substring: Union[str, "bases.BaseExpression"], expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
p = position(dialect, "world", Column(dialect, "text"))
sql, params = p.to_sql()
# sql: 'POSITION(?, "text")'
# params: ("world",)
```

### overlay

创建 `OVERLAY` 函数调用 (替换子字符串)。

```python
def overlay(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], replacement: Union[str, "bases.BaseExpression"], start: int, length: Optional[int] = None) -> "core.FunctionCall": ...
```

**示例:**
```python
o = overlay(dialect, Column(dialect, "text"), "xxx", 1, 3)
sql, params = o.to_sql()
# sql: 'OVERLAY("text", ?, ?, ?)'
# params: ("xxx", 1, 3)
```

### translate

创建 `TRANSLATE` 函数调用 (字符替换)。

```python
def translate(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], from_chars: str, to_chars: str) -> "core.FunctionCall": ...
```

**示例:**
```python
t = translate(dialect, Column(dialect, "text"), "abc", "xyz")
sql, params = t.to_sql()
# sql: 'TRANSLATE("text", ?, ?)'
# params: ("abc", "xyz")
```

### repeat

创建 `REPEAT` 函数调用 (重复字符串)。

```python
def repeat(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], count: int) -> "core.FunctionCall": ...
```

**示例:**
```python
r = repeat(dialect, "ab", 3)
sql, params = r.to_sql()
# sql: 'REPEAT(?, ?)'
# params: ("ab", 3)
```

### space

创建 `SPACE` 函数调用 (生成空格)。

```python
def space(dialect: "SQLDialectBase", count: int) -> "core.FunctionCall": ...
```

**示例:**
```python
s = space(dialect, 5)
sql, params = s.to_sql()
# sql: 'SPACE(?)'
# params: (5,)
```

### current_timestamp

创建 `CURRENT_TIMESTAMP` 函数调用。

```python
def current_timestamp(dialect: "SQLDialectBase", precision: Optional[int] = None) -> "core.FunctionCall": ...
```

**示例:**
```python
c = current_timestamp(dialect, 6)
sql, params = c.to_sql()
# sql: 'CURRENT_TIMESTAMP(?)'
# params: (6,)
```

### localtimestamp

创建 `LOCALTIMESTAMP` 函数调用。

```python
def localtimestamp(dialect: "SQLDialectBase", precision: Optional[int] = None) -> "core.FunctionCall": ...
```

**示例:**
```python
l = localtimestamp(dialect)
sql, params = l.to_sql()
# sql: 'LOCALTIMESTAMP'
# params: ()
```

### extract

创建 `EXTRACT` 函数调用 (提取日期时间部分)。

```python
def extract(dialect: "SQLDialectBase", field: str, expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**示例:**
```python
e = extract(dialect, "YEAR", Column(dialect, "created_at"))
sql, params = e.to_sql()
# sql: 'EXTRACT(?, "created_at")'
# params: ("YEAR",)
```

### current_user, session_user, system_user

创建用户信息函数调用。

```python
def current_user(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
def session_user(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
def system_user(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
```

**示例:**
```python
u = current_user(dialect)
sql, params = u.to_sql()
# sql: 'CURRENT_USER'
# params: ()
```
