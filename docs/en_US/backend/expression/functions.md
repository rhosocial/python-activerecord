# Function Factories

This document describes the factory functions defined in `src/rhosocial/activerecord/backend/expression/functions.py`. These functions provide a convenient way to create aggregate and scalar function expressions.

## Overview

The `functions` module provides factory functions that simplify the creation of SQL function calls. Instead of manually instantiating `FunctionCall` objects, you can use these helpers which handle type conversion and provide a more Pythonic interface.

## Aggregate Functions

### FunctionCall (aggregate use)

An aggregate call is a `FunctionCall`; aggregate factories set its
construction-time `is_aggregate` fact. It supports `FILTER (WHERE ...)`
clauses and `OVER (...)` window clauses.

```python
import inspect
from rhosocial.activerecord.backend.expression import FunctionCall

print(inspect.signature(FunctionCall.__init__))
print(inspect.signature(FunctionCall.filter))
print(inspect.signature(FunctionCall.over))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import (
    BooleanColumn, Column, StringColumn,
)
from rhosocial.activerecord.backend.expression.functions import count, sum_

# COUNT with FILTER -- typed columns build real predicates
active_count = count(dialect, "*", alias="active_count").filter(
    StringColumn(dialect, "status") == "active"
)
sql, params = active_count.to_sql()
# sql: 'COUNT(*) FILTER (WHERE "status" = ?) AS "active_count"'
# params: ("active",)

# SUM with multiple chained filters
high_value_sum = sum_(dialect, Column(dialect, "amount"), alias="high_value_sum").filter(
    StringColumn(dialect, "category") == "sales"
).filter(
    BooleanColumn(dialect, "priority") == True
)
sql, params = high_value_sum.to_sql()
# sql: 'SUM("amount") FILTER (WHERE "category" = ? AND "priority" = ?) AS "high_value_sum"'
# params: ("sales", True)
```

### count

Creates a `COUNT` aggregate function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import count

# The signature as the library declares it
print(inspect.signature(count))
```

**Usage Rules:**
- `count(dialect, "*")` -> `COUNT(*)` (a `RowCountWildcard`)
- `count(dialect, Column(dialect, "id"))` -> `COUNT("id")`
- `count(dialect, "val")` -> `COUNT("val")` (a column reference)

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import count

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
import inspect
from rhosocial.activerecord.backend.expression.functions import sum_

# The signature as the library declares it
print(inspect.signature(sum_))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import sum_

s = sum_(dialect, Column(dialect, "amount"))
sql, params = s.to_sql()
# sql: 'SUM("amount")'
# params: ()
```

### avg

Creates an `AVG` aggregate function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import avg

# The signature as the library declares it
print(inspect.signature(avg))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import avg

a = avg(dialect, Column(dialect, "score"), is_distinct=True, alias="avg_score")
sql, params = a.to_sql()
# sql: 'AVG(DISTINCT "score") AS "avg_score"'
# params: ()
```

### min_

Creates a `MIN` aggregate function call. Note the trailing underscore.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import min_

# The signature as the library declares it
print(inspect.signature(min_))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import min_

m = min_(dialect, Column(dialect, "price"))
sql, params = m.to_sql()
# sql: 'MIN("price")'
# params: ()
```

### max_

Creates a `MAX` aggregate function call. Note the trailing underscore.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import max_

# The signature as the library declares it
print(inspect.signature(max_))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import max_

m = max_(dialect, Column(dialect, "price"))
sql, params = m.to_sql()
# sql: 'MAX("price")'
# params: ()
```

## String Functions

### concat

Creates a `CONCAT` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import concat

# The signature as the library declares it
print(inspect.signature(concat))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import concat

c = concat(dialect, Column(dialect, "first_name"), " ", Column(dialect, "last_name"))
sql, params = c.to_sql()
# sql: 'CONCAT("first_name", ?, "last_name")'
# params: (" ",)
```

### coalesce

Creates a `COALESCE` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import coalesce

# The signature as the library declares it
print(inspect.signature(coalesce))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import coalesce

c = coalesce(dialect, Column(dialect, "nickname"), Column(dialect, "real_name"), "Anonymous")
sql, params = c.to_sql()
# sql: 'COALESCE("nickname", "real_name", ?)'
# params: ("Anonymous",)
```

### length

Creates a `LENGTH` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import length

# The signature as the library declares it
print(inspect.signature(length))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import length

l = length(dialect, Column(dialect, "description"))
sql, params = l.to_sql()
# sql: 'LENGTH("description")'
# params: ()
```

### substring

Creates a `SUBSTRING` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import substring

# The signature as the library declares it
print(inspect.signature(substring))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import substring

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
import inspect
from rhosocial.activerecord.backend.expression.functions import trim

# The signature as the library declares it
print(inspect.signature(trim))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import trim

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
import inspect
from rhosocial.activerecord.backend.expression.functions import replace

# The signature as the library declares it
print(inspect.signature(replace))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import replace

r = replace(dialect, Column(dialect, "content"), "http", "https")
sql, params = r.to_sql()
# sql: 'REPLACE("content", ?, ?)'
# params: ("http", "https")
```

### upper

Creates an `UPPER` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import upper

# The signature as the library declares it
print(inspect.signature(upper))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import upper

u = upper(dialect, Column(dialect, "email"))
sql, params = u.to_sql()
# sql: 'UPPER("email")'
# params: ()
```

### lower

Creates a `LOWER` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import lower

# The signature as the library declares it
print(inspect.signature(lower))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import lower

l = lower(dialect, Column(dialect, "email"))
sql, params = l.to_sql()
# sql: 'LOWER("email")'
# params: ()
```

### initcap

Creates an `INITCAP` scalar function call (title case).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import initcap

# The signature as the library declares it
print(inspect.signature(initcap))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import initcap

i = initcap(dialect, Column(dialect, "title"))
sql, params = i.to_sql()
# sql: 'INITCAP("title")'
# params: ()
```

### left

Creates a `LEFT` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import left

# The signature as the library declares it
print(inspect.signature(left))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import left

l = left(dialect, Column(dialect, "code"), 3)
sql, params = l.to_sql()
# sql: 'LEFT("code", ?)'
# params: (3,)
```

### right

Creates a `RIGHT` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import right

# The signature as the library declares it
print(inspect.signature(right))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import right

r = right(dialect, Column(dialect, "code"), 4)
sql, params = r.to_sql()
# sql: 'RIGHT("code", ?)'
# params: (4,)
```

### lpad

Creates an `LPAD` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import lpad

# The signature as the library declares it
print(inspect.signature(lpad))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import lpad

p = lpad(dialect, Column(dialect, "id"), 5, "0")
sql, params = p.to_sql()
# sql: 'LPAD("id", ?, ?)'
# params: (5, "0")
```

### rpad

Creates an `RPAD` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import rpad

# The signature as the library declares it
print(inspect.signature(rpad))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import rpad

p = rpad(dialect, Column(dialect, "id"), 5, " ")
sql, params = p.to_sql()
# sql: 'RPAD("id", ?, ?)'
# params: (5, " ")
```

### reverse

Creates a `REVERSE` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import reverse

# The signature as the library declares it
print(inspect.signature(reverse))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import reverse

r = reverse(dialect, Column(dialect, "text"))
sql, params = r.to_sql()
# sql: 'REVERSE("text")'
# params: ()
```

### strpos

Creates a `STRPOS` scalar function call (find substring position).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import strpos

# The signature as the library declares it
print(inspect.signature(strpos))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import strpos

p = strpos(dialect, Column(dialect, "text"), "world")
sql, params = p.to_sql()
# sql: 'STRPOS("text", ?)'
# params: ("world",)
```

## Math Functions

### abs_

Creates an `ABS` scalar function call. Note the trailing underscore to avoid conflict with Python's built-in `abs`.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import abs_

# The signature as the library declares it
print(inspect.signature(abs_))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import abs_

a = abs_(dialect, -5)
sql, params = a.to_sql()
# sql: 'ABS(?)'
# params: (-5,)
```

### round_

Creates a `ROUND` scalar function call. Note the trailing underscore.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import round_

# The signature as the library declares it
print(inspect.signature(round_))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import round_

r = round_(dialect, 3.14159, 2)
sql, params = r.to_sql()
# sql: 'ROUND(?, ?)'
# params: (Decimal('3.14159'), 2)  -- numeric literals bind as Decimal
```

### ceil

Creates a `CEIL` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import ceil

# The signature as the library declares it
print(inspect.signature(ceil))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import ceil

c = ceil(dialect, 3.14)
sql, params = c.to_sql()
# sql: 'CEIL(?)'
# params: (Decimal('3.14'),)
```

### floor

Creates a `FLOOR` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import floor

# The signature as the library declares it
print(inspect.signature(floor))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import floor

f = floor(dialect, 3.99)
sql, params = f.to_sql()
# sql: 'FLOOR(?)'
# params: (Decimal('3.99'),)
```

### sqrt

Creates a `SQRT` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import sqrt

# The signature as the library declares it
print(inspect.signature(sqrt))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import sqrt

s = sqrt(dialect, 16)
sql, params = s.to_sql()
# sql: 'SQRT(?)'
# params: (16,)
```

### power

Creates a `POWER` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import power

# The signature as the library declares it
print(inspect.signature(power))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import power

p = power(dialect, 2, 3)
sql, params = p.to_sql()
# sql: 'POWER(?, ?)'
# params: (2, 3)
```

### exp

Creates an `EXP` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import exp

# The signature as the library declares it
print(inspect.signature(exp))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import exp

e = exp(dialect, 1)
sql, params = e.to_sql()
# sql: 'EXP(?)'
# params: (1,)
```

### log

Creates a `LOG` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import log

# The signature as the library declares it
print(inspect.signature(log))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import log

l = log(dialect, 100, 10)
sql, params = l.to_sql()
# sql: 'LOG(?, ?)'
# params: (100, 10)
```

### sin, cos, tan

Creates trigonometric function calls.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import sin, cos, tan

# The signature as the library declares it
print(inspect.signature(sin))
print(inspect.signature(cos))
print(inspect.signature(tan))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import cos, sin, tan

s = sin(dialect, 0)
c = cos(dialect, 0)
t = tan(dialect, 0)
```

## Date/Time Functions

### now

Creates a `NOW` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import now

# The signature as the library declares it
print(inspect.signature(now))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import now

n = now(dialect)
sql, params = n.to_sql()
# sql: 'NOW()'
# params: ()
```

### current_date

Creates a `CURRENT_DATE` niladic value function. Per SQL:2003, generates `CURRENT_DATE` without parentheses.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import current_date

# The signature as the library declares it
print(inspect.signature(current_date))
```

**Example:**

```python
from rhosocial.activerecord.backend.expression.functions import current_date

d = current_date(dialect)
sql, params = d.to_sql()
# sql: 'CURRENT_DATE'
# params: ()
```

### current_time

Creates a `CURRENT_TIME` niladic value function. Per SQL:2003, generates `CURRENT_TIME` without parentheses.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import current_time

# The signature as the library declares it
print(inspect.signature(current_time))
```

**Example:**

```python
from rhosocial.activerecord.backend.expression.functions import current_time

t = current_time(dialect)
sql, params = t.to_sql()
# sql: 'CURRENT_TIME'
# params: ()
```

### year, month, day, hour, minute, second

Creates date part extraction function calls.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import year, month, day, hour, minute, second

# The signature as the library declares it
print(inspect.signature(year))
print(inspect.signature(month))
print(inspect.signature(day))
print(inspect.signature(hour))
print(inspect.signature(minute))
print(inspect.signature(second))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import year

y = year(dialect, Column(dialect, "created_at"))
sql, params = y.to_sql()
# sql: 'YEAR("created_at")'
# params: ()
```

### date_part

Creates a `DATE_PART` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import date_part

# The signature as the library declares it
print(inspect.signature(date_part))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import date_part

p = date_part(dialect, "year", Column(dialect, "created_at"))
sql, params = p.to_sql()
# sql: 'EXTRACT(YEAR FROM "created_at")'
# params: ()
```

### date_trunc

Creates a `DATE_TRUNC` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import date_trunc

# The signature as the library declares it
print(inspect.signature(date_trunc))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import date_trunc

t = date_trunc(dialect, "month", Column(dialect, "created_at"))
sql, params = t.to_sql()
# sql: 'DATE_TRUNC('month', "created_at")'
# params: ()
```

## Conditional Functions

### case

Creates a `CASE` expression.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import case

# The signature as the library declares it
print(inspect.signature(case))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Literal, StringColumn
from rhosocial.activerecord.backend.expression.advanced_functions import CaseExpression
from rhosocial.activerecord.backend.expression.functions import case

# The factory creates an empty CASE node
c = case(dialect)

# Branches are supplied as (condition, result) pairs at construction
c = CaseExpression(
    dialect,
    cases=[(StringColumn(dialect, "status") == "active", Literal(dialect, "Active"))],
    else_result=Literal(dialect, "Inactive"),
)
sql, params = c.to_sql()
# sql: 'CASE WHEN "status" = ? THEN ? ELSE ? END'
# params: ("active", "Active", "Inactive")
```

### nullif

Creates a `NULLIF` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import nullif

# The signature as the library declares it
print(inspect.signature(nullif))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import nullif

n = nullif(dialect, Column(dialect, "value"), "N/A")
sql, params = n.to_sql()
# sql: 'NULLIF("value", ?)'
# params: ("N/A",)
```

### greatest

Creates a `GREATEST` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import greatest

# The signature as the library declares it
print(inspect.signature(greatest))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import greatest

g = greatest(dialect, Column(dialect, "a"), Column(dialect, "b"), Column(dialect, "c"))
sql, params = g.to_sql()
# sql: 'GREATEST("a", "b", "c")'
# params: ()
```

### least

Creates a `LEAST` scalar function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import least

# The signature as the library declares it
print(inspect.signature(least))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import least

l = least(dialect, Column(dialect, "a"), Column(dialect, "b"), Column(dialect, "c"))
sql, params = l.to_sql()
# sql: 'LEAST("a", "b", "c")'
# params: ()
```

## Window Functions

### row_number

Creates a `ROW_NUMBER` window function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import row_number

# The signature as the library declares it
print(inspect.signature(row_number))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import row_number

r = row_number(dialect)
sql, params = r.to_sql()
# sql: 'ROW_NUMBER()'
# params: ()
```

### rank, dense_rank

Creates `RANK` and `DENSE_RANK` window function calls.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import rank, dense_rank

# The signature as the library declares it
print(inspect.signature(rank))
print(inspect.signature(dense_rank))
```

### lag, lead

Creates `LAG` and `LEAD` window function calls.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import lag, lead

# The signature as the library declares it
print(inspect.signature(lag))
print(inspect.signature(lead))
```

### first_value, last_value, nth_value

Creates value window function calls.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import first_value, last_value, nth_value

# The signature as the library declares it
print(inspect.signature(first_value))
print(inspect.signature(last_value))
print(inspect.signature(nth_value))
```

## JSON Functions

### json_extract, json_extract_text

Creates JSON extraction function calls.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import json_extract, json_extract_text

# The signature as the library declares it
print(inspect.signature(json_extract))
print(inspect.signature(json_extract_text))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import json_extract

j = json_extract(dialect, Column(dialect, "data"), "$.name")
sql, params = j.to_sql()
# Uses -> operator to extract JSON value
```

### json_build_object

Creates a `JSON_BUILD_OBJECT` function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import json_build_object

# The signature as the library declares it
print(inspect.signature(json_build_object))
```

### json_array_elements

Creates a `JSON_ARRAY_ELEMENTS` function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import json_array_elements

# The signature as the library declares it
print(inspect.signature(json_array_elements))
```

### json_objectagg, json_arrayagg

Creates JSON aggregate function calls.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import json_objectagg, json_arrayagg

# The signature as the library declares it
print(inspect.signature(json_objectagg))
print(inspect.signature(json_arrayagg))
```

## Array Functions

### array_agg

Creates an `ARRAY_AGG` aggregate function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import array_agg

# The signature as the library declares it
print(inspect.signature(array_agg))
```

### unnest

Creates an `UNNEST` function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import unnest

# The signature as the library declares it
print(inspect.signature(unnest))
```

### array_length

Creates an `ARRAY_LENGTH` function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import array_length

# The signature as the library declares it
print(inspect.signature(array_length))
```

## Type Conversion Functions

### cast

Creates a type conversion expression.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import cast

# The signature as the library declares it
print(inspect.signature(cast))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import cast
from rhosocial.activerecord.backend.expression.types import IntegerType

# The target type is a DataType object, never a type-name string
c = cast(dialect, Column(dialect, "value"), IntegerType(dialect))
sql, params = c.to_sql()
# sql: 'CAST("value" AS INTEGER)'
# params: ()
```

### to_char

Creates a `TO_CHAR` function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import to_char

# The signature as the library declares it
print(inspect.signature(to_char))
```

### to_number

Creates a `TO_NUMBER` function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import to_number

# The signature as the library declares it
print(inspect.signature(to_number))
```

### to_date

Creates a `TO_DATE` function call.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import to_date

# The signature as the library declares it
print(inspect.signature(to_date))
```

## Grouping Functions

### rollup

Creates a `ROLLUP` grouping expression.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import rollup

# The signature as the library declares it
print(inspect.signature(rollup))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import rollup

r = rollup(dialect, Column(dialect, "department"), Column(dialect, "region"))
sql, params = r.to_sql()
# sql: 'ROLLUP("department", "region")'
# params: ()
```

### cube

Creates a `CUBE` grouping expression.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import cube

# The signature as the library declares it
print(inspect.signature(cube))
```

### grouping_sets

Creates a `GROUPING SETS` grouping expression.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import grouping_sets

# The signature as the library declares it
print(inspect.signature(grouping_sets))
```

## String Concatenation Operator

### concat_op

Creates a string concatenation expression using the `||` operator.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import concat_op

# The signature as the library declares it
print(inspect.signature(concat_op))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import concat_op

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
import inspect
from rhosocial.activerecord.backend.expression.functions import mod

# The signature as the library declares it
print(inspect.signature(mod))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import mod

m = mod(dialect, 10, 3)
sql, params = m.to_sql()
# sql: 'MOD(?, ?)'
# params: (10, 3)
```

### sign

Creates a `SIGN` function call (returns -1, 0, or 1).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import sign

# The signature as the library declares it
print(inspect.signature(sign))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import sign

s = sign(dialect, -42)
sql, params = s.to_sql()
# sql: 'SIGN(?)'
# params: (-42,)
```

### truncate

Creates a `TRUNCATE` function call (truncates a number).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import truncate

# The signature as the library declares it
print(inspect.signature(truncate))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import truncate

t = truncate(dialect, 3.14159, 2)
sql, params = t.to_sql()
# sql: 'TRUNCATE(?, ?)'
# params: (Decimal('3.14159'), 2)
```

### chr_

Creates a `CHR` function call (ASCII code to character). Note the trailing underscore.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import chr_

# The signature as the library declares it
print(inspect.signature(chr_))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import chr_

c = chr_(dialect, 65)  # Returns 'A'
sql, params = c.to_sql()
# sql: 'CHR(?)'
# params: (65,)
```

### ascii

Creates an `ASCII` function call (character to ASCII code).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import ascii

# The signature as the library declares it
print(inspect.signature(ascii))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import ascii

a = ascii(dialect, "A")
sql, params = a.to_sql()
# sql: 'ASCII(?)'
# params: ("A",)
```

### octet_length

Creates an `OCTET_LENGTH` function call (returns byte length).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import octet_length

# The signature as the library declares it
print(inspect.signature(octet_length))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import octet_length

o = octet_length(dialect, Column(dialect, "text"))
sql, params = o.to_sql()
# sql: 'OCTET_LENGTH("text")'
# params: ()
```

### bit_length

Creates a `BIT_LENGTH` function call (returns bit length).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import bit_length

# The signature as the library declares it
print(inspect.signature(bit_length))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import bit_length

b = bit_length(dialect, Column(dialect, "text"))
sql, params = b.to_sql()
# sql: 'BIT_LENGTH("text")'
# params: ()
```

### position

Creates a `POSITION` function call (find substring position, 1-based).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import position

# The signature as the library declares it
print(inspect.signature(position))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import position

p = position(dialect, "world", Column(dialect, "text"))
sql, params = p.to_sql()
# sql: 'POSITION(?, "text")'
# params: ("world",)
```

### overlay

Creates an `OVERLAY` function call (replace substring).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import overlay

# The signature as the library declares it
print(inspect.signature(overlay))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import overlay

o = overlay(dialect, Column(dialect, "text"), "xxx", 1, 3)
sql, params = o.to_sql()
# sql: 'OVERLAY("text", ?, ?, ?)'
# params: ("xxx", 1, 3)
```

### translate

Creates a `TRANSLATE` function call (character substitution).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import translate

# The signature as the library declares it
print(inspect.signature(translate))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import translate

t = translate(dialect, Column(dialect, "text"), "abc", "xyz")
sql, params = t.to_sql()
# sql: 'TRANSLATE("text", ?, ?)'
# params: ("abc", "xyz")
```

### repeat

Creates a `REPEAT` function call (repeat string).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import repeat

# The signature as the library declares it
print(inspect.signature(repeat))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import repeat

r = repeat(dialect, "ab", 3)
sql, params = r.to_sql()
# sql: 'REPEAT(?, ?)'
# params: ("ab", 3)
```

### space

Creates a `SPACE` function call (generate spaces).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import space

# The signature as the library declares it
print(inspect.signature(space))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import space

s = space(dialect, 5)
sql, params = s.to_sql()
# sql: 'SPACE(?)'
# params: (5,)
```

### current_timestamp

Creates a `CURRENT_TIMESTAMP` niladic value function. Per SQL:2003, generates `CURRENT_TIMESTAMP` without parentheses when no precision is specified. When precision is specified, generates `CURRENT_TIMESTAMP(precision)` with parentheses.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import current_timestamp

# The signature as the library declares it
print(inspect.signature(current_timestamp))
```

**Example:**

```python
from rhosocial.activerecord.backend.expression.functions import current_timestamp

# Without precision — niladic form (no parentheses)
c = current_timestamp(dialect)
sql, params = c.to_sql()
# sql: 'CURRENT_TIMESTAMP'
# params: ()

# With precision — has parentheses
c = current_timestamp(dialect, 6)
sql, params = c.to_sql()
# sql: 'CURRENT_TIMESTAMP(?)'
# params: (6,)
```

### localtimestamp

Creates a `LOCALTIMESTAMP` niladic value function. Per SQL:2003, generates `LOCALTIMESTAMP` without parentheses when no precision is specified. When precision is specified, generates `LOCALTIMESTAMP(precision)` with parentheses.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import localtimestamp

# The signature as the library declares it
print(inspect.signature(localtimestamp))
```

**Example:**

```python
from rhosocial.activerecord.backend.expression.functions import localtimestamp

# Without precision — niladic form (no parentheses)
l = localtimestamp(dialect)
sql, params = l.to_sql()
# sql: 'LOCALTIMESTAMP'
# params: ()
```

### extract

Creates an `EXTRACT` function call (extract datetime part).

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import extract

# The signature as the library declares it
print(inspect.signature(extract))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import extract

e = extract(dialect, "YEAR", Column(dialect, "created_at"))
sql, params = e.to_sql()
# sql: 'EXTRACT(YEAR FROM "created_at")'
# params: ()
```

### current_user, session_user, system_user

Creates SQL:2003 niladic value functions. These generate `CURRENT_USER`, `SESSION_USER`, `SYSTEM_USER` without parentheses.

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import current_user, session_user, system_user

# The signature as the library declares it
print(inspect.signature(current_user))
print(inspect.signature(session_user))
print(inspect.signature(system_user))
```

**Example:**
```python
from rhosocial.activerecord.backend.expression.functions import current_user

u = current_user(dialect)
sql, params = u.to_sql()
# sql: 'CURRENT_USER'
# params: ()
```

## SQL/XML Functions

This section describes SQL/XML standard expression factory functions, defined in `rhosocial.activerecord.backend.expression.functions.xml`.

### xmlparse

Parses a string into an XML type.

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlparse

# Parse string as XML DOCUMENT
expr = xmlparse(dialect, Column(dialect, "xml_string"), document=True)
sql, params = expr.to_sql()
# sql: 'XMLPARSE(DOCUMENT "xml_string")'
# params: ()

# Parse string as XML CONTENT
expr = xmlparse(dialect, Column(dialect, "xml_string"), document=False)
```

### xmlserialize

Serializes an XML type to a string.

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlserialize
from rhosocial.activerecord.backend.expression.types import VarCharType

# The target type is a DataType object, never a type-name string
expr = xmlserialize(dialect, Column(dialect, "xml_data"), VarCharType(dialect, length=255))
sql, params = expr.to_sql()
# sql: 'XMLSERIALIZE(CONTENT "xml_data" AS VARCHAR(255))'
# params: ()
```

### xmlelement

Constructs an XML element.

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlelement, xmlattributes

# Simple element
elem = xmlelement(dialect, "name", Column(dialect, "user_name"))
sql, params = elem.to_sql()
# sql: 'XMLELEMENT(NAME name, "user_name")'
# params: ()

# Element with attributes -- attributes are passed by name, not as content
elem = xmlelement(
    dialect,
    "person",
    Column(dialect, "name"),
    attributes=xmlattributes(dialect, (Column(dialect, "id"), "id")),
)
# sql: 'XMLELEMENT(NAME person, XMLATTRIBUTES("id" AS id), "name")'
```

### xmlforest

Constructs an XML forest (sequence of elements).

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlforest

expr = xmlforest(dialect,
    (Column(dialect, "first_name"), "first"),
    (Column(dialect, "last_name"), "last"))
sql, params = expr.to_sql()
# sql: 'XMLFOREST("first_name" AS first, "last_name" AS last)'
# params: ()
```

### xmlconcat

Concatenates multiple XML values.

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlconcat

expr = xmlconcat(dialect, Column(dialect, "xml1"), Column(dialect, "xml2"))
```

### xmlcomment

Creates an XML comment.

```python
from rhosocial.activerecord.backend.expression.functions.xml import xmlcomment

expr = xmlcomment(dialect, "This is a comment")
# sql: 'XMLCOMMENT(?)'
# params: ("This is a comment",)
```

### xmlpi

Creates an XML processing instruction.

```python
from rhosocial.activerecord.backend.expression.functions.xml import xmlpi

expr = xmlpi(dialect, "xml-stylesheet", 'type="text/xsl" href="style.xsl"')
# sql: 'XMLPI(NAME xml-stylesheet, ?)'
# params: ('type="text/xsl" href="style.xsl"',)
```

### xmlroot

Modifies the root node attributes of an XML value.

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlroot
from rhosocial.activerecord.backend.expression.xml import XMLStandaloneOption

expr = xmlroot(
    dialect,
    Column(dialect, "xml_data"),
    version="1.0",
    standalone=XMLStandaloneOption.YES,
)
# sql: 'XMLROOT("xml_data", VERSION ?, STANDALONE YES)'
# params: ('1.0',)
```

### xmlagg

XML aggregate function.

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlagg

expr = xmlagg(dialect, Column(dialect, "xml_column"))
# sql: 'XMLAGG("xml_column")'
# params: ()
```

### xmlquery

XQuery evaluation.

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlquery

expr = xmlquery(dialect, "/root/element/text()",
    passing=[Column(dialect, "xml_column")])
# sql: 'XMLQUERY(? PASSING "xml_column" RETURNING CONTENT)'
# params: ('/root/element/text()',)
```

### xmlexists

XQuery existence check.

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlexists

expr = xmlexists(dialect, "/root/element",
    passing=[Column(dialect, "xml_column")])
# sql: 'XMLEXISTS(? PASSING "xml_column")'
# params: ('/root/element',)
```

### xmltable

Generates a table-valued result from an XQuery expression.

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmltable
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType
from rhosocial.activerecord.backend.expression.xml import XMLTableColumn

expr = xmltable(
    dialect,
    "/root/row",
    passing=[Column(dialect, "xml_data")],
    columns=[
        XMLTableColumn("id", IntegerType(dialect), path=Column(dialect, "id")),
        XMLTableColumn(
            "name", VarCharType(dialect, length=100), path=Column(dialect, "name")
        ),
    ],
)
# sql: 'XMLTABLE(? PASSING "xml_data" COLUMNS ("id" INTEGER PATH "id", "name" VARCHAR(100) PATH "name"))'
# params: ('/root/row',)
```

## Date/Time Interval Expressions

Functions defined in `rhosocial.activerecord.backend.expression.functions.datetime`.

### extract

Creates a structured `EXTRACT` expression (stricter field enumeration than the `extract` factory above).

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.datetime import (
    DateTimeField, ExtractExpression,
)

# Extract the year
expr = ExtractExpression(dialect, DateTimeField.YEAR, Column(dialect, "created_at"))
sql, params = expr.to_sql()
# sql: 'EXTRACT(YEAR FROM "created_at")'
# params: ()
```

### interval

Creates a structured interval value.

```python
from rhosocial.activerecord.backend.expression.datetime import (
    IntervalExpression, IntervalUnit,
)

# A 7-day interval
interval = IntervalExpression(dialect, 7, IntervalUnit.DAY)
sql, params = interval.to_sql()
# sql: "INTERVAL '7' DAY"
# params: ()
```

### Date/time arithmetic

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.datetime import (
    DateTimeField,
    DatetimeAddExpression,
    DatetimeDiffExpression,
    DatetimeSubtractExpression,
    IntervalExpression,
    IntervalUnit,
)

# date + interval
expr = DatetimeAddExpression(dialect,
    Column(dialect, "created_at"),
    IntervalExpression(dialect, 30, IntervalUnit.DAY))
# sql: '"created_at" + INTERVAL '30' DAY'
# params: ()

# date - interval
expr = DatetimeSubtractExpression(dialect,
    Column(dialect, "created_at"),
    IntervalExpression(dialect, 7, IntervalUnit.DAY))

# date difference -- rendering is dialect-specific (SQL Server: DATEDIFF(DAY, ...))
expr = DatetimeDiffExpression(dialect, DateTimeField.DAY,
    Column(dialect, "start_date"),
    Column(dialect, "end_date"))
```
