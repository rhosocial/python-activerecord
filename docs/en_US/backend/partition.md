# Partition Maintenance Contract

Partition maintenance lives in the backend. PostgreSQL owns a recursive tree
with heterogeneous child strategies; Oracle owns one table-level subpartition
strategy; SQL Server owns a partition function plus a scheme; MySQL and MariaDB
own a flat set of caller-owned definitions; ClickHouse owns a server-assigned
partition id and only `DROP` / `DETACH` / `ATTACH`. Core does not define a plan
grammar for any of them.

What core defines is the shape of the answer and the verbs a caller may detect
on an executor, so a caller can read a report without knowing which engine
produced it.

## Value objects

All three live in `rhosocial.activerecord.backend.partition`.

### PartitionInfo

One partition row as the catalogue reports it.

| Field | Meaning |
|---|---|
| `name` | Partition or subpartition name, as the server spells it |
| `parent` | Containing object, or `None` for a row at the top of the target |
| `level` | Nesting depth: `0` root, `1` first-level partition, `2` subpartition |
| `method` | Strategy word the server reports (`RANGE`, `LIST`, `HASH`, `KEY`) |
| `bound` | Boundary text verbatim; never parsed |
| `schema` | Schema, when the engine has schemas |
| `row_count` | Row count, when the catalogue exposes it |
| `size_bytes` | On-disk size in bytes, when the catalogue exposes it |
| `is_partitioned` | Whether the row itself has children |
| `extras` | Engine-specific facts that no second engine shares |

`extras` is intentionally a mapping rather than a widening set of fields:
SQL Server's partition number, Oracle's subpartition count, ClickHouse's
partition id, and MySQL's child names belong to one engine each.

### PartitionOperation

One statement the executor ran, or would run under a dry run.

| Field | Meaning |
|---|---|
| `action` | Verb in the backend's own spelling (`create`, `drop`, `split`, `merge`, `detach`, ...) |
| `name` | Object the statement acts on |
| `parent` | Containing object, when the statement has one |
| `sql` | Rendered SQL, when the backend records it |
| `level` | Nesting depth of the affected object, when it has one |

The action word is free-form on purpose. Normalizing `split` and `merge` into
`alter` would hide the distinction the operator needs.

### PartitionReport

One envelope for the catalogue state and the operation's outcome.

| Field | Meaning |
|---|---|
| `target` | Scope: a parent table, a table, or a partition function/scheme |
| `engine` | Backend name, when the executor records one |
| `extras` | Engine-specific report facts, such as SQL Server's function/scheme/table collections |
| `partitions` | Catalogue rows in the order the backend read them |
| `missing` | `(parent, name)` pairs the plan expects but the catalogue lacks |
| `orphans` | Existing partitions the plan does not describe |
| `issues` | Read-only findings: gaps, overlaps, strategy mismatches |
| `operations` | Statements the executor ran or would run |
| `added` | Names created, for backends that report by name rather than by statement |
| `dropped` | Names removed |
| `skipped` | `(name, reason)` pairs for work deliberately refused |
| `errors` | Per-statement failures on engines with non-transactional DDL |
| `dry_run` | Whether the report describes work that was not executed |

Convenience helpers:

- `children_of(name)` — direct children of a row.
- `partition_names` — names at the top of the target, excluding the target row
  itself.
- `tree` — direct children grouped by parent. A flat report produces `{}`,
  which says there is no tree rather than inventing one.
- `leaves` — rows that no other row names as its parent. In a flat report every
  row is a leaf.
- `has_errors` — whether `errors` is non-empty.

## Batch and paired reports

`PartitionBatchReport` wraps the reports of several targets and adds the drift
between pairs the caller declared as "must match". It does not flatten the
per-target reports: each target keeps its own `missing` and `orphans`.

| Field | Meaning |
|---|---|
| `reports` | `target -> PartitionReport`, the original report of each target |
| `pairs` | Pair names the caller declared, in declaration order; empty for an independent batch |
| `differences` | First-level partitions present on exactly one side of a declared pair |
| `issues` | Reasons a pair could not be compared: incompatible plans, boundary disagreement |

`PairedDifference` describes one row of `differences`:

| Field | Meaning |
|---|---|
| `pair` | Caller-chosen pair name, such as `log_tables` |
| `key` | Normalized bucket the two sides are compared on, such as `2026_01` |
| `present_in` | Side that holds the row: `left` or `right` |
| `left_partition` | Name the left catalogue reported, or `None` |
| `right_partition` | Name the right catalogue reported, or `None` |

`differences` has narrower B semantics than the symmetric difference of the two
reports' `missing` collections:

- It only names actual first-level partitions that one side holds and the other
  does not. `present_in` says which side owns the row.
- A bucket absent from both sides is not a difference. It stays in each
  report's own `missing`, because it is a per-target fact.
- A bucket present on both sides whose boundary text disagrees is not a
  difference either. It goes to `issues`, because the pair is structurally
  incomparable.
- Incompatible plans (method, columns, interval or explicit bounds) also go to
  `issues`; no differences are emitted for them.
- Differences are ordered by `(pair, key)`, so two backends that saw the same
  drift emit the same order.

`extras` is only for facts that are temporary or unique to one engine. A
stable, shared shape does not go into `extras`: add a field to the core object,
or subclass it in the backend and document the extra field. Never introduce a
private key that other backends then have to mimic.

## Protocols

Each verb is its own protocol. One protocol declaring every verb would claim
too much: MySQL has no `validate`, ClickHouse has no `ensure`, and SQL Server
merges a boundary where PostgreSQL drops a range.

| Verb | Sync protocol | Async protocol | Backends that offer it |
|---|---|---|---|
| Read the tree | `PartitionInventory` | `AsyncPartitionInventory` | PostgreSQL, Oracle, SQL Server, MySQL, MariaDB |
| Create what is missing | `PartitionEnsurer` | `AsyncPartitionEnsurer` | PostgreSQL, Oracle, SQL Server, MySQL, MariaDB |
| Drop before a cutoff | `PartitionRetention` | `AsyncPartitionRetention` | PostgreSQL, Oracle, MySQL, MariaDB |
| Report findings only | `PartitionValidator` | `AsyncPartitionValidator` | PostgreSQL, Oracle, SQL Server |

ClickHouse is deliberately absent. Its maintenance surface is
`DROP` / `DETACH` / `ATTACH` by a server-assigned partition id, with no plan,
no report and no `ensure`; wrapping those rows in this envelope would add a
translation no caller needs. The ClickHouse service keeps its own
introspection rows and its own tests. SQL Server is absent from
`PartitionRetention` for the same reason: it merges a boundary with
`drop_or_merge` instead of dropping a range, and that verb is not the same
operation under another name.

Detection uses `isinstance`:

```python
from rhosocial.activerecord.backend.partition import PartitionRetention

if isinstance(executor, PartitionRetention):
    report = executor.drop_before(plan, cutoff, dry_run=True)
```

`isinstance` on a runtime-checkable protocol inspects method presence. It
cannot tell a sync executor from an async one, because the method names are
identical by design; the caller already knows which backend object it holds.

## What stays engine-specific

- The plan and policy classes, including tree depth, subpartition strategy,
  naming, boundary direction, filegroups and server partition ids.
- The destructive verb: `drop_before` on a boundary, `drop_or_merge` on SQL
  Server, `drop_partition(name)` on Oracle, `detach` / `attach` on ClickHouse.
- Transaction semantics. PostgreSQL and MySQL can wrap a unit of work; Oracle
  commits per statement and reports partial failures in `errors`.
- Reasons a requested change needs a different verb first, such as MySQL's
  `REORGANIZE PARTITION` requirement or Oracle's `MAXVALUE` terminator.
