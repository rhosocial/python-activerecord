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
  - [TypeCastingMixin](#typecastingmixin)
- [Core Expressions](#core-expressions)
  - [Table Sources and Relation Objects](#table-sources-and-relation-objects)
  - [Column](#column)
  - [Literal](#literal)
  - [AllColumnsWildcard](#allcolumnswildcard)
  - [Subquery](#subquery)
- [Operators](#operators)
  - [Identifier](#identifier)
  - [SQLOperation](#sqloperation)
  - [BinaryExpression](#binaryexpression)
  - [ArithmeticOperation](#arithmeticoperation)
  - [UnaryExpression](#unaryexpression)
  - [RawSQL](#rawsqlexpression)
  - [RawSQLPredicate](#rawsqlpredicate)
- [COLLATE Expressions](#collate-expressions)

## Base Classes

The expression system is built on a hierarchy of abstract base classes defined in `rhosocial.activerecord.backend.expression.bases`.

### ToSQLProtocol

The `ToSQLProtocol` defines the contract for any object that can be converted to SQL.

```python
from typing import Protocol, Tuple

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

`BaseExpression` is the root base class for all expression components. It satisfies `ToSQLProtocol` structurally, holds a **per-node** dialect reference, and implements `to_sql()` **once, centrally** — subclasses never override it; they declare only their dialect formatting method name via the read-only `format_method` property.

```python
from typing import Optional, Tuple

class BaseExpression:
    def __init__(self, dialect: Optional["SQLDialectBase"] = None):
        # The dialect is the conventional first argument but optional —
        # binding may be deferred (e.g. model declaration time has no
        # dialect; ActiveRecord's DDL derivation binds one per node).
        self.dialect = dialect

    @property
    def dialect(self) -> "SQLDialectBase":
        # Reading validates that a dialect is bound; rendering requires one,
        # so access before binding raises ValueError ("... has no dialect
        # bound ...").
        ...

    @dialect.setter
    def dialect(self, dialect: Optional["SQLDialectBase"]) -> None:
        # Affects ONLY this node — no propagation into child expressions.
        # Bind each node at construction, or walk the tree and bind
        # nodes individually.
        ...

    @property
    def format_method(self) -> str:
        # Name of the dialect's format_*() method that renders this
        # expression. Read-only by contract; not declaring it (or a
        # dialect not providing it) makes the expression unrenderable.
        ...

    def to_sql(self) -> Tuple[str, tuple]:
        # Implemented once, here. Stateless and allocation-free:
        # resolves format_method on this node's own bound dialect and
        # calls formatter(self). No reconstruction, no propagation,
        # no copies.
        ...
```

### SQLPredicate

`SQLPredicate` represents an expression that evaluates to a boolean value (e.g., `WHERE` conditions). It mixes in `LogicalMixin` to support `&` (AND), `|` (OR), and `~` (NOT) operators.

```python
from rhosocial.activerecord.backend.expression import bases, mixins

class SQLPredicate(mixins.LogicalMixin, BaseExpression):
    pass
```

### SQLValue

`SQLValue` represents an expression that evaluates to a scalar value (e.g., columns, literals, function results).

```python
class SQLValue(BaseExpression):
    pass
```

## Core Components

The `rhosocial.activerecord.backend.expression.core` module defines the fundamental building blocks of SQL queries.

### Literal

Represents a literal value in a SQL query. It handles parameter binding automatically.

```python
import inspect
from rhosocial.activerecord.backend.expression import Literal

# The constructor as the library declares it
print(inspect.signature(Literal.__init__))

# Default: bind-parameter mode
# Literal(dialect, "active")
# -> ('?', ('active',))

# Inline mode: value embedded directly in SQL (for DDL clauses)
# Literal(dialect, "active", inline=True)
# -> ("'active'", ())
```

#### Inline Literals

By default, `Literal` renders as a **bind parameter** (`?` or `%s` depending on the dialect), following DB-API 2.0 (PEP 249) conventions. This is the safe, preferred mode for DML statements (`INSERT`, `SELECT`, `UPDATE`, `DELETE`).

However, **DDL clauses** (`DEFAULT`, `CHECK`, partition boundaries, partial-index `WHERE`) do **not** accept bind parameters — the database engine expects literal SQL text. For these cases, set `inline=True` on the `Literal` node:

```python
from rhosocial.activerecord.backend.expression import (
    Column,
    ColumnCheckConstraint,
    ColumnConstraint,
    ColumnDefaultConstraint,
    ColumnDefinition,
    ComparisonOperator,
    ComparisonPredicate,
    Literal,
)
from rhosocial.activerecord.backend.expression.types import IntegerType

# DDL: DEFAULT value must be inlined
ColumnDefinition(
    dialect,
    name="age",
    data_type=IntegerType(dialect),
    constraints=[
        ColumnConstraint(
            dialect,
            branch=ColumnDefaultConstraint(
                dialect,
                value=Literal(dialect, 0, inline=True),  # -> DEFAULT 0
            ),
        ),
    ],
)

# DDL: CHECK condition — the comparison value must be inlined
ColumnConstraint(
    dialect,
    branch=ColumnCheckConstraint(
        dialect,
        condition=ComparisonPredicate(
            dialect,
            ComparisonOperator.GTE,
            Column(dialect, "score"),
            Literal(dialect, 0, inline=True),  # -> CHECK ("score" >= 0)
        ),
    ),
)
```

The `inline` switch is **per-node** — each `Literal` decides independently. A single predicate can mix inline and bind-parameter values:

```python
from rhosocial.activerecord.backend.expression import ComparisonPredicate, Literal

pred = ComparisonPredicate(
    dialect, "=",
    Literal(dialect, "a", inline=True),  # inline
    Literal(dialect, "b"),               # bind param
)
pred.to_sql()  # -> ("'a' = ?", ("b",))
```

> **Security note**: Inline literals are a SQL-injection hazard when the value can be influenced by end users. Only use `inline=True` for developer-declared constants (DDL defaults, schema-derived values).

### Column

Represents a column reference, optionally with a table qualifier and an alias.

```python
import inspect
from rhosocial.activerecord.backend.expression import Column

print(inspect.signature(Column.__init__))

# Example: users.name
# Column(dialect, "name", table="users")
```

The bare `Column` is a *reference* only. Comparison, arithmetic and string operators were deliberately removed from it: `Column(...) == Literal(...)` is a plain Python `bool`, not a predicate. Use a typed column instead — `StringColumn`, `IntegerColumn`, `NumericColumn`, `TimestampColumn` or `BooleanColumn` — which wraps a plain Python value in a `Literal` and therefore builds a real predicate. `ComparisonPredicate(dialect, ComparisonOperator.EQ, left, right)` is the explicit node when the operands are already expressions.

### Table Sources and Relation Objects

Everything a `FROM` clause can name is a **table source**, but not every source is a persisted object. The two questions are answered by two separate trees:

- **Persisted relations** — `Table`, `View`, `MaterializedView`, `ForeignTable`, and the graph tables `NodeTable` / `EdgeTable` — live in `rhosocial.activerecord.backend.expression.objects`. They carry catalog identity (a name plus optional catalog and schema) and nothing else.
- **Query-only sources** — `NamedRelationRef`, `DerivedTableSource`, `ValuesTableSource`, `TableFunctionSource`, `JsonTableSource`, `XmlTableSource` and `GraphTableSource` — live in `rhosocial.activerecord.backend.expression.sources`. Their rows exist for the duration of one statement; `FROM json_table(...)` has no catalog identity at all.

The trees are connected by **composition**, not inheritance: `NamedRelationRef` holds a relation object. Aliases and temporal options belong to the source, because `FROM users AS u` renames a row for the duration of a query and renames nothing in the catalogue.

```python
import inspect
from rhosocial.activerecord.backend.expression.objects import (
    EdgeTable,
    ForeignTable,
    MaterializedView,
    NodeTable,
    Table,
    View,
)

for relation in (Table, View, MaterializedView, ForeignTable, NodeTable, EdgeTable):
    print(relation.__name__, inspect.signature(relation.__init__))
```

```python
import inspect
from rhosocial.activerecord.backend.expression.sources import (
    DerivedTableSource,
    GraphTableSource,
    JsonTableSource,
    NamedRelationRef,
    TableFunctionSource,
    ValuesTableSource,
    XmlTableSource,
)

for source in (
    NamedRelationRef,
    DerivedTableSource,
    ValuesTableSource,
    TableFunctionSource,
    JsonTableSource,
    XmlTableSource,
    GraphTableSource,
):
    print(source.__name__, inspect.signature(source.__init__))
```

```python
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef

# FROM "users"
NamedRelationRef(dialect, Table(dialect, "users"))
# -> ('"users"', ())

# FROM "users" AS "u" -- the alias lives on the source
NamedRelationRef(dialect, Table(dialect, "users"), alias="u")
# -> ('"users" AS "u"', ())
```

### FunctionCall

Represents a generic scalar function call.

When `niladic=True` and no arguments are provided, the function call generates SQL without parentheses (e.g., `CURRENT_TIMESTAMP` instead of `CURRENT_TIMESTAMP()`). Per SQL:2003, certain value functions are niladic and must not use parentheses when invoked without arguments. When a niladic function has arguments (e.g., `CURRENT_TIMESTAMP(6)`), parentheses are included as normal.

```python
import inspect
from rhosocial.activerecord.backend.expression import FunctionCall

print(inspect.signature(FunctionCall.__init__))
```

**Niladic usage:**

```python
# SQL:2003 niladic function — generates CURRENT_TIMESTAMP (no parentheses)
FunctionCall(dialect, 'CURRENT_TIMESTAMP', niladic=True)
# -> ('CURRENT_TIMESTAMP', ())

# Niladic with argument — generates CURRENT_TIMESTAMP(?)
FunctionCall(dialect, 'CURRENT_TIMESTAMP', Literal(dialect, 6), niladic=True)
# -> ('CURRENT_TIMESTAMP(?)', (6,))

# Regular function — always has parentheses
FunctionCall(dialect, 'NOW')
# -> ('NOW()', ())
```

### AllColumnsWildcard

Represents the select-list wildcard (`*`), optionally qualified through a
relation reference (`rel.*`). PREFER this over `Literal("*")`.

```python
import inspect
from rhosocial.activerecord.backend.expression import AllColumnsWildcard

print(inspect.signature(AllColumnsWildcard.__init__))
```

A bare `*` lets the surrounding clause decide what the expansion spans (the
select list's FROM sources, or a RETURNING clause's DML target). The row
count is a different contract: `COUNT(*)`'s parameter is `RowCountWildcard`,
which carries no relation and renders only the bare asterisk.

### Subquery

Represents a subquery expression. It can wrap a SQL string, a `(sql, params)` tuple, or another expression.

```python
import inspect
from rhosocial.activerecord.backend.expression import Subquery

print(inspect.signature(Subquery.__init__))

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

Enables standard Python comparison operators (`==`, `!=`, `>`, `<`, `>=`, `<=`) to generate SQL predicates. The mixin is carried by typed columns and expression wrappers; a bare `Column` deliberately does not carry it.

```python
from rhosocial.activerecord.backend.expression import (
    Column, IntegerColumn, StringColumn,
)

# age >= 18 -- a typed column wraps 18 in a Literal
IntegerColumn(dialect, "age") >= 18

# status == 'active'
StringColumn(dialect, "status") == "active"

# IS NULL / IS NOT NULL
Column(dialect, "email").is_null()
Column(dialect, "email").is_not_null()

# IN / NOT IN
StringColumn(dialect, "status").in_(["active", "pending"])
StringColumn(dialect, "status").not_in(["banned", "deleted"])

# BETWEEN
IntegerColumn(dialect, "age").between(18, 65)
```

### ArithmeticMixin

Enables standard Python arithmetic operators (`+`, `-`, `*`, `/`, `%`) to generate SQL arithmetic expressions. Arithmetic needs a numeric typed column, which also supplies the literal for the other operand.

```python
from rhosocial.activerecord.backend.expression import IntegerColumn, NumericColumn

# price * 0.9
NumericColumn(dialect, "price") * 0.9

# (count + 1)
IntegerColumn(dialect, "count") + 1
```

### LogicalMixin

Enables standard Python bitwise operators (`&`, `|`, `~`) to generate SQL logical predicates (`AND`, `OR`, `NOT`).

```python
from rhosocial.activerecord.backend.expression import (
    BooleanColumn, IntegerColumn, StringColumn,
)

# (age >= 18) AND (active = true)
(IntegerColumn(dialect, "age") >= 18) & (BooleanColumn(dialect, "active") == True)

# NOT (status = 'banned')
~(StringColumn(dialect, "status") == "banned")
```

### StringMixin

Provides string-specific methods like `like` and `ilike`.

```python
from rhosocial.activerecord.backend.expression import StringColumn

# name LIKE 'John%'
StringColumn(dialect, "name").like("John%")

# email ILIKE '%@gmail.com'
StringColumn(dialect, "email").ilike("%@gmail.com")
```

### TypeCastingMixin

Provides type casting capability, allowing expressions to be converted to different SQL types. It follows the Expression-Dialect separation architecture where the actual SQL syntax is generated by each backend's `format_cast_expression` method.

```python
from rhosocial.activerecord.backend.expression import NumericColumn, StringColumn
from rhosocial.activerecord.backend.expression.types import IntegerType, VarCharType

# Basic type casting -- the target is a DataType object, never a type-name string
NumericColumn(dialect, "price").cast(IntegerType(dialect))
# PostgreSQL generates: "price"::INTEGER
# Other backends generate: CAST("price" AS INTEGER)

# Type modifiers belong to the DataType object
StringColumn(dialect, "name").cast(VarCharType(dialect, length=100))
# PostgreSQL generates: "name"::VARCHAR(100)

# Chained type conversions
StringColumn(dialect, "amount").cast(VarCharType(dialect, length=20)).cast(IntegerType(dialect))
# -> CAST(CAST("amount" AS VARCHAR(20)) AS INTEGER)

# Type casting supports method chaining
expr = NumericColumn(dialect, "value").cast(IntegerType(dialect))
result = expr * 1.1       # Arithmetic operation
predicate = expr > 100    # Comparison operation
```

**Important Notes**:
- `TypeCastingMixin` does not directly concatenate SQL strings
- The target type is always a `DataType` instance (`IntegerType(dialect)`, `VarCharType(dialect, length=100)`, ...); a type-name string is refused at construction
- Type modifiers (e.g., `VARCHAR(100)`) are expressed as `DataType` arguments such as `VarCharType(dialect, length=100)`
- The actual SQL syntax is determined by the dialect's `format_cast_expression` method
- PostgreSQL uses `::` syntax, other databases use `CAST()` function

## Core Expressions

### Table Sources in FROM

A relation object carries only catalog identity; the source wraps it and carries the alias (and any temporal options).

```python
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef

# The persisted relation: catalog identity only, no alias
relation = Table(dialect, "users")
relation.to_sql()  # -> ('"users"', ())

# The query source: wraps the relation and carries the alias
source = NamedRelationRef(dialect, relation, alias="u")
source.to_sql()  # -> ('"users" AS "u"', ())
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

### AllColumnsWildcard

Represents `*` or `table.*`.

```python
from rhosocial.activerecord.backend.expression import AllColumnsWildcard
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef

# SELECT *
wildcard = AllColumnsWildcard(dialect)

# SELECT users.*
wildcard = AllColumnsWildcard(
    dialect, relation=NamedRelationRef(dialect, Table(dialect, "users"))
)
```

### Subquery

Represents a subquery expression.

```python
from rhosocial.activerecord.backend.expression import Column, QueryStatement, Subquery
from rhosocial.activerecord.backend.expression.objects import Table

query = QueryStatement(
    dialect, select=[Column(dialect, "id")], from_=Table(dialect, "users")
)

# (SELECT ...) AS sub
sub = Subquery(dialect, query, alias="sub")
```

## Operators and Expressions

The `rhosocial.activerecord.backend.expression.operators` module provides classes for various SQL operations.

### Identifier

Represents a generic SQL identifier (e.g., table name, column name).

```python
import inspect
from rhosocial.activerecord.backend.expression import Identifier

print(inspect.signature(Identifier.__init__))
```

### SQLOperation

Represents a generic function-call style operation.

```python
from rhosocial.activerecord.backend.expression import Literal, SQLOperation

# Example: custom_op(?, ?)
op = SQLOperation(dialect, "custom_op", Literal(dialect, 1), Literal(dialect, 2))
```

### BinaryExpression

Represents a standard binary operator (e.g., `=`, `!=`, `LIKE`).

```python
import inspect
from rhosocial.activerecord.backend.expression import BinaryExpression

print(inspect.signature(BinaryExpression.__init__))
```

### UnaryExpression

Represents a unary operator (e.g., `NOT`, `-`).

```python
import inspect
from rhosocial.activerecord.backend.expression import UnaryExpression

print(inspect.signature(UnaryExpression.__init__))
```

### ArithmeticOperation

Represents binary arithmetic operations with operator precedence handling.

`op` is an `ArithmeticOperator` member whose stored value is the **operation as
a word** — `add` / `sub` / `mul` / `div` / `mod` — and the dialect formatter maps
each word to the character its SQL writes (see `OPERATOR_SYMBOLS`). The artifact
therefore carries a language-neutral word, not one language's spelling of the
operator. The word set is closed: an unknown word is refused at construction.

```python
import inspect
from rhosocial.activerecord.backend.expression import ArithmeticOperation

print(inspect.signature(ArithmeticOperation.__init__))
```

### Raw Expressions

**Warning**: These classes should be used with caution as they allow raw SQL injection. Ensure all inputs are trusted or properly sanitized.

#### RawSQL

Represents a raw SQL string as a value expression.

```python
import inspect
from rhosocial.activerecord.backend.expression import RawSQL

print(inspect.signature(RawSQL.__init__))
```

#### RawSQLPredicate

Represents a raw SQL string as a predicate (boolean condition).

```python
from rhosocial.activerecord.backend.expression.operators import RawSQLPredicate

# Example: Raw SQL condition
pred = RawSQLPredicate(dialect, "EXISTS (SELECT 1 FROM log WHERE log.user_id = users.id)")
```

## COLLATE Expressions

`CollateFunction` (defined in `rhosocial.activerecord.backend.expression.collation`) applies an explicit collation to a SQL value expression.

```python
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.collation import collate

# Basic usage: give a column a collation
expr = collate(Column(dialect, "name"), "Chinese_PRC_CI_AS")
sql, params = expr.to_sql()
# sql: '"name" COLLATE Chinese_PRC_CI_AS'
# params: ()

# Chaining: a collated expression still supports every mixin operation
expr = collate(Column(dialect, "name"), "NOCASE") == "alice"
sql, params = expr.to_sql()
# sql: '"name" COLLATE NOCASE = ?'
# params: ("alice",)
```

`CollateFunction` mixes in `AliasableMixin`, `ArithmeticMixin`, `ComparisonMixin`, `StringPatternPredicateMixin` and `TypeCastingMixin`, so it takes part in arithmetic, comparison, pattern matching and aliasing like any other SQL value expression.

### Dialect Integration

Each backend dialect must implement `supports_collation()` and `format_collation()` to support the COLLATE clause. The SQLite backend provides built-in COLLATE formatting support.
