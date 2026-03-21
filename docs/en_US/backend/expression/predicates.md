# Predicates

This document describes the predicate expression classes defined in `src/rhosocial/activerecord/backend/expression/predicates.py`. These classes represent SQL conditions used in `WHERE`, `HAVING`, and `ON` clauses.

## Overview

Predicates are expressions that evaluate to a boolean result (TRUE, FALSE, or UNKNOWN/NULL). They are the building blocks of filtering logic in SQL queries. All predicate classes inherit from `bases.SQLPredicate`.

## Classes

### ComparisonPredicate

Represents standard comparison operations between two expressions.

```python
class ComparisonPredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", op: str, left: "SQLValueExpression", right: "SQLValueExpression"): ...
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `op`: The comparison operator (e.g., `=`, `>`, `<`, `>=`, `<=`, `<>`).
- `left`: The left-side expression.
- `right`: The right-side expression.

**Example:**
```python
# users.age >= 18
    # pred = ComparisonPredicate(dialect, ">=", Column(dialect, "age"), Literal(dialect, 18))
    # -> ('"age" >= ?', (18,))
```

### LogicalPredicate

Represents logical operations combining other predicates.

```python
class LogicalPredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", op: str, *predicates: "bases.SQLPredicate"): ...
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `op`: The logical operator (e.g., `AND`, `OR`, `NOT`).
- `*predicates`: One or more predicates to combine.

**Example:**
```python
# (age >= 18) AND (status = 'active')
    # pred1 = ComparisonPredicate(dialect, ">=", Column(dialect, "age"), Literal(dialect, 18))
    # pred2 = ComparisonPredicate(dialect, "=", Column(dialect, "status"), Literal(dialect, "active"))
    # combined = LogicalPredicate(dialect, "AND", pred1, pred2)
    # -> ('"age" >= ? AND "status" = ?', (18, 'active'))
```

### LikePredicate

Represents pattern matching operations (`LIKE`, `ILIKE`).

```python
class LikePredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", op: str, expr: "SQLValueExpression", pattern: "SQLValueExpression"): ...
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `op`: The operator (`LIKE`, `ILIKE`, `NOT LIKE`, etc.).
- `expr`: The expression to test.
- `pattern`: The pattern to match against.

**Example:**
```python
# name LIKE 'User%'
    # pred = LikePredicate(dialect, "LIKE", Column(dialect, "name"), Literal(dialect, "User%"))
    # -> ('"name" LIKE ?', ('User%',))
```

### InPredicate

Represents set membership tests (`IN`).

```python
class InPredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", expr: "SQLValueExpression", values: "bases.BaseExpression"): ...
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `expr`: The expression to test.
- `values`: A `Literal` containing a collection (list/tuple) or a subquery expression.

**Example:**
```python
# status IN ('active', 'pending')
pred = InPredicate(dialect, Column(dialect, "status"), Literal(dialect, ["active", "pending"]))
```

### BetweenPredicate

Represents range tests (`BETWEEN`).

```python
class BetweenPredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", low: "bases.BaseExpression", high: "bases.BaseExpression"): ...
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `expr`: The expression to test.
- `low`: The lower bound.
- `high`: The upper bound.

**Example:**
```python
# age BETWEEN 18 AND 65
pred = BetweenPredicate(dialect, Column(dialect, "age"), Literal(dialect, 18), Literal(dialect, 65))
```

### IsNullPredicate

Represents NULL tests (`IS NULL`, `IS NOT NULL`).

```python
class IsNullPredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", is_not: bool = False): ...
```

**Parameters:**
- `dialect`: The SQL dialect instance.
- `expr`: The expression to test.
- `is_not`: If `True`, creates `IS NOT NULL`. Default is `False` (`IS NULL`).

**Example:**
```python
# email IS NOT NULL
    # pred = IsNullPredicate(dialect, Column(dialect, "email"), is_not=True)
    # -> ('"email" IS NOT NULL', ())
```

### IsBooleanPredicate

Represents boolean value tests (`IS TRUE`, `IS NOT TRUE`, `IS FALSE`, `IS NOT FALSE`).

```python
class IsBooleanPredicate(bases.SQLPredicate):
    def __init__(self, dialect: "SQLDialectBase", expr: "bases.BaseExpression", value: bool, is_not: bool = False): ...
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
# is_active IS TRUE
pred = IsBooleanPredicate(dialect, Column(dialect, "is_active"), value=True, is_not=False)
# -> ('"is_active" IS TRUE', ())

# is_active IS NOT FALSE
pred = IsBooleanPredicate(dialect, Column(dialect, "is_active"), value=False, is_not=True)
# -> ('"is_active" IS NOT FALSE', ())
```

**Convenience Methods:**
The `Column` class provides convenience methods for creating these predicates:

```python
col = Column(dialect, "is_active")
col.is_true()       # IS TRUE
col.is_not_true()   # IS NOT TRUE
col.is_false()      # IS FALSE
col.is_not_false()  # IS NOT FALSE
```
