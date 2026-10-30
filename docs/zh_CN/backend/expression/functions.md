# 函数工厂 (Function Factories)

本文档描述了定义在 `src/rhosocial/activerecord/backend/expression/functions.py` 中的工厂函数。这些函数提供了一种创建聚合函数和标量函数表达式的便捷方式。

## 概述

`functions` 模块提供了简化 SQL 函数调用创建的工厂函数。您可以使用这些助手函数来代替手动实例化 `FunctionCall` 对象，它们处理类型转换并提供更符合 Python 习惯的接口。

## 聚合函数 (Aggregate Functions)

### FunctionCall（聚合用法）

聚合调用就是 `FunctionCall`；聚合工厂会在构造时设置其 `is_aggregate` 事实。它支持 `FILTER` (WHERE) 子句和 `OVER (...)` 窗口子句。

```python
import inspect
from rhosocial.activerecord.backend.expression import FunctionCall

print(inspect.signature(FunctionCall.__init__))
print(inspect.signature(FunctionCall.filter))
print(inspect.signature(FunctionCall.over))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import (
    BooleanColumn, Column, StringColumn,
)
from rhosocial.activerecord.backend.expression.functions import count, sum_

# 带 FILTER 的 COUNT —— 带类型的列会构造真正的谓词
active_count = count(dialect, "*", alias="active_count").filter(
    StringColumn(dialect, "status") == "active"
)
sql, params = active_count.to_sql()
# sql: 'COUNT(*) FILTER (WHERE "status" = ?) AS "active_count"'
# params: ("active",)

# 带多个链式过滤器的 SUM
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

创建 `COUNT` 聚合函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import count

# 库实际声明的函数签名
print(inspect.signature(count))
```

**使用规则:**
- `count(dialect, "*")` -> `COUNT(*)`（`RowCountWildcard`）
- `count(dialect, Column(dialect, "id"))` -> `COUNT("id")`
- `count(dialect, "val")` -> `COUNT("val")`（列引用）

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import count

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
import inspect
from rhosocial.activerecord.backend.expression.functions import sum_

# 库实际声明的函数签名
print(inspect.signature(sum_))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import sum_

s = sum_(dialect, Column(dialect, "amount"))
sql, params = s.to_sql()
# sql: 'SUM("amount")'
# params: ()
```

### avg

创建 `AVG` 聚合函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import avg

# 库实际声明的函数签名
print(inspect.signature(avg))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import avg

a = avg(dialect, Column(dialect, "score"), is_distinct=True, alias="avg_score")
sql, params = a.to_sql()
# sql: 'AVG(DISTINCT "score") AS "avg_score"'
# params: ()
```

### min_

创建 `MIN` 聚合函数调用。注意尾随下划线。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import min_

# 库实际声明的函数签名
print(inspect.signature(min_))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import min_

m = min_(dialect, Column(dialect, "price"))
sql, params = m.to_sql()
# sql: 'MIN("price")'
# params: ()
```

### max_

创建 `MAX` 聚合函数调用。注意尾随下划线。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import max_

# 库实际声明的函数签名
print(inspect.signature(max_))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import max_

m = max_(dialect, Column(dialect, "price"))
sql, params = m.to_sql()
# sql: 'MAX("price")'
# params: ()
```

## 字符串函数 (String Functions)

### concat

创建 `CONCAT` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import concat

# 库实际声明的函数签名
print(inspect.signature(concat))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import concat

c = concat(dialect, Column(dialect, "first_name"), " ", Column(dialect, "last_name"))
sql, params = c.to_sql()
# sql: 'CONCAT("first_name", ?, "last_name")'
# params: (" ",)
```

### coalesce

创建 `COALESCE` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import coalesce

# 库实际声明的函数签名
print(inspect.signature(coalesce))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import coalesce

c = coalesce(dialect, Column(dialect, "nickname"), Column(dialect, "real_name"), "Anonymous")
sql, params = c.to_sql()
# sql: 'COALESCE("nickname", "real_name", ?)'
# params: ("Anonymous",)
```

### length

创建 `LENGTH` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import length

# 库实际声明的函数签名
print(inspect.signature(length))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import length

l = length(dialect, Column(dialect, "description"))
sql, params = l.to_sql()
# sql: 'LENGTH("description")'
# params: ()
```

### substring

创建 `SUBSTRING` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import substring

# 库实际声明的函数签名
print(inspect.signature(substring))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import substring

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
import inspect
from rhosocial.activerecord.backend.expression.functions import trim

# 库实际声明的函数签名
print(inspect.signature(trim))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import trim

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
import inspect
from rhosocial.activerecord.backend.expression.functions import replace

# 库实际声明的函数签名
print(inspect.signature(replace))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import replace

r = replace(dialect, Column(dialect, "content"), "http", "https")
sql, params = r.to_sql()
# sql: 'REPLACE("content", ?, ?)'
# params: ("http", "https")
```

### upper

创建 `UPPER` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import upper

# 库实际声明的函数签名
print(inspect.signature(upper))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import upper

u = upper(dialect, Column(dialect, "email"))
sql, params = u.to_sql()
# sql: 'UPPER("email")'
# params: ()
```

### lower

创建 `LOWER` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import lower

# 库实际声明的函数签名
print(inspect.signature(lower))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import lower

l = lower(dialect, Column(dialect, "email"))
sql, params = l.to_sql()
# sql: 'LOWER("email")'
# params: ()
```

### initcap

创建 `INITCAP` 标量函数调用 (首字母大写)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import initcap

# 库实际声明的函数签名
print(inspect.signature(initcap))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import initcap

i = initcap(dialect, Column(dialect, "title"))
sql, params = i.to_sql()
# sql: 'INITCAP("title")'
# params: ()
```

### left

创建 `LEFT` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import left

# 库实际声明的函数签名
print(inspect.signature(left))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import left

l = left(dialect, Column(dialect, "code"), 3)
sql, params = l.to_sql()
# sql: 'LEFT("code", ?)'
# params: (3,)
```

### right

创建 `RIGHT` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import right

# 库实际声明的函数签名
print(inspect.signature(right))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import right

r = right(dialect, Column(dialect, "code"), 4)
sql, params = r.to_sql()
# sql: 'RIGHT("code", ?)'
# params: (4,)
```

### lpad

创建 `LPAD` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import lpad

# 库实际声明的函数签名
print(inspect.signature(lpad))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import lpad

p = lpad(dialect, Column(dialect, "id"), 5, "0")
sql, params = p.to_sql()
# sql: 'LPAD("id", ?, ?)'
# params: (5, "0")
```

### rpad

创建 `RPAD` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import rpad

# 库实际声明的函数签名
print(inspect.signature(rpad))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import rpad

p = rpad(dialect, Column(dialect, "id"), 5, " ")
sql, params = p.to_sql()
# sql: 'RPAD("id", ?, ?)'
# params: (5, " ")
```

### reverse

创建 `REVERSE` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import reverse

# 库实际声明的函数签名
print(inspect.signature(reverse))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import reverse

r = reverse(dialect, Column(dialect, "text"))
sql, params = r.to_sql()
# sql: 'REVERSE("text")'
# params: ()
```

### strpos

创建 `STRPOS` 标量函数调用 (查找子字符串位置)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import strpos

# 库实际声明的函数签名
print(inspect.signature(strpos))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import strpos

p = strpos(dialect, Column(dialect, "text"), "world")
sql, params = p.to_sql()
# sql: 'STRPOS("text", ?)'
# params: ("world",)
```

## 数学函数 (Math Functions)

### abs_

创建 `ABS` 标量函数调用。注意尾随下划线以避免与 Python 内置的 `abs` 冲突。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import abs_

# 库实际声明的函数签名
print(inspect.signature(abs_))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import abs_

a = abs_(dialect, -5)
sql, params = a.to_sql()
# sql: 'ABS(?)'
# params: (-5,)
```

### round_

创建 `ROUND` 标量函数调用。注意尾随下划线。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import round_

# 库实际声明的函数签名
print(inspect.signature(round_))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import round_

r = round_(dialect, 3.14159, 2)
sql, params = r.to_sql()
# sql: 'ROUND(?, ?)'
# params: (Decimal('3.14159'), 2)  -- 数值字面量以 Decimal 绑定
```

### ceil

创建 `CEIL` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import ceil

# 库实际声明的函数签名
print(inspect.signature(ceil))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import ceil

c = ceil(dialect, 3.14)
sql, params = c.to_sql()
# sql: 'CEIL(?)'
# params: (Decimal('3.14'),)
```

### floor

创建 `FLOOR` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import floor

# 库实际声明的函数签名
print(inspect.signature(floor))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import floor

f = floor(dialect, 3.99)
sql, params = f.to_sql()
# sql: 'FLOOR(?)'
# params: (Decimal('3.99'),)
```

### sqrt

创建 `SQRT` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import sqrt

# 库实际声明的函数签名
print(inspect.signature(sqrt))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import sqrt

s = sqrt(dialect, 16)
sql, params = s.to_sql()
# sql: 'SQRT(?)'
# params: (16,)
```

### power

创建 `POWER` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import power

# 库实际声明的函数签名
print(inspect.signature(power))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import power

p = power(dialect, 2, 3)
sql, params = p.to_sql()
# sql: 'POWER(?, ?)'
# params: (2, 3)
```

### exp

创建 `EXP` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import exp

# 库实际声明的函数签名
print(inspect.signature(exp))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import exp

e = exp(dialect, 1)
sql, params = e.to_sql()
# sql: 'EXP(?)'
# params: (1,)
```

### log

创建 `LOG` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import log

# 库实际声明的函数签名
print(inspect.signature(log))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import log

l = log(dialect, 100, 10)
sql, params = l.to_sql()
# sql: 'LOG(?, ?)'
# params: (100, 10)
```

### sin, cos, tan

创建三角函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import sin, cos, tan

# 库实际声明的函数签名
print(inspect.signature(sin))
print(inspect.signature(cos))
print(inspect.signature(tan))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import cos, sin, tan

s = sin(dialect, 0)
c = cos(dialect, 0)
t = tan(dialect, 0)
```

## 日期时间函数 (Date/Time Functions)

### now

创建 `NOW` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import now

# 库实际声明的函数签名
print(inspect.signature(now))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import now

n = now(dialect)
sql, params = n.to_sql()
# sql: 'NOW()'
# params: ()
```

### current_date

创建 `CURRENT_DATE` 零元值函数。根据 SQL:2003 标准，生成不含括号的 `CURRENT_DATE`。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import current_date

# 库实际声明的函数签名
print(inspect.signature(current_date))
```

**示例:**

```python
from rhosocial.activerecord.backend.expression.functions import current_date

d = current_date(dialect)
sql, params = d.to_sql()
# sql: 'CURRENT_DATE'
# params: ()
```

### current_time

创建 `CURRENT_TIME` 零元值函数。根据 SQL:2003 标准，生成不含括号的 `CURRENT_TIME`。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import current_time

# 库实际声明的函数签名
print(inspect.signature(current_time))
```

**示例:**

```python
from rhosocial.activerecord.backend.expression.functions import current_time

t = current_time(dialect)
sql, params = t.to_sql()
# sql: 'CURRENT_TIME'
# params: ()
```

### year, month, day, hour, minute, second

创建提取日期部分的函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import year, month, day, hour, minute, second

# 库实际声明的函数签名
print(inspect.signature(year))
print(inspect.signature(month))
print(inspect.signature(day))
print(inspect.signature(hour))
print(inspect.signature(minute))
print(inspect.signature(second))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import year

y = year(dialect, Column(dialect, "created_at"))
sql, params = y.to_sql()
# sql: 'YEAR("created_at")'
# params: ()
```

### date_part

创建 `DATE_PART` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import date_part

# 库实际声明的函数签名
print(inspect.signature(date_part))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import date_part

p = date_part(dialect, "year", Column(dialect, "created_at"))
sql, params = p.to_sql()
# sql: 'EXTRACT(YEAR FROM "created_at")'
# params: ()
```

### date_trunc

创建 `DATE_TRUNC` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import date_trunc

# 库实际声明的函数签名
print(inspect.signature(date_trunc))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import date_trunc

t = date_trunc(dialect, "month", Column(dialect, "created_at"))
sql, params = t.to_sql()
# sql: 'DATE_TRUNC('month', "created_at")'
# params: ()
```

## 条件函数 (Conditional Functions)

### case

创建 `CASE` 表达式。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import case

# 库实际声明的函数签名
print(inspect.signature(case))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Literal, StringColumn
from rhosocial.activerecord.backend.expression.advanced_functions import CaseExpression
from rhosocial.activerecord.backend.expression.functions import case

# 工厂创建一个空的 CASE 节点
c = case(dialect)

# 分支以 (条件, 结果) 对的形式在构造时传入
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

创建 `NULLIF` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import nullif

# 库实际声明的函数签名
print(inspect.signature(nullif))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import nullif

n = nullif(dialect, Column(dialect, "value"), "N/A")
sql, params = n.to_sql()
# sql: 'NULLIF("value", ?)'
# params: ("N/A",)
```

### greatest

创建 `GREATEST` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import greatest

# 库实际声明的函数签名
print(inspect.signature(greatest))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import greatest

g = greatest(dialect, Column(dialect, "a"), Column(dialect, "b"), Column(dialect, "c"))
sql, params = g.to_sql()
# sql: 'GREATEST("a", "b", "c")'
# params: ()
```

### least

创建 `LEAST` 标量函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import least

# 库实际声明的函数签名
print(inspect.signature(least))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import least

l = least(dialect, Column(dialect, "a"), Column(dialect, "b"), Column(dialect, "c"))
sql, params = l.to_sql()
# sql: 'LEAST("a", "b", "c")'
# params: ()
```

## 窗口函数 (Window Functions)

### row_number

创建 `ROW_NUMBER` 窗口函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import row_number

# 库实际声明的函数签名
print(inspect.signature(row_number))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import row_number

r = row_number(dialect)
sql, params = r.to_sql()
# sql: 'ROW_NUMBER()'
# params: ()
```

### rank, dense_rank

创建 `RANK` 和 `DENSE_RANK` 窗口函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import rank, dense_rank

# 库实际声明的函数签名
print(inspect.signature(rank))
print(inspect.signature(dense_rank))
```

### lag, lead

创建 `LAG` 和 `LEAD` 窗口函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import lag, lead

# 库实际声明的函数签名
print(inspect.signature(lag))
print(inspect.signature(lead))
```

### first_value, last_value, nth_value

创建值窗口函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import first_value, last_value, nth_value

# 库实际声明的函数签名
print(inspect.signature(first_value))
print(inspect.signature(last_value))
print(inspect.signature(nth_value))
```

## JSON 函数 (JSON Functions)

### json_extract, json_extract_text

创建 JSON 提取函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import json_extract, json_extract_text

# 库实际声明的函数签名
print(inspect.signature(json_extract))
print(inspect.signature(json_extract_text))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import json_extract

j = json_extract(dialect, Column(dialect, "data"), "$.name")
sql, params = j.to_sql()
# 使用 -> 操作符提取 JSON 值
```

### json_build_object

创建 `JSON_BUILD_OBJECT` 函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import json_build_object

# 库实际声明的函数签名
print(inspect.signature(json_build_object))
```

### json_array_elements

创建 `JSON_ARRAY_ELEMENTS` 函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import json_array_elements

# 库实际声明的函数签名
print(inspect.signature(json_array_elements))
```

### json_objectagg, json_arrayagg

创建 JSON 聚合函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import json_objectagg, json_arrayagg

# 库实际声明的函数签名
print(inspect.signature(json_objectagg))
print(inspect.signature(json_arrayagg))
```

## 数组函数 (Array Functions)

### array_agg

创建 `ARRAY_AGG` 聚合函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import array_agg

# 库实际声明的函数签名
print(inspect.signature(array_agg))
```

### unnest

创建 `UNNEST` 函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import unnest

# 库实际声明的函数签名
print(inspect.signature(unnest))
```

### array_length

创建 `ARRAY_LENGTH` 函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import array_length

# 库实际声明的函数签名
print(inspect.signature(array_length))
```

## 类型转换函数 (Type Conversion Functions)

### cast

创建类型转换表达式。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import cast

# 库实际声明的函数签名
print(inspect.signature(cast))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import cast
from rhosocial.activerecord.backend.expression.types import IntegerType

# 目标类型是 DataType 对象，绝不是类型名字符串
c = cast(dialect, Column(dialect, "value"), IntegerType(dialect))
sql, params = c.to_sql()
# sql: 'CAST("value" AS INTEGER)'
# params: ()
```

### to_char

创建 `TO_CHAR` 函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import to_char

# 库实际声明的函数签名
print(inspect.signature(to_char))
```

### to_number

创建 `TO_NUMBER` 函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import to_number

# 库实际声明的函数签名
print(inspect.signature(to_number))
```

### to_date

创建 `TO_DATE` 函数调用。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import to_date

# 库实际声明的函数签名
print(inspect.signature(to_date))
```

## 分组函数 (Grouping Functions)

### rollup

创建 `ROLLUP` 分组表达式。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import rollup

# 库实际声明的函数签名
print(inspect.signature(rollup))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import rollup

r = rollup(dialect, Column(dialect, "department"), Column(dialect, "region"))
sql, params = r.to_sql()
# sql: 'ROLLUP("department", "region")'
# params: ()
```

### cube

创建 `CUBE` 分组表达式。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import cube

# 库实际声明的函数签名
print(inspect.signature(cube))
```

### grouping_sets

创建 `GROUPING SETS` 分组表达式。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import grouping_sets

# 库实际声明的函数签名
print(inspect.signature(grouping_sets))
```

## 字符串连接操作符 (String Concatenation Operator)

### concat_op

使用 `||` 操作符创建字符串连接表达式。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import concat_op

# 库实际声明的函数签名
print(inspect.signature(concat_op))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import concat_op

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
import inspect
from rhosocial.activerecord.backend.expression.functions import mod

# 库实际声明的函数签名
print(inspect.signature(mod))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import mod

m = mod(dialect, 10, 3)
sql, params = m.to_sql()
# sql: 'MOD(?, ?)'
# params: (10, 3)
```

### sign

创建 `SIGN` 函数调用 (返回 -1, 0, 或 1)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import sign

# 库实际声明的函数签名
print(inspect.signature(sign))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import sign

s = sign(dialect, -42)
sql, params = s.to_sql()
# sql: 'SIGN(?)'
# params: (-42,)
```

### truncate

创建 `TRUNCATE` 函数调用 (截断数字)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import truncate

# 库实际声明的函数签名
print(inspect.signature(truncate))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import truncate

t = truncate(dialect, 3.14159, 2)
sql, params = t.to_sql()
# sql: 'TRUNCATE(?, ?)'
# params: (Decimal('3.14159'), 2)
```

### chr_

创建 `CHR` 函数调用 (ASCII 码转字符)。注意尾随下划线。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import chr_

# 库实际声明的函数签名
print(inspect.signature(chr_))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import chr_

c = chr_(dialect, 65)  # 返回 'A'
sql, params = c.to_sql()
# sql: 'CHR(?)'
# params: (65,)
```

### ascii

创建 `ASCII` 函数调用 (字符转 ASCII 码)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import ascii

# 库实际声明的函数签名
print(inspect.signature(ascii))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import ascii

a = ascii(dialect, "A")
sql, params = a.to_sql()
# sql: 'ASCII(?)'
# params: ("A",)
```

### octet_length

创建 `OCTET_LENGTH` 函数调用 (返回字节长度)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import octet_length

# 库实际声明的函数签名
print(inspect.signature(octet_length))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import octet_length

o = octet_length(dialect, Column(dialect, "text"))
sql, params = o.to_sql()
# sql: 'OCTET_LENGTH("text")'
# params: ()
```

### bit_length

创建 `BIT_LENGTH` 函数调用 (返回位长度)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import bit_length

# 库实际声明的函数签名
print(inspect.signature(bit_length))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import bit_length

b = bit_length(dialect, Column(dialect, "text"))
sql, params = b.to_sql()
# sql: 'BIT_LENGTH("text")'
# params: ()
```

### position

创建 `POSITION` 函数调用 (查找子字符串位置，1-based)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import position

# 库实际声明的函数签名
print(inspect.signature(position))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import position

p = position(dialect, "world", Column(dialect, "text"))
sql, params = p.to_sql()
# sql: 'POSITION(?, "text")'
# params: ("world",)
```

### overlay

创建 `OVERLAY` 函数调用 (替换子字符串)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import overlay

# 库实际声明的函数签名
print(inspect.signature(overlay))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import overlay

o = overlay(dialect, Column(dialect, "text"), "xxx", 1, 3)
sql, params = o.to_sql()
# sql: 'OVERLAY("text", ?, ?, ?)'
# params: ("xxx", 1, 3)
```

### translate

创建 `TRANSLATE` 函数调用 (字符替换)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import translate

# 库实际声明的函数签名
print(inspect.signature(translate))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import translate

t = translate(dialect, Column(dialect, "text"), "abc", "xyz")
sql, params = t.to_sql()
# sql: 'TRANSLATE("text", ?, ?)'
# params: ("abc", "xyz")
```

### repeat

创建 `REPEAT` 函数调用 (重复字符串)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import repeat

# 库实际声明的函数签名
print(inspect.signature(repeat))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import repeat

r = repeat(dialect, "ab", 3)
sql, params = r.to_sql()
# sql: 'REPEAT(?, ?)'
# params: ("ab", 3)
```

### space

创建 `SPACE` 函数调用 (生成空格)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import space

# 库实际声明的函数签名
print(inspect.signature(space))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import space

s = space(dialect, 5)
sql, params = s.to_sql()
# sql: 'SPACE(?)'
# params: (5,)
```

### current_timestamp

创建 `CURRENT_TIMESTAMP` 零元值函数。根据 SQL:2003 标准，无精度参数时生成不含括号的 `CURRENT_TIMESTAMP`；指定精度时生成 `CURRENT_TIMESTAMP(precision)`（带括号）。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import current_timestamp

# 库实际声明的函数签名
print(inspect.signature(current_timestamp))
```

**示例:**

```python
from rhosocial.activerecord.backend.expression.functions import current_timestamp

# 无精度参数 — 零元形式（无括号）
c = current_timestamp(dialect)
sql, params = c.to_sql()
# sql: 'CURRENT_TIMESTAMP'
# params: ()

# 有精度参数 — 带括号
c = current_timestamp(dialect, 6)
sql, params = c.to_sql()
# sql: 'CURRENT_TIMESTAMP(?)'
# params: (6,)
```

### localtimestamp

创建 `LOCALTIMESTAMP` 零元值函数。根据 SQL:2003 标准，无精度参数时生成不含括号的 `LOCALTIMESTAMP`；指定精度时生成 `LOCALTIMESTAMP(precision)`（带括号）。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import localtimestamp

# 库实际声明的函数签名
print(inspect.signature(localtimestamp))
```

**示例:**

```python
from rhosocial.activerecord.backend.expression.functions import localtimestamp

# 无精度参数 — 零元形式（无括号）
l = localtimestamp(dialect)
sql, params = l.to_sql()
# sql: 'LOCALTIMESTAMP'
# params: ()
```

### extract

创建 `EXTRACT` 函数调用 (提取日期时间部分)。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import extract

# 库实际声明的函数签名
print(inspect.signature(extract))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.functions import extract

e = extract(dialect, "YEAR", Column(dialect, "created_at"))
sql, params = e.to_sql()
# sql: 'EXTRACT(YEAR FROM "created_at")'
# params: ()
```

### current_user, session_user, system_user

创建 SQL:2003 零元值函数。生成不含括号的 `CURRENT_USER`、`SESSION_USER`、`SYSTEM_USER`。

```python
import inspect
from rhosocial.activerecord.backend.expression.functions import current_user, session_user, system_user

# 库实际声明的函数签名
print(inspect.signature(current_user))
print(inspect.signature(session_user))
print(inspect.signature(system_user))
```

**示例:**
```python
from rhosocial.activerecord.backend.expression.functions import current_user

u = current_user(dialect)
sql, params = u.to_sql()
# sql: 'CURRENT_USER'
# params: ()
```

## SQL/XML 函数

本节介绍 SQL/XML 标准表达式工厂函数，定义在 `rhosocial.activerecord.backend.expression.functions.xml`。

### xmlparse

XML 解析：将字符串解析为 XML 类型。

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlparse

# 将字符串解析为 XML DOCUMENT
expr = xmlparse(dialect, Column(dialect, "xml_string"), document=True)
sql, params = expr.to_sql()
# sql: 'XMLPARSE(DOCUMENT "xml_string")'
# params: ()

# 将字符串解析为 XML CONTENT
expr = xmlparse(dialect, Column(dialect, "xml_string"), document=False)
```

### xmlserialize

XML 序列化：将 XML 类型序列化为字符串。

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlserialize
from rhosocial.activerecord.backend.expression.types import VarCharType

# 目标类型是 DataType 对象，绝不是类型名字符串
expr = xmlserialize(dialect, Column(dialect, "xml_data"), VarCharType(dialect, length=255))
sql, params = expr.to_sql()
# sql: 'XMLSERIALIZE(CONTENT "xml_data" AS VARCHAR(255))'
# params: ()
```

### xmlelement

构造 XML 元素。

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlelement, xmlattributes

# 简单元素
elem = xmlelement(dialect, "name", Column(dialect, "user_name"))
sql, params = elem.to_sql()
# sql: 'XMLELEMENT(NAME name, "user_name")'
# params: ()

# 带属性的元素 —— 属性按名称传入，而不是作为内容
elem = xmlelement(
    dialect,
    "person",
    Column(dialect, "name"),
    attributes=xmlattributes(dialect, (Column(dialect, "id"), "id")),
)
# sql: 'XMLELEMENT(NAME person, XMLATTRIBUTES("id" AS id), "name")'
```

### xmlforest

构造 XML 森林（多个元素的序列）。

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

连接多个 XML 值。

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlconcat

expr = xmlconcat(dialect, Column(dialect, "xml1"), Column(dialect, "xml2"))
```

### xmlcomment

创建 XML 注释。

```python
from rhosocial.activerecord.backend.expression.functions.xml import xmlcomment

expr = xmlcomment(dialect, "This is a comment")
# sql: 'XMLCOMMENT(?)'
# params: ("This is a comment",)
```

### xmlpi

创建 XML 处理指令。

```python
from rhosocial.activerecord.backend.expression.functions.xml import xmlpi

expr = xmlpi(dialect, "xml-stylesheet", 'type="text/xsl" href="style.xsl"')
# sql: 'XMLPI(NAME xml-stylesheet, ?)'
# params: ('type="text/xsl" href="style.xsl"',)
```

### xmlroot

修改 XML 值的根节点属性。

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

XML 聚合函数。

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlagg

expr = xmlagg(dialect, Column(dialect, "xml_column"))
# sql: 'XMLAGG("xml_column")'
# params: ()
```

### xmlquery

XQuery 查询评估。

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlquery

expr = xmlquery(dialect, "/root/element/text()",
    passing=[Column(dialect, "xml_column")])
# sql: 'XMLQUERY(? PASSING "xml_column" RETURNING CONTENT)'
# params: ('/root/element/text()',)
```

### xmlexists

XQuery 存在性检查。

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.functions.xml import xmlexists

expr = xmlexists(dialect, "/root/element",
    passing=[Column(dialect, "xml_column")])
# sql: 'XMLEXISTS(? PASSING "xml_column")'
# params: ('/root/element',)
```

### xmltable

通过 XQuery 表达式生成表值。

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

## 日期时间间隔表达式

定义在 `rhosocial.activerecord.backend.expression.functions.datetime` 的函数。

### extract

创建结构化的 `EXTRACT` 表达式（相比 `core.md` 中的 `extract` 函数，本实现支持更严格的字段枚举）。

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.datetime import (
    DateTimeField, ExtractExpression,
)

# 提取年份
expr = ExtractExpression(dialect, DateTimeField.YEAR, Column(dialect, "created_at"))
sql, params = expr.to_sql()
# sql: 'EXTRACT(YEAR FROM "created_at")'
# params: ()
```

### interval

创建结构化时间间隔值。

```python
from rhosocial.activerecord.backend.expression.datetime import (
    IntervalExpression, IntervalUnit,
)

# 间隔 7 天
interval = IntervalExpression(dialect, 7, IntervalUnit.DAY)
sql, params = interval.to_sql()
# sql: "INTERVAL '7' DAY"
# params: ()
```

### 日期时间运算

```python
from rhosocial.activerecord.backend.expression import Column

from rhosocial.activerecord.backend.expression.datetime import (
    DatetimeAddExpression, DatetimeSubtractExpression, DatetimeDiffExpression,
    IntervalExpression, IntervalUnit, DateTimeField
)

# 日期 + 间隔
expr = DatetimeAddExpression(dialect,
    Column(dialect, "created_at"),
    IntervalExpression(dialect, 30, IntervalUnit.DAY))
# sql: '"created_at" + INTERVAL '30' DAY'
# params: ()

# 日期 - 间隔
expr = DatetimeSubtractExpression(dialect,
    Column(dialect, "created_at"),
    IntervalExpression(dialect, 7, IntervalUnit.DAY))

# 日期差值
expr = DatetimeDiffExpression(dialect, DateTimeField.DAY,
    Column(dialect, "start_date"),
    Column(dialect, "end_date"))
# sql: 'DATEDIFF(DAY, "start_date", "end_date")'
```
