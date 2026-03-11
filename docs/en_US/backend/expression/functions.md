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

### rpad

Creates an `RPAD` scalar function call.

```python
def rpad(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], length: int, pad: Optional[str] = None) -> "core.FunctionCall": ...
```

**Example:**
```python
p = rpad(dialect, Column(dialect, "id"), 5, " ")
sql, params = p.to_sql()
# sql: 'RPAD("id", ?, ?)'
# params: (5, " ")
```

### reverse

Creates a `REVERSE` scalar function call.

```python
def reverse(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
r = reverse(dialect, Column(dialect, "text"))
sql, params = r.to_sql()
# sql: 'REVERSE("text")'
# params: ()
```

### strpos

Creates a `STRPOS` scalar function call (find substring position).

```python
def strpos(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], substring: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
p = strpos(dialect, Column(dialect, "text"), "world")
sql, params = p.to_sql()
# sql: 'STRPOS("text", ?)'
# params: ("world",)
```

## Math Functions

### abs_

Creates an `ABS` scalar function call. Note the trailing underscore to avoid conflict with Python's built-in `abs`.

```python
def abs_(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
a = abs_(dialect, -5)
sql, params = a.to_sql()
# sql: 'ABS(?)'
# params: (-5,)
```

### round_

Creates a `ROUND` scalar function call. Note the trailing underscore.

```python
def round_(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"], decimals: Optional[int] = None) -> "core.FunctionCall": ...
```

**Example:**
```python
r = round_(dialect, 3.14159, 2)
sql, params = r.to_sql()
# sql: 'ROUND(?, ?)'
# params: (3.14159, 2)
```

### ceil

Creates a `CEIL` scalar function call.

```python
def ceil(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
c = ceil(dialect, 3.14)
sql, params = c.to_sql()
# sql: 'CEIL(?)'
# params: (3.14,)
```

### floor

Creates a `FLOOR` scalar function call.

```python
def floor(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
f = floor(dialect, 3.99)
sql, params = f.to_sql()
# sql: 'FLOOR(?)'
# params: (3.99,)
```

### sqrt

Creates a `SQRT` scalar function call.

```python
def sqrt(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
s = sqrt(dialect, 16)
sql, params = s.to_sql()
# sql: 'SQRT(?)'
# params: (16,)
```

### power

Creates a `POWER` scalar function call.

```python
def power(dialect: "SQLDialectBase", base: Union[int, float, "bases.BaseExpression"], exponent: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
p = power(dialect, 2, 3)
sql, params = p.to_sql()
# sql: 'POWER(?, ?)'
# params: (2, 3)
```

### exp

Creates an `EXP` scalar function call.

```python
def exp(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
e = exp(dialect, 1)
sql, params = e.to_sql()
# sql: 'EXP(?)'
# params: (1,)
```

### log

Creates a `LOG` scalar function call.

```python
def log(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"], base: Optional[Union[int, float, "bases.BaseExpression"]] = None) -> "core.FunctionCall": ...
```

**Example:**
```python
l = log(dialect, 100, 10)
sql, params = l.to_sql()
# sql: 'LOG(?, ?)'
# params: (100, 10)
```

### sin, cos, tan

Creates trigonometric function calls.

```python
def sin(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def cos(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def tan(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
s = sin(dialect, 0)
c = cos(dialect, 0)
t = tan(dialect, 0)
```

## Date/Time Functions

### now

Creates a `NOW` scalar function call.

```python
def now(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
```

**Example:**
```python
n = now(dialect)
sql, params = n.to_sql()
# sql: 'NOW()'
# params: ()
```

### current_date

Creates a `CURRENT_DATE` scalar function call.

```python
def current_date(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
```

**Example:**
```python
d = current_date(dialect)
sql, params = d.to_sql()
# sql: 'CURRENT_DATE'
# params: ()
```

### current_time

Creates a `CURRENT_TIME` scalar function call.

```python
def current_time(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
```

**Example:**
```python
t = current_time(dialect)
sql, params = t.to_sql()
# sql: 'CURRENT_TIME'
# params: ()
```

### year, month, day, hour, minute, second

Creates date part extraction function calls.

```python
def year(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def month(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def day(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def hour(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def minute(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
def second(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
y = year(dialect, Column(dialect, "created_at"))
sql, params = y.to_sql()
# sql: 'YEAR("created_at")'
# params: ()
```

### date_part

Creates a `DATE_PART` scalar function call.

```python
def date_part(dialect: "SQLDialectBase", field: str, expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
p = date_part(dialect, "year", Column(dialect, "created_at"))
sql, params = p.to_sql()
# sql: 'DATE_PART(?, "created_at")'
# params: ("year",)
```

### date_trunc

Creates a `DATE_TRUNC` scalar function call.

```python
def date_trunc(dialect: "SQLDialectBase", precision: str, expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
t = date_trunc(dialect, "month", Column(dialect, "created_at"))
sql, params = t.to_sql()
# sql: 'DATE_TRUNC(?, "created_at")'
# params: ("month",)
```

## Conditional Functions

### case

Creates a `CASE` expression.

```python
def case(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "core.CaseExpression": ...
```

**Example:**
```python
c = case(dialect).when(Column(dialect, "status") == "active", "Active").else_("Inactive")
sql, params = c.to_sql()
```

### nullif

Creates a `NULLIF` scalar function call.

```python
def nullif(dialect: "SQLDialectBase", expr1: Union[str, "bases.BaseExpression"], expr2: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
n = nullif(dialect, Column(dialect, "value"), "N/A")
sql, params = n.to_sql()
# sql: 'NULLIF("value", ?)'
# params: ("N/A",)
```

### greatest

Creates a `GREATEST` scalar function call.

```python
def greatest(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
g = greatest(dialect, Column(dialect, "a"), Column(dialect, "b"), Column(dialect, "c"))
sql, params = g.to_sql()
# sql: 'GREATEST("a", "b", "c")'
# params: ()
```

### least

Creates a `LEAST` scalar function call.

```python
def least(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
l = least(dialect, Column(dialect, "a"), Column(dialect, "b"), Column(dialect, "c"))
sql, params = l.to_sql()
# sql: 'LEAST("a", "b", "c")'
# params: ()
```

## Window Functions

### row_number

Creates a `ROW_NUMBER` window function call.

```python
def row_number(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
```

**Example:**
```python
r = row_number(dialect)
sql, params = r.to_sql()
# sql: 'ROW_NUMBER()'
# params: ()
```

### rank, dense_rank

Creates `RANK` and `DENSE_RANK` window function calls.

```python
def rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
def dense_rank(dialect: "SQLDialectBase", alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
```

### lag, lead

Creates `LAG` and `LEAD` window function calls.

```python
def lag(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], offset: Optional[int] = 1, default: Optional[Union[str, "bases.BaseExpression"]] = None, alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
def lead(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], offset: Optional[int] = 1, default: Optional[Union[str, "bases.BaseExpression"]] = None, alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
```

### first_value, last_value, nth_value

Creates value window function calls.

```python
def first_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
def last_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
def nth_value(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], n: int, alias: Optional[str] = None) -> "advanced_functions.WindowFunctionCall": ...
```

## JSON Functions

### json_extract, json_extract_text

Creates JSON extraction function calls.

```python
def json_extract(dialect: "SQLDialectBase", expr: "bases.BaseExpression", path: str) -> "operators.BinaryExpression": ...
def json_extract_text(dialect: "SQLDialectBase", expr: "bases.BaseExpression", path: str) -> "operators.BinaryExpression": ...
```

**Example:**
```python
j = json_extract(dialect, Column(dialect, "data"), "$.name")
sql, params = j.to_sql()
# Uses -> operator to extract JSON value
```

### json_build_object

Creates a `JSON_BUILD_OBJECT` function call.

```python
def json_build_object(dialect: "SQLDialectBase", *args: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

### json_array_elements

Creates a `JSON_ARRAY_ELEMENTS` function call.

```python
def json_array_elements(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

### json_objectagg, json_arrayagg

Creates JSON aggregate function calls.

```python
def json_objectagg(dialect: "SQLDialectBase", key_expr: Union[str, "bases.BaseExpression"], value_expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
def json_arrayagg(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

## Array Functions

### array_agg

Creates an `ARRAY_AGG` aggregate function call.

```python
def array_agg(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], is_distinct: bool = False, alias: Optional[str] = None) -> "aggregates.AggregateFunctionCall": ...
```

### unnest

Creates an `UNNEST` function call.

```python
def unnest(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

### array_length

Creates an `ARRAY_LENGTH` function call.

```python
def array_length(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], dimension: int = 1) -> "core.FunctionCall": ...
```

## Type Conversion Functions

### cast

Creates a type conversion expression.

```python
def cast(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], type_name: str) -> "core.Column": ...
```

**Example:**
```python
c = cast(dialect, Column(dialect, "value"), "INTEGER")
sql, params = c.to_sql()
# sql: 'CAST("value" AS INTEGER)'
# params: ()
```

### to_char

Creates a `TO_CHAR` function call.

```python
def to_char(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], format: Optional[str] = None) -> "core.FunctionCall": ...
```

### to_number

Creates a `TO_NUMBER` function call.

```python
def to_number(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], format: Optional[str] = None) -> "core.FunctionCall": ...
```

### to_date

Creates a `TO_DATE` function call.

```python
def to_date(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], format: Optional[str] = None) -> "core.FunctionCall": ...
```

## Grouping Functions

### rollup

Creates a `ROLLUP` grouping expression.

```python
def rollup(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "query_parts.GroupingExpression": ...
```

**Example:**
```python
r = rollup(dialect, Column(dialect, "department"), Column(dialect, "region"))
sql, params = r.to_sql()
# sql: 'ROLLUP("department", "region")'
# params: ()
```

### cube

Creates a `CUBE` grouping expression.

```python
def cube(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "query_parts.GroupingExpression": ...
```

### grouping_sets

Creates a `GROUPING SETS` grouping expression.

```python
def grouping_sets(dialect: "SQLDialectBase", *sets: List[Union[str, "bases.BaseExpression"]]) -> "query_parts.GroupingExpression": ...
```

## String Concatenation Operator

### concat_op

Creates a string concatenation expression using the `||` operator.

```python
def concat_op(dialect: "SQLDialectBase", *exprs: Union[str, "bases.BaseExpression"]) -> "operators.BinaryExpression": ...
```

**Example:**
```python
# Concatenate two columns
expr = concat_op(dialect, Column(dialect, "first_name"), Column(dialect, "last_name"))
sql, params = expr.to_sql()
# sql: '"first_name" || "last_name"'
# params: ()

# Concatenate columns and literals
expr = concat_op(dialect, Column(dialect, "first_name"), " ", Column(dialect, "last_name"))
sql, params = expr.to_sql()
# sql: '"first_name" || ? || "last_name"'
# params: (" ",)
```

---

## Additional SQL Standard Functions

The following functions are defined in SQL:2003 standard but were not previously implemented.

### mod

Creates a `MOD` function call (modulo operation).

```python
def mod(dialect: "SQLDialectBase", dividend: Union[int, float, "bases.BaseExpression"], divisor: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
m = mod(dialect, 10, 3)
sql, params = m.to_sql()
# sql: 'MOD(?, ?)'
# params: (10, 3)
```

### sign

Creates a `SIGN` function call (returns -1, 0, or 1).

```python
def sign(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
s = sign(dialect, -42)
sql, params = s.to_sql()
# sql: 'SIGN(?)'
# params: (-42,)
```

### truncate

Creates a `TRUNCATE` function call (truncates a number).

```python
def truncate(dialect: "SQLDialectBase", expr: Union[int, float, "bases.BaseExpression"], precision: Optional[int] = None) -> "core.FunctionCall": ...
```

**Example:**
```python
t = truncate(dialect, 3.14159, 2)
sql, params = t.to_sql()
# sql: 'TRUNCATE(?, ?)'
# params: (3.14159, 2)
```

### chr_

Creates a `CHR` function call (ASCII code to character). Note the trailing underscore.

```python
def chr_(dialect: "SQLDialectBase", code: Union[int, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
c = chr_(dialect, 65)  # Returns 'A'
sql, params = c.to_sql()
# sql: 'CHR(?)'
# params: (65,)
```

### ascii

Creates an `ASCII` function call (character to ASCII code).

```python
def ascii(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
a = ascii(dialect, "A")
sql, params = a.to_sql()
# sql: 'ASCII(?)'
# params: ("A",)
```

### octet_length

Creates an `OCTET_LENGTH` function call (returns byte length).

```python
def octet_length(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
o = octet_length(dialect, Column(dialect, "text"))
sql, params = o.to_sql()
# sql: 'OCTET_LENGTH("text")'
# params: ()
```

### bit_length

Creates a `BIT_LENGTH` function call (returns bit length).

```python
def bit_length(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
b = bit_length(dialect, Column(dialect, "text"))
sql, params = b.to_sql()
# sql: 'BIT_LENGTH("text")'
# params: ()
```

### position

Creates a `POSITION` function call (find substring position, 1-based).

```python
def position(dialect: "SQLDialectBase", substring: Union[str, "bases.BaseExpression"], expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
p = position(dialect, "world", Column(dialect, "text"))
sql, params = p.to_sql()
# sql: 'POSITION(?, "text")'
# params: ("world",)
```

### overlay

Creates an `OVERLAY` function call (replace substring).

```python
def overlay(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], replacement: Union[str, "bases.BaseExpression"], start: int, length: Optional[int] = None) -> "core.FunctionCall": ...
```

**Example:**
```python
o = overlay(dialect, Column(dialect, "text"), "xxx", 1, 3)
sql, params = o.to_sql()
# sql: 'OVERLAY("text", ?, ?, ?)'
# params: ("xxx", 1, 3)
```

### translate

Creates a `TRANSLATE` function call (character substitution).

```python
def translate(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], from_chars: str, to_chars: str) -> "core.FunctionCall": ...
```

**Example:**
```python
t = translate(dialect, Column(dialect, "text"), "abc", "xyz")
sql, params = t.to_sql()
# sql: 'TRANSLATE("text", ?, ?)'
# params: ("abc", "xyz")
```

### repeat

Creates a `REPEAT` function call (repeat string).

```python
def repeat(dialect: "SQLDialectBase", expr: Union[str, "bases.BaseExpression"], count: int) -> "core.FunctionCall": ...
```

**Example:**
```python
r = repeat(dialect, "ab", 3)
sql, params = r.to_sql()
# sql: 'REPEAT(?, ?)'
# params: ("ab", 3)
```

### space

Creates a `SPACE` function call (generate spaces).

```python
def space(dialect: "SQLDialectBase", count: int) -> "core.FunctionCall": ...
```

**Example:**
```python
s = space(dialect, 5)
sql, params = s.to_sql()
# sql: 'SPACE(?)'
# params: (5,)
```

### current_timestamp

Creates a `CURRENT_TIMESTAMP` function call.

```python
def current_timestamp(dialect: "SQLDialectBase", precision: Optional[int] = None) -> "core.FunctionCall": ...
```

**Example:**
```python
c = current_timestamp(dialect, 6)
sql, params = c.to_sql()
# sql: 'CURRENT_TIMESTAMP(?)'
# params: (6,)
```

### localtimestamp

Creates a `LOCALTIMESTAMP` function call.

```python
def localtimestamp(dialect: "SQLDialectBase", precision: Optional[int] = None) -> "core.FunctionCall": ...
```

**Example:**
```python
l = localtimestamp(dialect)
sql, params = l.to_sql()
# sql: 'LOCALTIMESTAMP'
# params: ()
```

### extract

Creates an `EXTRACT` function call (extract datetime part).

```python
def extract(dialect: "SQLDialectBase", field: str, expr: Union[str, "bases.BaseExpression"]) -> "core.FunctionCall": ...
```

**Example:**
```python
e = extract(dialect, "YEAR", Column(dialect, "created_at"))
sql, params = e.to_sql()
# sql: 'EXTRACT(?, "created_at")'
# params: ("YEAR",)
```

### current_user, session_user, system_user

Creates user information function calls.

```python
def current_user(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
def session_user(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
def system_user(dialect: "SQLDialectBase") -> "core.FunctionCall": ...
```

**Example:**
```python
u = current_user(dialect)
sql, params = u.to_sql()
# sql: 'CURRENT_USER'
# params: ()
```
