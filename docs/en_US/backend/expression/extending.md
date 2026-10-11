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

`CollateExpression` is the `**kwargs` case in core: it collects `**collation_options` into `self.collation_options: dict`, so `get_params()` returns `binary`, `pad` and the rest as top-level parameters and reconstruction passes them back as keywords.

A parameter the convention cannot resolve is skipped with a warning. That warning is the diagnostic — it means `__init__` stores state under a name `get_params()` cannot see — and the repair is always in `__init__`.

### Why There Is No Custom get_params()

`get_params()` is not an extension point: an override is a defect, not a customization. Core enforces this with no exceptions in `tests/.../dummy2/test_expression_contract.py::test_no_get_params_override` — every registered expression class must leave the generic implementation alone. (The single exemption the test allows, a `VAR_POSITIONAL` class doing genuine raw-vs-normalized round-trip rewriting, has no instance in the core registry.)

The reason is structural rather than stylistic. A round-trip is rebuilt by calling the constructor with whatever `get_params()` returned, so those two halves have to agree. An override is exactly where they drift: the class emits a key the constructor renames, merges or refuses, `_reconstruct()` wraps the resulting `TypeError` as `ExpressionDeserializationError`, and the state is silently gone. The backend packages accumulated their own overrides, every one of them written because `__init__` renamed or merged what the caller passed — and every one of them became unnecessary once the state was stored under the name it was given.

When the generic result is not what you wanted, the repair is always in `__init__`, and it is one of three shapes:

| The problem | The repair |
|---|---|
| You renamed or merged what the caller passed | Store it under the name the parameter has |
| Two constructor spellings mean one thing | Keep both slots; put the value in the one the caller used and leave the other `None` |
| The value cannot be serialized as it stands | Convert it in `__init__` and store the converted value |

## Registration Mechanism

### Auto-Registration

Built-in expressions are auto-registered to `ExpressionRegistry` via `_auto_register_builtins()`.

### Manual Registration

Custom expressions need manual registration:

```python
from rhosocial.activerecord.backend.expression.serialization import ExpressionRegistry

ExpressionRegistry.register(MyExpression)
```

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

When the parent genuinely has to travel with the node, make it an ordinary nested-expression parameter: that is what `{"__expr__": ...}` exists for. The tree is then simply finite.

## IntrospectionExpression Convention

`IntrospectionExpression` subclasses (like `TableListExpression`) combine a constructor with fluent setters that share the parameter names. Both halves of the generic path already account for this:

```python
class TableListExpression(IntrospectionExpression):
    def __init__(self, dialect, schema=None, include_views=True, include_system=False, table_type=None):
        super().__init__(dialect, schema)
        self._include_views = include_views
        self._include_system = include_system
        self._table_type = table_type

    def include_views(self, value: bool = True):
        self._include_views = value  # the same attribute the parameter is read from
        return self
```

- **When both spellings exist, the callable one is not the state.** If a parameter has both `self.foo` and `self._foo` and the public attribute is a fluent method, the private attribute is taken as the value.
- **An optional parameter left unset is emitted as `null`, not omitted.** That is safe: the deserializer passes it back and the constructor's default applies. What is *not* safe is dropping a parameter whose value differs from its default — that is state the round-trip loses.

## Error Contract

All paths through `_reconstruct()`, `TypeError` is wrapped as `ExpressionDeserializationError`. This ensures callers only need to catch one exception type.

## Serialization Format Convention (Reserved Key Names)

The **values** `get_params()` returns must not contain the following reserved keys at any depth, otherwise deserialization behavior is undefined — the deserializer reads them as framework markers:

- `__expr__`: Used to mark nested expressions
- `__tuple__`: Used to mark tuples
- `__value__` / `__vdc__`: Used to mark codec-encoded scalars and dataclass values

Your own top-level keys come from your `__init__` parameter names (plus whatever `**kwargs` extras were merged in), so never name a parameter after a reserved key. For an opaque payload whose keys you do not control, the hazard is inside the payload: those keys are copied into the spec verbatim, and renaming the parameter does nothing about them. Validate at construction time, or store the payload as text.

```python
_RESERVED = ("__expr__", "__tuple__", "__value__", "__vdc__")

# Incorrect - a payload containing "__expr__" is read back as a nested expression
class RawJsonStorageExpr(BaseExpression):
    def __init__(self, dialect, data: dict):
        super().__init__(dialect)
        self._data = data

# Correct - the payload is rejected before it can reach a spec
class SafeJsonStorageExpr(BaseExpression):
    def __init__(self, dialect, json_data: dict):
        super().__init__(dialect)
        for key in json_data:
            if key in _RESERVED:
                raise ValueError(f"{key!r} is a reserved serialization key")
        self._json_data = json_data
```

## Related Documents

- [Core Documentation](./serialization.md): Serialization mechanism
- [Format Reference](./format-reference.md): Complete ExpressionSpec specification