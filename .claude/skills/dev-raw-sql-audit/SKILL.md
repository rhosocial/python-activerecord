---
name: dev-raw-sql-audit
description: Audit RawSQLExpression and RawSQLPredicate usage across every rhosocial-activerecord project - AST-based classification of constructions, subclassing, type guards and dead imports, with production-code severity and dynamic-SQL detection
license: MIT
compatibility: opencode
metadata:
  category: architecture
  level: intermediate
  audience: developers
  order: 11
  prerequisites:
    - dev-expression-dialect
    - dev-expression-lineage
---

# RawSQL Expression Audit

Answers one question precisely: **is `RawSQLExpression` or `RawSQLPredicate` being
constructed anywhere it should not be?**

## Why these two classes are different from every other expression

`RawSQLExpression` and `RawSQLPredicate` were introduced as a *temporary* shortcut —
a way to validate an expression while the real typed construct did not exist yet.
Every other class in `backend/expression/` is a **dialect-formatted tree node**: a
dialect renders it, parameters are bound separately, and the dialect can reject it
when the construct is unsupported.

These two bypass all of that. The SQL text is carried as a string and handed to the
driver verbatim. Nothing validates it, nothing formats it, nothing owns it.

That makes them different in kind from a normal design smell. An expression a
dialect formats is a *checked* string; a raw SQL string is only as safe as the code
that assembled it. So a construction in `src/` is not "ugly code to clean up later" —
it is a marker that **the real expression was never written**, and it will keep
working long after the reason it was added has been forgotten. That is the debt this
skill exists to surface.

## The script

```bash
S=.claude/skills/dev-raw-sql-audit/scripts

python3 $S/raw_sql_audit.py                      # core + every sibling backend
python3 $S/raw_sql_audit.py --area src           # production code only
python3 $S/raw_sql_audit.py --project python-activerecord-postgres
python3 $S/raw_sql_audit.py --fail-on review     # tighten the gate
python3 $S/raw_sql_audit.py --json               # machine-readable
```

| Option | Effect |
|---|---|
| `--repo PATH` | Repository to scan. Sibling `python-activerecord*` projects are discovered automatically. |
| `--project NAME` | Restrict to named projects. Repeatable. |
| `--area src` / `--area tests` | Restrict by area. Default: both. |
| `--fail-on SEVERITY` | Lowest severity that fails the run. Default `violation`. |
| `--json` | Emit JSON with per-finding `kind`, `severity` and `dynamic_sql`. |

Exit codes: `0` clean, `1` findings at or above the gate, `2` bad usage.

**It is pure AST.** It parses, imports nothing, and touches no interpreter state, so
it runs under any Python and needs no virtualenv — unlike `dev-expression-lineage`,
which reflects over live classes and therefore requires the venv with all backends
installed. That is deliberate: a check that can be broken by an unrelated import
error in the tree is a check that gets skipped.

## Classification

Every reference is resolved through the AST and given a **kind**, because the
difference between the roles *is* the question. `grep RawSQL` cannot tell them apart.

| Kind | Meaning | `src/` | `tests/` |
|---|---|---|---|
| `construction` | The class is called. A raw node comes into existence. | `violation` | `review` |
| `subclass` | Used as a base class. | `violation` | `review` |
| `typecheck` | `isinstance` / `issubclass` / `cast` argument. | `review` | `info` |
| `unused_import` | Imported, referenced nowhere. | `review` | `info` |
| `annotation` | Type hint only. | `info` | `info` |
| `formatter` | The `format_raw_sql` dialect method. | `info` | `info` |
| `definition` | The class statement itself. | `info` | `info` |
| `mention` | Bare name, no recognised role. | `info` | `info` |

**`src/` and `tests/` are not the same thing.** Constructing a raw expression in a
test is the shortcut working as designed — that is literally what it was built for.
Constructing one in `src/` is the debt. Separating them is what keeps the report
readable: 23 production sites instead of 223 undifferentiated lines.

**Prose is counted, never reported.** Docstrings and error messages name these
classes constantly, which is desirable — the guidance against them has to be readable
at the call site. The report shows `prose mentions (not uses): N` so "109 mentions" is
never mistaken for "109 uses".

### `dynamic-sql`: the finding that outranks the rest

A construction is additionally flagged `dynamic-sql` when the SQL text is **computed
at run time** rather than a literal. This is not a sub-category of `violation`; it is
ranked above it, because the two are different problems:

```python
RawSQLExpression(dialect, "*")                    # ugly, but inert
RawSQLExpression(dialect, formatted_sql, params)  # SQL injection surface
```

`args[0]` is the dialect by constructor signature, so anything after it that is not a
compile-time constant means the embedded string was assembled from live values.

### Reference forms that are all counted

Aliasing and module-qualified access are resolved, not guessed:

```python
from ...operators import RawSQLExpression            # direct
from ...operators import RawSQLExpression as Raw     # aliased
import operators; operators.RawSQLExpression(...)   # qualified
```

Subclassing is matched on the bare target name even when the module never imported
it, because that is an unambiguous intent (and an imminent `NameError`).

## Current state

As of the last run, `src/` carries **23 constructions across 5 projects**:

| Project | Count | Shape of the debt |
|---|---:|---|
| `python-activerecord` | 19 | `query/cte_query.py` (10), `query/base.py` (2), `query/join.py` + `async_join.py` (2), `query/set_operation.py` (2), `expression/functions/string.py` (2), `expression/functions/aggregate.py` (1) |
| `python-activerecord-postgres` | 1 | `backend/base.py` |
| `python-activerecord-oracle` | 1 | `mixins/functions.py` |
| `python-activerecord-mariadb` | 1 | `functions/fulltext.py` |
| `python-activerecord-firebird` | 1 | `expression/ddl/domain.py` |

22 of the 23 are `dynamic-sql`. `python-activerecord-sqlserver` constructs none and
is clean; its single `src/` reference is a type guard.

**Read the biggest cluster as a design signal, not as 10 tickets.**
`query/cte_query.py` converts a nested query to SQL and re-wraps it in a
`RawSQLExpression` "to avoid extra parentheses" — ten times, in two near-duplicate
sync/async halves. That comment describes a missing feature: a query
expression that renders unparenthesised when it is used as a subquery. Writing that
one construct retires the whole cluster, plus its mirror in `set_operation.py`. The
`RawSQLPredicate` sites in `query/base.py` and `query/join.py` are the same shape: a
user-supplied raw SQL string being funnelled through an expression node that does not
inspect it.

## Using the result

**Never satisfy the gate with an exclusion list.** An allowlist of "known raw SQL"
sites is a list that only grows, and it converts a check into a registry. If a
construction must survive, it needs a named reason in the commit that introduced it,
and the severity should be revisited, not the file hidden.

**Fix the construct, not the expression.** Replacing `RawSQLExpression(d, sql_text)`
with a typed expression means the dialect can now format it, bind its parameters and
reject it where unsupported — which is what removes the finding rather than relocating
it.

**Add the gate to CI** once the count is trending down:

```bash
python3 .claude/skills/dev-raw-sql-audit/scripts/raw_sql_audit.py --fail-on violation
```

Run it in `dev-merge-evaluation` as part of the evidence pass. A merge that raises the
production count is a merge that grows debt silently, and this is the mechanical check
that catches it.

## What this skill does not do

- It does not judge whether a raw expression is *semantically* correct. It reports
  construction sites and their risk shape; the replacement is a design decision.
- It does not detect raw SQL built outside these classes. A hand-formatted string
  passed to `execute()` bypasses the expression system entirely and is invisible here.
  `dev-dialect-protocol-lineage` covers the adjacent question of whether dialects
  honour what their protocols promise.
- It does not check `docs/`, markdown or changelog fragments — only `.py` under `src/`
  and `tests/`.