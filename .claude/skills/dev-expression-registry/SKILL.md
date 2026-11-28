---
name: dev-expression-registry
description: Answer "which expressions exist" from the published registries - print CORE_EXPRESSIONS for core, or CORE_EXPRESSIONS plus a named backend's own table. Use when asked what expressions core or a backend supports, which kinds can be serialized/deserialized, or to compare backend expression vocabularies.
license: MIT
compatibility: opencode
metadata:
  category: architecture
  level: advanced
  audience: developers
  order: 9
  prerequisites:
    - dev-expression-dialect
---

# Expression Registry

Answers one question: **which expressions exist?** The published registries are
the answer, because they are the tables the serializer actually consults. No
source walking, no guessing from class names, no inference from a directory
layout.

Two cases, and only two:

| Question | Command | Output |
|---|---|---|
| What expressions does core have? | `expression_registry.py` | `CORE_EXPRESSIONS` |
| What expressions does backend X have? | `expression_registry.py --backend X` | `CORE_EXPRESSIONS` **and** `X_EXPRESSIONS` |

A backend's own table is a dictionary merge with core's
(`{**CORE_EXPRESSIONS, **X_EXPRESSIONS}`), so printing both is enough to see
the whole vocabulary a backend can read: core kinds plus the backend's own.
The script also reports the size of the merged registry as a cross-check.

## 1. What the list means

Each entry is `kind -> fully qualified class name`:

- **kind** is the snake_case form of the class name. It is the node's identity
  on the wire; an artifact carries a kind, never an import path.
- **FQN** is what the registry uses to import the class when a reader resolves
  a kind. Moving a node between namespaces changes the FQN but not the kind.

Because writing needs no registry and reading needs one, the table is the
**read-side whitelist**: exactly the nodes the codec promises to write and read
back. A kind outside the table is refused by name.

## 2. What the list does NOT mean

Three boundaries, all easy to confuse:

1. **A backend table is not a render-support claim.** It is a plain merge with
   core's kinds. It says the reader can rebuild those node classes; it does not
   say the backend's dialect implements a formatter for each of them.
2. **Support can differ by dialect version.** SQLite's RETURNING clause is the
   standing example: the kind is in the table regardless of version, while
   `supports_returning_*()` gates rendering. Ask the dialect, not the registry.
3. **A parameter's host value has no kind.** All values travel in the single
   `parameter` node, so admitting `"parameter"` admits values of any type;
   JSON-compatibility of the value stays the caller's responsibility.

See the serialization document (`docs/en_US/backend/expression/serialization.md`)
for the full contract.

## 3. Commands

```bash
PY=.venv3.14/bin/python            # any venv with core + backends installed
S=.claude/skills/dev-expression-registry/scripts

$PY $S/expression_registry.py --list-backends
$PY $S/expression_registry.py                       # core only
$PY $S/expression_registry.py --backend sqlite      # core + sqlite
$PY $S/expression_registry.py --backend mysql --kinds-only
$PY $S/expression_registry.py --backend all --json
```

`--backend` accepts one namespace (`sqlite`, `mysql`, `postgres`, `mariadb`,
`sqlserver`, `oracle`, `snowflake`, `clickhouse`, `bigquery`, `firebird`), may
be repeated, or may be `all`. `--kinds-only` drops the FQNs; `--json` emits the
whole result as one document for diffing between revisions.

Backends are discovered from directories on
`rhosocial.activerecord.backend.impl.__path__` — they are PEP 420 namespace
portions with no `__init__.py`, so `pkgutil.iter_modules` would silently miss
them. Drivers that cannot load are stubbed before import; this never modifies
a driver that imports correctly.

## 4. When to reach for it

- "Does core have a `X` expression?" — run core only and search the kinds.
- "Can backend X read this kind back?" — run with `--backend X`; a kind in
  either section is admitted by that backend's registry.
- "Why did deserialization refuse this artifact?" — check the chosen table;
  the answer is always a kind that is not in it.
- "Did the expression set change?" — capture `--json` before and after and
  diff. Class *names* are the wire identity, so a namespace move changes only
  the FQN, not the kind list.

## 5. Limits

- The script reads registries, not capability. For formatting support use the
  dialect's `supports_*()` probes and the conformance tests.
- A backend whose package is not installed is absent from `--list-backends`
  and cannot be printed. Check the project list before trusting a comparison.
- The registry is a **read-side** boundary: it does not restrict what a writer
  may produce, nor what may be executed.
