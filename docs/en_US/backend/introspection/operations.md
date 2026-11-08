# Operational Introspection

The [declaration layer](../introspection.md) answers what the server *is*: its
tables, columns, indexes, and what they declare. [Column data
profiles](data-profiles.md) answer what the rows *hold*. The six families on this
page answer a third question: what the server has *been doing*.

The tense is the point. A declaration is a present-tense fact, true until the
schema changes. An operational answer is a past-tense count over a window the
server defines, and it is true only of that window. Most misreadings here come
from reading a past-tense number as a present-tense property: an index with a
zero counter becomes "unused" rather than "unused since the last reset", a table
nobody scanned becomes "cold" rather than "not read in the window".

| Method | The question |
|--------|--------------|
| `list_unused_indexes(schema=None)` | Which indexes served no query in the window the server remembers |
| `list_table_usage_stats(schema=None)` | How often each table was read and written in that window |
| `list_runtime_metrics(schema=None)` | What the server itself has been doing |
| `list_index_usage_stats(schema=None)` | How much each index was used, not only whether it ever was |
| `list_object_dependencies(object_name=None, schema=None)` | Which object needs which, and what breaks if one is dropped |
| `get_ddl_statement(object_name, object_type=None, schema=None)` | The text that recreates one object |

## The Tense of the Answer

The list-returning families here return narrow records, each carrying whatever
identifies the thing measured -- an address for an object, a name for a
measurement -- plus an `extra` mapping for anything the server reports beyond the
common slots. Two conventions hold across all six. An absent slot is `None` and
means not measured, never zero: a server that does not count a thing says so by
leaving the slot out rather than by reporting a zero it never measured. And a
window travels with the number that needs one, because a count without its
window is not a fact.

## list_unused_indexes

An index is unused when its counter is zero. That is all this layer can say, and
it is weaker than the word suggests: zero means no scan in the window the server
remembers, not no scan ever. The method returns the address of each such index --
schema, table, index -- because an address is what every server that can answer
at all can supply; any further number rides in `extra` and means what the server
says it means.

An unused index is a fact about the database rather than about one table, which
is why the call takes no table name. Narrowing is the caller's job; a formatter
asked to filter by table would have to invent a filter its statistics cannot
honour, and an invented filter is worse than a reported answer.

### Zero Is a Window, Not a Lifetime

The window starts at the last reset -- a restart, a statistics reset, a flush of
the counters -- events whose schedule the backend's documentation names. Zero says
no scan happened in that stretch of time, so an index that has served queries for
years can report zero the day after a reset. Nothing in the answer dates the
window; treat the number as relative to an unstated moment unless the connection
tells you otherwise.

Absence is weaker still. An index missing from the listing is not proof that it
was used: it may fall outside the statistics the server can see, or below a
threshold the listing applies. Treat a miss as no evidence, never as evidence of
use.

### Review, Not Proof

Zero makes an index worth reviewing, not safe to drop: it may serve a query whose
counters are attributed elsewhere, enforce a constraint, or be the only one that
makes a rare query tolerable. The family reports; the decision belongs to a
reader who knows what the index is for.

## list_table_usage_stats

`list_table_usage_stats()` reads every table's counters in one query for the
schema: sequential and indexed reads, inserts, updates, deletes, plus the row
estimate that turns a scan count into a share of the table. One query rather than
one per table, because the first read of a statistics collector is priced far
above the next, and a per-table form would invite looping the catalogue.

### Every Counter Is Since Something

Every counter is since the statistics were last reset, and a slot the server does
not track is `None` rather than zero. Zero has a meaning here -- nothing happened
in the window -- and it is a different fact from "this server keeps no such
counter", which is why the parser leaves the slot out instead of writing a zero
over it.

A zero on the write side and a zero on the read side support different
conclusions: one says a table is written but never read, the other says it is
read but never written. Neither survives being read as "no activity at all".

## list_runtime_metrics

`list_runtime_metrics()` returns measurements of the server rather than of a
table: concurrency, throughput, latency, failures, whatever the connection can
report as a named number. Its items carry a name and a value, an optional `kind`,
`unit` and `description`, and `source` -- the window the number covers.

### No Table Name, Deliberately

The statement takes a schema but no table name, and the omission is the contract.
A runtime measurement is not attached to a table, so a table filter would discard
rows that were never about a table; a filter that does not apply is worse than no
filter, because it looks like an answer.

`kind` stays `None` unless the server named one: guessing whether a metric is a
rate or a duration from its name would turn the server's statistics into this
library's interpretation. `source` is where the meaning lives. A throughput
figure covering a minute and one covering a day are both true, and neither is
useful without the sentence that says which.

## list_index_usage_stats

`list_index_usage_stats()` is the stronger reading of the same subject. Where the
unused listing gives a yes-or-no answer, this one gives the numbers behind it:
`scans`, `rows_read`, `rows_fetched` and `size_bytes`, each present only where
the server counts it. The two families stay separate rather than becoming one
type with an unused flag: a reader asking whether an index earns its space wants
the counters, and a reader running a hygiene pass wants the short list.

### How Much, Not Only Ever

A counter of one scan and a counter of a million describe different indexes, and
the unused listing cannot distinguish them. The counters also answer what the
listing cannot: an index used once is not unused, but it may still not be worth
its bytes. A slot the server does not count is `None`; a zero is a measurement.

## list_object_dependencies

`list_object_dependencies()` returns the dependency graph as edges: a dependent
object, the object it needs, the relation between them, and the drop behaviour
where the server declares one. Naming `object_name` narrows the answer to that
object's dependants -- the "what breaks if I drop this" question; omitting it
returns the whole graph, which is larger and slower.

### Direction Is Fixed

`dependent` needs `referenced`, and the direction is not negotiable: a reader
asking what breaks is asking about dependants, not about dependencies. Reversing
the pair turns every answer into its mirror image and makes a safe drop look
dangerous, or a dangerous one look safe.

### The Edge Is the Engine's Record

The edge is what the engine records, not what this library infers from names and
call sites. A view on a table, an index on a table, a function used by a trigger:
each is an edge because the catalogue declares it, and `kind` carries the
relation in the engine's own vocabulary because there is no standard one.

An engine that records a narrower set of edge kinds is answering its own
catalogue honestly, and what each kind means is stated in that backend's own
documentation.

`action` decides whether the drop is safe: CASCADE, RESTRICT or SET NULL where
the server declares one, and `None` where it does not. A graph without `action`
still says what depends on what; it just does not say what the drop will do.

## get_ddl_statement

`get_ddl_statement()` returns the text that recreates one object -- the answer to
"what did this actually get created as", which structure introspection cannot
reconstruct: a check expression, a generated column's expression, a storage
parameter and a trigger body exist only in text the server kept. It is always
about one object, because the text is large and the question is always asked of
a specific thing.

### native Says Which

`DDLStatement.native` says where the text came from: `True` for the server's own
retrieval, `False` for an assembly this library built out of catalogue facts, and
`None` when the server answered without saying. The distinction is not a
formality. An assembly is a reconstruction and therefore lossy: it can reproduce
the columns and miss the storage options, so a caller deciding whether to trust
the text has to know which it holds.

### None Is Not Missing

`None` means the DDL could not be reproduced, not that the object does not exist.
The object was found; the server declined or the library could not assemble it.
A caller that reads `None` as "no such table" reports a missing object for one
that is present and working. A row carrying no text is skipped rather than
returned with an empty `ddl`, because a caller asked for text and absence of text
is not a value.

Check `supports_ddl_extraction()` before the call, and
`supports_ddl_extraction_native()` when the origin matters. A server can be able
to answer and unable to answer natively, and a caller that needs the original
must not accept a reconstruction in its place.

```python
ddl = backend.introspector.get_ddl_statement("orders", object_type="table")
if ddl is None:
    print("DDL could not be reproduced")
else:
    print(ddl.native, ddl.ddl)
```

## What They Cost

The families that read counters are catalogue reads on a connection that keeps
them, and scans on one that does not. Which of the two a family is depends on the
connection rather than on the family: unused-index detection may be a listing
over kept statistics or an aggregation somebody has to pay for, and the same
method name covers both. The probe is how a caller learns which before paying.

Every one of them is cached, and cached answers age faster here than in the
declaration layer. A schema cached yesterday is probably still the schema; a
counter cached yesterday describes a window that has since kept running.

A family that cannot answer is a `False` probe, not an empty list. The empty
list is reserved for a question that was asked and had nothing to report, and
keeping those apart lets a report say which of the two it is showing.
