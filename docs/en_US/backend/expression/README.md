# Expression System

The Expression System provides a database-agnostic way to build SQL queries using Python objects. It handles SQL generation, parameter binding, and dialect-specific differences.

## Key Features

- **Stateless Design**: Expression objects are pure functions with no internal state, eliminating the need for complex object state management
- **Direct SQL Generation**: Only 2 steps from expression to SQL, avoiding multi-layer compilation architectures
- **Flexible Fragment Generation**: Any expression can call `to_sql()` independently to generate SQL fragments, unlike systems that require complete query compilation
- **User Control**: Users have complete control over when and how SQL is generated, without hidden automatic behaviors
- **Explicit Over Implicit**: No hidden state management, automatic compilation, or complex object lifecycle tracking
- **No Hidden Behaviors**: No automatic flushing or hidden database operations, unlike systems with automatic session management

## Important Notes

- [**Limitations & Considerations**](limitations.md): Critical information about the boundaries and responsibilities of the expression system.

## Modules

- [**Core**](core.md): Base classes, protocols, mixins, and fundamental operators.
- [**Statements**](statements.md): Top-level SQL statements (SELECT, INSERT, UPDATE, DELETE, MERGE, etc.).
- [**Clauses**](clauses.md): Query components like WHERE, JOIN, GROUP BY, ORDER BY.
- [**Predicates**](predicates.md): Boolean expressions for filtering (comparisons, logical ops, LIKE, IN, etc.).
- [**Functions**](functions.md): SQL function builders (COUNT, SUM, string functions, etc.).
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
