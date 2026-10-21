# Extending Guide: Implementing Serializable Expressions

This document is for backend developers, explaining how to make custom expressions serializable.

## Basic Requirements

Expression classes must meet the following requirements to be correctly handled by the serialization framework:

1. Inherit from `BaseExpression`
2. `__init__` parameter names must correspond to attribute names (using `_` prefix for private attributes or same-named attributes)
3. Do not implement `get_params()` — the generic implementation is the single serialization path, so `__init__` must store its state under the name the constructor received it as

## get_params() Convention

The generic `get_params()` implementation automatically infers using `inspect.signature`:

- Parameter `foo` → attribute `self._foo` or `self.foo`
- `VAR_POSITIONAL (*args)` → list
- `VAR_KEYWORD (**kwargs)` → the extras, collected into a dict stored on an attribute named after the parameter (e.g. `self.collation_options`) and merged into the top level of `params`, so reconstruction re-expands them

```python
class MyExpression(BaseExpression):
    def __init__(self, dialect, name, value):
        super().__init__(dialect)
        self._name = name
        self._value = value
    # No need to manually implement get_params(), default implementation auto-extracts
```

`CollateFunction` is the `**kwargs` case in core: it collects `**collation_options` into `self.collation_options: dict`, so `get_params()` returns `binary`, `pad` and the rest as top-level parameters and reconstruction passes them back as keywords.

A parameter the convention cannot resolve is skipped with a warning. That warning is the diagnostic — it means `__init__` stores state under a name `get_params()` cannot see — and the repair is always in `__init__`.

### Why There Is No Custom get_params()

`get_params()` is not an extension point: an override is a defect, not a customization. Core enforces this with no exceptions in `tests/.../dummy2/test_expression_artifact_contract.py::test_no_get_params_override` — every registered expression class must leave the generic implementation alone. (The single exemption the test allows, a `VAR_POSITIONAL` class doing genuine raw-vs-normalized round-trip rewriting, has no instance in the core registry.)

The reason is structural rather than stylistic. A round-trip is rebuilt by calling the constructor with whatever `get_params()` returned, so those two halves have to agree. An override is exactly where they drift: the class emits a key the constructor renames, merges or refuses, and the state is silently gone — the decoder hands values over by name and does not second-guess the result. The backend packages accumulated their own overrides, every one of them written because `__init__` renamed or merged what the caller passed — and every one of them became unnecessary once the state was stored under the name it was given.

When the generic result is not what you wanted, the repair is always in `__init__`, and it is one of three shapes:

| The problem | The repair |
|---|---|
| You renamed or merged what the caller passed | Store it under the name the parameter has |
| Two constructor spellings mean one thing | Keep both slots; put the value in the one the caller used and leave the other `None` |
| The value cannot be serialized as it stands | Convert it in `__init__` and store the converted value |

## Registration Mechanism

### Auto-Registration

Built-in expressions need nothing from you. The framework assembles its default
registry once, by walking the expression packages, and every node it finds is
registered by its kind. There is no function for a caller to invoke and no
list to maintain.

### Registering Your Own

`ExpressionRegistry` starts empty — that is what makes it safe to hand a caller
a table that admits only what you chose. `register_node` is an instance method
and the kind is derived from the class:

```python
from rhosocial.activerecord.backend.expression.registry import ExpressionRegistry

allowed = ExpressionRegistry()
allowed.register_node(MyExpression)          # kind "my_expression"
```

An enum needs no registration at all. A `(str, Enum)` member is a JSON string,
so there is nothing to resolve — the closed set is declared in the class, where
every language declares its own.

Two kinds ship without being in the default table: `RawSQL` and `RawSQLPredicate`,
because `to_sql()` emits caller-vouched text and an artifact should not be able
to choose it. They set `REGISTER_BY_DEFAULT = False`; registering either one is
the same call as any other, for a caller that trusts its artifacts.

Then pass it to the read:

```python
deserialize(artifact, dialect, registry=allowed)
```

A registry only governs what a *reader* may produce. Writing consults none, so
nothing here affects `serialize`.

## Four Special Cases

The four cases below are the usual reasons a developer reaches for a custom `get_params()`. None of them needs one: each is solved in `__init__`.

### 1. Dialect-Specific Enum Parameters

Some dialects have specific enum values (e.g., PostgreSQL's `IsolationLevel`). Accept whichever spelling the caller has and store the value the spec can carry:

```python
class MyTransactionExpression(BaseExpression):
    def __init__(self, dialect, isolation_level="READ COMMITTED"):
        super().__init__(dialect)
        # Accept the dialect's enum or its string; store the normalized string
        self._isolation_level = (
            isolation_level.value
            if isinstance(isolation_level, Enum)
            else str(isolation_level)
        )

# get_params() returns {"isolation_level": "SERIALIZABLE"} — a string, dialect-independent
# and reconstruction passes that string back into a constructor that accepts one
```

### 2. State Set via Fluent API

State modified via fluent API must be synced to `__init__` parameters — the setter and the parameter have to read and write the *same* attribute, because that attribute is all `get_params()` ever sees:

```python
class MyExpression(BaseExpression):
    def __init__(self, dialect, hint: str = None):
        super().__init__(dialect)
        self._hint = hint  # Both __init__ parameter and fluent API target

    def with_hint(self, hint: str):
        self._hint = hint
        return self
```

A setter that writes a second attribute alongside the parameter's own is writing state the round-trip cannot see.

### 3. set Type Parameters

A `set` is a poor carrier for expression state: it has no order, and the codec encodes it as a flat list whose members never receive the nested-expression markers they would need, so a `set` of expressions does not survive a JSON round-trip. Convert in `__init__` and store the converted value — the generic path then emits exactly what the constructor accepts:

```python
class ColumnSetExpression(BaseExpression):
    def __init__(self, dialect, columns):
        super().__init__(dialect)
        self._columns = list(columns)  # set or any iterable in, list stored

# get_params() returns {"columns": [...]}; reconstruction passes the list back
# into the same constructor, which accepts a list just as happily
```

### 4. Circular References

The framework does not detect cycles, and a self-reference cannot be serialized — the serializer would recurse until Python's recursion limit. Store the link by identity rather than by object: the parameter is the id, and the object, if it is needed at all, lives on an attribute the constructor does not take, which `get_params()` never reads.

```python
class TreeNodeExpression(BaseExpression):
    def __init__(self, dialect, name, parent_id=None):
        super().__init__(dialect)
        self._name = name
        self._parent_id = parent_id  # identity, not the object
        # Resolved by the tree walker; no matching parameter, so never serialized
        self._parent = None
```

When the parent genuinely has to travel with the node, make it an ordinary nested-expression parameter — a plain `parent` holding another expression, which serializes as a nested `{kind, params}` node. The tree is then simply finite.

## IntrospectionExpression Convention

An introspection node combines a constructor with fluent setters, and the two used
to want the same names. They no longer do, because a parameter has to be
readable by its own name for an artifact to be rebuildable at all:

```python
class TableListExpression(IntrospectionExpression):
    def __init__(self, dialect, schema=None, include_views=True, include_system=False, table_type=None):
        super().__init__(dialect, schema)
        self.include_views = include_views   # the parameter's own name
        self.include_system = include_system
        self.table_type = table_type

    def with_include_views(self, value: bool = True):   # never plain `include_views`
        self.include_views = value
        return self
```

- **One spelling, and it is the parameter's own name.** `get_params()` reads
  `getattr(self, name)`. There is no `_{name}` probe, and no "the callable one is
  not the state" rule to apply. A parameter the class did not store raises
  `AttributeError` naming the class and the parameter — which is the defect
  worth hearing about, rather than a warning nobody reads.
- **A fluent setter is `with_*`.** A setter called `include_views` would occupy
  the name the value itself needs, and the class would have to choose between
  `self.include_views = value` (which shadows the method) and hiding the value
  where `get_params()` has to go looking for it.
- **An optional parameter left unset is emitted as `null`, not omitted.** That is
  safe: the deserializer passes it back and the constructor's default applies.
  What is *not* safe is dropping a parameter whose value differs from its
  default — that is state the round-trip loses.

## Error Contract

Everything a read can reject surfaces as `ExpressionDeserializationError`, so a
caller catches that one type and nothing else:

```
ExpressionDeserializationError
├── ArtifactError                    — the artifact itself is malformed
└── a registry refusal, restated     — the kind is not admitted here
```

`ArtifactError` is the *subclass*, so `except ExpressionDeserializationError`
covers both. `RegistryError` never reaches a caller: the decode layer restates it
in its own vocabulary, because the registry is a lower layer and must not know
what a reader catches.

A `TypeError` from your own constructor is **not** caught for you. An artifact
carrying `{"name": 123}` for a `name` parameter rebuilds without complaint when
the constructor does not check. Validate there if it matters — the deserializer's
job is to hand values over by name, not to decide whether they are acceptable.

## Parameter Convention (JSON scalars)

**There are no reserved keys any more.** An artifact is plain JSON, so a
parameter's value must already be something JSON can say: null, a boolean, a
number, a string, an array, or an object.

That gives a custom expression two obligations and one option.

- **A closed value set takes a string enum.** Declare it `(str, Enum)` and set
  `__str__ = str.__str__` so the member *is* the word it renders — `(str, Enum)`
  alone does not do that, `Enum.__str__` wins. The wire form is then the member's
  value, which is a JSON string, and the closed set is declared in code where
  every language can declare it too. An enum that does not subclass `str` cannot
  be written at all.
- **A value sent to the database goes in a `Literal`.** That is the one place a
  type JSON cannot spell may appear; the `LiteralKind` member names the text.
- **An opaque payload is the hazard.** A `dict` of keys you do not control is
  copied verbatim into the artifact, and renaming your parameter does nothing
  about its *contents*. A key that happens to read as a node (`kind` plus
  `params`) will be read back as one. Validate at construction time, or store the
  payload as text.

```python
# Incorrect - a dict parameter whose contents you do not control
class RawJsonStorageExpr(BaseExpression):
    def __init__(self, dialect, data: dict):
        super().__init__(dialect)
        self.data = data  # {"kind": ..., "params": ...} in it is read back as a node

# Correct - reject the shape before it can reach an artifact
class SafeJsonStorageExpr(BaseExpression):
    def __init__(self, dialect, json_data: dict):
        super().__init__(dialect)
        if set(json_data) & {"kind", "params"}:
            raise ValueError("payload must not carry node-shaped keys")
        self.json_data = json_data
```

## Related Documents

- [Core Documentation](./serialization.md): Serialization mechanism
- [Format Reference](./format-reference.md): Complete artifact specification