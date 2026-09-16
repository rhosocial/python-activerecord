# Custom Expressions

## Overview

rhosocial-activerecord's expression system is extensible. You can create custom expression classes for database-specific SQL syntax that isn't covered by the core expression library.

## Expression Design Principles

Before creating custom expressions, understand these core principles:

### 1. Expressions Are Declarative, Not Imperative

An expression instance **collects all parameters** that affect SQL generation. It is a data container, not an SQL generator. The expression itself does not produce SQL — it delegates to the dialect's format functions.

```python
# This expression collects parameters, not generates SQL
expr = ComparisonPredicate(dialect, column, operator='>=', value=literal)
# expr.dialect, expr.column, expr.operator, expr.value are all stored
```

### 2. Delegation to Dialect

When `to_sql()` is called, the expression delegates to its bound dialect's `format_*()` methods. The dialect decides the actual SQL syntax based on:
- Backend type (MySQL, PostgreSQL, SQLite, etc.)
- Dialect version (e.g., MySQL 5.7 vs 8.0)
- Feature flags (e.g., `supports_returning_insert()`)
- The expression's parameters

You never write this delegation yourself: `to_sql()` is implemented **once in `BaseExpression`** and resolves the `format_method` name your class declares:

```python
class MyExpression(SQLValueExpression):
    @property
    def format_method(self) -> str:
        # to_sql() resolves this name on the bound dialect and calls
        # dialect.format_my_expression(self) — the dialect decides the SQL.
        return "format_my_expression"
```

### 3. DataTypes Are Expressions

DataType classes inherit from `BaseExpression` just like other expressions. They follow the same delegation pattern: `to_sql()` calls `dialect.format_data_type(self)`. This means DataTypes benefit from the same extensibility as other expressions.

### 4. Serialization Support

Because expression instances collect all parameters that affect SQL generation, they can be **serialized** (e.g., to JSON) and **deserialized** back. This enables:
- Caching query plans
- Transmitting queries across processes
- Storing query definitions for later execution

The serialization round-trip preserves all information needed to regenerate the SQL.

### 5. Composition Over Inheritance

Expressions gain capabilities by composing mixins, not through deep inheritance hierarchies. A `DistanceExpression` can gain comparison operators by mixing in `ComparisonMixin`, without inheriting from a "comparable expression" base class.

## Expression Base Classes

All expressions inherit from one of these base classes in `rhosocial.activerecord.backend.expression.bases`:

| Base Class | Purpose | Use When |
|-----------|---------|----------|
| `SQLValueExpression` | Returns a non-boolean value (integer, string, date, etc.) | Creating a function call or computed value |
| `SQLPredicate` | Returns a boolean value | Creating a condition or filter |

Both are rendered through the unified `to_sql()` — your subclass declares only its `format_method` name; the dialect's matching `format_*()` method returns `(sql_string, params_tuple)`.

## Creating a Custom Value Expression

Subclass `SQLValueExpression` for expressions that produce a value:

```python
from rhosocial.activerecord.backend.expression.bases import SQLValueExpression, SQLQueryAndParams


class RegexMatchExpression(SQLValueExpression):
    """Custom expression: column REGEXP pattern."""

    def __init__(self, dialect, column, pattern):
        super().__init__(dialect)
        self._column = column
        self._pattern = pattern

    @property
    def format_method(self) -> str:
        return "format_regex_match"
```

The rendering lives on the dialect:

```python
class RegexMatchDialectMixin:
    def format_regex_match(self, expr: RegexMatchExpression) -> SQLQueryAndParams:
        col_sql, col_params = expr.column.to_sql()
        return f"{col_sql} REGEXP ?", col_params + (expr.pattern,)
```

Usage:

```python
# Assuming User.c.name is a Column expression
expr = RegexMatchExpression(dialect, User.c.name, r'^admin.*')
query = User.query().where(expr)
```

## Creating a Custom Predicate

Subclass `SQLPredicate` for expressions that produce a boolean:

```python
from rhosocial.activerecord.backend.expression.bases import SQLPredicate, SQLQueryAndParams


class FuzzyMatchPredicate(SQLPredicate):
    """Custom predicate: column FUZZY_MATCH pattern."""

    def __init__(self, dialect, column, pattern, threshold=0.8):
        super().__init__(dialect)
        self._column = column
        self._pattern = pattern
        self._threshold = threshold

    @property
    def format_method(self) -> str:
        return "format_fuzzy_match"
```

The rendering lives on the dialect:

```python
class FuzzyMatchDialectMixin:
    def format_fuzzy_match(self, expr: FuzzyMatchPredicate) -> SQLQueryAndParams:
        col_sql, col_params = expr.column.to_sql()
        return (
            f"{col_sql} FUZZY_MATCH(?, ?)",
            col_params + (expr.pattern, expr.threshold),
        )
```

## Adding Operator Support

Expression classes gain operators by composing mixins from `rhosocial.activerecord.backend.expression.mixins`:

| Mixin | Provides |
|-------|----------|
| `ComparisonMixin` | `==`, `!=`, `>`, `>=`, `<`, `<=`, `is_null()`, `in_()`, `between()` |
| `ArithmeticMixin` | `+`, `-`, `*`, `/`, `%` |
| `LogicalMixin` | `&` (AND), `\|` (OR), `~` (NOT) |
| `StringMixin` | `.like()`, `.ilike()` |
| `AliasableMixin` | `.as_()` alias |
| `TypeCastingMixin` | `.cast()` |

Example with operator support:

```python
from rhosocial.activerecord.backend.expression.bases import SQLValueExpression
from rhosocial.activerecord.backend.expression.mixins import ArithmeticMixin, ComparisonMixin


class DistanceExpression(ArithmeticMixin, ComparisonMixin, SQLValueExpression):
    """Custom expression: ST_Distance(col1, col2)."""

    def __init__(self, dialect, col1, col2):
        super().__init__(dialect)
        self._col1 = col1
        self._col2 = col2

    @property
    def format_method(self) -> str:
        return "format_st_distance"
```

The rendering lives on the dialect:

```python
from rhosocial.activerecord.backend.expression.bases import SQLQueryAndParams


class DistanceDialectMixin:
    def format_st_distance(self, expr: DistanceExpression) -> SQLQueryAndParams:
        sql1, params1 = expr.col1.to_sql()
        sql2, params2 = expr.col2.to_sql()
        return f"ST_Distance({sql1}, {sql2})", params1 + params2
```

Now you can use comparison operators:

```python
# Find users within 10km
distance = DistanceExpression(dialect, User.c.location, Literal(dialect, target_location))
query = User.query().where(distance < 10000)
```

## Delegating to the Dialect

Delegation is the **only** rendering mechanism: the expression class declares the formatting method name, and the dialect implements it. This allows different backends to produce different SQL:

```python
class MyCustomExpression(SQLValueExpression):
    @property
    def format_method(self) -> str:
        # to_sql() resolves this on the bound dialect and calls
        # dialect.format_my_custom_expression(self)
        return "format_my_custom_expression"
```

Then in your custom dialect mixin:

```python
class MyCustomDialectMixin:
    def format_my_custom_expression(self, expr) -> SQLQueryAndParams:
        sql, params = expr.inner.to_sql()
        # MySQL syntax
        return f"MY_FUNC({sql})", params
```

## Using in Queries

### Direct Construction

```python
expr = RegexMatchExpression(dialect, User.c.name, r'^admin.*')
query = User.query().where(expr)
```

### As a Model Method (Recommended)

Wrap the expression in a model method for cleaner API:

```python
class User(ActiveRecord):
    name: str

    @classmethod
    def table_name(cls) -> str:
        return 'users'

    @classmethod
    def regex_match(cls, column, pattern):
        """Create a REGEXP match expression."""
        return RegexMatchExpression(cls.backend().dialect, column, pattern)

# Usage
query = User.query().where(User.regex_match(User.c.name, r'^admin.*'))
```

## See Also

- [Dialect Expressions](../backend_specific_features/dialect.md) — expression system architecture
- [Custom Data Types](custom_types.md) — defining new DataType subclasses
- [Core: Expression Base Classes](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/expression)

💡 *AI Prompt:* "How do I create a custom expression for a database-specific function?"
