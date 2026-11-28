# Expression Serialization

> **Runnable example**: `docs/examples/expression_artifact.py`. Everything below is
> exercised there end to end.

## Design Motivation

An expression is a **value object**: the same query built twice must be equal,
and it must survive being written down and read back somewhere else — a cache,
a queue, another process.

The artifact is the whole of that. It is deliberately small, and everything
about its shape follows from one decision: **the artifact carries no import
path**. A dotted path in a payload is what would force a reader to import
whatever module the string pointed at, and an artifact is untrusted input. So a
node is named by a **kind** — a snake_case form of its class name — and that
kind is the node's identity, whether in memory or on the wire.

Two consequences worth stating up front:

- **Writing needs no registry.** A node reports its own kind, derived from its
  class name. A caller that only serializes never builds a lookup table.
- **Reading takes one.** Turning a kind back into a class is a question only a
  table can answer, and the caller decides which table.

## Core API

### serialize(expr)

```python
from rhosocial.activerecord.backend.expression_registry import serialize, serialize_json

artifact = serialize(query)
```

When the host values are JSON-native, plain `json.dumps` is enough — and
`serialize_json` is the shorthand that calls it for you:

```python
text = json.dumps(artifact)          # or: text = serialize_json(query)
```

A value that JSON cannot spell is the caller's responsibility: make the value
type JSON-serializable, or pass `default=` to `serialize_json(...)` (forwarded
to `json.dumps`). Without a hook, a value `json.dumps` cannot write is the
caller's problem. `serialize` carries the host value unchanged and never
converts, names, validates or rejects a value type.

### deserialize(artifact, *, registry=None)

```python
from rhosocial.activerecord.backend.expression_registry import deserialize

expr = deserialize(json.loads(text))
```

The codec needs **no `object_hook`** — there is nothing for it to do. The
artifact is plain JSON throughout: a node is `{kind, params}`, and a value
inside `params` is a scalar, an array, an object or a nested node. There are no
markers, so a node is recognised by its shape and nothing has to be decoded
before `deserialize` sees it. `deserialize_json(text, *, registry=None,
object_hook=None)` does accept an optional `object_hook=` and forwards it to
`json.loads`, for callers whose own values need reconstruction; the codec
itself never uses it. A value sent to the database is carried by a `parameter`
node as-is: `deserialize` hands it back unchanged, with no type dispatch and no
unpacking. `None` stays JSON null (SQL NULL); a tuple travels as a JSON array
and comes back as an array — the reader cannot infer the host type.

`registry=None` means **core's table**, never a framework-wide default. To read
a backend's own kinds, pass that backend's published table (for example
`SQLITE_EXPRESSION_REGISTRY`); see "Registry Ownership" below.

### serialize_json(expr, *, default=None) / deserialize_json(text, *, registry=None, object_hook=None) / deserialize_xml(payload, *, registry=None)

The same artifact in three renderings: a dict, a JSON text, an XML document.
All three rebuild the same instance; the parameters, and the SQL rendered from
it afterwards, must both come back unchanged. On the JSON rendering, `default=`
is forwarded to `json.dumps` and `object_hook=` to `json.loads`; both are caller
hooks for caller-owned values, and the codec uses neither.

## Artifact Format

A **bare node. No envelope.**

| Field | Type | Description |
|-------|------|-------------|
| `kind` | str | The node's kind (e.g. `column`, `comparison_predicate`) |
| `params` | dict | Constructor parameters, keyed by the `__init__` parameter names |

That is the whole thing — no version, no producer, no captured dialect, no
connection fingerprint.

```python
# Column("users", "id")
{
    "kind": "column",
    "params": {
        "name": "id",
        "table": {"kind": "table", "params": {"name": "users"}},
        "alias": None,
    }
}
```

A constructor parameter's value is either a **language-independent scalar**,
a host value carried as-is (a `Parameter`'s `value`), or an **expression**. The
third form — a nested `{kind, params}` node — is the same thing at a different
layer: a live instance in memory, an encoded node on the wire. No wrapper or
type tag is added, which is what makes the artifact readable at all.

Note there is **no wrapper** around a nested expression. The shape is the whole
signal, so there is nothing to unwrap and no second, weaker way of saying the
same thing. An `__expr__` envelope would have given one fact two spellings and
left the reader guessing which a payload used.

Note what is *not* there. The artifact carries no dialect, so the same payload
re-renders under any dialect object you hand it:

```python
deserialize(artifact).to_sql(SQLiteDialect(version=(3, 53, 0)))
```

## Bind Parameters

`to_sql()` returns a pair — the statement and the values to bind:

```python
sql, params = expr.to_sql()
# ("SELECT ... WHERE age > ?", (18,))
```

That `18` was never stored anywhere. It was read off the `parameter` node inside
the payload, where it travels unchanged as the host value:

```python
{"kind": "parameter", "params": {"value": 18, "inline": false}}
```

Every value that reaches SQL is a `parameter` node. A raw Python value at a
**value position** — a comparison operand, an `IN` list, a `BETWEEN` bound, a
`LIKE` pattern, a function argument — is wrapped into one by the framework at
construction, so the SQL text only ever holds placeholders and the value travels
in `params`. The same class serves an inlined position: `inline` is the internal
decision for a **grammar position that takes no placeholder**, such as a DDL
`DEFAULT` or a `CHECK` operand, and the formatter then asks the dialect's
`format_literal(value)` for escaped SQL text.

Name positions get no such coercion: a table name, a column name or an `ORDER BY`
item stays an identifier, so `"id"` there is not the value `'id'`.

The `parameter` node is an ordinary `BaseExpression`: its kind comes from the
class name (`parameter`), and its params are its constructor parameters,
`value` and `inline`. No value type is named, converted or validated. Whether
`json.dumps` can write the value is the value type's own contract — make the
value JSON-serializable or pass `default=` to `serialize_json(...)` (forwarded
to `json.dumps`). If `json.dumps` fails, that is the caller's problem, not a
serializer rule.

## Registry Ownership

A registry is not one framework-wide table; it is **one per owner**, and the
owner is the expression package that declares the kinds. Each table is plain
data — a `kind -> fully qualified class name` mapping:

| Owner | Entry point | Contents |
|-------|-------------|----------|
| core | `CORE_EXPRESSIONS` → `CORE_EXPRESSION_REGISTRY` | core's kinds only, with no backend among them |
| a backend | `SQLITE_EXPRESSIONS` / `SQLITE_EXPRESSION_REGISTRY`, `DUMMY_EXPRESSIONS` / `DUMMY_EXPRESSION_REGISTRY` | core's kinds ∪ that backend's own, never a sibling's |

- **Core collects its own packages.** `CORE_EXPRESSIONS` is the merge of
  `collect_expressions` over core's own packages — **node kinds only**,
  `parameter` among them; `CORE_EXPRESSION_REGISTRY` is
  `ExpressionRegistry(CORE_EXPRESSIONS).freeze()`, built once when the module is
  imported. Core knows no backend and keeps no list of them.
- **A backend joins its kinds by a dictionary merge**:
  `merge_expressions(CORE_EXPRESSIONS, SQLITE_EXPRESSIONS)` — the union
  `{**CORE_EXPRESSIONS, **SQLITE_EXPRESSIONS}`, refused if two mappings claim one
  kind with different classes. Two backends are never merged, so one backend's
  kinds do not become readable just because another backend is installed.
- **No dialect takes part.** A dialect is a renderer; it neither owns a table
  nor selects one.
- The artifact is still **dialect-free data**: a tree returned by
  `deserialize(artifact)` is unbound and renders through `to_sql(dialect)`.

The table `deserialize` uses is:

1. the `registry` the caller supplied explicitly;
2. otherwise `CORE_EXPRESSION_REGISTRY`.

A published registry is **frozen**. To widen or narrow it, start from `twin()`
(a mutable copy) or `merged()` (a frozen union), or build a fresh
`ExpressionRegistry(kinds)` from a mapping you composed yourself. Mutation or
assembly by anyone else cannot change a published table.

## Selective Registration

A registry is a **read-side boundary**: it filters what an artifact *contains*,
not what a class *declares*. A parameter left at its default produces no node,
and so needs no entry.

```python
from rhosocial.activerecord.backend.expression_registry import (
    CORE_EXPRESSION_REGISTRY,
    ExpressionRegistry,
)

read_only = ExpressionRegistry()
for kind in ("query_statement", "where_clause", "comparison_predicate",
             "column", "table", "parameter"):
    read_only.register_node(CORE_EXPRESSION_REGISTRY.resolve_node(kind))

deserialize(artifact, registry=read_only)
```

A selective table admits values by admitting `"parameter"`: every parameter is
that one node, whatever value it carries, so there is no per-value kind to
register. `CORE_EXPRESSIONS` is node kinds only, `parameter` among them.

A query without a grouping reads fine under that table; one with a `GROUP BY`
is refused, by name. That is the permission shape: **whatever this channel does
not accept, it cannot be made to accept by sending it something.**

Be clear about what a registry does *not* do. `serialize` consults no registry,
so a narrow table does not stop a tree being written, and it does not decide
what may be executed. It governs what a reader accepts from an artifact it did
not author. A boundary that had to hold on the write side would need a
different mechanism, because the writer is the same process that would enforce
it.

## Error Handling

Every rejection names what it rejected, because an artifact you did not write
cannot be debugged by guessing.

| Situation | Error |
|-----------|-------|
| A kind nobody registered | `kind 'x' is not in the kind whitelist` |
| A leftover envelope field | `a bare node carries exactly 'kind' and 'params'` |
| An unrecognised parameter | `kind 'x' does not accept parameter 'y'` |
| A missing kind | `the kind is the node's identity and is mandatory` |
| Nesting past the depth limit | `artifact nesting depth exceeds N` |

A `json.dumps` failure for a value JSON cannot write is not in this table: it is
raised by `json.dumps`, and no serializer value-type rule is consulted.

## Use Cases

### Cache Query Plans

```python
stored = json.dumps(serialize(query))
# ... later, in another process
query = deserialize(json.loads(stored))          # core's table
query.to_sql(SQLiteDialect(version=(3, 53, 0)))  # rendered here, not read
```

The cache holds JSON text, so it goes into any cache that stores strings. The
read rebuilds a tree and nothing more: the dialect is chosen when the tree is
rendered, so one cache serves every backend. A payload built from a backend's
own kinds is read with that backend's table
(`registry=SQLITE_EXPRESSION_REGISTRY`); the dialect still takes no part in the
read.

### Distributed Task Scheduling

A worker receives text and rebuilds the tree, then renders it under its own
dialect. Nothing about the payload is tied to the machine that produced it.

## Security Considerations

### No name in an artifact reaches an import

Resolution is by whitelist, never by import path. A payload naming
`os.system` gets "not in the kind whitelist" — it is looked up, found absent,
and the read fails. The only name that can reach an import is the fully
qualified class name the table already holds for a kind: registrations are
trusted data, and the artifact supplies nothing but the kind.

Nothing in the registry imports an expression package on its own initiative.
`collect_expressions` imports exactly the one package name it is handed; core
hands it core's own packages and a backend hands it its own, then publishes the
mapping it got back. There is no generic package walker, so nothing is
discovered: a table exists because an owner collected a package and said so.

### The artifact is untrusted input

- Unknown kinds, leftover fields and unrecognised parameters each fail by name.
- Nesting depth and length are bounded.
- No dialect-level validation happens here — that is left to `to_sql()`, where
  support questions belong.

### Do not hand-edit artifacts

```python
# Correct: build the tree, let the codec write it
text = json.dumps(serialize(query))

# Wrong: assembling a payload by hand couples you to a format the library
# does not promise to keep, and an artifact you did not write is exactly the
# input the reader is built to distrust.
```

## Related Documents

- `docs/examples/expression_artifact.py` — a runnable end-to-end example
- `.claude/plan/2026-10-12/表达式-方言架构规则.md` §7, §10 — registry and artifact rules