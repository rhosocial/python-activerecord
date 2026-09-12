# Expression System

The Expression System provides a database-agnostic way to build SQL using Python objects. It handles SQL generation, parameter binding, and dialect-specific differences.

## Design Goal: Encapsulate All SQL Semantics

The fundamental goal of the expression system is to **fully encapsulate all SQL semantics with Python objects** — from the simplest `SELECT`/`INSERT`, through window functions, CTEs, JSON operations, property graph queries (PGQ), to data types and backend-private syntax.

`to_sql()` is the single production entry point: any expression can independently call `to_sql()` to produce `(SQL string, parameter tuple)` without a full query compilation. This means:

- Every expression object is **self-contained**: it holds all the information needed to build its SQL fragment
- Expressions compose **freely** (nesting, bitwise operators, chaining)
- Expressions can be tested in isolation without any backend, or produce executable SQL once bound to a dialect

## Design Philosophy: Generic vs. Backend-Specific

The expression system is a **generic (core) and backend-specific two-layer structure**.

### Principle 1: Broad Coverage to Save Backend Work

The generic layer (`rhosocial.activerecord.backend.expression` and `backend.dialect`) strives to cover **SQL standard semantics as broadly as possible**. For syntax that most databases express in a standard way, the framework implements it once in the generic layer — backend packages **do not need to re-implement** it to gain those capabilities.

Direct benefits:

- Backend authors only focus on **dialect differences**, not re-implementing generic semantics
- New backend integration cost drops dramatically — most expression capabilities work out of the box
- Low learning cost: the generic API behaves identically across all backends

### Principle 2: Respect Backend Reality

Broad coverage is not "one size fits all". Every database has its own syntax and capability boundaries, and the generic layer **never imposes unified semantics**:

- **Strictly faithful rendering**: a dialect renders only declarations it natively supports; unsupported cases **raise errors with guidance** instead of silently substituting approximate semantics (e.g. declaring a generic auto-increment type on PostgreSQL raises and points to `PostgresSerialType`)
- **Capability negotiation**: dialects expose their supported scope via protocols and capability query methods (e.g. `supports_graph_match()`), checkable at runtime
- **Backend-specific extensions**: private syntax the generic layer cannot cover is provided by backend packages as **backend-name-prefixed** expressions (below)

### Principle 3: Backend-Specific Expressions Use the Backend Name as Prefix

Backend-specific expressions (as well as protocols, mixins, and types) **must use the backend name as a prefix**, for example:

| Backend | Example backend-specific expression/type |
|---------|------------------------------------------|
| MySQL | `MySQLVectorType`, `MySQLEnumType` |
| PostgreSQL | `PostgresSerialType`, `PostgresTSVectorType` |
| SQLite | `SQLiteIntegerType`, `SQLiteBlobType` |

This naming convention ensures readability, discoverability, and isolation: users can immediately tell "is this a generic capability or a backend-private one", and extensions of different backends never clash.

> **Related convention**: dialect protocols follow the same rule — generic protocols (e.g. `WindowFunctionSupport`) have no prefix, backend-specific protocols (e.g. `PostgresPartitionSupport`, `MySQLFullTextSearchSupport`) must carry the backend prefix. See [Custom Backend](../custom_backend.md).

## Key Features

- **Per-Node Dialect Binding**: Each expression is bound to a dialect individually — the dialect is the conventional first constructor argument (optional, default `None`, so binding may be deferred). The `dialect` setter affects only the node it is set on; there is no propagation into child expressions
- **Stateless Rendering**: `to_sql()` takes no arguments, reads the node's own bound dialect and renders the existing tree in place — no reconstruction, no copies. Rendering with no dialect bound raises `ValueError` (fail-fast guard)
- **Direct SQL Generation**: Only 2 steps from expression to SQL — resolve the class's declared `format_method` on the bound dialect and call the formatter — avoiding multi-layer compilation architectures
- **Flexible Fragment Generation**: Any expression can call `to_sql()` independently to generate SQL fragments, unlike systems that require complete query compilation
- **User Control**: Users have complete control over when and how SQL is generated, without hidden automatic behaviors
- **Explicit Over Implicit**: No hidden state management, automatic compilation, or complex object lifecycle tracking
- **No Hidden Behaviors**: No automatic flushing or hidden database operations, unlike systems with automatic session management

## Serialization & Deserialization

Because **all expressions are class definitions** and **collect all parameters at instantiation**, expression objects naturally support **serialization / deserialization** — a direct consequence of the "self-contained" design principle.

Expressions can be serialized into three forms and reconstructed from them into equivalent expression objects:

| Form | Entry points | Description |
|------|--------------|-------------|
| Dict (spec) | `serialize(expr)` / `deserialize(spec, dialect)` | JSON-compatible dict structure |
| JSON string | `serialize_json(expr)` / `deserialize_json(s, dialect)` | For network transfer and storage |
| XML | `serialize_xml(expr)` / `deserialize_xml(x, dialect)` | For cross-language interoperability |

Key points:

- **The dialect is not serialized**: it must be supplied at deserialization time (the `dialect` parameter), because SQL generation depends on the dialect
- Nested expressions, tuples, `cast()` chains, dataclass values, and non-JSON-native scalars round-trip fully through reserved keys (`__expr__`, `__tuple__`, `__cast__`, `__vdc__`, `__value__`)
- Serialization lets expressions travel **across processes, machines, and languages**, laying the groundwork for query templating, caching, and distributed scenarios

> For the full serialization spec (spec format, nested/tuple markers, security considerations and the registry mechanism) see [Expression Serialization](serialization.md); for wiring custom expressions into serialization see [Extending](extending.md).

## Modules

- [**Core**](core.md): Base classes, protocols, mixins, and fundamental operators.
- [**Statements**](statements.md): Top-level SQL statements (SELECT, INSERT, UPDATE, DELETE, MERGE, etc.).
- [**Clauses**](clauses.md): Query components like WHERE, JOIN, GROUP BY, ORDER BY.
- [**Predicates**](predicates.md): Boolean expressions for filtering (comparisons, logical ops, LIKE, IN, etc.).
- [**Functions**](functions.md): SQL function builders (COUNT, SUM, string functions, etc.).
- [**Data Types**](types.md): Generic and backend-specific data types, and how they cooperate.
- [**Advanced**](advanced.md): Advanced features like Window Functions, CTEs, JSON operations, and Graph queries.

## Usage Overview

The expression system allows you to compose queries programmatically:

```python
from rhosocial.activerecord.backend.expression import (
    QueryExpression, TableExpression, Column, Literal
)

# SELECT name, age FROM users WHERE age >= 18
query = QueryExpression(
    dialect,
    select=[Column(dialect, "name"), Column(dialect, "age")],
    from_=TableExpression(dialect, "users"),
    where=Column(dialect, "age") >= Literal(dialect, 18)
)
sql, params = query.to_sql()
# sql: 'SELECT "name", "age" FROM "users" WHERE "age" >= ?'
# params: (18,)
```