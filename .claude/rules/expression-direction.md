# Expression direction: expr -> format, never the reverse

## The rule

Information flows one way: from a typed object to SQL text.

```
caller builds an expression  ->  factory composes expressions  ->  dialect renders
   Column / Literal / ...         FunctionCall                   format_*
```

A formatter's subject is an expression. Without one it has nothing to render,
so **no formatting function may manufacture the expression it is about to
format**. That includes guessing, coercing, and parsing.

## Why the reverse direction is not a style preference

The type position of a cast cannot take a bound parameter, so whatever lands
there is SQL code. That is why `cast()` takes a `DataType` and refuses a
string, and why `CustomType` validates its name: the reverse direction is where
injection lives.

The same shape appears wherever a loose value is turned into a node. A helper
that accepts `str` and decides whether it is a column name or a string value is
inferring SQL semantics at run time, and the decision is invisible at the call
site -- the reader sees `f(dialect, x)` and cannot tell what will be rendered.
It is also unreviewable, because the branch that decides is in the wrong place.

## Formatters

- Each expression declares which formatter it needs; `to_sql()` looks it up.
  A node never formats itself.
- A formatter takes an expression. It does not accept a string and validate it
  afterwards -- `format_cast_expression` used to check the target with a regex
  and reject a bad name at render time, which meant the check sat three steps
  from where the value entered.
- A type renders itself through `to_sql()`, so the type and its spelling
  cannot disagree.

## What this forbids

- A coercion helper that turns a loose value into an expression.
- A factory parameter typed `Any` or `Union[str, BaseExpression]`, because that
  signature invites a loose value and leaves something downstream to guess.
- Parsing rendered SQL back into a domain object. If a type name has to be
  understood, that is a parser for a grammar nobody needed.

## Where the difficulty actually is

Deleting a coercion helper is only mechanical when it coerces in one direction
for every input. Measured across the function factories, most do, but some map a
string to a `Column` -- a different convention, not a variant -- and a few turn
a domain object into a typed literal, which is real work:

```python
# Antisymmetric: this one is worthless, the behaviour is unchanged by removing it.
x = x if isinstance(x, BaseExpression) else Literal(dialect, x)

# Real: the object becomes a value of a known type, and the cast is the point.
Literal(dialect, value.to_postgres_string()).cast(PostgresHstoreType(dialect))
```

Inlining the second at every call site writes the same six-branch chain dozens
of times; one such attempt grew a file by 872 lines while keeping the SQL
byte-identical. It removed the helper's name and left its body copied everywhere.
That is not a resolution. Turn the conversion into an explicit construction
instead, or leave the module for its own pass.
