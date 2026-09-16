# Dialect Expressions

## Expression Design Principles

Understanding these principles is essential for working with the expression system:

### 1. Expressions Are Declarative

An expression instance **collects all parameters** that affect SQL generation. It is a data container, not an SQL generator. When you construct `Column('age') >= Literal(18)`, you are building a data structure that captures the column name, the operator, and the value — not generating SQL.

### 2. Delegation to Dialect

When `to_sql()` is called, the expression delegates to its bound dialect's `format_*()` methods. The expression never concatenates SQL strings directly. The dialect decides the actual SQL syntax based on:
- Backend type (MySQL, PostgreSQL, SQLite, etc.)
- Dialect version (e.g., MySQL 5.7 vs 8.0)
- Feature flags (e.g., `supports_returning_insert()`)
- The expression's parameters

### 3. DataTypes Are Expressions

DataType classes inherit from `BaseExpression`. They follow the same delegation pattern: `to_sql()` calls `dialect.format_data_type(self)`. This means `IntegerType`, `VarCharType`, `TimestampType` etc. are all expressions that delegate to the dialect for rendering.

### 4. Serialization Support

Because expression instances collect all parameters that affect SQL generation, they can be **serialized** (e.g., to JSON) and **deserialized** back without loss. This enables caching query plans, transmitting queries across processes, and storing query definitions for later execution.

### 5. Composition Over Inheritance

Expressions gain capabilities by composing mixins (`ComparisonMixin`, `ArithmeticMixin`, `LogicalMixin`), not through deep inheritance hierarchies. This keeps the type hierarchy flat and composable.

## Two-Layer Architecture

rhosocial-activerecord's expression system has two layers:

1. **Core layer** — Expression classes (`Column`, `Literal`, `FunctionCall`, `ComparisonPredicate`, etc.) store data and define the structure of SQL expressions. They do not format SQL themselves. Instead, every `to_sql()` call delegates to `self.dialect.format_*()` methods.

2. **Dialect layer** — Each backend provides a dialect class that composes dozens of mixin classes. The dialect's `format_*()` methods produce {database}-specific SQL syntax. Backend-specific mixins override core mixins to customize formatting.

This means the **same expression class** produces different SQL depending on which backend is configured:

```python
# Core expression — works on any backend
expr = Column('age') >= Literal(18)

# On MySQL dialect:   `age` >= %s
# On PostgreSQL dialect: "age" >= $1
# On SQLite dialect:  "age" >= ?
```

## Discovering Feature Support

Not every backend supports every feature. PostgreSQL has JSONB arrays and LATERAL JOIN; MySQL has ROLLUP but not CUBE; SQLite has no table partitioning. rhosocial-activerecord provides a **protocol-based capability system** that lets you discover what your backend supports at runtime.

### Protocol Classes

Every feature category is defined as a `@runtime_checkable` Protocol in `rhosocial.activerecord.backend.dialect.protocols`. These protocols describe the interface a dialect must implement to claim support for a feature group.

```python
from rhosocial.activerecord.backend.dialect.protocols import (
    CTESupport,
    JSONSupport,
    PartitionSupport,
    WindowFunctionSupport,
)
```

### Checking with isinstance

Because protocols are `@runtime_checkable`, you can check whether a dialect implements a feature group:

```python
from rhosocial.activerecord.backend.dialect.protocols import WindowFunctionSupport

dialect = get_current_dialect()

if isinstance(dialect, WindowFunctionSupport):
    # Window functions are available — check version-gated specifics
    if dialect.supports_window_frame_clause():
        # Frame clause (ROWS BETWEEN ...) is available
        ...
```

### Checking Specific Features

Each protocol exposes `supports_*()` methods that return `True` or `False`. These methods may be version-gated — a backend might support a feature only on newer versions:

```python
# Check if the backend supports a specific feature
if dialect.supports_returning_insert():
    # Use RETURNING clause
    query = User.query().insert(...).returning('id')

if dialect.supports_json_type():
    # Use JSON column type
    ...

if dialect.supports_table_partitioning():
    # Create partitioned tables
    ...
```

### Enforcing Support

When a feature is required (not optional), use the guard methods that raise clear exceptions:

```python
from rhosocial.activerecord.backend.dialect.protocols import PartitionSupport
from rhosocial.activerecord.backend.dialect.exceptions import (
    ProtocolNotImplementedError,
    UnsupportedFeatureError,
)

# Enforce that the protocol is implemented at all
try:
    dialect.require_protocol(PartitionSupport, "table partitioning", "MyMigration")
except ProtocolNotImplementedError as e:
    print(f"This backend does not implement partitioning: {e}")

# Enforce that a specific feature variant is supported
try:
    dialect.check_feature_support("supports_list_table_partitioning", "LIST partitioning")
except UnsupportedFeatureError as e:
    print(f"This backend does not support LIST partitioning: {e}")
```

### How It Works Under the Hood

The system has three layers:

1. **Protocol declaration** — The dialect class lists Protocol classes as base classes. This makes `isinstance(dialect, SomeProtocol)` return `True`.

2. **Generic mixin defaults** — Generic mixins (e.g., `CTEMixin`, `JSONMixin`, `PartitionMixin`) provide default implementations where every `supports_*()` method returns `False` and every `format_*()` method raises `UnsupportedFeatureError`. This is the safe default.

3. **Backend-specific overrides** — Backend mixins override the `supports_*()` methods to return `True` (often version-gated) and provide real `format_*()` implementations.

This means you never need to guess — if a feature is not supported, you get a clear error at SQL generation time, not a cryptic database error.

## Common Expression Classes

The following expression classes are shared across all backends. They live in `rhosocial.activerecord.backend.expression`:

| Class | Purpose |
|-------|---------|
| `Column` | Column reference |
| `Literal` | Parameter placeholder (e.g., `?`, `%s`, `$1`) |
| `FunctionCall` | Function invocation (`FUNC(args)`) |
| `Subquery` | Subquery as expression |
| `TableExpression` | Table reference with temporal options |
| `WildcardExpression` | `*` wildcard |
| `ComparisonPredicate` | `=`, `!=`, `>`, `>=`, `<`, `<=` |
| `LikePredicate` | `LIKE`, `ILIKE` |
| `InPredicate` | `IN (...)` |
| `BetweenPredicate` | `BETWEEN ... AND ...` |
| `IsNullPredicate` | `IS NULL`, `IS NOT NULL` |
| `LogicalPredicate` | `AND`, `OR`, `NOT` |
| `BinaryExpression` | Binary operators |
| `BinaryArithmeticExpression` | `+`, `-`, `*`, `/`, `%` |
| `CaseExpression` | `CASE WHEN ... THEN ... END` |
| `WindowFunctionCall` | Window functions (`OVER (...)`) |
| `JSONExpression` | JSON operators |
| `ArrayExpression` | Array operators |

### Mixin Classes (Operator Overloading)

Expression classes use mixins to provide Python operator overloading:

| Mixin | Provides |
|-------|----------|
| `ComparisonMixin` | `==`, `!=`, `>`, `>=`, `<`, `<=`, `in_()`, `between()`, `is_null()` |
| `ArithmeticMixin` | `+`, `-`, `*`, `/`, `%` |
| `LogicalMixin` | `&` (AND), `\|` (OR), `~` (NOT) |
| `StringMixin` | `.like()`, `.ilike()` |
| `TypeCastingMixin` | `.cast()` |
| `AliasableMixin` | `.as_()` |

## {database}-Specific Overrides

The {backend} dialect overrides specific `format_*()` methods to produce {database}-compatible SQL.

### Identifier Quoting

Different backends quote identifiers differently. The dialect handles this transparently:

| Backend | Quoting Style | Example |
|---------|--------------|---------|
| MySQL | Backtick | `` `column_name` `` |
| PostgreSQL | Double quote | `"column_name"` |
| SQLite | Double quote | `"column_name"` |

### Parameter Placeholder

The placeholder style determines how parameter values appear in generated SQL. This is controlled by `get_parameter_placeholder()` on the dialect:

| Backend | Placeholder | Example |
|---------|------------|---------|
| MySQL | `%s` | `WHERE \`age\` >= %s` |
| PostgreSQL | `%s` (psycopg converts to `$1`, `$2`, ...) | `WHERE "age" >= $1` |
| SQLite | `?` | `WHERE "age" >= ?` |

### Type Casting Syntax

| Backend | Syntax | Example |
|---------|--------|---------|
| Standard | `CAST(expr AS type)` | `CAST(age AS FLOAT)` |
| PostgreSQL | `expr::type` (also supports CAST) | `age::float` |
| MySQL | `CAST(expr AS type)` or `CONVERT(expr, type)` | `CAST(age AS FLOAT)` |

### Date/Time Functions

| Backend | Functions |
|---------|-----------|
| MySQL | `DATE_ADD()`, `DATE_SUB()`, `TIMESTAMPDIFF()`, `DATE_FORMAT()`, `NOW()` |
| PostgreSQL | `+`/`-` operators, `DATE_TRUNC()`, `EXTRACT()`, `NOW()`, `CURRENT_TIMESTAMP` |
| SQLite | `DATE()`, `TIME()`, `DATETIME()`, `JULIANDAY()`, `strftime()` |

### Affected Row Counts

The way backends report affected rows after DML operations differs:

| Backend | INSERT | UPDATE (no change) | UPDATE (changed) | UPSERT |
|---------|--------|-------------------|-----------------|--------|
| MySQL | 1 | 0 | 1 | 2 (updated) |
| PostgreSQL | 1 | 0 | 1 | 0 (conflict) or 1 |
| SQLite | 1 | 0 | 1 | 1 |

**Note**: When PostgreSQL uses `RETURNING`, the affected row count may be 0 even though data was returned — the data is in the result set, not in `cursor.rowcount`.

### DML Limitations

| Feature | MySQL | PostgreSQL | SQLite |
|---------|-------|------------|--------|
| RETURNING clause | No | Yes | Yes (3.35.0+) |
| MERGE statement | No | Yes | No |
| FILTER clause | No | Yes | Yes (3.10.0+) |
| UPSERT syntax | `ON DUPLICATE KEY UPDATE` | `ON CONFLICT ... DO UPDATE` | `ON CONFLICT ... DO UPDATE` |

## {database}-Specific Expression Classes

In addition to overriding core methods, the {backend} backend provides its own expression classes in `rhosocial.activerecord.backend.impl.{backend}.expression`:

<!-- Document backend-specific expression classes. Examples:

### MySQL-Specific

| Class | Purpose |
|-------|---------|
| `MySQLMatchAgainstExpression` | Full-text search |
| `MySQLLoadDataExpression` | LOAD DATA INFILE |
| `MySQLPartitionClause` | Partitioning syntax |
| `MySQLJSONExtractExpression` | JSON functions |

### PostgreSQL-Specific

| Class | Purpose |
|-------|---------|
| `PostgresAdvisoryLockExpression` | Advisory locks |
| `PostgresCreatePartitionExpression` | Partition DDL |
| `PostgresDetachPartitionExpression` | Detach partition |

-->

## Using Expressions

### In Queries

```python
# Using core expression classes directly
from rhosocial.activerecord.backend.expression import Column, Literal, FunctionCall

# Column references
query = User.query().where(Column('age') >= Literal(18))

# Function calls
query = User.query().select(FunctionCall('COUNT', Column('id')))
```

### Through Model Proxies

```python
# More idiomatic: use model.c proxy
query = User.query().where(User.c.age >= 18)

# This is equivalent — User.c.age returns a Column expression
```

## See Also

- [Type System](field_types.md) — DataType hierarchy and backend-specific types
- [Feature Support Matrix](feature_support_matrix.md) — complete compatibility table
- [Core: Expression System](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/expression)
- [Core: Expression Limitations](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/expression/limitations)

💡 *AI Prompt:* "How does the expression system generate different SQL for different databases?"
