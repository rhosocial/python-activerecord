# rhosocial-activerecord Architecture Document

## Core Architecture Components

### 1. Expression-Dialect System

The Expression-Dialect System is the core query building component of rhosocial-activerecord, which achieves separation between database-agnostic SQL query building and database-specific SQL generation.

#### Architectural Principles
- **Expression classes** implement the `ToSQLProtocol` interface, defining how to generate SQL
- **Each expression class** must call its dialect's `format_*` methods instead of self-formatting
- **Dialect classes** are responsible for the actual SQL formatting and parameter handling
- **Expression classes** should never directly concatenate SQL strings; they should delegate to dialect
- This pattern ensures each dialect can customize formatting behavior while maintaining security

#### Relationship Model
```
Expression.to_sql() -> Dialect.format_*() -> SQL string and parameters
```

#### Main Modules

`backend/expression/`: `bases.py`, `core.py`, `literals.py`, `executable.py`, `mixins.py`,
`operators.py`, `predicates.py`, `query_parts.py`, `statements/` (directory pkg: `ddl_*`, `dml`,
`dql`, `explain`), `functions/` (directory pkg), `aggregates.py`, `advanced_functions.py`,
`query_sources.py`, `graph.py`, plus `collation.py`, `datetime.py`, `serialization.py`,
`transaction.py`, `introspection.py`, `xml.py`, `types/`.

> Note: `functions.py` and `statements.py` were refactored into directory packages
> (`functions/` and `statements/`).
>
> Full protocol/mixin table, golden rules, and "how to add a protocol" workflow are in the
> **`dev-expression-dialect`** skill.

#### Important Limitations
The expression system faithfully builds SQL according to user intent, but **does not validate** whether the generated SQL complies with SQL standards or can be successfully executed in the target database. Semantic validation is the responsibility of the database engine.

### 2. Backend System

The backend system is responsible for database connection management and actual SQL execution.

#### Main Components
- `StorageBackend`: Base class for storage backends
- `SQLDialectBase`: Base class for SQL dialects
- Concrete implementations: `sqlite`, `dummy`, etc.

#### Generic vs Concrete Expression Placement (Design Philosophy)

Backend expressions are split between a **generic (core) layer** and **per-backend
implementations**, decided by the *breadth* of the feature's base:

1. **Broad base → generic layer.** A feature that exists with standard semantics across many
   databases (SQL-standard or widely-supported constructs) is lifted to the core: a `XxxSupport`
   protocol, a `XxxMixin` generic implementation, and `supports_xxx()` capability detection.
   Backends compose the pair and inherit the behaviour; the goal is for the generic layer to
   implement **as much as possible**, minimising backend work.
2. **No broad base → per-backend, backend-named.** A feature without broad base (e.g. table
   partitioning, vendor-proprietary syntax) is implemented by each backend **and prefixed with the
   backend name** (`MySQLRangePartition`, `PostgresRangePartition`, `OracleListPartition`, …).
   The core provides at most an empty marker base; each backend claims its own classes.
3. **Generic implementation doesn't fit a backend → that backend overrides.** If a generic-layer
   expression is supported but its generic implementation does not satisfy a concrete backend's
   needs, the backend simply overrides the affected methods (see `dev-expression-dialect` →
   "Override Discipline (Generic-First)"). Overriding is the correctness escape hatch; it is not a
   reason to avoid lifting broadly-shared features to the core.

### 3. Model Layer

The model layer provides the implementation of the Active Record pattern.

#### Main Components
- `ActiveRecord`: Base class for the Active Record pattern
- `FieldProxy`: Field proxy that bridges the gap between Python objects and SQL queries
- Mixins: `UUIDMixin`, `TimestampMixin`, etc.

### 4. Query Interface

The query interface provides a fluent, type-safe query API.

#### Main Components
- `ActiveQuery`: Most commonly used query object bound to ActiveRecord models
- `CTEQuery`: Query object for building Common Table Expressions (CTEs)
- `SetOperationQuery`: Set operation query object

## Design Patterns

### Sync-Async Parity
Synchronous and asynchronous implementations provide equivalent functionality with unified APIs.

### Gradual ORM
Balancing strict type safety (OLTP) with raw performance (OLAP).

### Layered Architecture
Clear distinction between Backend and ActiveRecord, avoiding tight coupling between database connection management and model definition in traditional ORMs.

## Core Architectural Principles

### 1. Independence from Existing ORMs
- **No ORM Dependencies**: Built from scratch without relying on SQLAlchemy, Django ORM, or other ORMs
- **Direct Driver Interaction**: Backends interact directly with database drivers
- **Lightweight Core**: Core functionality requires only Pydantic

### 2. Open-Closed Principle
- **Open for Extension**: New backends can be added without modifying core code
- **Closed for Modification**: Core interfaces remain stable
- **Implementation**: Protocol-based design with abstract base classes

### 3. Dependency Inversion
- High-level modules (ActiveRecord) don't depend on low-level modules (backends)
- Both depend on abstractions (interfaces)
- Dependency injection through configuration

### 4. Single Responsibility
- Each module has one clear purpose
- Backends handle database-specific details
- Models handle business logic
- Query builders handle query construction

### 5. Consistent SQL Identifier and Literal Formatting (Single Point of Call)

**Purpose**: Ensure all database identifiers (table names, column names, aliases) and literal values are consistently and correctly formatted according to the specific database dialect. This is crucial for conforming to dialect-specific quoting rules (e.g., `"name"`, ``` `name` ```, `[name]`) and ensuring broad compatibility.

**Security Note**: While proper identifier formatting is essential for SQL correctness, the primary mechanism for preventing SQL injection vulnerabilities in this project is the use of **SQL placeholders and parameter separation**, ensuring that literal values are always bound securely and never concatenated directly into the SQL query string.

**Implementation**: The `SQLDialectBase` (and its concrete implementations like `SQLiteDialect`) provides dedicated methods for this:
- `format_identifier(self, identifier: str) -> str`: Formats and quotes identifiers.
- `format_string_literal(self, value: str) -> str`: Formats and quotes string literals.

All query building components (e.g., mixins, `SQLExpression` subclasses) are designed to route identifier and literal formatting through these dialect methods, ensuring a single, centralized point of control for SQL syntax generation.

```python
# In backend/dialect.py
class SQLDialectBase(ABC):
    @abstractmethod
    def format_identifier(self, identifier: str) -> str:
        """Format identifier (table name, column name)."""
        pass

    @abstractmethod
    def format_string_literal(self, value: str) -> str:
        """Format string literal."""
        pass

# Usage in query builder (conceptual)
# formatted_column = self.model_class.backend().dialect.format_identifier(column_name)
# formatted_string = self.model_class.backend().dialect.format_string_literal(string_value)
```

### 6. ActiveRecord Adapts to the Backend (Backend Never Serves ActiveRecord)

**The backend is a consumer contract, not a servant of ActiveRecord.** ActiveRecord is a *user*
of the backend. The backend — its `StorageBackend`, dialect, expression layer, protocols — knows
**nothing** about ActiveRecord and must never be written to accommodate it. Backends describe
**generic SQL and the concrete capabilities of a specific database** (and their SQL-standard /
vendor-proprietary expression surface), never the features of the ActiveRecord layer above them.

**Correct direction of adaptation:**
- ActiveRecord adapts to the backend: it uses whatever the backend provides — and nothing more.
- If a feature ActiveRecord wants requires backend cooperation, the only correct path is to
  **negotiate a protocol / interface contract** on the backend's own generic terms (see the
  `XxxSupport`/`XxxMixin` protocol system), then have ActiveRecord consume that contract.

**Forbidden — the reverse direction:** changing the backend's design principles to satisfy an
ActiveRecord feature requirement is **absolutely wrong**, because the backend would then be
modelled after ActiveRecord instead of after SQL/database reality.

Typical wrong practices (all forbidden):
- Requiring the backend/dialect to add ActiveRecord-serving helpers such as `ddl_inline`,
  `inline_params`, or any parameter-inlining / SQL-rewriting machinery whose only purpose is to
  make an ActiveRecord DDL feature work.
- Requiring the backend/dialect to infer intent from **string characteristics** of SQL/text —
  matching a regex, checking a prefix/suffix, statement-type sniffing from the leading keyword,
  etc. The backend must never interpret SQL text to guess what ActiveRecord meant.

**Why this rule exists:** the backend is the negotiated, cross-cutting foundation every database
backend shares. It describes SQL reality, not the transient needs of one caller. Keeping
ActiveRecord on the consuming side is what lets one model run identically on every backend and
lets new backends be added without touching core. 

**What happens if you break it (harm):** the backend accretes ActiveRecord-specific hacks
(`ddl_inline`, `inline_params`, string-sniffing) that only one caller uses; every other backend
and every future backend must then replicate those hacks or diverge; behaviour forks per caller;
the "generic backend" claim dies and the system degrades into a per-feature patchwork that is
impossible to reason about or extend.

### 7. `to_sql()` Is Terminal and Parameterless — Iron Rule

The expression layer exposes exactly **two** kinds of semantic entry points, and nothing else:

1. **`to_sql()`** — the single method on every expression/predicate/statement object. It returns
   `(sql, params)`.
2. **`dialect.format_*()`** — the single family of formatting functions on the dialect.

**IRON RULE — `to_sql()` accepts NO parameters. Absolutely never.** `to_sql()` is a *terminal*
method: every value it needs was already collected when the expression was **instantiated**. The
signature is fixed by `ToSQLProtocol` as `to_sql(self) -> SQLQueryAndParams` and **never takes
arguments of any kind** — no `to_sql(inline_literals=...)`, no keyword arguments, no rendering
options. Violating this is a protocol violation and is unacceptable.

**IRON RULE — `format_*()` formatting functions accept expression-class instances only, never
additional formatting parameters.** A formatting function receives the expression/predicate it
must render (and the dialect), and nothing else. There is no `format_*(..., inline_literals=...)`,
no rendering flags, no per-call formatting options on the formatting function either.

**Consequence — every formatting choice is a construction-time (factory) choice.** If an output
format must differ (e.g. a `Literal` inside a DDL clause that accepts no bind parameters must be
rendered as inline SQL text rather than a placeholder), that choice is **captured when the
expression is instantiated** — the expression class collects it as a constructor parameter and
carries it, so both `to_sql()` and `format_*()` are pure reads of already-collected state.

**No other semantic methods are permitted.** In particular, **`render*()` methods,
`to_sql_inline()` / `to_sql_inline_literals()` and any other "variant rendering" entry points are
absolutely forbidden** — there is exactly one `to_sql()` and exactly one `format_*` per concern.

If a render-time choice appears necessary, the expression was constructed wrong: the choice
belongs at **construction** time, never in `to_sql()` and never as a formatting-function parameter.

**Why this rule exists:** `to_sql()` and `format_*()` are the *only* two negotiated seams of the
whole expression/dialect system — the entire ecosystem (every backend dialect, every expression,
every call site) is built on them being stable and compositional. `to_sql()` is the fixed,
terminal contract every expression satisfies; `format_*()` is the fixed set of dialect hooks every
backend overrides. Making them parameterized or adding render-time switches breaks that
composition at every layer at once.

**What happens if you break it (harm):** adding a parameter to `to_sql()` (e.g.
`to_sql(inline_literals=...)`) or a render-time option to `format_*()` ripples through every
expression class, every dialect, and every call site simultaneously — a single protocol change
that breaks all backends at once, exactly the failure the "broad research before protocol change"
rule (rule 9) exists to prevent. Render-time switches also make output depend on *how* something
is called rather than *what it is*, so the same expression renders differently in different
places — the system stops being deterministic and auditable.

### 8. No Private Functions in Backend Protocol / Implementation — Everything Is Transparent

The backend protocol and its implementations need **no private helper functions**. All backend
functionality is **transparent**: every behavior is reachable through the documented public surface
(`to_sql()` on expressions; `format_*()` / `supports_*()` on the dialect; the expression/statement
classes; the type adapters), and each of those is self-contained.

**IRON RULE — if you feel the urge to add a private function (a method or module-level helper
prefixed with `_`, or any "internal" formatting/render/recurse helper), you are doing something
wrong. Stop.** A private function means one of two things, both unacceptable:

1. **You are re-implementing or pre-empting public protocol behaviour** (e.g. a private
   `_render_ddl_expression` that walks predicates and inlines literals) — but the public
   `format_*()` functions already exist precisely for that, and they are pure readers. A private
   duplicate is a protocol leak: it bypasses the negotiated interface, cannot be overridden by
   backends, and silently forks behaviour per caller.
2. **You are hiding a design gap** behind an unexposed helper instead of fixing the public
   surface / construction contract. The fix belongs in the public protocol (or in how expressions
   are **constructed**), not in an internal shortcut.

Everything a backend can do must be expressed through public, composable, backend-overridable
functions. If a behaviour cannot be expressed that way, the protocol is incomplete — extend the
protocol deliberately (with broad cross-backend research and design), do **not** paper over it with
a private function.

**Why this rule exists:** the backend's power comes from a *known, negotiated* public surface.
Backends override public `format_*()`/`supports_*()`; expressions and callers consume public
`to_sql()`. A private helper is invisible to that contract: it can't be overridden by a backend
that needs different behaviour, it isn't covered by protocol tests, and it hides *where* behaviour
actually lives. Transparency is what makes the ecosystem composable and testable.

**What happens if you break it (harm):** a private render helper (e.g. `_render_ddl_expression`)
silently forks behaviour — core renders one way, a backend that doesn't know about the helper
renders another, and no protocol test catches the divergence. The helper becomes a hidden second
protocol that only its author's call path uses; later work either duplicates it (drift) or
"fixes" it per-backend (fragmentation). The urge to add a private function is a reliable signal
that the public protocol is missing a deliberate, negotiated capability — hiding it only
guarantees the gap festers.

### 9. Backend Protocol Changes Require Extreme Restraint, Deep Deliberation, and Broad Research

The backend protocol is **not owned by any single backend or by the core in isolation** — it is a
shared contract **implicated across every backend** (core + all extension backends: mysql,
postgres, mariadb, sqlserver, oracle, firebird, clickhouse, snowflake, bigquery, …). Changing any
part of it is a **large, cross-cutting project** that must be treated with **extreme restraint and
deep deliberation**, preceded by **broad research**.

**Process — before touching backend protocol:**
1. **Broad research first.** Survey every backend's implementation and tests for the feature in
   question (and every caller of the affected surface), and validate against real database servers
   where available. Do not design from the core's needs alone.
2. **Deliberate.** Establish that the change is the *minimal* possible expression of the need,
   that it is generic (not serving one caller), and that it composes with every existing
   `format_*()` / `supports_*()` / expression contract.
3. **Negotiate, then implement.** Decide the protocol change deliberately; implement it in the
   generic layer and across every backend together; update all tests; keep behaviour identical
   everywhere.

**Why this rule exists:** the protocol is the system's nervous system — every backend dials into
the same seams (`to_sql()`, `format_*()`, `supports_*()`, expression/statement classes). A
protocol change made hastily for one purpose ripples through all backends at once. Because the
backend protocol is enormously complex and interconnected, restraint is not caution for its own
sake — it is the only way the shared contract stays coherent.

**What happens if you break it (harm):** a hasty protocol change (e.g. inventing a new
`format_ddl_predicate` render helper, or parameterizing `to_sql()`/`format_*()`) commits every
backend to behaviour that was never designed or surveyed; backends drift as each "fixes" it
differently; the generic layer accretes special cases; and the negotiated contract fractures,
forcing costly retrofits across the whole ecosystem. This is exactly what happened repeatedly in
the abandoned DDL-derivation work (`ddl_inline`, `inline_params`, string-sniffing, invented
render helpers) — each was a protocol shortcut that poisoned the shared contract.

### 10. Formatting Is Pure Concatenation — Never Touch or Scan the SQL String

Backend expressions and formatting functions build SQL by **simple concatenation** of fragments:
identifiers (via `format_identifier`), literal atoms (via `format_literal`), placeholders, and
pre-rendered sub-fragment SQL. They **must never inspect, parse, scan, or rewrite the SQL string
itself** — no `startswith`/`endswith`/`in` checks on generated SQL, no regex matching, no
character-by-character scanning, no quote-state machines, no post-hoc placeholder substitution.

**Why this rule exists:** generated SQL is the *output* of formatting, not its input. Any logic
that reads the generated string is by definition guessing at structure that the formatter already
knew when it concatenated — a second, unreliable parse of information that was available as typed
data at construction time. String scanning of SQL is also a classic injection surface: any
mismatch between the scanner's assumptions (quote states, escape rules, placeholder characters)
and the real dialect syntax silently corrupts the statement.

**The single exception — inline-literal resolution.** When a statement
(`requires_inline_literals() == True`, trusted developer-declared DDL) renders its literal
values inline, the dialect's `format_literal` produces **escaped, quoted atoms**; these are
concatenated directly during formatting and never require re-scanning the assembled SQL.
Because this exception deals with splicing raw values into SQL text, it is a **SQL-injection
hazard by nature**: developers must be highly alert that inline content is trusted-only and
never reachable by end users. `Literal.requires_inline_literals` / the statement-level switch
must default to `False` (bind parameters) for exactly this reason.

**What happens if you break it (harm):** a scanner (e.g. walking the assembled SQL to replace
`?` placeholders) mis-fires on placeholders that appear *inside* string literals, breaks the
moment a dialect's quoting or placeholder syntax differs, and duplicates knowledge the
formatter already had — all to solve a problem that pure concatenation never creates.

## Package Architecture

### Package Structure

```
rhosocial-activerecord/          # Core package (PEP 420 namespace package - no __init__.py at
├── src/rhosocial/activerecord/  #   the activerecord/ and backend/ levels; see below)
│   │   ├── bulk_operations.py  # Bulk operations support
│   │   ├── column_name_mixin.py # Column name handling mixin
│   │   ├── derived_field_handler.py # Derived field handler
│   │   ├── derived_field_mixin.py # Derived field mixin
│   │   ├── field_adapter_mixin.py # Field adapter mixin
│   │   ├── field_proxy.py      # Field proxy implementation
│   │   ├── fields.py           # Field definitions
│   │   ├── metaclass.py        # Model metaclass
│   │   └── query_mixin.py      # Query functionality mixin
│   ├── field/                  # Field mixins and types
│   │   ├── __init__.py
│   │   ├── composite_pk.py     # Composite primary key mixin
│   │   ├── integer_pk.py       # Integer primary key mixin
│   │   ├── README.md
│   │   ├── soft_delete.py      # Soft delete mixin
│   │   ├── timestamp.py        # Timestamp mixin
│   │   ├── uuid.py             # UUID mixin
│   │   └── version.py          # Version mixin
│   ├── interface/              # Public API interfaces
│   │   ├── __init__.py
│   │   ├── base.py             # Base interfaces
│   │   ├── model.py            # Model interface
│   │   ├── query.py            # Query interface
│   │   ├── update.py           # Update interface
│   ├── query/                  # Query building components
│   │   ├── __init__.py
│   │   ├── active_query.py     # Main query interface
│   │   ├── aggregate.py        # Aggregate query functionality
│   │   ├── async_join.py       # Async join functionality
│   │   ├── async_relational.py # Async relational query functionality
│   │   ├── base.py             # Base query functionality
│   │   ├── cte_query.py        # CTE query functionality
│   │   ├── join.py             # Join query functionality
│   │   ├── range.py            # Range query functionality
│   │   ├── relational.py       # Relational query functionality
│   │   ├── set_operation.py    # Set operation query functionality
│   │   └── utils.py            # Query utilities (placeholder conversion, etc.)
│   ├── relation/               # Relationship components
│   │   ├── __init__.py
│   │   ├── async_descriptors.py # Async relationship descriptors
│   │   ├── base.py             # Base relationship functionality
│   │   ├── cache.py            # Relationship caching
│   │   ├── cache_backend.py    # Cache backend abstraction
│   │   ├── cache_backends/     # Cache backend implementations (in_memory, redis)
│   │   ├── descriptors.py      # Relationship descriptors
│   │   ├── interfaces.py       # Relationship interfaces
│   │   └── type_resolver.py    # Relation type resolver
│   ├── model.py                # ActiveRecord + AsyncActiveRecord classes
│   ├── connection/             # Named connection support
│   ├── logging/                # Logging infrastructure
│   ├── worker/                 # Background worker support
│   ├── types.py
│   └── backend/                # Backend abstraction and implementations
│       ├── base/               # Backend base classes
│       │   ├── __init__.py
│       │   └── base.py         # StorageBackend base class
│       ├── dialect/            # SQL dialect implementations
│       │   ├── __init__.py
│       │   └── base.py         # SQLDialect base class
│       ├── expression/         # Expression system
│       │   ├── __init__.py     # Expression system entry point
│       │   ├── advanced_functions.py # Advanced SQL functions (CASE, CAST, etc.)
│       │   ├── aggregates.py   # Aggregate function expressions
│       │   ├── bases.py        # Base expression classes and protocols
│       │   ├── collation.py    # Collation expressions
│       │   ├── core.py         # Core expressions (Column, Literal, etc.)
│       │   ├── datetime.py     # Date/time expressions
│       │   ├── executable.py   # Executable expression support
│       │   ├── functions/      # Factory functions (directory package)
│       │   ├── graph.py        # Graph query expressions
│       │   ├── introspection.py # Introspection expressions
│       │   ├── literals.py     # Literal expressions
│       │   ├── mixins.py       # Expression mixins with operator overloading
│       │   ├── operators.py    # SQL operation expressions
│       │   ├── predicates.py   # Predicate expressions
│       │   ├── query_parts.py  # Query clause expressions
│       │   ├── query_sources.py # Query source expressions
│       │   ├── serialization.py # Expression serialization
│       │   ├── statements/     # SQL statement expressions (directory package)
│       │   ├── transaction.py  # Transaction-related expressions
│       │   ├── types/          # Type-related expressions (directory package)
│       │   └── xml.py          # SQL/XML expressions
│       ├── impl/               # Backend implementations
│       │   ├── dummy/          # Dummy backend for testing
│       │   │   ├── __init__.py
│       │   │   ├── backend.py
│       │   │   └── dialect.py
│       │   └── sqlite/         # SQLite backend implementation
│       │       ├── __init__.py
│       │       ├── __main__.py
│       │       ├── adapters.py # SQLite type adapters
│       │       ├── backend/    # Backend implementation (directory package)
│       │       │   ├── sync.py         # SQLiteBackend
│       │       │   ├── async_backend.py # AsyncSQLiteBackend
│       │       │   └── common.py
│       │       ├── config.py   # SQLite configuration
│       │       ├── dialect.py  # SQLite dialect implementation
│       │       ├── transaction.py # SQLite transaction handling
│       │       ├── async_transaction.py # SQLite async transaction handling
│       │       ├── expression/ # SQLite-specific expressions
│       │       ├── functions/  # SQLite-specific SQL functions
│       │       ├── mixins/     # SQLite dialect mixins
│       │       ├── extension/  # SQLite extensions (FTS5, RTree, etc.)
│       │       ├── pragma/     # PRAGMA support
│       │       ├── explain/    # EXPLAIN support
│       │       ├── introspection/ # SQLite introspection
│       │       ├── schema/     # SQLite schema helpers
│       │       ├── protocols.py # SQLite protocol declarations
│       │       ├── cli/        # SQLite CLI tools
│       │       └── examples/   # SQLite examples
│       ├── config.py           # Backend configuration base classes
│       ├── errors.py           # Backend-specific errors
│       ├── helpers.py          # Backend helper functions
│       ├── options.py          # Backend options
│       ├── output_abc.py       # Output abstraction
│       ├── output_rich.py      # Rich output implementation
│       ├── output.py           # Output utilities
│       ├── protocols.py        # Backend protocol declarations
│       ├── README.md           # Backend documentation
│       ├── result.py           # Query result handling
│       ├── schema/             # Schema management (directory package: snapshot, differ, ...)
│       ├── transaction.py      # Transaction base classes
│       ├── type_adapter.py     # Type adaptation system
│       └── type_registry.py    # Type adapter registry
```

> Note: `src/rhosocial/activerecord/` and `backend/` are **PEP 420 namespace packages** — they
> intentionally have **no `__init__.py`**, so extension backends
> (`rhosocial-activerecord-mysql`, `rhosocial-activerecord-postgres`, ...) can drop their
> packages into `backend/impl/{name}/` without modifying core. The tree above is representative,
> not exhaustive; the project evolves quickly and additional modules/subpackages may exist.

### Namespace Package Structure

The `rhosocial.activerecord` package uses **PEP 420 implicit namespace packages** (no
`__init__.py` at the `activerecord/` and `backend/` levels). This allows multiple distributions
to contribute to the same namespace: the core package provides `base/`, `query/`, `relation/`,
`backend/impl/dummy/`, `backend/impl/sqlite/`, etc., while extension projects ship their own
`backend/impl/{name}/` directory (e.g., `mysql`, `postgres`) in separate distributions.

```python
# No __init__.py and no pkgutil.extend_path() is required anywhere in the core package.
# Python's namespace-package mechanism resolves the merged package automatically when the
# core and extension distributions are installed side by side.
```

This allows multiple packages to contribute to the same namespace, enabling distributed backend implementations.

## Layer Architecture

### 1. Interface Layer

**Location**: `interface/`

**Purpose**: Define contracts for all components

```python
# interface/model.py
class IActiveRecord(ActiveRecordBase):  # ActiveRecordBase(BaseModel, ABC)
    """Core ActiveRecord interface."""

    @abstractmethod
    def save(self) -> int:
        """Save record to database; returns number of affected rows."""
        pass

    @abstractmethod
    def delete(self) -> int:
        """Delete record from database; returns number of affected rows."""
        pass

    # Additional abstract members (find_one, find_all, find_one_or_fail, refresh(), ...)
```

> Note: `save()`/`delete()` return `int` (affected row count), not `bool`. An
> `IAsyncActiveRecord` parallel interface also exists.

### 2. Model Layer

**Location**: `base/`, main `ActiveRecord` class

**Purpose**: Business logic and data management

```python
# model.py - composition through mixins (sync)
class ActiveRecord(
    RelationManagementMixin,  # Relationship handling
    QueryMixin,                # Query capabilities
    ColumnNameMixin,           # Column name mapping
    FieldAdapterMixin,         # Field-specific type adaptation
    DerivedFieldMixin,         # Derived/computed fields
    MetaclassMixin,            # Metaclass-based feature handling
    BaseActiveRecord           # Core CRUD
):
    pass

# A parallel AsyncActiveRecord uses AsyncQueryMixin + AsyncBaseActiveRecord.
```

### 3. Backend Layer

**Location**: `backend/base/` (base classes), `backend/impl/` (implementations)

**Purpose**: Database abstraction and operations

```python
# backend/base/base.py -> StorageBackendBase (ABC)
# backend/base/__init__.py -> composed StorageBackend / AsyncStorageBackend
class StorageBackend(
    # ...composed from LoggingMixin, CapabilityMixin, TypeAdaptionMixin, SQLBuildingMixin, etc.
    ABC
):
    """
    Abstract storage backend, primarily composed from various functional mixins.
    Its `execute` method acts as a template method orchestrating these mixins.
    """

    # The actual execute method is a template method, coordinating mixins
    def execute(self, sql: str, params: Dict, **kwargs) -> QueryResult:
        # ... implementation coordinates mixins for connection, parsing,
        #     returning clause, cursor, SQL building, execution, result processing ...
        pass
```

### 4. Implementation Layer

**Location**: `backend/impl/`

**Purpose**: Concrete database implementations

```python
# backend/impl/sqlite/backend/sync.py
class SQLiteBackend(StorageBackend):
    """SQLite-specific implementation."""

    def execute(self, sql: str, params: Dict) -> QueryResult:
        # SQLite-specific execution
        pass
```

## Design Patterns

### 1. Active Record Pattern

**Implementation**: Core pattern of the library

```python
class User(ActiveRecord):
    __table_name__ = "users"

    name: str
    email: str

# Usage
user = User(name="John", email="john@example.com")
user.save()  # Persists to database
```

**Benefits**:
- Intuitive API
- Encapsulated persistence logic
- Domain model and data access combined

### 2. Protocol Pattern

**Purpose**: Define interfaces without inheritance

```python
from typing import Protocol, runtime_checkable

# Example: SQLTypeAdapter protocol
from typing import Protocol, runtime_checkable, Any, Type, Dict, Optional

@runtime_checkable
class SQLTypeAdapter(Protocol):
    """Protocol for type conversion between Python and database values."""

    def to_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any: ...
    def from_database(self, value: Any, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any: ...

    @property
    def supported_types(self) -> Dict[Type, Set[Type]]: ...
```

**Benefits**:
- Duck typing with type safety
- No forced inheritance hierarchy
- Runtime type checking available

### 3. Mixin Pattern

**Purpose**: Composable functionality

```python
class TimestampMixin:
    """Add timestamp tracking."""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

class SoftDeleteMixin:
    """Add soft delete capability."""
    deleted_at: Optional[datetime] = None

    def delete(self):
        self.deleted_at = datetime.now()
        return self.save()

# Composition
class Article(TimestampMixin, SoftDeleteMixin, ActiveRecord):
    __table_name__ = "articles"
    title: str
    content: str

# Mixins are also extensively used for backend composition (e.g., StorageBackend in backend/base/)
# providing modular and reusable components for database interaction.
```

### 4. Builder Pattern

**Implementation**: Query construction

```python
# The project's query builder is ActiveQuery, composed from specialized mixins.
from rhosocial.activerecord.query import (
    ActiveQuery, BaseQueryMixin, AggregateQueryMixin, JoinQueryMixin,
    RangeQueryMixin, RelationalQueryMixin,
)

class ActiveQuery(
    AggregateQueryMixin,
    BaseQueryMixin,
    JoinQueryMixin,
    RelationalQueryMixin,
    RangeQueryMixin,
    IActiveQuery,
    ISetOperationQuery,
):
    """
    Complete ActiveQuery implementation, combining all query mixins.
    It builds SQL by collecting conditions, orders, joins, etc.,
    and delegates to its mixins for specific functionalities.

    NOTE: CTE queries are built with a separate CTEQuery class (cte_query.py),
    which is NOT part of ActiveQuery's inheritance.
    """
    pass
```

### 5. Registry Pattern

**Purpose**: Manage type converters and backends

```python
# The project uses backend.type_registry.TypeRegistry for SQLTypeAdapter instances
from typing import Dict, Tuple, Type, Optional
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter

class TypeRegistry:
    """Central registry for SQLTypeAdapter instances."""
    def __init__(self):
        self._adapters: Dict[Tuple[Type, Type], SQLTypeAdapter] = {}

    def register(self, adapter: SQLTypeAdapter, py_type: Type, db_type: Type) -> None:
        self._adapters[(py_type, db_type)] = adapter

    def get_adapter(self, py_type: Type, db_type: Type) -> Optional[SQLTypeAdapter]:
        return self._adapters.get((py_type, db_type))
```

### 6. Template Method Pattern

**Purpose**: Define algorithm skeleton in base class

```python
# The execute method in StorageBackend acts as a Template Method
# Located in backend/base/ (StorageBackendBase in base.py; the composed StorageBackend
# and AsyncStorageBackend in __init__.py). Mixin names below are illustrative of the
# responsibilities; concrete composition lives in backend/base/.
class StorageBackend(
    # ...composed from various functional mixins like SQLBuildingMixin,
    # QueryAnalysisMixin, ReturningClauseMixin, ResultProcessingMixin, etc.
    ABC
):
    """
    Abstract storage backend. Its `execute` method is a Template Method
    that orchestrates the query execution process by coordinating its
    composed functional mixins.
    """

    # This is the actual Template Method
    def execute(self, sql: str, params: Optional[Tuple] = None, **kwargs) -> QueryResult:
        # 1. Start timer
        # 2. Log SQL and parameters
        # 3. Handle connection setup (if not already connected)
        # 4. Parse statement type (via QueryAnalysisMixin)
        # 5. Process RETURNING clause (via ReturningClauseMixin)
        # 6. Get cursor
        # 7. Prepare SQL and parameters (via SQLBuildingMixin)
        # 8. Execute query (hook method `_execute_query` in concrete backend)
        # 9. Process results (via TypeAdaptionMixin, ResultProcessingMixin)
        # 10. Log completion
        # 11. Build QueryResult
        # 12. Handle auto-commit (hook method `_handle_auto_commit_if_needed`)
        # 13. Handle errors (hook method `_handle_execution_error`)
        pass

    # Hook methods (some are abstract in StorageBackend, others in mixins)
    @abstractmethod
    def _execute_query(self, cursor, sql: str, params: Optional[Tuple]): ...
    # ... other abstract hook methods like connect(), disconnect(), etc.
```

### 7. Backend Registration and Binding

There is **no generic `create_backend()` factory function** in the core package. Backends are
bound to a model via `configure()`, which instantiates the backend under the hood.

```python
# configure() builds the backend from a config + backend_class and binds it to the model.
User.configure(config, SQLiteBackend)   # or MySQLBackend, PostgresBackend, etc.
# -> internally: cls.__backend__ = backend_class(connection_config=config, ...)
#    and calls backend.introspect_and_adapt()
```

Because all backends share a namespace package (`rhosocial.activerecord.backend.impl.{name}`),
each backend can be imported and configured independently without a central factory mapping
backend names to classes.

## Class Hierarchy

### Model Hierarchy

```
BaseModel (Pydantic)
    └── IActiveRecord (Interface - implemented by BaseActiveRecord)
        └── BaseActiveRecord / AsyncBaseActiveRecord (Core implementations)
            # ActiveRecord is composed from these mixins and BaseActiveRecord
            └── RelationManagementMixin
            └── QueryMixin            # AsyncActiveRecord uses AsyncQueryMixin
            └── ColumnNameMixin
            └── FieldAdapterMixin
            └── DerivedFieldMixin
            └── MetaclassMixin
                └── ActiveRecord (Full sync implementation)
                └── AsyncActiveRecord (Full async implementation)
                    └── User, Post, etc. (User models)
```

Note: The actual composition (`model.py`) is `ActiveRecord(RelationManagementMixin,
QueryMixin, ColumnNameMixin, FieldAdapterMixin, DerivedFieldMixin, MetaclassMixin,
BaseActiveRecord)`, and a parallel `AsyncActiveRecord` class exists for async support.

### Backend Hierarchy

```
StorageBackendBase (ABC)                # backend/base/base.py
    # Composed from mixins for sync operations
    └── StorageBackend (ABC)            # backend/base/__init__.py
        └── SQLiteBackend               # backend/impl/sqlite/backend/sync.py
        # └── MySQLBackend (extension: rhosocial-activerecord-mysql)
        # └── PostgreSQLBackend (extension: rhosocial-activerecord-postgres)
        # ...

StorageBackendBase (ABC)
    # Composed from mixins for async operations
    └── AsyncStorageBackend (ABC)       # backend/base/__init__.py
        └── AsyncSQLiteBackend          # backend/impl/sqlite/backend/async_backend.py (implemented)
        # └── AsyncMySQLBackend (extension)
        # ...
```

> Note: `StorageBackendBase` lives in `backend/base/base.py`; the composed `StorageBackend` and
> `AsyncStorageBackend` (both ABC) are re-exported from `backend/base/__init__.py`. The async
> SQLite backend is fully implemented.

## Module Interactions

### Configuration Flow

```python
# 1. User configures model
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

class User(ActiveRecord):
    __table_name__ = "users"
    name: str

# 2. Configure backend
config = SQLiteConnectionConfig(database="app.db")
User.configure(config, SQLiteBackend)

# 3. Backend initialized and attached
# User.__backend__ = SQLiteBackend(config)
```

### Query Execution Flow

```
User.query().where("name = ?", ("John",))
    ↓
ActiveQuery.where()  # builds a RawSQLPredicate / typed predicate in the WHERE clause
    ↓
ActiveQuery.to_sql()
    ↓
Backend.execute()
    ↓
Database
    ↓
Backend.fetch_results()
    ↓
Model instantiation
    ↓
User instances
```

## Dependency Management

### Core Dependencies

The project maintains **minimal core dependencies** by design:

```toml
# Minimal core dependencies - Pydantic only
[project]
dependencies = [
    "pydantic==2.10.6; python_version == '3.8'",          # Data validation and model definition
    "pydantic>=2.12.0; python_version >= '3.9'",
    "typing_extensions>=4.0.0",                            # Backported typing features for Python 3.8
]
```

**Important**: This is a **standalone ActiveRecord implementation** with no dependencies on existing ORMs like SQLAlchemy, Django ORM, or others. All database interaction logic is implemented from scratch.

### Optional Dependencies

The core package does **not** depend on any native database driver directly. Backend support is
provided by separate extension distributions, exposed as optional extras:

```toml
[project.optional-dependencies]
mysql = ["rhosocial-activerecord-mysql>=1.0.0,<2.0.0"]    # MySQL backend extension
postgres = ["rhosocial-activerecord-postgres>=1.0.0,<2.0.0"]  # PostgreSQL backend extension
```

Each backend extension depends on its own native driver (e.g., `mysql-connector-python`,
`psycopg`) and ships its own `backend/impl/{name}/` package.

### Backend Discovery

There is **no `discover_backends()` function** in the core package. Backends are imported
explicitly and bound to models via `configure()`:

```python
# Users (or extension entry points) import the backend explicitly.
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
# Installed extensions are importable the same way:
#   from rhosocial.activerecord.backend.impl.mysql import MySQLBackend
#   from rhosocial.activerecord.backend.impl.postgres import PostgresBackend

User.configure(SQLiteConnectionConfig(database="app.db"), SQLiteBackend)
```

## Extension Points

### 1. Custom Fields

```python
class EncryptedField(Field):
    """Custom encrypted field type."""

    def __set__(self, instance, value):
        encrypted = encrypt(value)
        super().__set__(instance, encrypted)

    def __get__(self, instance, owner):
        value = super().__get__(instance, owner)
        return decrypt(value) if value else None
```

### 2. Custom Validators

```python
from pydantic import field_validator

class User(ActiveRecord):
    email: str

    @field_validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email')
        return v.lower()
```

### 3. Custom Query Methods

```python
class UserQueryMixin:
    @classmethod
    def find_by_email(cls, email: str):
        return cls.query().where("email = ?", (email,)).one()

    @classmethod
    def active_users(cls):
        return cls.query().where(cls.c.is_active == True).all()  # noqa: E712

class User(UserQueryMixin, ActiveRecord):
    pass
```

### 4. Event Hooks

```python
class User(ActiveRecord):
    def before_save(self):
        """Called before saving."""
        self.updated_at = datetime.now()

    def after_save(self):
        """Called after saving."""
        cache.invalidate(f"user:{self.id}")
```

## Performance Optimization

### 0. Lightweight Foundation

The architecture is designed for minimal overhead:
- **No ORM layers**: Direct database driver communication
- **Single dependency**: Only Pydantic required for core functionality
- **Fast startup**: Minimal imports and initialization
- **Low memory footprint**: No heavy framework baggage

### 1. Connection Pooling

Connection pooling is provided by the `connection/pool/` subpackage (sync + async), not by a
`PooledBackend` subclass of `StorageBackend`.

Key components (`src/rhosocial/activerecord/connection/pool/`):
- `BackendPool` (`sync_pool.py`) / `AsyncBackendPool` (`async_pool.py`) — the pool managers
- `PoolConfig` (`config.py`) — pool configuration (`min_size`, `max_size`, `backend_factory`, ...)
- `PoolStats` (`stats.py`) — pool statistics
- `PooledBackend` (`pooled_backend.py`) — a **dataclass wrapper** around a backend instance
  tracking lifecycle (created/last_used/acquired timestamps, use_count, health, thread affinity);
  it is **not** a `StorageBackend` subclass

The pool supports three connection modes selected automatically or explicitly:
- **persistent** — connections stay open across acquire/release (for `threadsafety >= 2` backends,
  e.g. PostgreSQL/psycopg)
- **transient** — connect on acquire / disconnect on release (for `threadsafety < 2` backends,
  e.g. SQLite, MySQL)
- **auto** (default) — picks persistent vs transient based on the backend's `threadsafety`

```python
from rhosocial.activerecord.connection.pool import PoolConfig, BackendPool

config = PoolConfig(
    min_size=2,
    max_size=10,
    backend_factory=lambda: PostgresBackend(host="localhost"),
)
pool = BackendPool.create(config)   # create() warms up connections

# Manual acquire/release
backend = pool.acquire()
try:
    result = backend.execute("SELECT 1")
finally:
    pool.release(backend)

# Or use context managers
with pool.connection() as backend:
    backend.execute("SELECT 1")
with pool.transaction() as backend:
    backend.execute("INSERT INTO users (name) VALUES (?)", ["Alice"])

pool.close()
```

Pool size can also be supplied per-config via `pool_size` (e.g. `configure(partial(prod_db,
pool_size=20), MySQLBackend)`). Backend-level pooling knobs live in
`backend/config.py` (`ConnectionPoolProtocol` / `ConnectionPoolMixin`).

### 2. Relation Caching (Instance-level)

```python
from rhosocial.activerecord.relation.cache import InstanceCache, CacheConfig

# In RelationDescriptor (used by mixins like RelationalQueryMixin)
class RelationDescriptor:
    # ...
    def _load_relation(self, instance: Any) -> Optional[T]:
        """
        Load relation with instance-level caching support.
        """
        cached = InstanceCache.get(instance, self.name, self._cache_config)
        if cached is not None:
            return cached

        data = self._loader.load(instance)
        InstanceCache.set(instance, self.name, data, self._cache_config)
        return data

# Cache configuration can be global or per-relation
global_config = GlobalCacheConfig()
global_config.set_config(enabled=True, ttl=300, max_size=1000)
```

### 3. Lazy Loading

```python
class RelationDescriptor:
    def __get__(self, instance, owner):
        if not hasattr(instance, '_relation_cache'):
            instance._relation_cache = {}

        if self.name not in instance._relation_cache:
            # Load relation only when accessed
            instance._relation_cache[self.name] = self.load(instance)

        return instance._relation_cache[self.name]
```

## Thread Safety

### Key Thread Safety Mechanisms

The project utilizes specific mechanisms for thread safety:

1. **ThreadSafeDict** for mutable shared state (e.g., query eager loads, `_eager_loads` in
   `RelationalQueryMixin`)
2. **InstanceCache** for per-instance caching (thread-safe for each instance's data)
3. **Backend connection management** — e.g., `SQLiteBackend` uses `sqlite3.connect`, which can be
   thread-safe for basic ops, while the built-in `connection/pool/` `BackendPool` /
   `AsyncBackendPool` provide robust pooling for other DBs (persistent/transient/auto modes
   based on backend `threadsafety`)

Example: `ThreadSafeDict` (from `interface/query.py`):

```python
from typing import Dict, Any, TypeVar
from threading import local

K = TypeVar('K')
V = TypeVar('V')

class ThreadSafeDict(Dict[K, V]):
    """A thread-safe dictionary that behaves exactly like a normal dict."""
    def __init__(self, *args, **kwargs):
        self._local = local()
        if not hasattr(self._local, 'data'):
            self._local.data = {}
        if args or kwargs:
            self.update(*args, **kwargs)

    def __getitem__(self, key: K) -> V:
        return self._local.data[key]
```

`InstanceCache` for relation caching (from `relation/cache.py`) ensures thread-safety by storing
cache data on the instance itself or using thread-local storage where appropriate, preventing
race conditions on shared cache structures.

## Error Handling Strategy

### Exception Hierarchy

```python
class ActiveRecordError(Exception):
    """Base exception for all ActiveRecord errors."""

class DatabaseError(ActiveRecordError):
    """Database operation errors."""

class ValidationError(ActiveRecordError):
    """Data validation errors."""

class RecordNotFound(DatabaseError):
    """Record not found in database."""
```

### Error Propagation

```
User Input
    ↓
Validation (ValidationError)
    ↓
Model Operations
    ↓
Backend Operations (DatabaseError)
    ↓
Database Driver (Driver-specific errors)
```

## Testing Architecture

### Test Organization

The test suite is a single package mirroring the source layout, not split into
unit/integration/fixtures directories:

```
tests/
├── conftest.py                        # Shared fixtures and hooks
├── benchmark/                         # Performance benchmarks (activerecord_bulk, backend, relation)
├── config/                            # Test scenario configs (e.g. redis_scenarios.yaml)
├── providers/                         # Testsuite-style provider/fixture implementations
│   ├── basic.py, query.py, relation.py, events.py, mixins.py ...
│   └── registry.py                    # Provider registry
└── rhosocial/activerecord_test/       # Main test package mirroring src layout
    ├── feature/                       # Feature tests: basic, query, relation, events,
    │   │                              #   mixins, interface, connection, worker, backend/
    │   └── test_features.py           # (async variant: test_features_async.py)
    ├── realworld/                     # Real-world scenario tests (e-commerce, finance, ...)
    └── logging_module/                # Logging module tests
```

Backend extension projects ship their own tests following the same
`tests/rhosocial/activerecord_test/feature/backend/{name}/` layout. Test execution and
PYTHONPATH requirements are in `testing.md`.

### Fixture Pattern

The suite uses a **Provider pattern** to decouple tests from concrete backends. The testsuite
(`rhosocial-activerecord-testsuite`) defines feature interfaces (e.g. `IBasicProvider`,
`IQueryProvider`); each project registers concrete sync/async providers in a registry, and
`tests/conftest.py` points the testsuite at it via `TESTSUITE_PROVIDER_REGISTRY`.

```python
# tests/providers/registry.py
from rhosocial.activerecord.testsuite.core.registry import ProviderRegistry
from .basic import BasicSyncProvider, BasicAsyncProvider

provider_registry = ProviderRegistry()
provider_registry.register("feature.basic.IBasicProvider", BasicSyncProvider)
provider_registry.register("feature.basic.IBasicSyncProvider", BasicSyncProvider)
provider_registry.register("feature.basic.IBasicAsyncProvider", BasicAsyncProvider)
```

Feature support is detected via **protocols** — tests use `isinstance()` checks (or
`@requires_protocol(...)` markers) against backend protocol implementations to decide whether a
feature test applies, so the same tests run across different backends. Full details: the
`dev-testing-contributor` skill.