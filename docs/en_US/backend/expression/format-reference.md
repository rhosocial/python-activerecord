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

There is no `type`, no `module`, no version, no producer, no captured dialect,
no connection fingerprint. A node carrying anything beyond `kind` and `params`
is rejected by name, so a leftover envelope field cannot ride along unnoticed.

## Where the kind comes from

`kind` is **computed from the class name**, never stored: a snake_case form, with
a run of capitals counted as one word (`JSONValue` → `json_value`). A class
carries no kind field, so the two cannot drift apart.

A **literal** is the one node whose kind is not its class name. One node carries
every value and the wire still names them apart — `null_value`, `integer_value`,
`date_value`, … — because a date's spelling and a string's are the same bytes and
only the kind tells them apart. The value kind is the node's identity on the wire;
`Literal` is merely what all of them resolve to.

## Parameters

`params` holds every constructor parameter except **`dialect`**, which is
context and never travels: the same artifact re-renders under any dialect object
the reader hands it.

Each parameter is one of exactly two forms:

- a **language-independent scalar** (JSON-native, or one of the markers below)
- an **expression**, written as a nested `{kind, params}` node

There is no third form, and no marker around a nested node — the shape *is* the
signal. A `set`, a driver handle, a closure or a pickled blob has no
language-independent encoding and is therefore not serializable; model it as an
expression instead.

## Marker Types

**There are none.**

An artifact contains only JSON: null, booleans, numbers, strings, arrays, and
objects that are either a node or a plain mapping. A nested expression is a bare
`{kind, params}` node; a value JSON cannot spell travels as the text its kind
names.

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
| `tuple` | array | The parameter's declared type says it was a pair; the constructor restores it |
| `dict` | object | Values processed recursively |
| `BaseExpression` | object | A bare nested node |
| `set` | — | Not supported; convert to a list |
| Driver handles, closures, arbitrary objects | — | No language-independent encoding; model as an expression |

### Bind values are the one exception

A parameter that is **sent to the database** may hold a type JSON has no spelling
for. It is wrapped in a `Literal`, and its kind names the text:

| Kind | Carries | Wire form |
|------|---------|-----------|
| `binary_value` | `bytes` | base64 string |
| `interval_value` | `timedelta` | ISO 8601 string — days/hours/minutes/seconds, since years and months have no fixed length |
| `decimal_value` | `Decimal` | exact decimal string, never a float |
| `timestamp_value` / `date_value` / `time_value` | date and time | ISO text |
| `uuid_value` | `UUID` | canonical text |

The kind is the whole reason a kind exists here: a date's spelling and a
string's are the same bytes, and only `date_value` tells them apart. The
constructor takes the scalar back and converts it.

## Serialization Flow

1. Read `get_params()` — one attribute per `__init__` parameter, under its own
   name, `dialect` excepted.
2. Process each value: a `BaseExpression` becomes a nested node; a list, tuple or
   dict is walked; everything else must already be a JSON scalar.
3. Emit `{"kind": ..., "params": ...}`.

No registry is consulted. A node knows its own kind, so a caller that only
serializes never builds a lookup table.

## Deserialization Flow

The artifact is **untrusted input** (§4.11.4).

1. Reject a node with any field beyond `kind` and `params`.
2. Resolve `kind` through the registry's whitelist. There is no import path and
   no reflection: a name is either registered or refused by name.
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
| Leftover envelope field | `artifact node has unexpected field(s) ['type']` |
| Missing kind | `artifact node has no usable 'kind' (got None)` |
| Unrecognised parameter | `kind 'x' does not accept parameter(s) [...]` |
| Missing required parameter | `kind 'x' is missing required parameter(s) [...]` |
| `**kwargs` declared | `kind 'x' accepts **kwargs, so its parameters cannot be matched by name` |
| Too deep | `artifact nesting depth exceeds 64` |

All of them are `ArtifactError`, which subclasses
`ExpressionDeserializationError` — so a caller catches that one type.
`RegistryError` never escapes: the decode layer restates it in its own
vocabulary, because the registry is a lower layer and must not know what a
reader catches.

## Related Documents

- [Core Documentation](./serialization.md)
- [Extending Guide](./extending.md)