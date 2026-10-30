# Predicates

This document describes the predicate expression classes defined in `src/rhosocial/activerecord/backend/expression/predicates.py`. These classes represent SQL conditions used in `WHERE`, `HAVING`, and `ON` clauses.

## Overview

Predicates are expressions that evaluate to a boolean result (TRUE, FALSE, or UNKNOWN/NULL). They are the building blocks of filtering logic in SQL queries. All predicate classes inherit from `bases.SQLPredicate`.

## Classes

### ComparisonPredicate

Represents standard comparison operations between two expressions.

```python
import inspect

from rhosocial.activerecord.backend.expression import ComparisonPredicate

print(inspect.signature(ComparisonPredicate))
# (dialect: 'SQLDialectBase', op: Any, left: 'SQLValue', right: 'SQLValue')
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `op`: The comparison operation — a `ComparisonOperator` member (`EQ`, `NE`, `GT`, `GTE`, `LT`, `LTE`) or its SQL spelling (`=`, `!=`, `>`, `>=`, `<`, `<=`).
- `left`: The left-side expression.
- `right`: The right-side expression.

**Example:**
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

Represents logical operations combining other predicates.

```python
import inspect

from rhosocial.activerecord.backend.expression import LogicalPredicate

print(inspect.signature(LogicalPredicate))
# (dialect: 'SQLDialectBase', op: str, *operands: 'SQLPredicate')
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `op`: The logical operator (e.g., `AND`, `OR`, `NOT`).
- `*operands`: One or more predicates to combine.

**Example:**
```python
from rhosocial.activerecord.backend.expression import (
    IntegerColumn, LogicalPredicate, StringColumn,
)

# (age >= 18) AND (status = 'active')
# Typed columns build comparison predicates with Python operators.
pred1 = IntegerColumn(dialect, "age") >= 18
pred2 = StringColumn(dialect, "status") == "active"
combined = LogicalPredicate(dialect, "AND", pred1, pred2)
combined.to_sql()
# -> ('"age" >= ? AND "status" = ?', (18, 'active'))
```

### LikePredicate

Represents pattern matching operations (`LIKE`, `ILIKE`).

```python
import inspect

from rhosocial.activerecord.backend.expression import LikePredicate

print(inspect.signature(LikePredicate))
# (dialect: 'SQLDialectBase', op: 'LikeOperator', left: 'SQLValue', pattern: 'SQLValue')
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `op`: The operation — a `LikeOperator` member (`like`, `not_like`, `ilike`) or its SQL keyword (`LIKE`, `NOT LIKE`, `ILIKE`).
- `left`: The expression to test.
- `pattern`: The pattern to match against.

**Example:**
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

Represents set membership tests (`IN`).

```python
import inspect

from rhosocial.activerecord.backend.expression import InPredicate

print(inspect.signature(InPredicate))
# (dialect: 'SQLDialectBase', operand: 'SQLValue', values: 'BaseExpression')
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `operand`: The expression to test.
- `values`: A `Literal` containing a collection (list/tuple) or a subquery expression.

**Example:**
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

Represents range tests (`BETWEEN`).

```python
import inspect

from rhosocial.activerecord.backend.expression import BetweenPredicate

print(inspect.signature(BetweenPredicate))
# (dialect: 'SQLDialectBase', operand: 'BaseExpression',
#  low: 'BaseExpression', high: 'BaseExpression')
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `operand`: The expression to test.
- `low`: The lower bound.
- `high`: The upper bound.

**Example:**
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

Represents NULL tests (`IS NULL`, `IS NOT NULL`).

```python
import inspect

from rhosocial.activerecord.backend.expression import IsNullPredicate

print(inspect.signature(IsNullPredicate))
# (dialect: 'SQLDialectBase', operand: 'BaseExpression', is_not: bool = False)
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `operand`: The expression to test.
- `is_not`: If `True`, creates `IS NOT NULL`. Default is `False` (`IS NULL`).

**Example:**
```python
from rhosocial.activerecord.backend.expression import IsNullPredicate, StringColumn

# email IS NOT NULL
pred = IsNullPredicate(dialect, StringColumn(dialect, "email"), is_not=True)
pred.to_sql()
# -> ('"email" IS NOT NULL', ())
```

### IsBooleanPredicate

Represents boolean value tests (`IS TRUE`, `IS NOT TRUE`, `IS FALSE`, `IS NOT FALSE`).

```python
import inspect

from rhosocial.activerecord.backend.expression import IsBooleanPredicate

print(inspect.signature(IsBooleanPredicate))
# (dialect: 'SQLDialectBase', expr: 'BaseExpression', value: bool, is_not: bool = False)
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `expr`: The expression to test.
- `value`: `True` for `IS TRUE`/`IS NOT TRUE`, `False` for `IS FALSE`/`IS NOT FALSE`.
- `is_not`: If `True`, creates the negated form. Default is `False`.

**Behavior:**
This predicate properly handles SQL's three-valued logic (TRUE, FALSE, NULL):

- `IS TRUE`: matches only TRUE values (not FALSE or NULL)
- `IS NOT TRUE`: matches FALSE and NULL values
- `IS FALSE`: matches only FALSE values (not TRUE or NULL)
- `IS NOT FALSE`: matches TRUE and NULL values

This is different from direct equality comparisons (`= TRUE` or `= FALSE`) which do not handle NULL values correctly.

**Example:**
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

**Convenience Methods:**
The `BooleanColumn` class provides convenience methods for creating these predicates:

```python
from rhosocial.activerecord.backend.expression import BooleanColumn

col = BooleanColumn(dialect, "is_active")
col.is_true().to_sql()       # -> ('"is_active" IS TRUE', ())
col.is_not_true().to_sql()   # -> ('"is_active" IS NOT TRUE', ())
col.is_false().to_sql()      # -> ('"is_active" IS FALSE', ())
col.is_not_false().to_sql()  # -> ('"is_active" IS NOT FALSE', ())
```
