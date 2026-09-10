---
name: dev-backend-development
description: Complete guide for implementing new database backends for rhosocial-activerecord - StorageBackend, dialect, type adaptation, transactions, error handling, async equivalence, testing and release readiness
license: MIT
compatibility: opencode
metadata:
  category: backend
  level: advanced
  audience: developers
---

# Backend Development Guide

Complete instructions for implementing new database backends. A robust backend is more than a
query executor: it includes a database-specific **SQL Dialect**, a precise **Type Adaptation**
system, reliable **Transaction Management**, robust **Error Handling**, clear **Feature
Detection**, and **Performance Optimizations**.

> Use this skill together with **`dev-expression-dialect`** for the Expression-Dialect
> separation rules. Reference implementations: `rhosocial-activerecord-mysql`,
> `rhosocial-activerecord-postgres`. Study their `backend.py`/`adapters.py`/`tests/`.

**Design constraint**: use **native database drivers only** (`mysql-connector-python`,
`psycopg`, ...). No SQLAlchemy/Django ORM dependencies.

## Package Structure

Standardized layout (namespace packages):

```
rhosocial-activerecord-{backend}/
├── src/rhosocial/activerecord/backend/impl/{backend}/
│   ├── __init__.py
│   ├── backend.py       # Storage implementation (may be a `backend/` subpackage)
│   ├── adapters.py      # Type adapters (may be an `adapters/` subpackage)
│   ├── config.py        # Connection configuration
│   ├── dialect.py       # SQL dialect handling
│   ├── transaction.py   # Transaction management
│   ├── expression/      # Backend-specific expressions (DIRECTORY, required)
│   │   └── __init__.py
│   ├── functions/       # Backend-specific SQL functions (DIRECTORY, required)
│   │   └── __init__.py
│   └── features.py      # Optional: Feature detection
```

Layout evolution note: PostgreSQL splits `backend.py` into a `backend/` subpackage
(`base.py`, `sync.py`, `async_backend.py`) and `adapters.py` into `adapters/`; MySQL keeps flat
files. Both add `mixins/`, `cli/`, `explain/`, `introspection/`, `schema/`, `protocols.py`.
Mirror current reference implementations where practical; `expression/` and `functions/`
**directories** are required conventions.

Use **absolute imports** for expressions from core/other backends; avoid deep relative imports.

## StorageBackend Interface

Implement every abstract method:

- `connect()` / `disconnect()` / `ping(reconnect=True)`
- `execute(sql, params=None, returning=None, column_adapters=None) -> QueryResult`
- `get_server_version() -> tuple`
- `introspect_and_adapt()` — connect, query server version, re-init dialect + adapters by
  version (no-op for backends that don't need version adaptation, e.g. SQLite/Dummy)
- `_initialize_capabilities() -> DatabaseCapabilities`
- `_handle_error(error)` — map driver exceptions to standard `DatabaseError` subclasses
- `transaction_manager` / `dialect` properties
- `get_default_adapter_suggestions()` — preferred conversion strategy for the core
- `_register_my_adapters()` — instantiate + register adapters (allow `allow_override=True`)

## Connection Configuration

Immutable `@dataclass(frozen=True)` extending `BaseConfig` (`backend/config.py`):

```python
from dataclasses import dataclass
from rhosocial.activerecord.backend.config import BaseConfig

@dataclass(frozen=True)
class MyDatabaseConfig(BaseConfig):
    host: str = "localhost"
    port: int = 5432
    database: str
    user: str | None = None
    password: str | None = None
```

## SQL Dialect

- Inherits `SQLDialectBase` + relevant mixins + protocols (`backend/dialect.py`).
- Implement `quote_identifier`, `get_placeholder`, `format_limit_offset`, `get_type_mappings`,
  plus protocol methods.
- **Protocol-Mixin architecture**: Protocols (`protocols.py`) define the contract; Mixins
  (`mixins.py`) provide SQL-standard defaults a dialect overrides.
- Adding a protocol: SQL-standard features go in the main package; dialect-specific features in
  the extension dialect; update `DummyDialect`; add tests. See `dev-expression-dialect` for the
  full protocol/mixin table and workflow.

### Generic vs Concrete Expression Placement

Decide whether an expression/protocol belongs in the **generic (core) layer** or a **specific
backend** by the *breadth* of its base — with the goal that the generic layer implements as much
as possible, to minimise backend work:

1. **Broad base → generic layer.** Feature exists with standard semantics across many databases:
   add a `XxxSupport` protocol + `XxxMixin` generic implementation + `supports_xxx()`. Backends
   compose the pair and inherit the behaviour; override only where their real capability differs.
2. **No broad base → implement per-backend, prefixed with the backend name** (e.g.
   `MySQLRangePartition`, `PostgresRangePartition`, `OracleListPartition`). Core provides at most
   an empty marker base; each backend claims its own via `build_spec`/`isinstance`.
3. **Generic implementation doesn't fit → override.** A backend overrides the affected
   method(s) when the generic behaviour doesn't satisfy its needs (Override Discipline,
   Generic-First). Overriding is the correctness escape hatch, not a reason to avoid lifting
   broadly-shared features to the core.

### Backend Boundary Rule

**The backend is a consumer contract, not a servant of ActiveRecord.** ActiveRecord is a *user*
of the backend; the backend knows **nothing** about ActiveRecord and must never be written to
accommodate it. A backend (its dialect, expressions, protocols) describes **generic SQL and the
concrete capabilities of the database it wraps** — never the features of the ActiveRecord layer.
Therefore ActiveRecord adapts to the backend: it uses whatever the backend provides, and nothing
more. When ActiveRecord needs a feature that requires backend cooperation, negotiate it as a
**protocol/interface contract** on the backend's generic terms — do not change backend design to
suit ActiveRecord.

Forbidden (all absolutely wrong):
- Adding ActiveRecord-serving dialect helpers (e.g. `ddl_inline`, `inline_params`) or any
  parameter-inlining / SQL-rewriting machinery that exists only to support an ActiveRecord
  feature.
- Making the dialect/backend infer intent from **string characteristics** (regex matches,
  prefix/suffix checks, statement-type sniffing from leading keywords, etc.).

### The Only Expression Semantics Are `to_sql()` and `dialect.format_*()`

The expression layer exposes exactly two kinds of semantic entry points and nothing else:

1. **`to_sql()`** — the single method on every expression/predicate/statement object.
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
absolutely forbidden.** There is exactly one `to_sql()` and exactly one `format_*` per concern.

If a render-time choice appears necessary, the expression was constructed wrong: the choice
belongs at **construction** time, never in `to_sql()` and never as a formatting-function parameter.

**Why / harm:** `to_sql()` and `format_*()` are the *only* negotiated seams of the whole
expression/dialect system; the entire ecosystem is built on them being stable and compositional.
Adding a parameter to `to_sql()` or a render-time option to `format_*()` ripples through every
expression class, every dialect, and every call site at once — a single protocol change that
breaks all backends simultaneously. Render-time switches also make output depend on *how*
something is called rather than *what it is*, so the same expression renders differently in
different places — the system stops being deterministic and auditable.

### No Private Functions in Backend Protocol / Implementation — Everything Is Transparent

Backend protocol and implementations need **no private helper functions**. All behaviour is
reachable through the public surface (`to_sql()` on expressions; `format_*()`/`supports_*()` on
the dialect; expression/statement classes; type adapters). **If you feel the urge to add a private
function, you are doing something wrong — stop.** A private helper either re-implements/pre-empts
public protocol behaviour (a protocol leak that bypasses the negotiated, backend-overridable
interface) or hides a design gap behind an unexposed shortcut; the fix belongs in the public
protocol or in construction, never in a private helper.

**Why / harm:** a private render helper silently forks behaviour — core renders one way, a backend
unaware of the helper renders another, no protocol test catches the divergence. It becomes a
hidden second protocol; later work duplicates it (drift) or "fixes" it per-backend
(fragmentation). The urge to add a private function is a reliable signal the public protocol is
missing a deliberate capability — hiding it guarantees the gap festers.

### Backend Protocol Changes Require Extreme Restraint, Deep Deliberation, Broad Research

The backend protocol is a **shared contract implicated across every backend** (core + all
extension backends). Changing any part of it is a large, cross-cutting project. **Before touching
backend protocol: (1) broadly research every backend's implementation/tests and validate against
real servers; (2) deliberate — ensure the change is minimal, generic, and composes with every
existing `format_*()`/`supports_*()`/expression contract; (3) negotiate, then implement across
the generic layer and every backend together, keeping behaviour identical everywhere.**

**Why / harm:** the protocol is the system's nervous system — every backend dials into the same
seams. A hasty protocol change (e.g. inventing a new render helper, parameterizing
`to_sql()`/`format_*()`) commits every backend to behaviour that was never surveyed; backends
drift as each "fixes" it differently; the shared contract fractures and forces costly retrofits.
**This is exactly what repeatedly poisoned
the abandoned DDL-derivation work** (`ddl_inline`, `inline_params`, string-sniffing, invented
render helpers) — each was a protocol shortcut with catastrophic cross-backend cost.

### Formatting Is Pure Concatenation — Never Touch or Scan the SQL String

Backend expressions and formatting functions build SQL by **simple concatenation** of fragments:
identifiers (via `format_identifier`), literal atoms (via `format_literal`), placeholders, and
pre-rendered sub-fragment SQL. They **must never inspect, parse, scan, or rewrite the SQL string
itself** — no `startswith`/`endswith`/`in` checks on generated SQL, no regex matching, no
character-by-character scanning, no quote-state machines, no post-hoc placeholder substitution.

**Why / harm:** generated SQL is the *output* of formatting, not its input — logic that reads it
is a second, unreliable parse of data the formatter already had as typed values. String scanning
of SQL is also an injection surface: a mismatch between scanner assumptions and real dialect
syntax silently corrupts the statement.

**The single exception — inline-literal resolution.** When a statement
(`requires_inline_literals() == True`, trusted developer-declared DDL) renders literal values
inline, the dialect's `format_literal` produces **escaped, quoted atoms** concatenated directly
during formatting — no re-scanning of the assembled SQL. Because this exception splices raw
values into SQL text, it is a **SQL-injection hazard by nature**: developers must be highly
alert that inline content is trusted-only and never reachable by end users, and the inline
switch must default to `False` (bind parameters).

## Type Adaptation

Two-part: define `SQLTypeAdapter`s, then register them and expose suggestions.

```python
# adapters: subclass BaseSQLTypeAdapter; implement _do_to_database / _do_from_database
# backend registration:
def _register_my_adapters(self):
    for adapter in (DateTimeAdapter(), DecimalAdapter(), MyCustomJSONAdapter()):
        for py_type, driver_types in adapter.supported_types.items():
            for driver_type in driver_types:
                self.adapter_registry.register(adapter, py_type, driver_type, allow_override=True)

def get_default_adapter_suggestions(self):
    # e.g. datetime->str, Decimal->str, dict->str via adapter_registry.get_adapter(...)
```

## Transaction Management

```python
class MyTransactionManager:
    @contextmanager
    def transaction(self, isolation_level=None):
        self.connection.begin()
        try:
            yield self
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    @contextmanager
    def savepoint(self, name=None):
        # SAVEPOINT / RELEASE / ROLLBACK TO SAVEPOINT
        ...
```

## Error Handling

Map driver exceptions to core `DatabaseError` subclasses (`IntegrityError`, `ConnectionError`, ...):

```python
def _handle_error(self, error):
    if isinstance(error, native_driver.UniqueConstraintViolation):
        raise IntegrityError("Unique constraint failed") from error
    if isinstance(error, native_driver.CannotConnectNow):
        raise ConnectionError("Connection failed") from error
    raise DatabaseError(f"Unexpected database error: {error}") from error
```

## Asynchronous Backends

`AsyncStorageBackend` must provide **functional equivalence** with the sync `StorageBackend`:
implement async versions of all I/O-bound methods (`async def connect(...)`, `async def
execute(...)`) and use async-compatible mixins.

## Testing Requirements

- Connection & configuration (success, disconnect, ping, bad-config failure modes)
- CRUD & query execution (`execute`, `fetch_one`, `fetch_all`, ...)
- Type adaptation: unit tests per adapter + `get_default_adapter_suggestions` + end-to-end save/retrieve
- Transaction: commit, rollback, savepoints
- Dialect & SQL formatting: `LIMIT`/`OFFSET`, `RETURNING`, ...
- Error handling mapping
- Expression formatting integration tests

## Release Readiness

1. Comprehensive backend test suite
2. Pass the official `rhosocial-activerecord-testsuite`
3. CI pipeline across Python versions (see `.github/workflows/` in the main project)

## Checklist

Required implementation: all `StorageBackend` abstract methods; config class; SQL dialect; full
type adaptation system (adapters + registration + suggestions); transaction management; error
handling; feature detection/capabilities; async functional equivalence if providing async.
Required tests: everything in Testing Requirements. Release: tests green, testsuite compliant, CI set up.