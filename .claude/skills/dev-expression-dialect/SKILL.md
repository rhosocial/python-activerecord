---
name: dev-expression-dialect
description: Architecture guide for the Expression-Dialect separation system in rhosocial-activerecord - expression modules, dialect protocols/mixins, SQL generation rules, and how to add new protocols
license: MIT
compatibility: opencode
metadata:
  category: architecture
  level: advanced
  audience: developers
---

# Expression-Dialect System

Explains the architecture that separates SQL **query construction** (expressions) from SQL
**generation** (dialects), enabling database-agnostic building with per-database formatting.

## Core Principle

**Expression defines structure. Dialect generates SQL.**

```
Query (ActiveQuery)
  ↓
Expression (SQLColumn)      ← calls dialect.format_*()
  ↓
Dialect (SQLiteDialect)     ← generates SQL
  ↓
Backend (StorageBackend)
```

## Golden Rule

**NEVER** concatenate SQL strings in Expression classes:
```python
# WRONG
return f'"{table}"."{column}"'

# CORRECT
return self.dialect.format_column_reference(table, column)
```

## Backend Boundary Rule

**ActiveRecord is the user of the backend; the backend never knows ActiveRecord exists.** The
dialect/expression layer describes **generic SQL and the concrete capabilities of the target
database** — it is never a description of, or servant to, the ActiveRecord layer above it.
Consequently ActiveRecord must adapt to the backend: it consumes whatever protocol/interface the
backend provides. If ActiveRecord needs a feature that requires backend cooperation, the feature
must be **negotiated as a protocol/interface contract** on the backend's own generic terms — never
by bending the backend's design to fit ActiveRecord.

Forbidden (all absolutely wrong):
- Adding ActiveRecord-serving helpers to the dialect, e.g. `ddl_inline`, `inline_params`, or any
  parameter-inlining / SQL-rewriting machinery whose only purpose is to support an ActiveRecord
  DDL feature.
- Making the dialect infer intent from **string characteristics** (regex matches, prefix/suffix
  checks, statement-type sniffing from leading keywords, etc.). The dialect never interprets SQL
  text to guess what a caller meant.

## The Only Expression Semantics Are `to_sql()` and `dialect.format_*()`

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

**No private functions in backend protocol/implementation — everything is transparent.** The
backend needs no private helper functions (no `_render_*`, no internal `_format_*` / recursion
helpers). All behaviour is reachable through the public surface: `to_sql()` on expressions,
`format_*()` / `supports_*()` on the dialect, the expression/statement classes, the type adapters.
**If you feel the urge to add a private function, you are doing something wrong — stop.** A private
function either re-implements / pre-empts public protocol behaviour (a protocol leak that bypasses
the negotiated, backend-overridable interface) or hides a design gap behind an unexposed shortcut.
The fix belongs in the public protocol (or in how expressions are **constructed**), never in a
private helper.

**Why this rule exists:** the backend's power comes from a *known, negotiated* public surface —
backends override public `format_*()`/`supports_*()`, expressions and callers consume public
`to_sql()`. A private helper is invisible to that contract: it can't be overridden by a backend
that needs different behaviour, isn't covered by protocol tests, and hides where behaviour lives.
**What happens if you break it (harm):** a private render helper silently forks behaviour — core
renders one way, a backend unaware of the helper renders another, no protocol test catches the
divergence. The helper becomes a hidden second protocol; later work duplicates it (drift) or
"fixes" it per-backend (fragmentation). The urge to add a private function is a reliable signal
the public protocol is missing a deliberate capability — hiding it guarantees the gap festers.

## Backend Protocol Changes Require Extreme Restraint, Deep Deliberation, Broad Research

The backend protocol is a **shared contract implicated across every backend** (core + all
extension backends). Changing any part of it is a large, cross-cutting project. **Before touching
backend protocol: (1) broadly research every backend's implementation/tests and validate against
real servers; (2) deliberate — ensure the change is minimal, generic, and composes with every
existing `format_*()`/`supports_*()`/expression contract; (3) negotiate, then implement across
the generic layer and every backend together, keeping behaviour identical everywhere.**

**Why:** the protocol is the system's nervous system — every backend dials into the same seams
(`to_sql()`, `format_*()`, `supports_*()`, expression/statement classes). A hasty protocol change
(e.g. inventing a new render helper, parameterizing `to_sql()`/`format_*()`) commits every backend
to behaviour that was never surveyed; backends drift as each "fixes" it differently; the shared
contract fractures and forces costly retrofits. **This is exactly what repeatedly poisoned the
abandoned DDL-derivation work** (`ddl_inline`, `inline_params`, string-sniffing, invented render
helpers) — each was a protocol shortcut with catastrophic cross-backend cost.

## Formatting Is Pure Concatenation — Never Touch or Scan the SQL String

Backend expressions and formatting functions build SQL by **simple concatenation** of fragments:
identifiers (via `format_identifier`), literal atoms (via `format_literal`), placeholders, and
pre-rendered sub-fragment SQL. They **must never inspect, parse, scan, or rewrite the SQL string
itself** — no `startswith`/`endswith`/`in` checks on generated SQL, no regex matching, no
character-by-character scanning, no quote-state machines, no post-hoc placeholder substitution.

**Why:** generated SQL is the *output* of formatting, not its input. Logic that reads the
generated string is guessing at structure the formatter already knew as typed data at
construction time — a second, unreliable parse. String scanning of SQL is also an injection
surface: any mismatch between the scanner's assumptions and the real dialect syntax silently
corrupts the statement.

**The single exception — inline-literal resolution.** When a statement
(`requires_inline_literals() == True`, trusted developer-declared DDL) renders literal values
inline, the dialect's `format_literal` produces **escaped, quoted atoms** concatenated directly
during formatting — no re-scanning of the assembled SQL. Because this exception splices raw
values into SQL text, it is a **SQL-injection hazard by nature**: developers must be highly
alert that inline content is trusted-only and never reachable by end users, and the inline
switch must default to `False` (bind parameters).

**What happens if you break it (harm):** a placeholder scanner mis-fires on `?` appearing inside
string literals, breaks when a dialect's quoting/placeholder syntax differs, and duplicates
knowledge the formatter already had — solving a problem pure concatenation never creates.

## Advantages Over Other Approaches

- No complex state management — expressions are stateless and pure
- Only 2 steps from expression to SQL; no multi-layer compilation
- Dummy backend is a complete SQL-standard reference; other dialects only override differences
- Test-friendly — SQL generation testable without a database connection
- Fragment generation — any expression can generate SQL independently
- Explicit control — full visibility into when database operations occur

## Relationship Model

```
Expression.to_sql() -> Dialect.format_*() -> SQL string and parameters
```

## Key Components

1. **Expression formatting**: `BaseExpression` subclasses build query structure and delegate
   formatting to dialect methods.
2. **Type adaptation**: plain Python values passed as parameters (e.g. `datetime` in WHERE) are
   converted by the **backend** via `SQLTypeAdapter` (see `dev-backend-development`).

## Expression System Modules

Located under `backend/expression/`:
- `bases.py` — abstract base classes and protocol definitions
- `core.py` — core components (columns, literals, function calls, subqueries)
- `literals.py` — literal value expressions
- `executable.py` — executable statement expressions
- `mixins.py` — operator-overloading capabilities (incl. `AliasableMixin.as_`)
- `operators.py` — binary/unary/arithmetic expressions
- `predicates.py` — WHERE-clause predicates
- `query_parts.py` — query clauses (WHERE, GROUP BY, HAVING, ORDER BY, ...)
- `statements/` — DML/DQL/DDL statements (directory package: `ddl_*`, `dml`, `dql`, `explain`)
- `functions/` — standalone factory functions (directory package)
- `aggregates.py` — aggregation expressions/functions
- `advanced_functions.py` — CASE, CAST, EXISTS, window functions
- `query_sources.py` — VALUES, table functions, CTEs
- `graph.py` — Graph Query (MATCH)
- Additional: `collation.py`, `datetime.py`, `serialization.py`, `transaction.py`,
  `introspection.py`, `xml.py`, `types/`

**Limitation**: the system builds SQL per user intent but does **not** validate standard
compliance or executability — that is the database engine's responsibility.

## Dialect Protocol-Mixin Architecture

- **Protocols** (`protocols.py`): interface contract — what a dialect must implement.
- **Mixins** (`mixins.py`): default SQL-standard implementations dialects can override.
- Every dialect inherits: `SQLDialectBase` + relevant Mixins + relevant Protocols.

### Current Protocols and Mixins (main package)

| Protocol | Mixin | Feature |
|----------|-------|---------|
| `WindowFunctionSupport` | `WindowFunctionMixin` | Window functions (OVER, PARTITION BY) |
| `CTESupport` | `CTEMixin` | CTEs (WITH clause) |
| `AdvancedGroupingSupport` | `AdvancedGroupingMixin` | ROLLUP, CUBE, GROUPING SETS |
| `ReturningSupport` | `ReturningMixin` | RETURNING clause |
| `UpsertSupport` | `UpsertMixin` | UPSERT (ON CONFLICT) |
| `LateralJoinSupport` | `LateralJoinMixin` | LATERAL joins |
| `ArraySupport` | `ArrayMixin` | Array types/operations |
| `JSONSupport` | `JSONMixin` | JSON types/operations |
| `ExplainSupport` | `ExplainMixin` | EXPLAIN |
| `FilterClauseSupport` | `FilterClauseMixin` | FILTER clause |
| `OrderedSetAggregationSupport` | `OrderedSetAggregationMixin` | WITHIN GROUP (ORDER BY) |
| `MergeSupport` | `MergeMixin` | MERGE |
| `TemporalTableSupport` | `TemporalTableMixin` | FOR SYSTEM_TIME |
| `QualifyClauseSupport` | `QualifyClauseMixin` | QUALIFY |
| `LockingSupport` | `LockingMixin` | FOR UPDATE, SKIP LOCKED |
| `GraphSupport` | `GraphMixin` | Graph queries (MATCH) |
| `JoinSupport` | `JoinMixin` | JOIN operations |
| `SetOperationSupport` | `SetOperationMixin` | UNION, INTERSECT, EXCEPT |
| `ILIKESupport` | `ILIKEMixin` | Case-insensitive LIKE |
| `TableSupport` | `TableMixin` | CREATE/DROP/ALTER TABLE |
| `ViewSupport` | `ViewMixin` | CREATE/DROP VIEW |
| `TruncateSupport` | `TruncateMixin` | TRUNCATE TABLE |
| `SchemaSupport` | `SchemaMixin` | CREATE/DROP SCHEMA |
| `IndexSupport` | `IndexMixin` | CREATE/DROP INDEX |
| `SequenceSupport` | `SequenceMixin` | CREATE/DROP/ALTER SEQUENCE |
| `TriggerSupport` | `TriggerMixin` | CREATE/DROP TRIGGER (SQL:1999) |
| `FunctionSupport` | `FunctionMixin` | CREATE/DROP FUNCTION (SQL/PSM) |

### Where to Add Features — Generic vs Concrete (Decision Rule)

**The goal is for the generic (core) layer to implement as much as possible, to minimise backend
work.** Decide placement by how *broad* a feature's base is:

1. **Has broad base across databases → lift to the generic layer.** The feature exists (with
   standard semantics) in many databases. Add: a `XxxSupport` protocol, a `XxxMixin` with the
   generic implementation, and `supports_xxx()` capability detection. Backends simply compose the
   pair and inherit the generic behaviour.
2. **No broad base (e.g. table partitioning, vendor-proprietary features) → each backend
   implements its own**, and **prefixes its classes with the backend name**
   (`MySQLRangePartition`, `PostgresRangePartition`, `OracleListPartition`, …). The core provides
   at most an empty marker base (`PartitionSpec`); each backend claims its own via `build_spec`
   / `isinstance`. There is no core "generic" implementation for a non-generic feature.
3. **If a generic-layer expression is supported but its generic implementation does not fit a
   concrete backend's needs, that backend simply overrides the affected method(s)** — this is
   the "Override Discipline (Generic-First)" rule below. Overriding is the escape hatch for
   correctness; it is not a reason to avoid lifting broadly-shared features to the core.

Placement summary (same as the table above, restated as a rule):

- **Main package** when: defined in SQL standard (SQL:1999–2016); widely supported across DBs; a
  DDL or DML construct.
- **Dialect extension** when: dialect-specific; differs across databases; vendor-proprietary.

Examples: `CREATE TRIGGER`/`CREATE FUNCTION` → main package; `COMMENT ON`, `CREATE TYPE ...
AS ENUM`, `BIGSERIAL` → PostgreSQL; `AUTO_INCREMENT` → MySQL; RANGE/LIST/HASH partitioning →
backend-specific (each backend names and implements its own partition classes).

### Adding a New Protocol

```python
# 1. main package protocols.py
@runtime_checkable
class NewFeatureSupport(Protocol):
    def supports_new_feature(self) -> bool: ...
    def format_new_feature_statement(self, expr): ...

# 2. main package mixins.py — generic implementation; the supports_* default
#    must represent the COMMON behaviour across databases (usually False for
#    non-universal features, True for near-universal ones like auto-increment)
class NewFeatureMixin:
    def supports_new_feature(self): return False
    def format_new_feature_statement(self, expr): ...

# 3. concrete dialects: compose the pair; override ONLY methods whose real
#    capability/behaviour differs from the generic implementation

# 4. dummy dialect: compose NewFeatureMixin/NewFeatureSupport and override
#    supports_* to True only where the generic default is not already True

# 5. tests: tests/.../dummy2/test_new_feature.py (expression),
#    tests/.../dummy/test_dummy_protocol_support.py (protocol support)
```

### Override Discipline (Generic-First)

Generic mixins implement the standard/common behaviour **once**. A concrete
dialect composes a Support/Mixin pair and inherits that behaviour untouched;
it overrides a method **only when its real capability differs from the
generic implementation**. Never re-declare a method just to return the same
value the mixin already provides.

Rationale:
- Concrete backends stay minimal — no boilerplate restating standard behaviour.
- The overrides in `{backend}/dialect.py` read as an exact diff against the
  generic implementation, so backends can be compared at a glance.
- Enforcement lives in `tests/.../dummy/test_dummy_protocol_member_completeness.py`
  (every protocol method must exist on `DummyDialect`) plus per-feature tests
  asserting `"method_name" not in ConcreteDialect.__dict__` for dialects that
  match the generic behaviour.

Example: `AutoIncrementMixin.supports_auto_increment()` defaults to `True`
(nearly all databases generate keys server-side). SQLite and the dummy
dialect simply compose the pair with zero overrides; ClickHouse alone
overrides it to `False`, which documents its deviation.

## The Dummy Dialect: Generic Reference and Test Vehicle

`backend/impl/dummy/dialect.py` (`DummyDialect`) is the SQL-standard
reference dialect and the vehicle for testing everything that does not
require a real database connection.

**Scope — compose (almost) everything:**

- Compose every generic `XxxSupport`/`XxxMixin` pair, so each protocol's
  code path is reachable in tests without a database.
- The only exclusions are capabilities that inherently need a real server:
  introspection is composed but every `supports_introspection*()` returns
  `False`; backend-specific data types are not modelled (core types get
  standard formatters via `DDLTypeMixin.handles(...)` for expression
  `to_sql()` testing).

**Behaviour — switches fully on:**

- Every feature-detection method returns `True`, either inherited from the
  generic mixin or overridden where the generic default differs. Dummy is a
  *reference switchboard*, not a simulation of any real product.

**Enforcement:**

- `tests/.../dummy/test_dummy_protocol_member_completeness.py` dynamically
  discovers every Protocol in `protocols.py` (excluding only
  `IntrospectionSupport`) and fails unless `DummyDialect` composes it and
  implements all of its members.

**Test organization — indirect coverage of the generic layer:**

- `tests/.../feature/backend/dummy/` — protocol support surface: every
  `supports_*()` verified `True`, plus member-completeness enforcement.
- `tests/.../feature/backend/dummy2/` — expression `to_sql()` generation:
  exercises the generic Expression classes through the dummy dialect's
  standard formatting, i.e. tests generic expressions, protocols, and
  mixin implementations indirectly, with no database involved.

When you add a protocol/mixin pair (see "Adding a New Protocol"), extending
both directories is part of the definition of done.

## Why This Matters

1. Backend agnostic — same expressions work with any database
2. SQL injection safe — centralized escaping
3. Extensible — new backend = new dialect only
4. Testable — structure and SQL tested separately

## Testing

- Expressions: verify structure, not SQL
- Dialects: verify correct SQL generation