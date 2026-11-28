# Artifact Format Reference

The complete specification of what `serialize()` writes and `deserialize()`
reads. Everything here is enforced by the code, not merely described by it.

> **Runnable**: `docs/examples/expression_artifact.py` walks the whole of it.

## Node Structure

An artifact is a **bare node. No envelope** (§4.11.3):

```python
{
    "kind": str,           # Required: the node's kind
    "params": dict         # Required: constructor parameters
}
```

| Field | Type | Constraint |
|-------|------|------------|
| `kind` | str | Non-empty; must be in the reader's registry |
| `params` | dict | Keys must match the target class's `__init__` parameter names |

There is no version, no module, no producer, no captured dialect, no connection
fingerprint, and nothing beyond `kind` and `params` at the node level. A node
carrying anything else is rejected by name, so a leftover envelope field cannot
ride along unnoticed.

## Where the kind comes from

`kind` is **computed from the class name**, never stored: a snake_case form, with
a run of capitals counted as one word (`JSONValue` → `json_value`). A class
carries no kind field, so the two cannot drift apart.

A **parameter** is an ordinary node under that same rule: its kind is
`parameter`, and its params are the constructor's own — `value` and `inline`.
Which value it holds is not an identity: the host value is carried as-is, with
no type name added. Two parameters holding a date and a string are the same
kind, and the reader cannot infer which host type either one held.

## Parameters

`params` holds every constructor parameter except **`dialect`**, which is
context and never travels: the same artifact re-renders under any dialect object
the reader hands it.

Each constructor parameter is one of three forms:

- a **language-independent JSON value** (null, boolean, number, string, array or object)
- a **host value carried as-is** — the `value` of a `Parameter`
- an **expression**, written as a nested `{kind, params}` node

There is no fourth form and no marker around a nested node or a value — the
shape and the node's own params *are* the signal. Whether a host value can be
written as JSON is its type's own contract, not a serializer rule. A `set`, a
driver handle, a closure or a pickled blob has no language-independent encoding;
if you need one to survive a JSON round trip, make it JSON-serializable, pass
`default=` to `serialize_json(...)` (forwarded to `json.dumps`), or model it as
an expression instead.

## Marker Types

**There are none.**

An artifact contains only JSON: null, booleans, numbers, strings, arrays, and
objects that are either a node or a plain mapping. A nested expression is a bare
`{kind, params}` node; a value held by a `Parameter` is carried unchanged in
`params.value`. Whether that value can be written as JSON is the value type's
own contract — the serializer adds no marker and consults no rule.

This is not a simplification. A marker is a *dispatch* — the reader has to
recognise the key and know what it means — and a dispatch is something every
language reimplements. The artifact is required to be byte-identical across
implementations, so anything a reader must dispatch on has to be something all
of them agree on by construction. A JSON scalar needs no agreement: every
language already parses one.

## Scalar Type Rules

| Python Type | JSON Representation | Notes |
|-------------|---------------------|-------|
| `str` | string | A `str`-based enum is one of these — it *is* its value |
| `int` | number | Arbitrary precision; a reader that cannot hold it must fail loudly |
| `float` | number | IEEE 754 bit pattern is what must survive, not the text |
| `bool` | boolean | |
| `None` | null | |
| `list` | array | Elements processed recursively |
| `tuple` | array | Goes out as an array. A structural tuple is restored to a tuple by its constructor; a tuple **value** comes back as an array — the reader cannot infer host types |
| `dict` | object | Values processed recursively |
| `BaseExpression` | object | A bare nested node |
| `set` | — | Not supported; convert to a list |
| Driver handles, closures, arbitrary objects | — | No language-independent encoding; model as an expression |

That table is for **structural** parameters — the constructor arguments that
shape the tree. A value held at a value position is different: it is a
`Parameter` node, and its `value` is carried as-is.

### Every parameter value travels as-is

A value that is **sent to the database** is held by a `Parameter`, and travels
unchanged — no text form, no type name, no conversion:

```python
# Parameter(dialect, 18)
{"kind": "parameter", "params": {"value": 18, "inline": false}}
```

Whether `json.dumps` can write that value is the **value type's own contract**.
Make the value JSON-serializable, or pass `default=` to `serialize_json(...)`
(forwarded to `json.dumps`). The serializer does not convert, name, validate or
reject value types: a `json.dumps` failure is the caller's problem, and no
serializer rule is consulted. On read, `deserialize_json(..., object_hook=...)`
forwards `object_hook=` to `json.loads` for caller-owned values; the codec
itself uses no hook.

`deserialize` hands the value back unchanged — no type dispatch, no unpacking.
`None` stays JSON null (SQL NULL). A tuple travels as a JSON array and comes
back as an array; the reader cannot infer host types. The distinction is between
the `parameter` **node** (kind `parameter`), an `SQLValue` / value result type
(which says what an expression yields), and the JSON-native value contract (what
`json.dumps` can write) — three separate things.

### Raw values and inline positions

A caller does not have to construct `Parameter` by hand. At a **value position**
— a comparison operand, an `IN` list, a `BETWEEN` bound, a `LIKE` pattern, a
function argument, an `INSERT`/`UPDATE` value, a DDL default — the framework
wraps a plain Python value into one. SQL therefore keeps its placeholder and the
value travels in `params`; it is never interpolated into the SQL text by the
caller. **Name positions** get no coercion: a table name, a column name or an
`ORDER BY` item stays an identifier, so the string `"id"` there is not the value
`'id'`.

`inline` is an **internal decision**, not a caller-facing type and not a second
kind. It is set for a grammar position that takes no placeholder — a DDL
`DEFAULT`, a `CHECK` operand, a partial-index `WHERE` — where the formatter asks
the dialect's `format_literal(value)` for escaped SQL text and the value no
longer appears in the **bind-parameter list** (it still travels in the artifact's
`params.value`). The default `inline: false` binds, which is what
every DQL/DML data position wants. Both cases serialize under the same
`parameter` kind; only the flag differs.

## Serialization Flow

1. Read `get_params()` — one attribute per `__init__` parameter, under its own
   name, `dialect` excepted.
2. Process each value: a `BaseExpression` becomes a nested node; a list, tuple or
   dict is walked; any other value — including a `Parameter`'s `value` — is
   carried unchanged.
3. Emit `{"kind": ..., "params": ...}`.

No registry is consulted. A node knows its own kind, so a caller that only
serializes never builds a lookup table.

## Deserialization Flow

The artifact is **untrusted input** (§4.11.4).

1. Reject a node with any field beyond `kind` and `params`.
2. Resolve `kind` through the registry's whitelist. The artifact never names a
   module: the table already holds the fully qualified class name for the kind,
   and that is the only name resolution imports. A kind the table does not hold
   is refused by name.
3. Require `params` to be an object, and check every key against the resolved
   class's `__init__` — an unrecognised parameter and a missing required one each
   fail by name.
4. Reject a class declaring `**kwargs`: a parameter whose identity depends on how
   many extras arrived cannot be matched by name on read.
5. Decode each value recursively and hand the result to the constructor **by
   name**. The decoder does no type checking of its own — validation belongs in
   `__init__`, where it can name the class and the parameter.
6. Bound nesting depth (64 by default) and total length.

### Not every kind is in the default table

`BaseExpression.REGISTER_BY_DEFAULT` decides. A node whose rendered SQL is
caller-vouched text sets it `False` — `RawSQL` and `RawSQLPredicate` do — so a
payload cannot name a kind whose `to_sql()` emits whatever the payload said.
That is a *default*, not a prohibition: `register_node` works exactly as it does
for any other kind, and a caller that trusts its artifacts can opt in.

### Failures

Every rejection names what it rejected, because an artifact you did not write
cannot be debugged by guessing:

| Situation | Message |
|-----------|---------|
| Kind not admitted | `kind 'x' is not in the kind whitelist (N kinds registered)` |
| Leftover envelope field | `artifact node has unexpected field(s) ['dialect']` |
| Missing kind | `artifact node has no usable 'kind' (got None)` |
| Unrecognised parameter | `kind 'x' does not accept parameter(s) [...]` |
| Missing required parameter | `kind 'x' is missing required parameter(s) [...]` |
| `**kwargs` declared | `kind 'x' accepts **kwargs, so its parameters cannot be matched by name` |
| Too deep | `artifact nesting depth exceeds 64` |

A `json.dumps` failure is not among them: it comes from `json.dumps`, not from a
serializer value-type rule.

All of them are `ArtifactError`, which subclasses
`ExpressionDeserializationError` — so a caller catches that one type.
`RegistryError` never escapes: the decode layer restates it in its own
vocabulary, because the registry is a lower layer and must not know what a
reader catches.

## Related Documents

- [Core Documentation](./serialization.md)
- [Extending Guide](./extending.md)