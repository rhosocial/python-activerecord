# Database Introspection

Database introspection is the ability to query database structure metadata at runtime. rhosocial-activerecord provides a complete introspection system that supports querying metadata for databases, tables, columns, indexes, foreign keys, views, triggers, and more.

## Overview

The introspection system is accessible via the `backend.introspector` attribute and provides:

- **Database Information**: Name, version, encoding, size, etc.
- **Table Information**: Table list, table details, table types (`BASE_TABLE`, `VIEW`, `MATERIALIZED_VIEW`, `FOREIGN_TABLE`, `PARTITIONED_TABLE`, `SYSTEM_TABLE`, `TEMPORARY`, `EXTERNAL`)
- **Column Information**: Column name, data type, nullability, default value, primary key info
- **Index Information**: Index name, columns, uniqueness, index type
- **Foreign Key Information**: Referenced table, column mapping, update/delete actions
- **View Information**: View definition SQL
- **Trigger Information**: Trigger event, timing, trigger SQL
- **Object State**: A neutral snapshot of a table, its partitioning, indexes, constraints, sequences and engine-derived objects, built from core dataclasses

## What You Can Ask

Introspection answers four kinds of question, and this page covers the first in detail:

- **Declaration layer** — what the catalogue says objects are: databases, tables, columns, indexes, foreign keys, views and triggers. The dialect's capability probes say which of these an engine answers at all; see [Capabilities](introspection/capabilities.md).
- **Operational layer** — what the engine has counted while running: unused indexes, table and index usage counters, runtime measurements, object dependencies and DDL retrieval; see [Operational Families](introspection/operations.md).
- **Data layer** — what the rows actually hold, rather than what the schema promises: column profiles, frequent values and join coverage; see [Column Data Profiles](introspection/data-profiles.md).
- **Object-state layer** — what the server holds right now, in shapes the caller owns: table state, partition state, index/constraint/sequence states, engine-derived objects and shared-object existence; see [Neutral Object State](#neutral-object-state).

A family whose capability probe answers `False` is not available on that engine; the backend's own documentation states which probes answer `True` and what its answers mean.

## Architecture Design

### Module Structure

```
backend/introspection/
├── __init__.py          # Module exports
├── base.py              # Abstract introspector bases (sync and async)
├── types.py             # Data structure definitions (TableType, ...)
├── errors.py            # Introspection-specific exceptions
├── executor.py          # Executor abstraction
├── cache.py             # IntrospectionCache -- the injectable result cache
├── backend_mixin.py     # Backend mixin class
└── status/              # Server status overview (config, performance, storage)
```

### A Catalogue Question Is a Statement

Introspection does not build SQL text inline. Each question is a statement class
(named `*Statement`, e.g. `TableListQueryStatement`), rendered by a dialect
`format_*_query_statement` method; the introspector holds the public method pairs
(`list_tables()` / `parse_tables()`, and so on) that use them. Two consequences
matter to a backend author:

- the expression layer keeps no state -- a statement holds what it needs to be
  rendered anywhere;
- a backend answers a catalogue question by declaring a statement plus a
  formatter, not by overriding a method that assembles a string.

### Sync and Async Separation

The introspection system follows the project's sync/async parity principle:

- `AbstractIntrospector` — Synchronous introspector
- `AsyncAbstractIntrospector` — Asynchronous introspector
- `IntrospectorMixin` — Shared non-I/O base: it knows the default schema and exposes the `dialect` and `server_version` shortcuts, but holds no state, performs no I/O and never sees a result row. Caching and row parsing belong to the manager that inherits it, and SQL is rendered by the dialect's `format_*` methods from statement objects. `server_version` is the version the introspector read from the server, so a capability question can be answered without asking again

## Capability Protocols

Capability declarations are split into four introspection families rather than
carried by one protocol. Each family has a synchronous protocol, an async twin
that declares the same members, and a dialect mixin with the same member list:

| Family | Question it answers | Protocol (sync / async twin) | Dialect mixin (sync / async twin) |
|--------|---------------------|------------------------------|------------------------------------|
| Structure | What the catalogue declares an object to be | `StructureIntrospectionSupport` / `AsyncStructureIntrospectionSupport` | `StructureIntrospectionMixin` / `AsyncStructureIntrospectionMixin` |
| Operational stats | How the objects have behaved | `OperationalStatsIntrospectionSupport` / `AsyncOperationalStatsIntrospectionSupport` | `OperationalStatsIntrospectionMixin` / `AsyncOperationalStatsIntrospectionMixin` |
| Data profile | What the rows in a column look like | `DataProfileIntrospectionSupport` / `AsyncDataProfileIntrospectionSupport` | `DataProfileIntrospectionMixin` / `AsyncDataProfileIntrospectionMixin` |
| DDL extraction | The text that would recreate an object | `DdlExtractionIntrospectionSupport` / `AsyncDdlExtractionIntrospectionSupport` | `DdlExtractionIntrospectionMixin` / `AsyncDdlExtractionIntrospectionMixin` |

`IntrospectionMixin` and `AsyncIntrospectionMixin` are **composition-only**
aggregates of the four: they declare no members of their own, so a dialect that
composes one inherits every family's answer, and a method-name override
anywhere in the dialect keeps winning. The split exists so a dialect can answer
one question — declaration, behaviour, data, retained text — without claiming
the others.

A family is **claimed** only if at least one of its probes answers `True`.
Composing the aggregate is not a claim: a dialect that composes
`IntrospectionMixin` while every operational probe answers `False` does not
claim operational statistics, even though the methods exist on the class. Every
backend's protocol-conformance test applies this rule.

```python
from rhosocial.activerecord.backend.dialect.protocols import (
    StructureIntrospectionSupport,
    OperationalStatsIntrospectionSupport,
    DataProfileIntrospectionSupport,
    DdlExtractionIntrospectionSupport,
)

FAMILIES = (
    StructureIntrospectionSupport,
    OperationalStatsIntrospectionSupport,
    DataProfileIntrospectionSupport,
    DdlExtractionIntrospectionSupport,
)

dialect = backend.dialect
for family in FAMILIES:
    probes = [name for name in dir(family) if name.startswith("supports_")]
    claimed = any(getattr(dialect, name)() for name in probes)
    print(f"{family.__name__}: claimed={claimed}")
```

A `True` promises that the engine will answer; a `False` means do not ask. See
[Capabilities](introspection/capabilities.md) for what each answer promises and
what it does not.

The object-state methods in [Neutral Object State](#neutral-object-state) are
not probes on these protocols. They are methods on the manager, and a backend
that cannot answer one refuses by name rather than returning an empty value.

## Data Structures

### IntrospectionDatabaseInfo

Basic database information:

```python
@dataclass
class IntrospectionDatabaseInfo:
    name: str                      # Database name
    version: str                   # Version string
    version_tuple: Tuple[int, ...] # Version tuple
    vendor: str                    # Database vendor
    encoding: Optional[str]        # Encoding
    collation: Optional[str]       # Collation
    timezone: Optional[str]        # Timezone
    size_bytes: Optional[int]      # Database size
    table_count: Optional[int]     # Table count
    extra: Dict[str, Any]          # Additional info
```

### IntrospectionTableInfo

Table information:

```python
@dataclass
class IntrospectionTableInfo:
    name: str                    # Table name
    schema: str                  # Schema name
    table_type: TableType        # Table type (BASE_TABLE, VIEW, MATERIALIZED_VIEW,
                                 #  FOREIGN_TABLE, PARTITIONED_TABLE, SYSTEM_TABLE,
                                 #  TEMPORARY, EXTERNAL)
    comment: Optional[str]       # Table comment
    row_count: Optional[int]     # Row count estimate
    size_bytes: Optional[int]    # Table size
    extra: Dict[str, Any]        # Additional info
```

`table_type` keeps the distinction the catalogue actually makes rather than
folding every relation into "table". How a particular engine classifies a
relation is that backend's own documentation to state.

### IntrospectionColumnInfo

Column information:

```python
@dataclass
class IntrospectionColumnInfo:
    name: str                         # Column name
    table_name: str                   # Owner table name
    data_type: str                    # Data type
    nullable: ColumnNullable          # Nullability
    default_value: Optional[str]      # Default value
    is_primary_key: bool              # Is primary key
    ordinal_position: int             # Column position
    comment: Optional[str]            # Column comment
    character_set: Optional[str]      # Character set
    collation: Optional[str]          # Collation
    extra: Dict[str, Any]             # Additional info
```

### IndexInfo

Index information:

```python
@dataclass
class IndexInfo:
    name: str                      # Index name
    table_name: str                # Owner table name
    columns: List[IndexColumnInfo] # Index columns
    is_unique: bool                # Is unique
    is_primary: bool               # Is primary key
    index_type: IndexType          # Index type
    comment: Optional[str]         # Index comment
    extra: Dict[str, Any]          # Additional info
```

### IntrospectionForeignKeyInfo

Foreign key information:

```python
@dataclass
class IntrospectionForeignKeyInfo:
    name: str                           # Foreign key name
    table_name: str                     # Owner table name
    columns: List[str]                  # Foreign key columns
    referenced_table: str               # Referenced table name
    referenced_columns: List[str]       # Referenced columns
    on_update: ReferentialAction        # Update action
    on_delete: ReferentialAction        # Delete action
    match_option: Optional[str]         # Match option
    extra: Dict[str, Any]               # Additional info
```

### IntrospectionViewInfo

View information:

```python
@dataclass
class IntrospectionViewInfo:
    name: str                    # View name
    schema: str                  # Schema name
    definition: str              # View definition SQL
    is_updatable: Optional[bool] # Is updatable
    comment: Optional[str]       # View comment
    extra: Dict[str, Any]        # Additional info
```

### IntrospectionTriggerInfo

Trigger information:

```python
@dataclass
class IntrospectionTriggerInfo:
    name: str                    # Trigger name
    table_name: str              # Associated table name
    event: TriggerEvent          # Trigger event
    timing: TriggerTiming        # Trigger timing
    statement: str               # Trigger SQL
    condition: Optional[str]     # Trigger condition
    extra: Dict[str, Any]        # Additional info
```

## Neutral Object State

The state methods answer "what does the server hold right now" in neutral core
dataclasses. A caller never sees a backend-specific result type: each backend
maps its own catalogue into the shapes below. The eight methods exist on both
introspectors under the same names; on the async class (`Async*Introspector`)
each call is awaited.

| Method | Parameters (defaults) | Returns |
|--------|-----------------------|---------|
| `get_table_state(table_name)` | `schema=None` | `TableState` |
| `get_partition_state(table_name)` | `schema=None, include_stats=False` | `PartitionState` |
| `list_index_states(table_name)` | `schema=None` | `List[IndexState]` |
| `list_constraint_states(table_name)` | `schema=None` | `List[ConstraintState]` |
| `list_sequence_states()` | `schema=None` | `List[SequenceState]` |
| `list_derived_objects(table_name)` | `schema=None` | `List[DerivedObjectState]` |
| `list_schemas()` | — | `List[str]` |
| `item_exists(kind, name)` | `schema=None` | `bool` |

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.introspection import TableState

backend = SQLiteBackend(database=":memory:")
backend.connect()
backend.executescript("""
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    status TEXT NOT NULL DEFAULT 'open'
);
""")

state = backend.introspector.get_table_state("orders")
assert isinstance(state, TableState)
print(state.name, state.schema, state.kind, state.traits)
```

### The state shapes

All state types are frozen dataclasses in
`rhosocial.activerecord.backend.introspection.types` and are re-exported from
`rhosocial.activerecord.backend.introspection`.

```python
@dataclass(frozen=True)
class TableState:
    name: str
    schema: Optional[str]
    kind: str                       # "regular" / "temporary" / "transient" / "unlogged";
                                    #  backends may add their own spelling
    traits: Tuple[str, ...]         # compound traits, e.g. "strict", "without_rowid"
    storage: StorageOptionsState
    comment: Optional[str]
    partitioning: PartitionState        # never None; an empty PartitionState when not partitioned
    raw: Dict[str, Any]            # the backend's own slots

@dataclass(frozen=True)
class StorageOptionsState:
    engine: Optional[str]           # None means the engine used its own default,
    charset: Optional[str]          #  not "unknown"
    collation: Optional[str]
    compression: Optional[str]
    tablespace: Optional[str]
    raw: Dict[str, Any]

@dataclass(frozen=True)
class PartitionState:
    scheme: Optional[PartitionScheme]   # None is the single answer for "not partitioned"
    key_expression: str
    key_columns: Tuple[str, ...]
    has_default: bool
    auto_extend: bool
    bounds: Tuple[PartitionBound, ...]
    raw: Dict[str, Any]

@dataclass(frozen=True)
class PartitionBound:
    name: str
    lower: Optional[str]            # RANGE/LIST boundary as the server spells it
    upper: Optional[str]
    values: Tuple[str, ...]
    modulus: Optional[int]          # HASH: key hashes to remainder modulo modulus
    remainder: Optional[int]
    is_default: bool
    is_maxvalue: bool
    row_count: Optional[int]        # populated only when include_stats was requested
    size_bytes: Optional[int]       # populated only when include_stats was requested
    subpartition_count: int
    tablespace: Optional[str]

@dataclass(frozen=True)
class IndexState:
    name: str
    table: str
    schema: Optional[str]
    unique: bool
    method: Optional[str]
    predicate: Optional[str]
    visible: bool
    usable: bool                    # False when the engine reports the index unusable/invalid
    backs_constraint: Optional[str]
    raw: Dict[str, Any]

@dataclass(frozen=True)
class ConstraintState:
    name: str
    table: str
    kind: str                       # e.g. "primary_key", "unique", "check", "foreign_key"
    schema: Optional[str]
    validated: bool
    enforced: bool
    deferred: bool
    disabled: bool
    backing_index: Optional[str]
    raw: Dict[str, Any]

@dataclass(frozen=True)
class SequenceState:
    name: str
    schema: Optional[str]
    owned_by: Optional[str]         # the column that owns the sequence, when one does
    start: Optional[int]
    increment: Optional[int]
    raw: Dict[str, Any]

@dataclass(frozen=True)
class DerivedObjectState:
    kind: str                       # "backing_index" / "identity_sequence" / "history_table" /
                                    #  "named_default" / "autoindex"
    name: str
    owned_by: Optional[str]
    raw: Dict[str, Any]
```

The two enums are `str` enums, so a value prints as its word:

| Enum | Values |
|------|--------|
| `PartitionScheme` | `range`, `list`, `hash`, `key`, `composite`, `interval`, `expression` |
| `ItemKind` | `schema`, `type`, `domain`, `function`, `sequence`, `table`, `index`, `extension`, `tablespace`, `partition_function`, `partition_scheme`, `fulltext_catalog` |

### `scheme=None` is the single answer for "not partitioned"

`PartitionState.scheme` is the one neutral answer to "is this table partitioned".
It is `None` for every backend, regardless of how that backend spells or
discovers partitions (child tables, system parts, decorated tables). Nothing
else stands in for it: not an empty `bounds` tuple, not a fabricated scheme, and
not a missing `PartitionState` — `get_partition_state` returns the state object
and puts `None` in `scheme`. When `scheme` is `None`, `bounds` is empty because
there are no partitions to describe.

```python
partition = backend.introspector.get_partition_state("orders")

assert partition.scheme is None      # the single neutral answer: not partitioned
assert partition.bounds == ()
print(partition.scheme, partition.key_columns)
```

`TableState.partitioning` is never `None`. An engine with no partitioning at all
answers an empty `PartitionState` whose `scheme` is `None`, the same single
neutral answer `get_partition_state` gives. `None` is not an answer, and callers
must not test for it.

### Statistics are opt-in, and the default must not ask for them

`include_stats=False` is the default. The choice is made at the projection and
query level, not by filtering values afterwards: with the default a backend must
not run the statistics query at all, so `PartitionBound.row_count` and
`PartitionBound.size_bytes` stay `None`. With `include_stats=True` the backend
adds the statistics columns — for example a row estimate from the catalogue and a
relation-size call — and the same bounds carry those figures. The cost difference
is that query: an engine that computes sizes by walking the relation can pay a
scan per partition, while the default answer costs one catalogue read.

```python
plain = backend.introspector.get_partition_state("orders")
assert all(bound.row_count is None and bound.size_bytes is None for bound in plain.bounds)

with_stats = backend.introspector.get_partition_state("orders", include_stats=True)
# On a partitioned engine, with_stats.bounds now carry row_count / size_bytes.
print([(bound.name, bound.row_count, bound.size_bytes) for bound in with_stats.bounds])
```

On an engine with no partitioning (SQLite) both calls answer
`PartitionState(scheme=None)`; there are no bounds to compare, so the difference
is observable only where a scheme exists.

### Refusal is by name

A method a backend has not implemented raises `ProtocolNotImplementedError`, and
the message names the dialect, the family and the method. An empty list or `None`
is never a stand-in for "cannot answer": those mean the question was asked and
the answer is "nothing", which is a different fact.

```python
from types import SimpleNamespace

from rhosocial.activerecord.backend.dialect.exceptions import ProtocolNotImplementedError
from rhosocial.activerecord.backend.introspection.base import (
    AbstractIntrospector,
    IntrospectorMixin,
)


class UnimplementedIntrospector(IntrospectorMixin):
    def __init__(self):
        self._backend = SimpleNamespace(dialect=SimpleNamespace(name="Custom"))


try:
    AbstractIntrospector.get_table_state(UnimplementedIntrospector(), "orders")
except ProtocolNotImplementedError as exc:
    # 'Custom' dialect does not implement StructureIntrospectionSupport
    # protocol, which is required by get_table_state.
    print(exc.dialect_name, exc.protocol_name, exc.required_by)
```

The exception carries the three names as attributes (`dialect_name`,
`protocol_name`, `required_by`), so a caller can react without parsing the
message. `None` as an answer is reserved for an answered question with nothing
to report: `get_ddl_statement` returns `None` when the engine was asked and has
no text, never because the engine cannot answer.

### `item_exists` answers three cases

`item_exists(kind, name)` asks whether a shared object exists. Shared objects
outlive a table: a sequence, a type, a domain, a function, an extension, a
tablespace, a partition function/scheme, a full-text catalogue. One rule covers
every kind:

1. the engine has no objects of this kind → `False`, a definite "there is none",
   not "cannot tell";
2. the engine has them and the catalogue query is implemented → query and answer
   `True` or `False`;
3. the engine has them but this backend has no query for the kind → refuse with
   `ProtocolNotImplementedError`: that is an implementation gap, and a `False`
   there would disguise it as absence.

```python
from rhosocial.activerecord.backend.introspection import ItemKind

introspector = backend.introspector

# case 2: SQLite has tables and this backend can query them
print(introspector.item_exists(ItemKind.TABLE, "orders"))      # True
print(introspector.item_exists(ItemKind.TABLE, "missing"))     # False: asked, none

# case 1: SQLite has no named type objects at all
print(introspector.item_exists(ItemKind.TYPE, "orders"))       # False: none exist
```

A backend in case 3 raises instead of answering `False`.

### Migration note: `list_partitions` was removed

`list_partitions` was removed with no compatibility layer. Its logic is folded
into `get_partition_state`: the scheme and the bounds now travel together in one
`PartitionState`, so `scheme` answers "is this table partitioned" and `bounds`
describes the parts. There is no alias and no fallback; the only supported
spelling is `get_partition_state`.

Partition capability moved out of the introspection families: ask
`PartitionSupport.supports_partition_metadata_introspection()` before requesting
partition metadata from a backend. See
[Capabilities](introspection/capabilities.md).

## Basic Usage

### Accessing the Introspector

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend

backend = SQLiteBackend(database=":memory:")
backend.connect()

# Access via introspector attribute
introspector = backend.introspector
```

### Getting Database Information

```python
# Sync API
db_info = backend.introspector.get_database_info()
print(f"Database name: {db_info.name}")
print(f"Version: {db_info.version}")
print(f"Vendor: {db_info.vendor}")

# Async API
db_info = await backend.introspector.get_database_info()
```

### Listing Tables

```python
# List all user tables
tables = backend.introspector.list_tables()
for table in tables:
    print(f"Table: {table.name}, Type: {table.table_type.value}")

# Include system tables
all_tables = backend.introspector.list_tables(include_system=True)

# Filter by specific type
base_tables = backend.introspector.list_tables(table_type="BASE TABLE")
views = backend.introspector.list_tables(table_type="VIEW")

# Check if table exists
if backend.introspector.table_exists("users"):
    print("users table exists")

# Get table details
table_info = backend.introspector.get_table_info("users")
```

### Querying Column Information

```python
# List all columns of a table
columns = backend.introspector.list_columns("users")
for col in columns:
    nullable = "NOT NULL" if col.nullable.value == "NOT_NULL" else "NULLABLE"
    pk = " [PK]" if col.is_primary_key else ""
    print(f"{col.name}: {col.data_type} {nullable}{pk}")

# Get primary key information
pk = backend.introspector.get_primary_key("users")
if pk:
    print(f"Primary key: {[c.name for c in pk.columns]}")

# Get single column information
col_info = backend.introspector.get_column_info("users", "email")
```

### Querying Indexes

```python
# List all indexes of a table
indexes = backend.introspector.list_indexes("users")
for idx in indexes:
    unique = "UNIQUE " if idx.is_unique else ""
    print(f"{unique}Index: {idx.name}")
    for col in idx.columns:
        desc = "DESC" if col.is_descending else "ASC"
        print(f"  - {col.name} ({desc})")

# Check if an index exists
if backend.introspector.get_index_info("users", "idx_users_email"):
    print("email index exists")
```

### Querying Foreign Keys

```python
# List foreign keys of a table
foreign_keys = backend.introspector.list_foreign_keys("posts")
for fk in foreign_keys:
    print(f"FK: {fk.name}")
    print(f"  Columns: {fk.columns} -> {fk.referenced_table}.{fk.referenced_columns}")
    print(f"  ON DELETE: {fk.on_delete.value}")
    print(f"  ON UPDATE: {fk.on_update.value}")
```

### Querying Views

```python
# List all views
views = backend.introspector.list_views()
for view in views:
    print(f"View: {view.name}")

# Get view details
view_info = backend.introspector.get_view_info("user_posts_summary")
if view_info:
    print(f"Definition: {view_info.definition}")

# Check if view exists
if backend.introspector.view_exists("user_posts_summary"):
    print("View exists")
```

### Querying Triggers

```python
# List all triggers
triggers = backend.introspector.list_triggers()
for trigger in triggers:
    print(f"Trigger: {trigger.name} on {trigger.table_name}")

# List triggers for a specific table
table_triggers = backend.introspector.list_triggers("users")
for trigger in table_triggers:
    print(f"Trigger: {trigger.name}")
    print(f"  Event: {trigger.event.value}")
    print(f"  Timing: {trigger.timing.value}")

# Get trigger details
trigger_info = backend.introspector.get_trigger_info("trg_users_audit")
```

## Async API

The async backend provides identical introspection methods with the same names as the sync version:

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import AsyncSQLiteBackend

backend = AsyncSQLiteBackend(database=":memory:")
await backend.connect()

# Async introspection methods (same names as sync version)
db_info = await backend.introspector.get_database_info()
tables = await backend.introspector.list_tables()
table_info = await backend.introspector.get_table_info("users")
columns = await backend.introspector.list_columns("users")
indexes = await backend.introspector.list_indexes("users")
foreign_keys = await backend.introspector.list_foreign_keys("posts")
views = await backend.introspector.list_views()
triggers = await backend.introspector.list_triggers()

# Neutral object state, same names, awaited
state = await backend.introspector.get_table_state("users")
partition = await backend.introspector.get_partition_state("users")
```

## Caching Mechanism

Introspection results are cached by default for performance. The cache is a
component the manager **owns** and a caller may replace, rather than a hidden
attribute: `backend.introspector.cache`.

### The Cache Contract

`IntrospectionCache` (`rhosocial.activerecord.backend.introspection.cache`) is a
protocol, so a backend can put its own implementation behind the manager instead
of inheriting this package's expiry policy:

| Method | Purpose |
|--------|---------|
| `key(scope, name=None, schema=None, extra=None)` | Build the key two callers asking the same question share |
| `get(key)` | Return a cached result, or `None` |
| `set(key, value)` | Store a result |
| `invalidate(scope=None, name=None)` | Drop results from everything down to one object |
| `clear()` | Drop every cached result |

`InMemoryIntrospectionCache` is the default: in-process, expiring after a TTL
(300 seconds by default), dropped lazily the moment somebody looks at an expired
entry rather than by a background sweeper.

```python
from rhosocial.activerecord.backend.introspection.cache import InMemoryIntrospectionCache

# Default: in-process, 300 s TTL
backend.introspector.cache = InMemoryIntrospectionCache(ttl=60)

# Or a cache of your own: anything that satisfies the protocol
class NoCache:
    def key(self, scope, name=None, schema=None, extra=None):
        return (scope, name, schema, extra)

    def get(self, key):
        return None

    def set(self, key, value):
        pass

    def invalidate(self, scope=None, name=None):
        pass

    def clear(self):
        pass

backend.introspector.cache = NoCache()
```

### Cache Management

```python
# Clear all cache
backend.introspector.clear_cache()

# Invalidate specific scope
from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

# Invalidate all table-related cache
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE)

# Invalidate cache for a specific table, index, column set, ...
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.TABLE,
    name="users"
)
backend.introspector.invalidate_cache(
    scope=IntrospectionScope.INDEX,
    name="idx_users_email"
)
```

### Cache Scopes

A scope says which cached answers an invalidation reaches, so the table a
question is about travels in the `name` (or, for `key()`, in `schema`/`extra`):

| Scope | Description |
|-------|-------------|
| `DATABASE` | Database information |
| `SCHEMA` | Schema information |
| `TABLE` | Table information |
| `COLUMN` | Column information |
| `INDEX` | Index information |
| `FOREIGN_KEY` | Foreign key information |
| `VIEW` | View information |
| `TRIGGER` | Trigger information |


## Backend-Specific Implementations

The common methods are assembled over helper introspectors the backend supplies — the built-in SQLite backend's `PragmaIntrospector` and, for example, MySQL's `ShowIntrospector` are two — and each backend's own documentation states which helpers it has, what they answer, and what those answers mean.

## Error Handling

The introspection system defines specific exceptions:

```python
from rhosocial.activerecord.backend.introspection.errors import (
    IntrospectionError,       # Base introspection exception
    TableNotFoundError,       # Table not found
    ColumnNotFoundError,      # Column not found
    IndexNotFoundError,       # Index not found
    ViewNotFoundError,        # View not found
    TriggerNotFoundError,     # Trigger not found
)

try:
    table_info = backend.introspector.get_table_info("nonexistent")
except TableNotFoundError as e:
    print(f"Table not found: {e}")
```

## Best Practices

### 1. Use Caching

Introspection operations typically involve multiple database queries. Leverage caching:

```python
# First query caches the result
tables = backend.introspector.list_tables()

# Subsequent queries return from cache
tables_again = backend.introspector.list_tables()

# Only clear cache when table structure changes
backend.introspector.invalidate_cache(scope=IntrospectionScope.TABLE, name="users")
```

### 2. Batch Operations

Prefer batch query methods when possible:

```python
# Good: One query for all columns
columns = backend.introspector.list_columns("users")

# Avoid: Multiple single-column queries
for col_name in column_names:
    col = backend.introspector.get_column_info("users", col_name)  # I/O each time
```

### 3. Check Existence

Check if objects exist before performing dependent operations:

```python
if backend.introspector.table_exists("users"):
    columns = backend.introspector.list_columns("users")
else:
    print("Table doesn't exist, skipping processing")
```

### 4. Using in Async Environments

```python
async def get_schema_info(backend):
    # Async methods have the same names as sync
    tables = await backend.introspector.list_tables()

    # Concurrently fetch columns for multiple tables
    import asyncio
    tasks = [
        backend.introspector.list_columns(table.name)
        for table in tables
    ]
    all_columns = await asyncio.gather(*tasks)
    return dict(zip([t.name for t in tables], all_columns))
```

## Limitations and Considerations

Three facts explain almost every surprising introspection answer:

1. **A counter is a window, not a lifetime.** The operational families report
   what the engine has counted *since the statistics were last reset*. A zero
   means "nothing in this window", never "nothing ever happened".
2. **A profile may describe an older table.** Figures read from a statistics
   catalogue can be as stale as the engine's last refresh; `collected_at`
   travels beside them so a reader can tell what moment they describe.
3. **Some engines cannot answer some questions.** Ask the dialect's capability
   probe first — see [Capabilities](introspection/capabilities.md). A `False`
   is a definite "this engine does not answer this family", and each backend's
   own documentation says which probes answer `True` and what its answers mean.

## API Reference

The signatures below omit `self`; the sync and async introspectors have the
same method names and parameters.

### Core Methods — Declaration Layer

What the catalogue says objects are. Every result is cached under the scope it
belongs to.

| Method | Parameters (defaults) | Description |
|--------|-----------------------|-------------|
| `get_database_info()` | — | Database information |
| `list_tables()` | `schema=None, include_system=False, table_type=None` | List tables (and views) |
| `get_table_info(table_name)` | `schema=None` | Table details, with columns, indexes and foreign keys |
| `table_exists(table_name)` | `schema=None` | Whether the table exists |
| `list_columns(table_name)` | `schema=None` | List columns |
| `get_column_info(table_name, column_name)` | `schema=None` | Column details |
| `column_exists(table_name, column_name)` | `schema=None` | Whether the column exists |
| `get_primary_key(table_name)` | `schema=None` | Primary key index |
| `list_indexes(table_name)` | `schema=None` | List indexes |
| `get_index_info(table_name, index_name)` | `schema=None` | Index details |
| `list_foreign_keys(table_name)` | `schema=None` | List foreign keys |
| `get_foreign_key_info(table_name, fk_name)` | `schema=None` | Foreign key details |
| `list_views()` | `schema=None, include_system=False` | List views |
| `get_view_info(view_name)` | `schema=None` | View details |
| `view_exists(view_name)` | `schema=None` | Whether the view exists |
| `list_triggers()` | `table_name=None, schema=None` | List triggers, optionally for one table |
| `get_trigger_info(trigger_name)` | `schema=None` | Trigger details |

### Core Methods — Neutral Object State

The eight methods below return core dataclasses, not backend-specific result
types. They are not gated by the four families' probes: a backend that has not
implemented one refuses by name (see
[Refusal is by name](#refusal-is-by-name)). The sync and async introspectors
declare the same names; on the async class each call is awaited.

| Method | Parameters (defaults) | Description |
|--------|-----------------------|-------------|
| `get_table_state(table_name)` | `schema=None` | Table kind, traits, storage options, comment and partition state |
| `get_partition_state(table_name)` | `schema=None, include_stats=False` | The partition scheme (`None` when not partitioned) and its bounds; statistics only when asked |
| `list_index_states(table_name)` | `schema=None` | Every index, with method, predicate, visibility and usability |
| `list_constraint_states(table_name)` | `schema=None` | Every constraint, with its kind and validation/enforcement state |
| `list_sequence_states()` | `schema=None` | The sequences of a schema, with their owning columns |
| `list_derived_objects(table_name)` | `schema=None` | Objects the engine created for a declaration (autoindex, identity sequence, ...) |
| `list_schemas()` | — | The schema/namespace names the server exposes |
| `item_exists(kind, name)` | `schema=None` | Whether a shared object of `ItemKind` exists, by the three-case rule |

### Core Methods — Operational Layer

Counters here are windows, not lifetimes: a zero means "nothing since the
statistics were last reset" (see
[Limitations and Considerations](#limitations-and-considerations)). Check the
dialect's capability probe before calling; a `False` means the family is not
available on that engine.

| Method | Parameters (defaults) | Description |
|--------|-----------------------|-------------|
| `list_unused_indexes()` | `schema=None` | Indexes the engine reports as never having served a query |
| `list_table_usage_stats()` | `schema=None` | Per-table read/write counters, since the last statistics reset |
| `list_runtime_metrics()` | `schema=None` | Live runtime measurements; each item's `source` states its window |
| `list_index_usage_stats()` | `schema=None` | Per-index use counters ("how much", not "ever") |
| `list_object_dependencies()` | `object_name=None, schema=None` | The dependency graph, or one object's dependants |
| `get_ddl_statement(object_name)` | `object_type=None, schema=None` | DDL that recreates one object, or `None` |

### Core Methods — Data Layer

The declaration says what a column *promises*; these say what it *holds*.
`None` means not measured, never zero, and a profile's `source` says where its
figures came from.

| Method | Parameters (defaults) | Description |
|--------|-----------------------|-------------|
| `list_column_data_profiles(table_name)` | `schema=None` | Profile every column of one table |
| `sample_column_values(table_name, column_name)` | `limit=VALUE_SAMPLE_LIMIT, schema=None` | A column's most frequent values, up to `limit` |
| `estimate_join_coverage(left_table, left_column, right_table, right_column)` | `schema=None` | How much two columns' value domains overlap; `None` when unmeasured |

`VALUE_SAMPLE_LIMIT` is defined once in
`backend/introspection/defaults.py` (currently 100); the signature names the
constant rather than repeating its value.

### Cache and Invalidation

The cache is the component every layer's results pass through; it is not a
layer of its own.

| Method | Parameters (defaults) | Description |
|--------|-----------------------|-------------|
| `clear_cache()` | — | Drop every cached result |
| `invalidate_cache()` | `scope=None, name=None` | Drop cached results, from everything down to one object |
