# Backend Architecture

The backend is the lowest layer of `rhosocial-activerecord`. It is the component that
actually talks to a database, and it is deliberately split into two independent parts:

- **`Backend`** — owns the connection, executes SQL, manages transactions and type
  adapters. It knows *how to run* SQL, but does **not** know *how to build* it.
- **`Dialect`** — owns the SQL grammar of a specific database, rendering expression
  objects into SQL strings and parameter tuples. It knows *how to build* SQL, but does
  **not** touch any connection.

The **Expression–Dialect** pair is the heart of the design: expressions only *describe*
structure and collect parameters; the dialect is the single place that turns that
description into concrete, database-specific SQL.

## The Two Halves of a Backend

```mermaid
flowchart TB
    subgraph AR["ActiveRecord Layer"]
        Model["ActiveRecord Model"]
        Query["ActiveQuery / FieldProxy"]
    end

    subgraph BE["Backend Component"]
        B["StorageBackend"]
        B --- BC["ConnectionMixin"]
        B --- BE1["ExecutionMixin"]
        B --- BT["TransactionManagementMixin"]
        B --- BA["TypeAdaptionMixin"]
        B --- BO["SQLOperationsMixin<br/>ResultProcessingMixin<br/>BatchExecutionMixin<br/>ExecutionHooksMixin<br/>SQLBuildingMixin<br/>ReturningClauseMixin<br/>LoggingMixin"]
    end

    subgraph DI["Dialect Component"]
        D["SQLDialect"]
        D --- DM["~40 generic Mixins<br/>(CTE, Window, JSON,<br/>DDL table/index/type,<br/>predicate, join, ...)"]
        D --- DS["~16 SQLite-specific Mixins<br/>(Pragma, FTS5, RTree,<br/>Identifier, Introspection, ...)"]
    end

    subgraph EX["Expression System"]
        E["Expression AST<br/>(Column / Literal / Comparison / ...)"]
    end

    Model --> Query
    Query --> E
    E -->|"to_sql() delegates to format_*()"| D
    DI -.->|"renders SQL + params (no connection)"| E
    E -->|"hands SQL + params"| B
    BE -.->|"connects / executes / manages transaction"| DB[("Database Driver (DB-API)")]
    D -.->|"capability protocols (supports_*)"| B
```

## Responsibility Boundary

| Concern | `Backend` | `Dialect` | `Expression` |
|---------|-----------|-----------|--------------|
| Holds a connection / cursor | ✅ | ❌ | ❌ |
| Executes SQL, fetches rows | ✅ | ❌ | ❌ |
| Manages transactions (begin/commit/rollback/savepoint) | ✅ | ❌ | ❌ |
| Maps Python ↔ DBAPI types (adapters) | ✅ | ❌ | ❌ |
| Renders SQL + parameter placeholders | ❌ | ✅ | ❌ |
| Quotes identifiers, escapes literals | ❌ | ✅ | ❌ |
| Declares feature support (`supports_*`) | ✅ (backend protocols) | ✅ (dialect protocols) | ❌ |
| Describes query structure, collects parameters | ❌ | ❌ | ✅ |

The backends explicitly do **not** inherit the dialect, and the dialect does **not** hold
a backend reference. They cooperate only through the SQL string + parameter tuple that the
dialect produces and the backend consumes — which is why the same expression renders and
runs unchanged across every backend.

## Backend Composition (`StorageBackend`)

The synchronous backend is assembled purely by composing Mixins onto a minimal base:

```mermaid
classDiagram
    class StorageBackendBase {
        <<abstract>>
        +config
        +_connection
        +_transaction_level
        +adapter_registry
        +connect()*
        +disconnect()*
        +ping()*
        +_handle_error()*
        +get_server_version()*
        +introspect_and_adapt()*
    }
    class LoggingMixin
    class TypeAdaptionMixin
    class SQLBuildingMixin
    class ReturningClauseMixin
    class ResultProcessingMixin
    class SQLOperationsMixin
    class ExecutionMixin
    class BatchExecutionMixin
    class ExecutionHooksMixin
    class ConnectionMixin
    class TransactionManagementMixin

    StorageBackendBase <|-- StorageBackend
    LoggingMixin <|-- StorageBackend
    TypeAdaptionMixin <|-- StorageBackend
    SQLBuildingMixin <|-- StorageBackend
    ReturningClauseMixin <|-- StorageBackend
    ResultProcessingMixin <|-- StorageBackend
    SQLOperationsMixin <|-- StorageBackend
    ExecutionMixin <|-- StorageBackend
    BatchExecutionMixin <|-- StorageBackend
    ExecutionHooksMixin <|-- StorageBackend
    ConnectionMixin <|-- StorageBackend
    TransactionManagementMixin <|-- StorageBackend
```

`AsyncStorageBackend` mirrors this exactly, but swaps each Mixin for its async sibling
(e.g. `ExecutionMixin` → `AsyncExecutionMixin`), keeping full sync/async API parity.

## Dialect Composition (`SQLDialect`)

The dialect is the mirror image — assembled from a far larger set of formatting Mixins:

```mermaid
classDiagram
    class SQLDialectBase {
        <<abstract>>
        +name
        +version
        +get_parameter_placeholder()
        +inline_sql_literal()
        +get_isolation_level_name()
        +supports_*()
    }
    class Generic_Mixins["~40 generic Mixins<br/>(format_* methods)"]
    class BackendSpecific_Mixins["~16 SQLite* Mixins<br/>(SQLite-specific format_*)"]

    SQLDialectBase <|-- SQLiteDialect
    Generic_Mixins <|-- SQLiteDialect
    BackendSpecific_Mixins <|-- SQLiteDialect
```

- **Generic Mixins** cover SQL-standard semantics once (CTE, window functions, JSON,
  locking, upsert, DDL for table/index/view/type/sequence, predicates, joins, set
  operations, grouping, ...). Every backend gets them for free.
- **Backend-specific Mixins** add capabilities that only that database understands, and are
  always prefixed with the backend name (`SQLitePragmaMixin`, `SQLiteFTS5Mixin`, ...), so
  different backends never collide.

## Data Flow: From Expression to Result

```mermaid
sequenceDiagram
    participant M as Model / Query
    participant E as Expression AST
    participant D as Dialect
    participant B as Backend
    participant DB as Database

    M->>E: build query (Column, Literal, Comparison, ...)
    E->>D: to_sql() → dialect.format_*(self)
    D-->>E: (SQL string, params tuple)
    E->>B: hand SQL + params
    B->>DB: open connection, execute, fetch rows
    DB-->>B: raw rows
    B-->>M: mapped result (via type adapters)
```

Two rules make this safe and predictable:

1. **Expressions never concatenate SQL strings.** They only describe structure and collect
   parameters; every value goes through a parameter placeholder (`?`), following DB-API 2.0
   (PEP 249) separation of SQL and parameters.
2. **The dialect is the single rendering exit.** Any expression can call `to_sql()` to
   inspect the exact SQL it would produce, because all rendering funnels through the
   dialect's `format_*` methods.

## Capability Negotiation

Neither backends nor dialects declare capability through inheritance depth. Instead, both
layers expose fine-grained protocols:

- `backend/protocols.py` — backend-level declarations (`ConcurrencyAware`, ...)
- `dialect/protocols.py` — dialect-level declarations (`WindowFunctionSupport`,
  `JSONSupport`, `DDLTypeSupport`, ...)

These are runtime-checkable (`runtime_checkable`), and the `supports_*` methods gate
behavior on the *actually connected* server version. Backends re-adapt their dialect via
`introspect_and_adapt()` after connecting, so capability is "negotiated with the server"
rather than statically declared.

## See Also

- **[Custom Backend](custom_backend.md)** — how to assemble your own backend from these
  same Mixins and protocols
- **[Expression System](expression/README.md)** — how the expression side works
- **[Architecture](../introduction/architecture.md)** — the higher-level ActiveRecord /
  query architecture that sits above the backend