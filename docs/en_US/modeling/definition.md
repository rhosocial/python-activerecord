# The ActiveRecord Definition

> This is the **authoritative reference** for how `rhosocial-activerecord` defines a model:
> a complete, accurate capability matrix of the declaration surface. It is **not** a tutorial —
> for how to use each capability, follow the pointers in [Section 6](#6-where-to-go-next).
>
> Scope and status: this page reflects the **current state** of the code, including boundaries
> and capabilities that are not yet implemented (see [Section 4](#4-current-boundaries--not-yet-implemented)).

---

## 0. At a glance

A model is defined in four layers. Each layer has one job, and the layers never cross:

```text
1. Annotations (Annotated[T, ...])   — say WHAT the model declares
        ↓
2. DDLSource                          — reads WHAT was declared (24 methods, dialect-free)
        ↓
3. derivation (build_*_statement)     — turns declarations into generic statement expressions
        ↓
4. migration (MigrationMixin / @migration / Runner) — executes or previews those statements
```

**The governing rule:** a declaration answers only *"what does the model declare?"* It never builds
SQL, never binds a dialect, never executes anything. Dialect binding and capability gating belong
to the consumers in layers 3 and 4.

Behavior mixins (timestamps, soft delete, optimistic locking, …) sit alongside this pipeline: they
change model *behavior* and, in their `Default*` forms, inject the columns the pipeline sees.

> **Backend integration boundary**: This four-layer pipeline is also where ActiveRecord hands
> declarations off to a backend. Dialect binding and capability gating happen at that handoff, in
> layers 3 and 4. All examples in this document use the built-in SQLite backend; other backends
> are documented separately.
>
> 💡 **AI Prompt**: "Using the built-in SQLite backend, explain where ActiveRecord hands model
> declarations off to the backend in this four-layer pipeline, and what each layer is responsible
> for before that handoff."

---

## 1. Capability matrix

### 1.1 Field annotations

Declared inside `typing.Annotated[T, ...]`. "In DDL?" means the declaration influences generated
DDL (column names, types, constraints, indexes, comments). Markers with **No** affect runtime
behavior or query expressions only.

> **Backend integration boundary**: Markers such as `UseSqlType`, `UseConstraint`, and
> `UseColumnAttributes` are the points where a backend plugs into the declaration surface — for
> example, SQLite renders them into its own SQL types, constraints, and attributes. All examples
> here use SQLite; other backends are documented separately.
>
> 💡 **AI Prompt**: "With `UseSqlType` on an `Annotated` field, explain how 'first renderable wins'
> works with the built-in SQLite backend. Show several ordered `DataType` candidates and how
> SQLite determines which one it can render into a column type."

| Annotation | Declares | In DDL? | Consumed by |
|---|---|---|---|
| `DDLAnnotation` | Common base for DDL markers; backend-owned markers must subclass it and register a handler | base only | `DDLFieldMetadata` |
| `UseSqlType` | Ordered SQL `DataType` candidates for **storage** (first renderable wins) | Yes | storage-type derivation |
| `UseConstraint` | A column constraint branch, or a table-level UNIQUE/FOREIGN KEY when `columns=` is given | Yes | `column_constraints()` / `table_constraints()` |
| `UseIndex` | An index anchored on the field (single or composite via `columns=`) | Yes | `column_indexes()` / `table_indexes()` |
| `UseColumnAttributes` | Dialect-free `IdentityAttribute` / `CollationAttribute` / `CharacterSetAttribute` | Yes | `column_attributes()` |
| `UseComment` | A column comment | Yes | `column_comment()` / comment statements |
| `UseGeneratedColumn` | A database-computed column expression (or `(dialect) -> constraint` factory) | Yes | `generated_column()` |
| `UsePartitionKey` | Marks the field as a partition-key member (column-name aware) | Yes (metadata) | `partition_key_columns()` |
| `UseColumn` | Maps the Python field name to a different database column name | Yes (name) | `column_name()` |
| `UseFieldGenerator` | Per-operation Python value generation (`before_insert`, `before_update`, `before_soft_delete`, `before_restore`, `on_all`) | No | write path |
| `UseAdapter` | A `SQLTypeAdapter` instance + target driver type for value conversion | No | runtime adapters |
| `UseColumnType` | The column class used by `Model.c.<field>` operations | No | `FieldProxy` / expressions |
| `DerivedField` | A query-time computed, non-column, read-only field | No (excluded) | derived-field handler |

Key value classes used through `UseColumnAttributes`: `IdentityAttribute` (generation must be
`ALWAYS` or `BY DEFAULT`), `CollationAttribute`, `CharacterSetAttribute`. `ObjectDeclaration`
(`TABLE` / `VIEW` / `MATERIALIZED_VIEW`) is the value behind `object_type()`.

### 1.2 Table-level declarations (`DDLSource` methods)

| Method | Returns | Produced by | Note |
|---|---|---|---|
| `table_options()` | `CreateTableOptions` (+ backend subclasses) | classmethod override | generic options only (`or_replace`, comment) |
| `table_storage_options()` | `StorageOptionsExpression` | classmethod override | passed through verbatim |
| `table_partition()` | `PartitionClause` | classmethod override | independent of `partition_key_columns()` |
| `table_indexes()` | `IndexDefinition` sequence | `__table_indexes__` | names cross-checked with field `UseIndex` |
| `table_constraints()` | `TableConstraint` sequence | field `UseConstraint` + `__table_constraints__` | synthesizes composite-PK constraint |
| `table_inherits()` | list of table names | classmethod override | `INHERITS` clause (not available in SQLite; backend-provided) |
| `table_tablespace()` | string | classmethod override | — |
| `object_type()` | `ObjectDeclaration` | classmethod override | a declaration, never an introspection probe |
| `schema_name()` | string or `None` | model interface | not implemented by `DDLSourceMixin` |

Related field-level facts on the same protocol: `table_name()`, `schema_name()`,
`primary_key_columns()`, `partition_key_columns()`, `is_composite_pk()`, `ddl_field_names()`
(excludes derived fields), `is_derived_field()`, plus the `field_*` / `column_*` accessors from
section 1.1.

### 1.3 Behavior mixins

Two conventions to know:

- **Semantics base vs `Default*`**: a semantics-only mixin (e.g. `TimestampMixin`) declares **no
  fields**; it maintains behavior by overriding hooks and points at a field the model declares
  via a classmethod (`created_at_field()`). The `Default*` subclass adds the conventional field.
  Use `Default*` unless you need a custom field name.
- **Only `Default*` variants and the two PK mixins inject DDL columns.** Semantics-only mixins
  reference columns by name (column-rename aware via `UseColumn`) and inject nothing.

| Mixin (semantics / default) | Behavior | Injected DDL column (Default* only) |
|---|---|---|
| `TimestampMixin` / `DefaultTimestampMixin` (+ `UtcTimestampMixin`) | generated `created_at` / `updated_at`; UTC normalization | `created_at`, `updated_at` |
| `OptimisticLockMixin` / `DefaultOptimisticLockMixin` | WHERE-version + increment on UPDATE; stale detection | `version` (NOT NULL) |
| `SoftDeleteMixin` / `AsyncSoftDeleteMixin` / `Default*` | mark deleted, filter queries, restore | `deleted_at` |
| `ReadOnlyMixin` | refuse all framework write paths | none |
| `UUIDMixin` | Python-generated UUID primary key (uuid4 / uuid7) | `id` |
| `IntegerPKMixin` | integer auto-increment PK declaration | `id` |
| `CompositePKMixin` | validate all PK members present at construction | none (validates declared columns) |

Behavior mixins are activated **by inheritance** (mix into the model class) — there is no marker
and no auto-discovery beyond the metaclass collecting feature handlers and interface checks.

---

## 2. Three design boundaries

These are the most frequently misunderstood aspects of the current definition.

### 2.1 `UseSqlType` and `UseColumnType` are independent

| | `UseSqlType` | `UseColumnType` |
|---|---|---|
| Answers | how the value is **stored** (DDL `DataType`) | what operations `Model.c.<field>` offers (column class) |
| Multiple candidates | allowed, first renderable wins | rejected (exactly one column class) |
| Cross-checked? | **No** — a field may declare either, both, or neither; the framework never reconciles them | same |

> **Backend integration boundary**: `UseSqlType` describes how a value is *stored*, and storage
> types are ultimately rendered by a backend's dialect. The examples in this document use the
> built-in SQLite backend; other backends are documented separately. `UseColumnType`, by contrast,
> is a pure ActiveRecord query-surface concern and never reaches a backend.

### 2.2 Semantics-only mixins inject no fields

`TimestampMixin`, `OptimisticLockMixin`, `SoftDeleteMixin`, `ReadOnlyMixin`, and `CompositePKMixin`
declare zero Pydantic fields. Only the `Default*` variants and `UUIDMixin` / `IntegerPKMixin`
inject columns into DDL. A custom column name declared via `UseColumn` is honored automatically.

### 2.3 Declaration, derivation, execution are separate

- `DDLSource` **reads** declarations and presents them (dialect-free).
- `base/derivation.py` `build_*` functions **derive** generic statement expressions; the deriver
  never imports a backend and never decides policy (e.g. inline vs standalone indexes is an
  explicit `include_indexes` argument, and column order is owned and fully specified by the caller).
- `MigrationMixin` **executes** statements via a backend; function-style migrations
  (`@migration` + `MigrationContext.apply`) **orchestrate** them, with dependency/version/record
  handling and `--dry-run` preview.

> **Backend integration boundary**: The generic statements derived here are dialect-free, but
> dialect binding and capability gating take effect when a backend consumes them in layers 3 and 4.
> The examples in this document use the built-in SQLite backend; other backends are documented
> separately.
>
> 💡 **AI Prompt**: "Using the built-in SQLite backend, trace how a declaration flows from
> `DDLSource` through derivation to migration, and identify exactly where the dialect is bound and
> where SQLite gates a capability."

---

## 3. A model's lifecycle

1. **Class creation** — Pydantic collects `model_fields`, then the metaclass runs feature handlers:
   DDL annotations are validated (`UseIndex` anchors, `UseConstraint` branches, `UsePartitionKey`
   conflicts), mixin field configuration is checked, sync/async relation descriptors are checked.
2. **Instantiation** — Pydantic validates types; value generators run; `UUIDMixin` / `CompositePKMixin`
   perform their checks.
3. **Query** — field proxies resolve column classes; derived fields are injected into `SELECT`;
   soft-delete predicates filter results.
4. **Persistence** — `save()` refuses read-only models then calls `validate_fields()`; DDL is
   produced by `build_*_statement()` from the declarations, and executed or previewed by the
   migration mechanism.

---

## 4. Current boundaries / not yet implemented

This section is intentionally explicit — it records what the current definition **does not** do.

- **Assignment-time validation is absent.** Models do not enable `validate_assignment`; assigning
  `instance.status = "x"` is not Pydantic-validated. Validation happens at construction and in
  `save()` via `validate_fields()` / `validate_record()`.
- **Field enumeration range (`UseEnumRange`) is not implemented.** It is researched and planned;
  today's value-set enforcement is limited to Pydantic's native construction-time checks for
  `Enum`-annotated fields and optional DDL `CHECK` constraints.
- **`object_type()` has no consumer in core.** The protocol, mixin, and re-export exist, but the
  deriver builds table statements only and never branches on `VIEW` / `MATERIALIZED_VIEW`.
  Treat this as a SQLite limitation rather than a missing ActiveRecord declaration entry point:
  the SQLite backend used in these examples does not render such statements through this path,
  while other backends provide them — other backends are documented separately.
- **`schema_name()` is not supplied by `DDLSourceMixin`** (it comes from the model interface),
  and `build_create_table_statement()` builds an unqualified `Table(dialect, table_name())`.
- **`table_partition()` and `partition_key_columns()` are two independent channels**; the generic
  deriver never synthesizes a `PartitionClause` from the partition key, and consistency is unchecked.

---

## 5. Verification status

- The shared contract suite `feature/ddl/core` covers most `DDLSource` methods, but as of this
  writing it has **zero bridges in all 11 repositories** — the contract has never run in a backend
  CI pipeline. The core repository has its own inline `feature/basic/ddl` tests covering part of it.
- Two protocol methods are **not mentioned by the shared contract**: `partition_key_columns()` and
  `object_type()`. They are, however, covered by the core repository's own inline tests
  (`test_ddl_partition_key.py` and readonly/view tests respectively).

---

## 6. Where to go next

| To learn about… | See |
|---|---|
| Field declarations, column names, proxies | [Fields & Proxies](fields.md) |
| The `DDLSource` protocol in detail | [DDLSource Declarations](ddl_source.md) |
| DDL declaration examples | [DDLSource Examples](ddl_source_examples.md) |
| Generated DDL and statements | [DDL](ddl.md) |
| Behavior mixins and their fields | [Mixins](mixins.md) |
| Derived fields | [Derived Fields](derived_fields.md) |
| Validation and hooks | [Validation & Hooks](validation.md) |
| Custom types and adapters | [Custom Types](custom_types.md) |
| Read-only / keyless models | [Read-Only Models](readonly_models.md) / [Keyless Models](keyless_models.md) |
| Concurrency and optimistic locking | [Concurrency](concurrency.md) |
