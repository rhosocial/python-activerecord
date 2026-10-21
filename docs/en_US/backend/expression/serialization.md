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
from rhosocial.activerecord.backend.expression.serialization import serialize

artifact = serialize(query)
```

The artifact is JSON-native, so it goes through a plain `json.dumps` with no
custom encoder:

```python
text = json.dumps(artifact)
```

### deserialize(artifact, dialect, registry=None)

```python
from rhosocial.activerecord.backend.expression.serialization import deserialize

expr = deserialize(json.loads(text), dialect)
```

`json.loads` needs **no `object_hook`** — and there is nothing for a hook to do.
The artifact is plain JSON throughout: a node is `{kind, params}`, a parameter
is a scalar, an array or an object. There are no markers, so nothing has to be
recognised in order to be decoded. The one thing JSON cannot spell — a value
sent to the database, such as `bytes` or a `timedelta` — is carried as the text
its kind names.

`registry=None` means the framework's default instance — every node the
distribution ships. Pass your own to control exactly which kinds a read may
produce.

### deserialize_json(text, dialect, registry=None) / deserialize_xml(bytes, ...)

The same artifact in three renderings: a dict, a JSON text, an XML document.
All three round-trip to the same instance; the parameters and the rendered SQL
must both come back unchanged.

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

A parameter is either a **language-independent scalar** or an **expression**.
The second form — a nested `{kind, params}` node — is the same thing at a
different layer: a live instance in memory, an encoded node on the wire. There
is no third form, which is what makes the artifact readable at all.

Note there is **no wrapper** around a nested expression. The shape is the whole
signal, so there is nothing to unwrap and no second, weaker way of saying the
same thing. An `__expr__` envelope would have given one fact two spellings and
left the reader guessing which a payload used.

Note what is *not* there. The artifact carries no dialect, so the same payload
re-renders under any dialect object you hand it:

```python
deserialize(artifact, SQLiteDialect(version=(3, 53, 0))).to_sql()
```

## Bind Parameters

`to_sql()` returns a pair — the statement and the values to bind:

```python
sql, params = expr.to_sql()
# ("SELECT ... WHERE age > ?", (18,))
```

That `18` was never stored anywhere. It was read off the `literal` node inside
the payload, so nothing else carries it and nothing else can disagree with it.
Expressions never inline a value into the SQL text; the database never sees a
quoted string built by concatenation.

## Selective Registration

A registry is a **read-side boundary**: it filters what an artifact *contains*,
not what a class *declares*. A parameter left at its default produces no node,
and so needs no entry.

```python
from rhosocial.activerecord.backend.expression.registry import ExpressionRegistry

read_only = ExpressionRegistry()
for kind in ("query_statement", "where_clause", "comparison_predicate",
             "column", "literal", "table"):
    read_only.register_node(default_registry().resolve_node(kind))

deserialize(artifact, dialect, registry=read_only)
```

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

## Use Cases

### Cache Query Plans

```python
stored = json.dumps(serialize(query))
# ... later, in another process
query = deserialize(json.loads(stored), dialect)
```

The cache holds JSON text, so it goes into any cache that stores strings, and
the dialect is chosen at read time — one cache serves every backend.

### Distributed Task Scheduling

A worker receives text and rebuilds the tree under its own dialect. Nothing
about the payload is tied to the machine that produced it.

## Security Considerations

### No name in an artifact reaches an import

Resolution is by whitelist, never by import path. A payload naming
`os.system` gets "not in the kind whitelist" — it is looked up, found absent,
and the read fails. There is no code path that could have imported it.

The registry module does not import expression packages at all, and the
mechanism that assembles the default instance lives with the framework, not in
the registry. A registry cannot discover anything.

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