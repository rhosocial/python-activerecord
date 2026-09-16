# Distinguishing Features Not Found in Other ORMs

This document catalogs the capabilities that are **unique to
rhosocial-activerecord and available in no other Python ORM** (SQLAlchemy,
Django ORM, SQLModel, Peewee, Tortoise ORM, Prisma Client Python, and
beyond). These are not "we do it slightly better" features — they are
architectural capabilities with no counterpart elsewhere.

> **Note**: Capabilities marked below are verified absent from all
> mainstream competitors. Where a competitor offers something *similar* in
> spirit, the difference is explicitly called out so the claim stays
> defensible.

### Cross-cutting principle: fail fast

A single design principle runs through every capability in this document
and, more broadly, through the entire software: **fail fast**. When a
database does not actually provide a feature, or when two backends differ
in a way that cannot be expressed losslessly, rhosocial-activerecord
refuses to proceed — it raises an explicit error (`UnsupportedFeatureError`,
`DatabaseError`, etc.) rather than silently emulating semantics the backend
does not provide. This "honest semantics, never emulation" stance is what
makes the capability declaration system trustworthy and is the design
backbone shared by the features below.

---

## 1. Expression–Dialect System: the Construction Guarantee

Underpinning every other capability in this document is the way
rhosocial-activerecord constructs SQL. SQL is represented as a **tree of
expression objects**, and rendering that tree into text is a **pure
read** — the SQL string is assembled by simple concatenation with **no
post-processing whatsoever** (no regex matching/replacement, no
`startswith`/`endswith`/`contains` inspection of the produced text).

The guarantee is structural, not procedural:

```python
# Every expression participates by declaring exactly ONE thing:
# the name of the dialect method that renders it.
@property
def format_method(self) -> str:
    return "format_cte_expression"   # e.g. CTEQuery declares this
```

`BaseExpression.to_sql()` is implemented **once, at the root** and is the
only rendering entry point. A concrete expression class never overrides it.
Rendering resolves the declared `format_method` on the node's own bound
dialect and hands **this** expression to the formatter — no re-instantiation,
no copies, and the `dialect` setter affects only the node it is set on
(binding is per-node, done at construction or individually re-bound):

```python
SQLQueryAndParams = Tuple[str, tuple]
# (sql_text, parameter_values)   — placeholders stay in the text,
# values travel separately, in DB-API 2.0 (PEP 249) paramstyle order.
```

Three properties follow directly from this design:

1. **Values never touch SQL text.** By default `inline_literals=False`, so
   literals render as bind-parameter placeholders (`?`, or `%s`/`$1` etc.
   per-dialect via `get_parameter_placeholder()`), and values are carried in
   the separate tuple. Inline rendering is an explicit, opt-in,
   security-relevant choice reserved for fully developer-declared content
   (e.g. derived DDL).
2. **No blind spots.** A dialect is either able to render an expression (it
   provides the required `format_*` method) or it is not — the failure is
   immediate (`AttributeError` / `UnsupportedFeatureError`), never a
   half-correct string. Combined with `validate()` and the capability
   protocols (§2), every constructible tree either renders correctly or
   refuses.
3. **Portable yet honest.** The same tree renders across relational
   databases *and* their versions, because rendering is delegated to the
   dialect's own `format_*` methods and dialect mixins — each backend
   expresses exactly the SQL it actually supports, never a lowest-common-
   denominator approximation.

### Why no competitor has this

- **SQLAlchemy** compiles to an internal AST but its escape hatches
  (`text()`, `literal_column()`) and the breadth of its dialect layer invite
  string-based SQL; there is no single, structural "tree render + separated
  params" guarantee enforced by construction.
- **Django / Peewee / Tortoise ORM** assemble SQL by progressively
  concatenating strings (Peewee notably post-processes placeholders), which
  is exactly the class of approach that requires "second-pass" string work.
- **Prisma** builds queries in a closed Rust engine — safe, but the AST is
  neither introspectable nor extensible from Python, so the "what SQL is
  actually produced" reasoning is opaque to the application.

In short, competitors achieve *some* of safety, *some* completeness, or
*some* portability; the Expression–Dialect system achieves all three from
one structural guarantee.

---

## 2. Capability Declaration Protocol System

Each SQL feature a database may (or may not) support — window functions,
CTEs, triggers, XML, JSON, GRAPH, MERGE, QUALIFY, temporal tables,
partitioning, sequences, generated columns, introspection, and ~35 more —
is described by a dedicated **`Support` protocol** on the dialect.

```python
from rhosocial.activerecord.backend.dialect.protocols import CTESupport

@runtime_checkable
class CTESupport(Protocol):
    def supports_basic_cte(self) -> bool: ...
    def supports_recursive_cte(self) -> bool: ...
    def supports_materialized_cte(self) -> bool: ...
```

A dialect *declares* what it supports, and every feature gate is resolved
at runtime through `isinstance(dialect, SomeSupport)`-style detection.
Unsupported features fail fast with an explicit `UnsupportedFeatureError`
instead of silently compiling wrong SQL or emulating semantics the
database does not actually provide.

### Why no competitor has this

- **SQLAlchemy** dialects translate syntax, but feature availability is
  implicit: whether a feature works on a given backend/version is the
  developer's burden to know, and mis-usage fails only at execution time.
- **Django ORM / Peewee / Tortoise ORM** offer a fixed feature surface;
  database-specific gaps surface as runtime errors or silent truncation
  rather than a declared capability matrix.
- **Prisma** centralizes this in its Rust query engine, but the
  declaration is closed and language-bound, not an extensible protocol
  the application can inspect and extend.

### What the declaration buys you

- **Granular, version-aware gating** — e.g. MySQL window functions are
  declared from 8.0 onward, so tests and code adapt automatically.
- **Graceful test skipping** — capability-aware test helpers skip
  unsupported features instead of failing.
- **Honest non-relational backends** — analytical engines (ClickHouse,
  Snowflake, BigQuery) *declare* the relational guarantees they do **not**
  provide and fail fast, rather than pretending to be a row-store OLTP
  engine.
- **Self-documenting dialects** — the capability declaration doubles as
  the backend's feature documentation.

---

## 3. Named Resource Family (the "Named" System)

A cohesive system that turns configuration and logic into **discoverable,
referencable, CLI-invocable named resources**. Three pillars, all using
fully-qualified names and sharing the same resolution model:

### 3.1 Named Connections (`NamedConnectionResolver`)

Database connections defined as ordinary Python callables, resolved by
qualified name at runtime:

```python
# myapp/connections.py
def production_db(pool_size: int = 10):
    """Production database configuration."""
    return MySQLConnectionConfig(host="prod.example.com", pool_size=pool_size)
```

```bash
# Resolve and use from the CLI, explicit params override named values
prog --named-connection myapp.connections.production_db --param pool_size=20
```

### 3.2 Named Expressions & Queries (`Procedure`, `ProcedureGraph`)

Named queries/expressions that can be orchestrated into executable
procedures — either imperatively or as a declared **DAG**:

```python
class MonthlyReportProcedure(Procedure):
    month: str              # required parameter
    threshold: int = 100    # optional with default

    def run(self, ctx: ProcedureContext) -> None:
        ctx.execute("myapp.queries.orders.monthly_summary",
                    params={"month": self.month}, bind="summary")
        total = ctx.scalar("summary", "total_count")
        if total < self.threshold:
            ctx.log(f"Total {total} below threshold"); return
        for row in ctx.rows("summary"):
            ctx.execute("myapp.queries.archive.insert_record",
                        params={"order_id": row["id"], "month": self.month})
```

The **`ProcedureGraph`** form separates structure ("what") from execution
("how") and adds unique properties:

- **Pure-data DAG** — `StepNode` steps with explicit dependencies, no I/O
  in the graph itself.
- **Single definition, dual execution** — the same graph runs via either a
  sync or async runner.
- **Automatic parallelism** — the runner identifies independent steps and
  runs them concurrently.
- **Visualization** — a `diagram` module renders the graph.

### 3.3 Named Migrations (`NamedMigration`)

Migrations as named, versioned classes with explicit dependencies,
UP/DOWN directions, dry-run, and a dialect-validation hook — exposed
through the backend CLI alongside the other named resources.

### Why no competitor has this

- **SQLAlchemy** (via Alembic) has migrations, but no named-connection or
  named-query/procedure system; queries are inline code, not discoverable
  named resources.
- **Django ORM** has named-nothing at this level; migrations are
  auto-generated, connections are settings-driven, and there is no
  procedure/DAG orchestration.
- **SQLModel / Peewee / Tortoise ORM** provide none of the three pillars.
- **Prisma**'s schema is declarative, but its "naming" is confined to the
  DSL; there is no named-connection or executable procedure graph.

---

## 4. Resident Worker Pool with Pluggable Scheduling

A first-class, spawn-based **resident process pool** — not a thread pool
or an async task runner — that stays alive across tasks and manages
graceful teardown in three phases (`DRAINING → STOPPING → KILLING →
STOPPED`).

```python
from rhosocial.activerecord.worker import WorkerPool, LeastTasksStrategy

pool = WorkerPool(
    target=my_worker_entry,
    num_workers=4,
    strategy=LeastTasksStrategy(),
)
pool.start()
# tasks dispatched via queue, scheduling governed by the chosen strategy
pool.stop()  # graceful: DRAINING → STOPPING → KILLING → STOPPED
```

Scheduling is a **pluggable strategy** interface with built-in policies:
`LeastTasks`, `RoundRobin`, and `Random`.

### Why no competitor has this

- ORMs uniformly treat *connection/pooling* as their concurrency surface
  (or delegate it entirely to the driver/application). **None** ship a
  resident multi-process worker pool as part of the ORM's own feature set.
- This is a deliberate consequence of rhosocial-activerecord's
  architecture — *process isolation* instead of connection pooling for
  concurrent scenarios — which no other Python ORM adopts as a
  first-class pattern, let alone with pluggable scheduling and phased
  graceful shutdown.

---

## 5. Built-in Backend CLI Tooling

Every backend ships its own command-line tool, invocable as
`python -m rhosocial.activerecord.backend.impl.<backend>`, with a
consistent set of subcommands:

| Subcommand | Purpose |
|------------|---------|
| `query` | Execute SQL / queries directly against the backend |
| `introspect` | Inspect tables, views, columns, indexes, foreign keys, triggers, database |
| `status` | Server status overview (config / performance / storage / databases) |
| `info` | Version and capability information |
| `named-connection` / `named-expression` / `named-procedure` / `named-procedure-graph` / `named-migration` | Operations over the Named Resource Family |

A shared `output` abstraction renders results uniformly as
`table` / `json` / `csv` / `tsv` (with optional Rich-formatted output).

### Why it matters

- **Operational surface in the backend itself** — the backend package alone
  yields a database operational tool; no application layer or separate
  devtools installation is required.
- **Wired into the Named Resource Family** — connection, expression,
  procedure, and migration commands are the same named resources usable
  programmatically and across DAG orchestration.
- **Uniform output across heterogeneous backends** — the same output
  formats and status categories across SQLite, MySQL, MariaDB, PostgreSQL,
  SQL Server, Oracle, Firebird, ClickHouse, etc.

### Why no competitor has this

- **SQLAlchemy, Peewee, Tortoise ORM, SQLModel** ship no `__main__`
  operational CLI of their own.
- **Django's** `manage.py dbshell` merely delegates to the native client; it
  performs no introspection or status reporting itself.
- **Prisma's** CLI is a code-generation/migration tool for its DSL, not a
  database operational surface unified with an ORM naming system.

> This is best understood as an extension of the Named Resource Family
> (§3) and of backend independence (§2): the CLI is the *operational
> front-end* of the same capabilities.

---

## 6. Derived DDL, DDL Locking, and Version Diffing (roadmap)

Under active development, this capability group aims to give
rhosocial-activerecord a fourth migration paradigm, distinct from the three
the industry currently offers. Its building blocks already exist in the
backend (`schema/`, `expression/statements/ddl_*.py`, and the `ddl_*`
dialect mixins).

### The vision

1. **Derive DDL from ActiveRecord classes** — the model is the source of
   truth; DDL is a *derived artifact*, rendered per-backend.
2. **Cross-backend yet honest** — derivation targets several backends at
   once, but respects each backend's real feature surface through the
   capability declaration system (§2); where a difference cannot be
   expressed losslessly, it fails fast rather than emulating.
3. **DDL locking per release** — lock each version's DDL before release,
   treating DDL as a versioned artifact like code.
4. **Version-to-version diffing** — compare locked DDL versions and produce
   **executable expression instances** (e.g. `ALTER TABLE` swap/rename
   expressions), not human-readable text diffs.

### Why it is a fourth paradigm

| Approach | Representative | DDL derivation | Lockable snapshot | Diff output |
|----------|----------------|----------------|-------------------|-------------|
| Auto-detection | Django ORM | Strong, DB-comparison driven | No (linear history) | Human-readable |
| Hand-written scripts | Alembic (SQLAlchemy) | Weak (autogenerate is auxiliary) | No | N/A |
| Schema-first DSL | Prisma | From DSL | Migration history | Text diff (`migrate diff`) |
| **Derive + lock + diff** | **rhosocial-activerecord (planned)** | **Strong (Python types)** | **Yes (versioned DDL)** | **Executable expressions** |

### Why no competitor has this

- **Django** derives DDL but treats the model as the only truth; DDL is a
  side effect, not a lockable, diffable, versioned artifact.
- **Alembic** requires hand-written revisions; `/autogenerate` only assists,
  and there is no versioned DDL snapshot to diff.
- **Prisma's** `migrate diff` is the closest in spirit, but it is anchored to
  a DSL and its own query engine, cannot connect to the Python type system,
  and produces text diffs rather than reusable expression instances.

### Why the pieces reinforce each other

This is not an isolated feature. It composes three capabilities that are
already unique to rhosocial-activerecord:

- **Capability Declaration Protocols (§2)** drive honest cross-backend DDL
  rendering.
- **The Expression–Dialect system (§1)** turns diffs into reusable,
  re-serializable expression instances rather than dead text.
- **The Named Resource Family (§3)** lets those expression instances be
  orchestrated as named migrations / procedures / DAG steps.

> **Status**: this group is **in development** and not yet released. It is
> listed here to make the roadmap's rationale explicit and is grounded in
> the "fail fast, never emulate" principle that already governs the shipped
> features.

---

## Summary

| Unique Capability | Counterpart in any other ORM |
|-------------------|------------------------------|
| Expression–Dialect System (tree rendering + separated params, no post-processing) | ❌ None — competitors post-process strings or hide the AST |
| Capability Declaration Protocol System (~40 `Support` protocols) | ❌ None — others rely on implicit dialect behavior |
| Named Resource Family (connections / expressions / migrations) | ❌ None — no equivalent naming + DAG orchestration + CLI |
| Resident Worker Pool + Pluggable Scheduling | ❌ None — no ORM ships a process pool as a first-class feature |
| Built-in Backend CLI Tooling | ❌ None — no ORM ships a unified operational CLI |
| Derived DDL + DDL Locking + Version Diffing | ❌ None (roadmap) — a fourth migration paradigm |