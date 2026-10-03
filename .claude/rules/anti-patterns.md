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

## A gate with no lower bound is not a gate

`supports_data_type_x()` returning `True` unconditionally tells the dialect it
can render a type on any server. The server disagrees, later, by executing the
statement:

```python
def supports_data_type_postgres_jsonpath(self) -> bool:
    return True                      # every server, including 9.4
```

`CREATE TABLE t (p jsonpath)` comes back `type "jsonpath" does not exist`. The
failure arrives at execution naming a table, when the cause was a version gap
decided at import time.

Four of these shipped at once and CI found them one per run, on one version
each — which is the worst order to find them in, because each run looks like a
new problem:

| Type | Floor | Found on |
|---|---|---|
| `macaddr8` | 10 | python 3.8 / postgres 9 |
| `jsonpath` | 12 | python 3.10 / postgres 12 and below |
| `xid8` | 13 | python 3.11 / postgres 13 |
| the six multiranges | 14 | python 3.8 / postgres 9 through 13 |

Three things made this take a run each rather than one pass:

**The floors were taken from the release notes, and the notes are wrong.**
jsonpath is documented as PostgreSQL 13. It is in 12. Asking the servers is a
loop over a scenario matrix that already exists; reading the notes is a guess
that has to be repeated per type.

**The failures only appear on the oldest combinations.** Everything from Python
3.12 on was green throughout, because the matrix pairs newer Pythons with newer
servers. A change can be entirely correct on the versions CI happens to run.

**A refusal that is correct still looks like a failure.** The dialect knew
multiranges were 14+ and said so — `requires PostgreSQL 14+` — and the tests
reported that refusal as a fault, so five combinations stayed red while the code
underneath was right.

The general form: a version gate answers `True` for every version when the
answer should be "everything from *n*". `is_extension_installed` is the same
question about an extension, and answered wrongly it produces the same shape of
failure.

What to do about the ones that are `True` on purpose — and there are many,
because `text`, `integer` and `varchar` predate the oldest server anyone tests —
is nothing. The distinction is not the count of unconditional gates, it is
whether the type arrived after the floor. So the check is one-directional: for
the types that have a floor, assert the floor. Not that all gates have one.

## A regex is not an editor

Adding one keyword to six call sites went wrong twice on the same file, in two
different ways, and both were caught by CI rather than by reading the diff:

```
Case("macaddr8", lambda d: PostgresMacAddr8Type(d, type_name="..."), ...)
```

placed the argument inside the factory instead of on `Case`'s own argument list.
And an earlier pass put the same keyword inside five others the same way, then a
`git checkout` during a later edit removed the code that read the field while
leaving the field and its six assignments behind — so the feature looked present
and did nothing.

The general problem is that a regex matches text, and a call is not text. It
does not know that `lambda d: T(d)` is one argument, that a multi-line call has
its closing paren three lines down, or that a neighbouring call already got the
same edit. So:

- Locate with `ast`, not with a pattern. `ast.parse` and then read
  `node.lineno`, `node.end_lineno`, `node.args` — a function's parameter list is
  a node, not a comma-split string.
- After any bulk edit, `ast.parse` the file. A syntax error is loud; a misplaced
  keyword argument is not, it is a `TypeError` three layers away at runtime.
- Then run the directory. See "Run the directory, not the files you edited" in
  `static-analysis.md` — the mistake survived because only the edited files were
  tested, and neither contained the error.

Bulk edits that are worth doing are the ones where a mistake is impossible to
confuse with success. A misplaced keyword argument is not.

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
- A refusal is not a failure. `UnsupportedFeatureError: requires PostgreSQL
  14+` is the code working: the dialect declined to render a type the server
  does not have. A test that reports that refusal as a fault is asking the
  wrong question — it should ask the dialect what the server supports and skip.
  Five Python/PostgreSQL combinations stayed red for this reason while the code
  underneath was correct.
- Version-dependent behaviour is a fact about servers, and the servers are
  reachable. Ask them in a loop over the scenario matrix rather than reading
  release notes: the notes put jsonpath in 13, and 12 has it.
