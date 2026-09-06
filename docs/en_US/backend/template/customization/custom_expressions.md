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

```python
class MyExpression(SQLValueExpression):
    def to_sql(self) -> SQLQueryAndParams:
        # Delegate to dialect — the dialect decides the SQL syntax
        return self.dialect.format_my_expression(self._inner)
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

Both require implementing `to_sql()` which returns `(sql_string, params_tuple)`.

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

    def to_sql(self) -> SQLQueryAndParams:
        col_sql, col_params = self._column.to_sql()
        return f"{col_sql} REGEXP ?", col_params + (self._pattern,)
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

    def to_sql(self) -> SQLQueryAndParams:
        col_sql, col_params = self._column.to_sql()
        return (
            f"{col_sql} FUZZY_MATCH(?, ?)",
            col_params + (self._pattern, self._threshold),
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
from rhosocial.activerecord.backend.expression.bases import SQLValueExpression, SQLQueryAndParams
from rhosocial.activerecord.backend.expression.mixins import ArithmeticMixin, ComparisonMixin


class DistanceExpression(ArithmeticMixin, ComparisonMixin, SQLValueExpression):
    """Custom expression: ST_Distance(col1, col2)."""

    def __init__(self, dialect, col1, col2):
        super().__init__(dialect)
        self._col1 = col1
        self._col2 = col2

    def to_sql(self) -> SQLQueryAndParams:
        sql1, params1 = self._col1.to_sql()
        sql2, params2 = self._col2.to_sql()
        return f"ST_Distance({sql1}, {sql2})", params1 + params2
```

Now you can use comparison operators:

```python
# Find users within 10km
distance = DistanceExpression(dialect, User.c.location, Literal(dialect, target_location))
query = User.query().where(distance < 10000)
```

## Delegating to the Dialect

The recommended pattern is to delegate SQL formatting to the dialect rather than hardcoding SQL strings. This allows different backends to produce different SQL:

```python
class MyCustomExpression(SQLValueExpression):
    def to_sql(self) -> SQLQueryAndParams:
        # Delegate to dialect for backend-specific formatting
        return self.dialect.format_my_custom_expression(self._inner)
```

Then in your custom dialect mixin:

```python
class MyCustomDialectMixin:
    def format_my_custom_expression(self, expr):
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
