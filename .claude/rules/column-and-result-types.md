# Column classes and result types

## Column classes are designed, not inferred

A column class says what a value of that kind **can do**. Define what exists;
do not add what might. Operations are methods on the class, so what a column
offers is a property of its type, visible to a reader and to a checker.

Users reach a column through their model's annotation, never through a registry
or a lookup by name:

```python
class Post(Model):
    title: str        # -> StringColumn
    views: int        # -> NumericColumn
    body: dict        # -> JSONColumn

Model.c.title.upper()
```

What decides this is a plain mapping from annotation to column class. It is a
closed table in the model layer, and it is read at class-definition time, so
the choice is static.

## Layering

Three layers, each adding to the one above:

1. **Core** -- what the SQL standard defines and what is widely shared.
   `StringColumn`, `NumericColumn`, `TimestampColumn`, `BooleanColumn`,
   `BinaryColumn`, `JSONColumn`, `ArrayColumn`, `UUIDColumn`.
2. **A backend overrides** what genuinely differs for it. An override replaces a
   method or a rendering; it does not accumulate into a growing subclass.
3. **A backend adds its own** for what only it has. PostgreSQL has no peers for
   `citext`, `ltree`, `hstore`, `int4range`, `inet` or `geometry`, so those are
   defined there and nowhere else.

Between them the coverage is meant to be complete: every operation the backend
supports has somewhere to call it from.

## A user's own column type

PostgreSQL lets a user define a column type. They own it the same way, and the
mechanism is open rather than closed:

```python
class MyTypeMixin:
    def as_mytype(self) -> MyTypeValueExpression:
        ...

class MyColumn(MyTypeMixin, ColumnBase):
    ...
```

Nobody has to register it, and the core does not need to know it exists.

## Result types the source cannot settle

Most operations know what they yield and say so by returning that class. A few
cannot: `NULLIF(x, y)` yields `x` when they differ and NULL when they do not, so
whether the result is text or an integer depends on the data. The standard
gives this example itself.

For those, the caller states it. **Never infer, and never accept a free-form
claim.** The statement has to be something a checker can read, which means it
has to be a function or method with a declared return type:

```python
NULLIF(name, blank).as_text().upper()    # fine
NULLIF(name, blank).as_text().sqrt()     # error: text has no sqrt
```

`ResultTypeMixin` provides this on the node whose result type is genuinely not
in the source -- a bare `FunctionCall`. It is a **mixin, not free functions**,
for three reasons:

- the dialect is already on the node, so there is nothing to pass;
- chaining reads as one expression rather than an argument in the middle;
- `dir()` finds it, so the way to say it is discoverable.

Because it is a mixin, a user composes it the same way: do not mix it in and
the operations are simply absent; find it short and subclass it, overriding one
method and keeping the rest.

## Anti-pattern, for contrast

```python
f(dialect, expr, result_type="string")    # a claim, not a type
```

The declared return stays `FunctionCall`. A checker learns nothing, the wrong
continuation is still unchecked, and the error surfaces as a server complaint
minutes later. It reads as if it solves the problem and does not.

The same objection applies to a runtime lookup keyed on a type name, and to a
family string carried on the object: both move a decision that could be a type
into run-time data. If the answer is knowable, make it a return type.
