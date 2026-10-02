# Catalogue: confirmed anti-patterns

Each of these was in the codebase. Each is listed with what it cost, so the
next one is recognised rather than reinvented.

## Runtime inference where a type would do

| Anti-pattern | Why it is wrong |
|---|---|
| `result_type="string"` on a factory | A claim, not a type. The return stays `FunctionCall`, so nothing downstream is checked. |
| A family string on the object (`VALUE_FAMILY`) | The only thing it bought was chaining on a function result, and `wrap_as` had to *infer* the family from the input to do it -- the same inference as above, under another name. |
| `family_for_sql_type_name("bigint")` | A table mapping type-name prefixes to meaning, duplicating what the class already knows and inferable only by parsing text. |
| `column_class_for(annotation)` used from a backend | A model-layer runtime table consulted by the dialect layer; the layering alone is wrong. |
| A `str` parameter on a factory | Leaves the decision to a downstream `isinstance`. |

## Coercion in the wrong direction

| Anti-pattern | Why it is wrong |
|---|---|
| `_convert_to_expression(dialect, value)` | Manufactures the expression the formatter is about to format. 59 copies existed. |
| `expr if isinstance(expr, X) else Literal(dialect, y)` inlined at every call site | Where the helper was literal-only this is behaviour-preserving, but at scale it duplicates the same chain dozens of times. Use it where it is genuinely small; do not spread it. |
| Parsing a type name to validate it (`type_name.py`) | Needed only because a string could reach the type position. 201 lines and a grammar, all downstream of that decision. |

## Things that disable checking rather than satisfy it

| Anti-pattern | Why it is wrong |
|---|---|
| `__getattr__` forwarding on an expression class | A checker stops there; every attribute looks valid. Nine of them. |
| `py.typed` absent | The installed package is skipped, so the annotations are invisible. |
| A checker config that does not load | The run continues far enough to look like it passed. |

## Inlining that only moves the problem

Converting a domain object to a typed literal is real work and belongs
somewhere explicit:

```python
Literal(dialect, value.to_postgres_string()).cast(PostgresHstoreType(dialect))
```

Written at every call site, it grew one file by 872 lines with byte-identical
SQL. That removed the helper's name and left its body copied everywhere, where
the copies drift. When a module needs this many, the conversion wants to be a
named construction, not a repeated branch chain.

## Verification discipline

- Rendering is not validation. `(end - start) * 1` renders happily on a
  dialect that cannot execute it. Test against a real database.
- Semantic expectations come from the server, not from intuition. Several
  first expectations in the range and address suites were wrong and the database
  corrected them: `[1,5)` and `[5,9)` are adjacent but do not overlap, `~cidr`
  is not a host mask, `range_union` refuses a gap.
- A byte-identical SQL diff before and after is the evidence that a refactor
  changed nothing. Capture it first, then compare.
- Run the whole check the change needs, not the one that happens to be fast.
  Full test suites are not run locally; targeted files, `--collect-only`, and
  lint are.
