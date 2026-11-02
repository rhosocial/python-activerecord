# Introspection

Four rules decide how introspection is built. They are judgements, not style
preferences: when an implementation disagrees with one of them, the
implementation changes.

## 1. Nobody spells SQL. This is absolute.

Production code contains no whole SQL statement and no SQL fragment built with
an f-string or `+`. Table names, column names, values, conditions and joins go
through the expression nodes (`column`, `relation`, `literal`, `compare`,
`join`, `select_sql`, ...). SQL text lives in one place only: the dialect's
`format_*` methods.

Unit tests may write SQL by hand, to build a fixture or to check what the
database actually returns. That exemption stops at the test boundary: a query
that a test spelled may not become the production path, and it may not be
"factored out" into a shared helper later.

When the expression layer cannot express an introspection question, the answer
is to add what is missing -- a node, a statement class, a formatter -- not to
fall back to a string inside the formatter. A gap is a missing class, not a
licence to spell SQL.

## 2. Core keeps the smallest set, and does not arbitrate capability.

Core carries only the families an ActiveRecord layer generally cares about and
most engines can answer: database information, tables, views, columns, indexes,
foreign keys, triggers. Partitions and schemas/catalogs are optional.

Core maintains no capability list. `supports_*` is a backend stating a fact
about itself; anything not declared is treated as unsupported. A backend that
cannot answer a question says so (`UnsupportedFeatureError`) and its CLI does
not offer the type -- it never returns a successful-looking answer about the
wrong objects.

The table-kind vocabulary is a different thing and does live in core:
`TableType` names what a catalogue can report (a base table, a view, a
materialized view, a partitioned table), and each backend maps its own
spelling onto it. Spellings that belong to one engine -- BigQuery's `CLONE`
and `SNAPSHOT`, ClickHouse's engines, Snowflake's `MANAGED` and `EVENT`
tables -- ride in `extra` beside the member they map to instead of widening
the enum. The rule is the same in both cases: the introspector is the only
layer that saw the catalog's distinction, so nothing may be folded away there
and recovered later.

### 2a. A capability switch buys discoverability, never semantics.

A `supports_*` name in core is a question worth asking through one spelling,
**not** a promise that every engine answers it the same way. That distinction
decides what to do when the mechanisms diverge, and it is settled by asking
which of the two is uniform:

- the **question** uniform, the **answer shape** not -> keep the name in core,
  and say so where a reader will look. `supports_fulltext_search` is the
  standing example: `MATCH ... AGAINST` and `CONTAINS` share nothing but the
  question, and the name stays because a caller wants one way to ask it;
- the **question** itself is not uniform -> the switch belongs to the backend
  alone, exactly as partitions do.

`supports_extensions` is the case that makes the rule necessary. `extension`
is not SQL vocabulary, and it names different objects per engine -- PostgreSQL
`CREATE EXTENSION` packages (version, schema), SQLite registered virtual table
modules. It was once argued that it should be withdrawn from core for exactly
that reason. The argument loses: withdrawing it would not make the semantics
agree, it would only make the question unaskable through a common surface, so
a caller would have to already know the backend's private spelling
(`supports_extension_introspection`) -- which is strictly worse than an answer
that has to be read together with its backend's docs.

Consequences for anyone editing such a probe:

1. **`True` promises "this engine will answer", never "it will answer in that
   shape".** The field set lives in the backend's own result type. A probe
   answered `True` with no query formatting, no result type and no CLI type
   behind it is a broken promise -- worse than `False`, because `False` is
   merely "I do not answer" while that is "I will" followed by nothing. This
   happened, and the fix was to answer `False`.
2. **One capability, one answer.** A backend must not answer `True` through
   its own spelling while the core spelling still defaults to `False`: two
   names for one fact let a caller be told "unsupported" by whichever name it
   happened to use. Either the backend answers through the core name, or the
   core name does not exist.

## 3. Every backend completes its own semantics.

An introspection class derives from core, and that derivation is the floor, not
the ceiling. The backend is responsible for asking *its* catalogue everything
its own model can answer.

Objects a given engine has and core does not -- Firebird generators and
domains, Oracle sequences, synonyms and packages, ClickHouse partitions and
storage definitions, BigQuery datasets, SQL Server schemas, extended
properties, procedures and functions -- get the backend's own statement
classes, formatters, manager factories and parsers. They are not squeezed into
core, and they are not hidden inside private helpers.

"Complete" means the engine can answer every question it is capable of
answering. It does not mean copying another backend, and it does not mean
deleting a fact that only this engine has in order to match core.

## 4. Every backend CLI can introspect, on one connection.

Each backend CLI has an `introspect` subcommand covering every question that
makes sense for the connection it was given.

That qualifier is the real difference: the connection arguments already name a
database (a file, a server, a port, a database), so cross-database and
cross-schema questions usually have no meaning from a CLI. A backend exposing
`list_tables(schema=...)` does not imply a `--schema` flag. Conversely, a type
listed by the CLI must actually be answerable -- never an option that ends in
`NotImplementedError`.

The type list is therefore owned by each backend (`INTROSPECT_TYPES` beside its
`introspect` command). It is a subset or a reshaping of the backend's
capability for the single-connection case, not a mirror of it, and core does
not arbitrate it.

## 5. Ownership is decided by divergence, and never by `extra`.

When backends answer a family differently, the difference itself decides where
the family lives. There are three bands:

- One shape, one question: core holds the smallest common type, every backend
  fills it.
- One question, drifted fields: core holds the common minimum -- the typed
  slots every engine can answer -- and each backend keeps its own complete
  class beside it. The core shape is the cross-dialect entry point, not the
  ceiling.
- A question only one engine asks: it does not enter core at all. The backend
  owns the statement, the type, the probe and the CLI type whole.

`extra` is not a place for other engines' facts, and it is not a way to widen a
signature: parameters that belong to one engine are named typed fields on that
engine's own class. The `extra` channel survives for one purpose only -- a
spelling that maps onto a core member (rule 2: BigQuery's `CLONE`,
ClickHouse's engines) -- never for a second family's fields. Where a
backend-specific family currently sits in core, it moves out; the paragraph in
`status/types.py` that steered such facts into `extra` is retired with the
move.

What the bands settled, concretely:

- **Sequences.** Core gains `SequenceInfo` as the common minimum: `name`,
  `schema`, `data_type`, `start_value`, `minimum_value`, `maximum_value`,
  `increment`, `cycle`, `cache_size`, `last_value`. The four parallel classes
  -- PostgreSQL's and MariaDB's `SequenceInfo`,
  `SQLServerSequenceInfo`, `OracleSequenceInfo` -- remain the complete
  semantics of their engines (name drift and all), and each must be
  projectable onto the core minimum.
- **Per-table storage.** Core widens `IntrospectionTableInfo` with
  `data_size_bytes` and `index_size_bytes` beside the existing `size_bytes`
  and `row_count`, and `supports_table_storage_introspection` gates the
  family. An engine that can answer it must: Firebird answers "not supported
  here", and its CLI offers nothing. An engine whose storage is not
  row-plus-index shaped -- ClickHouse, BigQuery, Snowflake -- leaves those two
  slots `None`; that is a legal answer, not a gap.
- **Status families one engine owns.** `WALInfo`, `ReplicationInfo`,
  `ArchiveInfo`, `SecurityInfo` move to PostgreSQL; `InnoDBInfo`,
  `BinaryLogInfo`, `SlowQueryInfo`, `ReplicationSlaveInfo`,
  `ReplicationMasterInfo`, `MySQLReplicationInfo` move to MySQL. Core's
  `ServerOverview` keeps the public slots only; a backend's overview is a
  subclass (`PostgreSQLServerOverview(ServerOverview)`,
  `MySQLServerOverview(ServerOverview)`) carrying its own typed fields, and
  `get_overview()`'s signature does not change. MariaDB writes its own binlog
  and replication classes when it answers that family -- it does not borrow
  MySQL's.

## 6. One enhancement lands whole: code, CLI, and capability together.

An introspection change that the backend's CLI cannot show is half a feature.
A family declared `supports_*` gets its CLI type in the same change, and the
type list stays derived from the capability mapping (`_TYPE_CAPABILITIES`),
so "answerable but unaskable" cannot happen and "unanswerable but offered"
stays refused. Per-table storage rides the existing `introspect tables`
columns on the narrow slots; an engine whose storage needs finer facts keeps
its own CLI type on its own class (Snowflake's `table-storage-metrics`).
Moving a type needs no CLI change -- the per-backend `_serialize_for_output`
recursion is agnostic to which module a dataclass came from.

## What follows for the code

- A statement collects all of its parameters at construction. There are no
  chained setters (`with_schema`, `for_table`, ...): a chain hides the final
  parameters from the IDE and from static analysis, which is exactly what
  one-shot construction exists to prevent.
- A question is three existing things, never a fourth: a statement class, a
  dialect `format_*_query_statement`, and a public manager method pair
  (`<family>_statement` / `parse_<family>`).
- Names carry no underscore. A method that would be private is either a
  public contract or a class that has not been written yet.
- Type relocation is consumed whole, in the feature branch that caused it:
  the move, the backend-side import change and the `ServerOverview` subclass
  all land in one change set. Version numbers in `pyproject.toml` stay
  untouched on feature branches: the merge carries the break, and numbering
  is the release process's alone -- this branch asserts nothing about it.
- mysql and mariadb look like copies -- SHOW node families, EXPLAIN rows,
  table options. No shared layer is extracted: the engines' evolution has
  already diverged (binlog, JSON explain) and a forced unification costs the
  second split later. The copies stay, and each repo's CHANGELOG annotates
  that the family has a twin in the other repo whose changes must be
  synchronized by hand.

## Checking it

Four mechanical checks belong in the shared test suite, one call per
repository:

1. no `def _name` inside the introspection packages (`__init__` and other
   dunders excepted);
2. no string literal that starts a statement (`SELECT`, `INSERT`, `UPDATE`,
   `DELETE`, `WITH`) and no f-string containing one;
3. every family declared by `supports_*_introspection()` has a matching
   `format_*_query_statement` that renders non-empty SQL;
4. every CLI type in a backend's `_TYPE_CAPABILITIES` names a `supports_*`
   switch that dialect actually declares, so a type cannot be offered
   without an answer behind it.
