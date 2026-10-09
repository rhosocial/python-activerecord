---
name: dev-expression-lineage
description: Compute and visualise the expression inheritance lineage across the core package and every backend - Mermaid pedigree diagrams, core-versus-backend placement evidence, iron-rule and dangling-annotation audits
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

# Expression Lineage

Answers questions that are hard to settle by reading code: *where did this expression class
come from, which backends actually depend on it, and is it in the right layer?*

Provides two scripts:

| Script | Role |
|---|---|
| `scripts/expression_lineage.py` | Data model. Builds the lineage DAG by reflection. No rendering. |
| `scripts/expression_lineage_mermaid.py` | Presentation. Mermaid diagrams plus a text report. |
| `scripts/fix_dangling_typecheck.py` | Repairs dangling `TYPE_CHECKING` imports, or lists them. |

Run them with the venv that has all backends installed (`.venv3.14-ubuntu26.04/bin/python`),
because projects are discovered from the active interpreter.

## 1. What counts as an expression

**A node is a subclass of `BaseExpression` and nothing else.**

This matters. `backend.expression.mixins` holds six mixins — `ComparisonMixin`,
`StringMixin`, `TypeCastingMixin`, `LogicalMixin`, `ArithmeticMixin`, `AliasableMixin` —
that derive from `object` only. They are ingredients, not expressions. They are recorded
per node under `mixins` and never become graph nodes or lineage edges. Counting them as
nodes was an early bug that inflated the graph from 1151 nodes / 692 edges to 1292 / 1563.

Lineage is a **DAG**, not a tree: expression classes multiply inherit from several
expression bases at once, so traversal carries cycle guards and takes shortest paths
through diamonds.

## 2. Scope and discovery

Projects are discovered at runtime, so a newly installed backend needs no code change:

- `rhosocial.activerecord.backend.expression` → project `core`
- `rhosocial.activerecord.backend.impl.<name>` → project `<name>`

A backend is scanned as a **whole `impl.<name>` package**, not just
`impl.<name>.expression`, so that a class in the wrong place is reported rather
than silently dropped from the graph. Scope follows the class hierarchy, not a
directory filter.

This mattered until recently: 70 expression classes used to sit outside
`impl.<name>.expression` (ClickHouse, MySQL and MariaDB had 20
`Show*Expression` introspection classes each in `impl.<name>.show.expressions`,
Oracle 9, Postgres 1 in `impl.<name>.types`). All of them have been relocated
into the expression namespace (`expression/show.py` and
`expression/enum_.py`), and the top-level `types` package has been renamed
`type_values` so that `types` unambiguously means DataType expressions.
`misplaced()` is therefore now an enforceable invariant and should report
**0**; a non-empty result is a regression.

**Third-party namespaces.** Pass extras to analyse them alongside the in-tree backends:

```bash
python scripts/expression_lineage_mermaid.py \
  --extra acme=acme.rhosocial.activerecord.backend.impl.acme \
  --scope backend:acme
```

Third-party projects are flagged `in_tree=False` and counted separately in the stats, so
they are never mistaken for repository backends.

## 3. Repairing dangling imports

```bash
$PY $S/fix_dangling_typecheck.py --list      # report only, changes nothing
$PY $S/fix_dangling_typecheck.py --apply     # rewrite in place, then re-verify
```

The fixer keeps the author's module tail and recomputes only the number of leading
dots, walking outward from the importing package until the target imports cleanly and
exposes the attribute. Cases where the *module* or the *name* is wrong cannot be fixed
that way and are listed in `MANUAL_OVERRIDES`, each entry confirmed against the
definition site. `--apply` re-runs the check afterwards and exits non-zero if anything
remains.

Two failure modes worth remembering, both hit while building this:

- **Do not redirect a whole multi-name import.** `impl.mysql.mixins.partition`
  imported 25 names from `expression.partition` plus 5 `*Helper` names that live in
  `expression.partition_lifecycle`. Redirecting the statement fixed the 5 and broke
  the 25 that were already correct; the file now carries two separate statements.
- **A parenthesised import must not be rewritten wholesale.** Its names live on the
  following lines, so only the `from ... import` prefix is replaced.

## 4. Commands

```bash
PY=.venv3.14-ubuntu26.04/bin/python
S=.claude/skills/dev-expression-lineage/scripts

$PY $S/expression_lineage_mermaid.py --report                      # text audit
$PY $S/expression_lineage_mermaid.py --list-families               # scope names
$PY $S/expression_lineage_mermaid.py --scope family:ddl.domain     # one family
$PY $S/expression_lineage_mermaid.py --scope backend:postgres      # one backend + core ancestors
$PY $S/expression_lineage_mermaid.py --scope consumers --min-consumers 3 --limit 25
$PY $S/expression_lineage_mermaid.py --scope violations
$PY $S/expression_lineage_mermaid.py --scope family:types --style flowchart --out /tmp/t.mmd
$PY $S/expression_lineage_mermaid.py --report --save-graph /tmp/lineage.json
```

`--save-graph` writes the raw graph as JSON. Diffing two of these across revisions turns
"the lineage changed" into a reviewable artefact, which is the point of keeping the model
separate from the renderer.

**Family labels are module tails, not a single segment.** The core keeps modules at
`expression/statements/ddl_domain.py` while backends use `expression/ddl/domain.py`, so
labels look like `statements.ddl_domain` and `ddl.domain`. Use `--list-families` rather
than guessing.

## 5. Diagram choice

| Style | When | Why |
|---|---|---|
| `flowchart LR` (default) | Whole-backend views, anything above ~40 nodes | `subgraph` per project is what makes the core-to-backend layering legible; `id["label"]` syntax is stable across renderers; survives hundreds of nodes |
| `classDiagram` (`--style class`) | Focused families of a few dozen classes | Semantically correct for inheritance and reads better, but degrades on large graphs |

`--style auto` picks `classDiagram` at or below 40 nodes. In `flowchart`, inheritance runs
parent to child so that reading left to right follows *generic base becomes backend
specialisation*. Node colour encodes role: core blue, backend amber, abstract grey
dashed, external white dashed.

Both styles are verified to parse against Mermaid 11.

## 6. The audits

Each of these answers a decision, not a curiosity.

**`violations()` — the iron rule.** Cross-backend inheritance, i.e. `child.project !=
parent.project` with both in the backend layer. Deriving inside one backend
(`MySQLPointType` from `MySQLGeometryType`) is ordinary type hierarchy and is *not*
flagged; `intra_project_bases()` returns those separately for edge styling. Only MySQL
reaching into Postgres, or MariaDB into MySQL, breaks the rule. Current state: **0**.

> An earlier version flagged any backend-to-backend base and produced 118 false
> positives, all of them same-backend. If you extend this check, keep the
> `project !=` condition.

**`consumers()` — the placement decision.** Distinct backends that transitively derive a
core class. This is the quantitative form of the two-way responsibility rule in
`dev-expression-dialect`:

- many consumers → the generic class is doing the core's job of absorbing backend work;
  leave it in core
- exactly one consumer → candidate to move down into that backend

`--scope consumers` renders it directly as core-class-to-backend fan-in, so a thin
fan-in is visible at a glance. A single import count is not sufficient evidence: a
`DomainSupport` protocol is imported by six backends precisely so that the ones which
*cannot* do something declare `False`.

**`dangling_typecheck_refs()` — rot detection.** `if TYPE_CHECKING:` imports whose target
attribute cannot be resolved from the import's source module. Resolution is attempted
against the **source module**, not the class inventory, because dialect classes such as
`SQLDialectBase` are not exported by expression modules and that is normal, not a defect.
Only a module that imports cleanly while the attribute is missing is genuinely dangling.
These are runtime-inert but break mypy, IDE resolution and any static tool. The case
that motivated the check — Firebird's `mixins/window.py` importing
`WindowFunctionCallExpression` while core defined `WindowFunctionCall` — is gone: the
node was unified into `FunctionCall` and the stale importer deleted, so the check
currently reports nothing. It is kept because the same shape recurs with every rename.

> Relative-import resolution must go through `importlib.util.resolve_name` with the
> module's `__package__`. Hand-rolled level arithmetic is wrong: level 0 is already
> absolute, and anchoring it to the importing module invents paths that never existed.

**`misplaced()` — the iron rule for placement.** An expression class must be defined under
`backend.expression` (core) or `impl.<name>.expression` (backend), with no exemptions. The
expected result is **0**; any entry is a regression.

> This check used to carry an allowlist. `SECONDARY_HOME_SEGMENTS = ("show", "types")`
> existed to stop this exact check reporting 70 classes — the `show` introspection
> expressions and `PostgresEnumType` — as drift. They *were* drift. They have since moved
> into the expression namespace and `types` has been renamed `type_values`, so the allowlist
> was deleted rather than emptied: an empty one would only invite the next exemption. Do not
> reintroduce it. If a future grouping looks legitimate, the fix is to move the classes, not
> to widen the rule.

The same invariant is asserted at test time by `test_expression_namespace.py` in the
postgres and oracle suites, so a violation fails CI without anyone running this script.

**Integrity: `parse_failures` and `unimportable`.** These exist because the check
originally failed silently, which is the worst possible failure for an audit:

- a file that does not parse yields no `TYPE_CHECKING` imports, so a broken file looks
  clean. Parse failures are recorded and reported.
- a package that cannot be imported skips its whole subtree, so the project simply
  disappears from the results. Skipped packages are recorded and reported, and the
  report marks the run as under-reported.

Always read `integrity` before trusting a clean run.

## 7. Using the model directly

```python
import sys; sys.path.insert(0, ".claude/skills/dev-expression-lineage/scripts")
from expression_lineage import build_graph, discover_projects

graph = build_graph()
graph.stats()                                  # counts for the report
graph.consumers("core::CreateDomainExpression") # {'postgres', 'firebird'}
graph.violations()                             # iron-rule breaches
[node.name for node in graph.misplaced()]
graph.node("postgres::PostgresCreateDomainExpression").bases
graph.ancestors("mysql::MySQLPointType")        # cycle-guarded
graph.save("/tmp/lineage.json"); graph = type(graph).load("/tmp/lineage.json")
```

## 8. Run this after every expression change

**Whenever the expression system is modified — a class added, moved, renamed, reparented,
or a backend gaining or losing expressions — run a lineage audit afterwards and check it
against what you intended.** This is the step that catches what review and tests miss,
because a rename can be correct in isolation and still leave the graph describing something
other than the layout you believe you have.

```bash
PY=.venv3.14-ubuntu26.04/bin/python
S=.claude/skills/dev-expression-lineage/scripts

# 1. placement, iron rule, and integrity in one pass
$PY $S/expression_lineage_mermaid.py --report

# 2. for a structural change, diff the graph against the base revision
$PY $S/expression_lineage_mermaid.py --report --save-graph /tmp/after.json
git stash            # or check out the base revision
$PY $S/expression_lineage_mermaid.py --report --save-graph /tmp/before.json
git stash pop
```

What to read, in order:

| Line | Expected after a clean change |
|---|---|
| `integrity` | `0 unparseable, 0 unimportable` — otherwise the run is under-reported and the rest means little |
| `placement` | `0 misplaced`; a non-zero value is a regression, not a known exception |
| `iron rule` | `0 cross-backend inheritance` |
| `nodes/edges` | changed by exactly the delta you intended, no more |
| `dangling TYPE_CHECKING imports` | `none`, or fewer than before |

`--save-graph` makes the diff reviewable, which is the point of separating the model from
the renderer. A class count that moved without a matching edit is the signal that something
imported twice, shadowed, or silently vanished.

**Reach for this after any change that moves a module, splits a file, renames a package, or
alters a base class.** Those are the operations that can leave the namespace correct in the
diff and wrong on disk.

## 9. Known limits

- **Backends must be *installed*, not merely importable.** `discover_projects()` stubs any
  DB driver that fails to load (see §10), so a missing OS library no longer costs a backend
  its audit. A backend whose *package* is not installed is still silently absent, so check
  `--report`'s project list before trusting a "0 violations" result.
- **No live-database verification.** The graph reflects code structure, not whether a
  database accepts the SQL. No driver is ever exercised, which is exactly why stubbing one
  is safe.
- **Mermaid is validated by parsing, not by pixel rendering.** Syntax is verified against
  Mermaid 11 in a headless DOM; actual layout needs a browser. Very large diagrams may
  still be unwieldy to read.
- **Reflection needs the code importable.** Classes in modules that fail to import for any
  reason other than a missing driver are absent from the graph; the shortfall is reported
  under `unimportable` rather than hidden, but it must be read.
- **A full run is slow on a network or mounted filesystem** — roughly 3-4 minutes on
  `/mnt/i`, of which only about 30 seconds is CPU. The cost is importing on the order of
  a thousand modules, so it tracks filesystem latency rather than graph size. Cache
  with `--save-graph` if you need to iterate.

## 10. Why drivers are stubbed

Lineage is computed by reflection only. Nothing here opens a connection, issues a query,
or touches a driver. But every backend's `__init__` imports its driver eagerly, and Python
runs a parent package's `__init__` before any submodule — so there is no way to reach
`impl.sqlserver.expression` without `impl.sqlserver.__init__` first.

That made `pyodbc` a hard requirement for auditing sqlserver, even though `pyodbc` is a C
extension needing the OS `libodbc.so` and the expression classes never reference it. The
wheel alone was not enough, so sqlserver used to drop out of the graph entirely and take
its placement audit with it.

`install_driver_stubs()` therefore replaces a driver with an inert module *before*
discovery runs, and only if the real import failed. Each stub attribute is a fresh
`Exception` subclass, which covers the only three things a backend does with its driver at
import time: subclass it, catch it, and call it. A driver that loads normally is never
touched, so this cannot mask a genuine environment problem.

```python
from expression_lineage import install_driver_stubs
install_driver_stubs()          # -> ['pyodbc', ...] for those that failed
```

Stubbing restores coverage; it does not verify anything about the driver. If you need the
real driver exercised, install the OS library and re-run, and `install_driver_stubs()` will
report an empty list.
