# 谓词表达式 (Predicates)

本文档描述了定义在 `src/rhosocial/activerecord/backend/expression/predicates.py` 中的谓词表达式类。这些类表示用于 `WHERE`、`HAVING` 和 `ON` 子句中的 SQL 条件。

## 概述

谓词是计算结果为布尔值（TRUE、FALSE 或 UNKNOWN/NULL）的表达式。它们是 SQL 查询中过滤逻辑的构建块。所有谓词类都继承自 `bases.SQLPredicate`。

## 类说明

### ComparisonPredicate

表示两个表达式之间的标准比较操作。

```python
import inspect

from rhosocial.activerecord.backend.expression import ComparisonPredicate

print(inspect.signature(ComparisonPredicate))
# (dialect: 'SQLDialectBase', op: Any, left: 'SQLValue', right: 'SQLValue')
```

**参数:**
- `dialect`: SQL 方言实例。
- `op`: 比较操作——`ComparisonOperator` 成员（`EQ`、`NE`、`GT`、`GTE`、`LT`、`LTE`）或其 SQL 写法（`=`、`!=`、`>`、`>=`、`<`、`<=`）。
- `left`: 左侧表达式。
- `right`: 右侧表达式。

**示例:**
```python
from rhosocial.activerecord.backend.expression import (
    ComparisonPredicate, IntegerColumn, Literal,
)

# users.age >= 18
pred = ComparisonPredicate(
    dialect, ">=", IntegerColumn(dialect, "age"), Literal(dialect, 18)
)
pred.to_sql()
# -> ('"age" >= ?', (18,))
```

### LogicalPredicate

表示组合其他谓词的逻辑操作。

```python
import inspect

from rhosocial.activerecord.backend.expression import LogicalPredicate

print(inspect.signature(LogicalPredicate))
# (dialect: 'SQLDialectBase', op: str, *operands: 'SQLPredicate')
```

**参数:**
- `dialect`: SQL 方言实例。
- `op`: 逻辑运算符 (例如 `AND`, `OR`, `NOT`)。
- `*operands`: 一个或多个要组合的谓词。

**示例:**
```python
from rhosocial.activerecord.backend.expression import (
    IntegerColumn, LogicalPredicate, StringColumn,
)

# (age >= 18) AND (status = 'active')
# 带类型的列用 Python 运算符构建比较谓词。
pred1 = IntegerColumn(dialect, "age") >= 18
pred2 = StringColumn(dialect, "status") == "active"
combined = LogicalPredicate(dialect, "AND", pred1, pred2)
combined.to_sql()
# -> ('"age" >= ? AND "status" = ?', (18, 'active'))
```

### LikePredicate

表示模式匹配操作 (`LIKE`, `ILIKE`)。

```python
import inspect

from rhosocial.activerecord.backend.expression import LikePredicate

print(inspect.signature(LikePredicate))
# (dialect: 'SQLDialectBase', op: 'LikeOperator', left: 'SQLValue', pattern: 'SQLValue')
```

**参数:**
- `dialect`: SQL 方言实例。
- `op`: 操作——`LikeOperator` 成员（`like`、`not_like`、`ilike`）或其 SQL 关键字（`LIKE`、`NOT LIKE`、`ILIKE`）。
- `left`: 要测试的表达式。
- `pattern`: 要匹配的模式。

**示例:**
```python
from rhosocial.activerecord.backend.expression import (
    LikePredicate, Literal, StringColumn,
)

# name LIKE 'User%'
pred = LikePredicate(
    dialect, "like", StringColumn(dialect, "name"), Literal(dialect, "User%")
)
pred.to_sql()
# -> ('"name" LIKE ?', ('User%',))
```

### InPredicate

表示集合成员测试 (`IN`)。

```python
import inspect

from rhosocial.activerecord.backend.expression import InPredicate

print(inspect.signature(InPredicate))
# (dialect: 'SQLDialectBase', operand: 'SQLValue', values: 'BaseExpression')
```

**参数:**
- `dialect`: SQL 方言实例。
- `operand`: 要测试的表达式。
- `values`: 包含集合（列表/元组）的 `Literal` 或子查询表达式。

**示例:**
```python
from rhosocial.activerecord.backend.expression import (
    InPredicate, Literal, StringColumn,
)

# status IN ('active', 'pending')
pred = InPredicate(
    dialect,
    StringColumn(dialect, "status"),
    Literal(dialect, ["active", "pending"]),
)
pred.to_sql()
# -> ('"status" IN (?, ?)', ('active', 'pending'))
```

### BetweenPredicate

表示范围测试 (`BETWEEN`)。

```python
import inspect

from rhosocial.activerecord.backend.expression import BetweenPredicate

print(inspect.signature(BetweenPredicate))
# (dialect: 'SQLDialectBase', operand: 'BaseExpression',
#  low: 'BaseExpression', high: 'BaseExpression')
```

**参数:**
- `dialect`: SQL 方言实例。
- `operand`: 要测试的表达式。
- `low`: 下界。
- `high`: 上界。

**示例:**
```python
from rhosocial.activerecord.backend.expression import (
    BetweenPredicate, IntegerColumn, Literal,
)

# age BETWEEN 18 AND 65
pred = BetweenPredicate(
    dialect, IntegerColumn(dialect, "age"), Literal(dialect, 18), Literal(dialect, 65)
)
pred.to_sql()
# -> ('"age" BETWEEN ? AND ?', (18, 65))
```

### IsNullPredicate

表示 NULL 测试 (`IS NULL`, `IS NOT NULL`)。

```python
import inspect

from rhosocial.activerecord.backend.expression import IsNullPredicate

print(inspect.signature(IsNullPredicate))
# (dialect: 'SQLDialectBase', operand: 'BaseExpression', is_not: bool = False)
```

**参数:**
- `dialect`: SQL 方言实例。
- `operand`: 要测试的表达式。
- `is_not`: 如果为 `True`，创建 `IS NOT NULL`。默认为 `False` (`IS NULL`)。

**示例:**
```python
from rhosocial.activerecord.backend.expression import IsNullPredicate, StringColumn

# email IS NOT NULL
pred = IsNullPredicate(dialect, StringColumn(dialect, "email"), is_not=True)
pred.to_sql()
# -> ('"email" IS NOT NULL', ())
```

### IsBooleanPredicate

表示布尔值测试 (`IS TRUE`, `IS NOT TRUE`, `IS FALSE`, `IS NOT FALSE`)。

```python
import inspect

from rhosocial.activerecord.backend.expression import IsBooleanPredicate

print(inspect.signature(IsBooleanPredicate))
# (dialect: 'SQLDialectBase', expr: 'BaseExpression', value: bool, is_not: bool = False)
```

**参数:**
- `dialect`: SQL 方言实例。
- `expr`: 要测试的表达式。
- `value`: `True` 表示 `IS TRUE`/`IS NOT TRUE`，`False` 表示 `IS FALSE`/`IS NOT FALSE`。
- `is_not`: 如果为 `True`，创建否定形式。默认为 `False`。

**行为说明:**
此谓词正确处理 SQL 的三值逻辑（TRUE、FALSE、NULL）：

- `IS TRUE`: 仅匹配 TRUE 值（不包括 FALSE 或 NULL）
- `IS NOT TRUE`: 匹配 FALSE 和 NULL 值
- `IS FALSE`: 仅匹配 FALSE 值（不包括 TRUE 或 NULL）
- `IS NOT FALSE`: 匹配 TRUE 和 NULL 值

这与直接使用相等比较（`= TRUE` 或 `= FALSE`）不同，后者无法正确处理 NULL 值。

**示例:**
```python
from rhosocial.activerecord.backend.expression import BooleanColumn, IsBooleanPredicate

# is_active IS TRUE
pred = IsBooleanPredicate(
    dialect, BooleanColumn(dialect, "is_active"), value=True, is_not=False
)
pred.to_sql()
# -> ('"is_active" IS TRUE', ())

# is_active IS NOT FALSE
pred = IsBooleanPredicate(
    dialect, BooleanColumn(dialect, "is_active"), value=False, is_not=True
)
pred.to_sql()
# -> ('"is_active" IS NOT FALSE', ())
```

**便捷方法:**
`BooleanColumn` 类提供了创建这些谓词的便捷方法：

```python
from rhosocial.activerecord.backend.expression import BooleanColumn

col = BooleanColumn(dialect, "is_active")
col.is_true().to_sql()       # -> ('"is_active" IS TRUE', ())
col.is_not_true().to_sql()   # -> ('"is_active" IS NOT TRUE', ())
col.is_false().to_sql()      # -> ('"is_active" IS FALSE', ())
col.is_not_false().to_sql()  # -> ('"is_active" IS NOT FALSE', ())
```
