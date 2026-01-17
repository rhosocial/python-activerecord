# Core Expressions

This section details the fundamental building blocks of the Expression System, including base classes, mixins, core expressions, and operators.

## Table of Contents

- [Protocols & Helpers](#protocols--helpers)
- [Base Classes](#base-classes)
- [Mixins](#mixins)
  - [AliasableMixin](#aliasablemixin)
  - [ComparisonMixin](#comparisonmixin)
  - [ArithmeticMixin](#arithmeticmixin)
  - [LogicalMixin](#logicalmixin)
  - [StringMixin](#stringmixin)
- [Core Expressions](#core-expressions)
  - [TableExpression](#tableexpression)
  - [Column](#column)
  - [Literal](#literal)
  - [WildcardExpression](#wildcardexpression)
  - [Subquery](#subquery)
- [Operators](#operators)
  - [Identifier](#identifier)
  - [SQLOperation](#sqloperation)
  - [BinaryExpression](#binaryexpression)
  - [BinaryArithmeticExpression](#binaryarithmeticexpression)
  - [UnaryExpression](#unaryexpression)
  - [RawSQLExpression](#rawsqlexpression)
  - [RawSQLPredicate](#rawsqlpredicate)

## Base Classes

The expression system is built on a hierarchy of abstract base classes defined in `rhosocial.activerecord.backend.expression.bases`.

### ToSQLProtocol

The `ToSQLProtocol` defines the contract for any object that can be converted to SQL.

```python
class ToSQLProtocol(Protocol):
    def to_sql(self) -> Tuple[str, tuple]:
        """
        Converts the object into a SQL string and a tuple of parameters.
        
        Returns:
            Tuple[str, tuple]: The SQL string and a tuple of parameters.
        """
        ...
```

### BaseExpression

`BaseExpression` is the root abstract base class for all expression components. It implements `ToSQLProtocol` and holds a reference to the `SQLDialect`.

```python
class BaseExpression(abc.ABC, ToSQLProtocol):
    def __init__(self, dialect: "SQLDialectBase"):
        self._dialect = dialect

    @property
    def dialect(self) -> "SQLDialectBase":
        return self._dialect

    @abc.abstractmethod
    def to_sql(self) -> Tuple[str, tuple]:
        raise NotImplementedError
```

### SQLPredicate

`SQLPredicate` represents an expression that evaluates to a boolean value (e.g., `WHERE` conditions). It mixes in `LogicalMixin` to support `&` (AND), `|` (OR), and `~` (NOT) operators.

```python
class SQLPredicate(mixins.LogicalMixin, BaseExpression):
    pass
```

### SQLValueExpression

`SQLValueExpression` represents an expression that evaluates to a scalar value (e.g., columns, literals, function results).

```python
class SQLValueExpression(BaseExpression):
    pass
```

## Core Components

The `rhosocial.activerecord.backend.expression.core` module defines the fundamental building blocks of SQL queries.

### Literal

Represents a literal value in a SQL query. It handles parameter binding automatically.

```python
class Literal(mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", value: Any): ...
    
    # Example: WHERE status = ?
    # Literal(dialect, "active")
    # -> ('?', ('active',))
```

### Column

Represents a column reference, optionally with a table qualifier and an alias.

```python
class Column(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", name: str, table: Optional[str] = None, alias: Optional[str] = None): ...

    # Example: users.name
    # Column(dialect, "name", table="users")
```

### TableExpression

Represents a table or view, optionally with an alias and temporal options (e.g., FOR SYSTEM_TIME).

```python
class TableExpression(mixins.AliasableMixin, bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase", name: str, alias: Optional[str] = None, temporal_options: Optional[Dict[str, Any]] = None): ...

    # Example: FROM users AS u
    # TableExpression(dialect, "users", alias="u")
    # -> ('"users" AS "u"', ())
```

### FunctionCall

Represents a generic scalar function call.

```python
class FunctionCall(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", func_name: str, *args: "bases.BaseExpression", is_distinct: bool = False, alias: Optional[str] = None): ...
```

### WildcardExpression

Represents a wildcard (`*`) or table wildcard (`table.*`). PREFER this over `Literal("*")`.

```python
class WildcardExpression(bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", table: Optional[str] = None): ...
```

### Subquery

Represents a subquery expression. It can wrap a SQL string, a `(sql, params)` tuple, or another expression.

```python
class Subquery(mixins.AliasableMixin, mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", query_input: Union[str, tuple, "BaseExpression"], query_params: Optional[tuple] = None, alias: Optional[str] = None): ...

    # Example: (SELECT id FROM users WHERE age > ?)
    # Subquery(dialect, "SELECT id FROM users WHERE age > ?", (25,))
    # -> ('(SELECT id FROM users WHERE age > ?)', (25,))
```

## Mixins

Mixins provide operator overloading and common functionality to expression classes.

### AliasableMixin

Provides the `.as_(alias)` method to assign an alias to an expression.

```python
# SELECT name AS user_name
Column(dialect, "name").as_("user_name")
```

### ComparisonMixin

Enables standard Python comparison operators (`==`, `!=`, `>`, `<`, `>=`, `<=`) to generate SQL predicates.

```python
# age >= 18
Column(dialect, "age") >= 18

# status == 'active'
Column(dialect, "status") == "active"

# IS NULL / IS NOT NULL
Column(dialect, "email").is_null()
Column(dialect, "email").is_not_null()

# IN / NOT IN
Column(dialect, "status").in_(["active", "pending"])
Column(dialect, "status").not_in(["banned", "deleted"])

# BETWEEN
Column(dialect, "age").between(18, 65)
```

### ArithmeticMixin

Enables standard Python arithmetic operators (`+`, `-`, `*`, `/`, `%`) to generate SQL arithmetic expressions.

```python
# price * 0.9
Column(dialect, "price") * 0.9

# (count + 1)
Column(dialect, "count") + 1
```

### LogicalMixin

Enables standard Python bitwise operators (`&`, `|`, `~`) to generate SQL logical predicates (`AND`, `OR`, `NOT`).

```python
# (age >= 18) AND (active = true)
(Column(dialect, "age") >= 18) & (Column(dialect, "active") == True)

# NOT (status = 'banned')
~(Column(dialect, "status") == "banned")
```

### StringMixin

Provides string-specific methods like `like` and `ilike`.

```python
# name LIKE 'John%'
Column(dialect, "name").like("John%")

# email ILIKE '%@gmail.com'
Column(dialect, "email").ilike("%@gmail.com")
```

## Core Expressions

### TableExpression

Represents a table or view in a SQL query.

```python
from rhosocial.activerecord.backend.expression import TableExpression

# FROM users AS u
table = TableExpression(dialect, "users", alias="u")
```

### Column

Represents a column reference.

```python
from rhosocial.activerecord.backend.expression import Column

# users.name
col = Column(dialect, "name", table="users")
```

### Literal

Represents a parameterized literal value.

```python
from rhosocial.activerecord.backend.expression import Literal

# ? (param: 100)
lit = Literal(dialect, 100)
```

### WildcardExpression

Represents `*` or `table.*`.

```python
from rhosocial.activerecord.backend.expression import WildcardExpression

# SELECT *
wildcard = WildcardExpression(dialect)

# SELECT users.*
wildcard = WildcardExpression(dialect, table="users")
```

### Subquery

Represents a subquery expression.

```python
from rhosocial.activerecord.backend.expression import Subquery, QueryExpression

# (SELECT ...) AS sub
sub = Subquery(dialect, query_expr, alias="sub")
```

## Operators and Expressions

The `rhosocial.activerecord.backend.expression.operators` module provides classes for various SQL operations.

### Identifier

Represents a generic SQL identifier (e.g., table name, column name).

```python
class Identifier(mixins.ComparisonMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", name: str): ...
```

### SQLOperation

Represents a generic function-call style operation.

```python
from rhosocial.activerecord.backend.expression import SQLOperation

# Example: custom_op(arg1, arg2)
op = SQLOperation(dialect, "custom_op", arg1, arg2)
```

### BinaryExpression

Represents a standard binary operator (e.g., `=`, `!=`, `LIKE`).

```python
class BinaryExpression(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase", op: str, left: "bases.BaseExpression", right: "bases.BaseExpression"): ...
```

### UnaryExpression

Represents a unary operator (e.g., `NOT`, `-`).

```python
class UnaryExpression(bases.BaseExpression):
    def __init__(self, dialect: "SQLDialectBase", op: str, operand: "bases.BaseExpression", pos: str = 'before'): ...
```

### BinaryArithmeticExpression

Represents binary arithmetic operations with operator precedence handling.

```python
class BinaryArithmeticExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", op: str, left: "bases.SQLValueExpression", right: "bases.SQLValueExpression"): ...
```

### Raw Expressions

**Warning**: These classes should be used with caution as they allow raw SQL injection. Ensure all inputs are trusted or properly sanitized.

#### RawSQLExpression

Represents a raw SQL string as a value expression.

```python
class RawSQLExpression(mixins.ArithmeticMixin, mixins.ComparisonMixin, mixins.StringMixin, bases.SQLValueExpression):
    def __init__(self, dialect: "SQLDialectBase", expression: str, params: tuple = ()): ...
```

#### RawSQLPredicate

Represents a raw SQL string as a predicate (boolean condition).

```python
from rhosocial.activerecord.backend.expression.operators import RawSQLPredicate

# Example: Raw SQL condition
pred = RawSQLPredicate(dialect, "EXISTS (SELECT 1 FROM log WHERE log.user_id = users.id)")
```
