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
`impl.<name>.expression`, because the layout convention does not hold everywhere: 70
expression classes sit outside `impl.<name>.expression` (ClickHouse, MySQL and MariaDB
have 20 `Show*Expression` introspection classes each in `impl.<name>.show.expressions`,
Oracle 9, Postgres 1). The graph keeps them and `misplaced()` reports them, because
scope follows the class hierarchy rather than a directory convention.

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
These are runtime-inert but break mypy, IDE resolution and any static tool. Firebird's
`mixins/window.py` imports `WindowFunctionCallExpression` while core defines
`WindowFunctionCall`.

> Relative-import resolution must go through `importlib.util.resolve_name` with the
> module's `__package__`. Hand-rolled level arithmetic is wrong: level 0 is already
> absolute, and anchoring it to the importing module invents paths that never existed.

**Placement: `misplaced()` versus `secondary_home_nodes()`.** Expression classes are
*expected* under `impl.<name>.expression`, but the backends also group introspection
under `impl.<name>.show` and data types under `impl.<name>.types`. Both are accepted as
secondary homes, so 70 classes that a naive check reports as misplaced are counted
separately instead. Only a class outside every accepted home is a `misplaced()`
finding.

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

## 8. Known limits

- **Requires all backends importable in one interpreter.** A missing backend is silently
  absent from the graph, so cross-backend findings are only as complete as the
  environment. Check `--report`'s project list before trusting a "0 violations" result.
- **No live-database verification.** The graph reflects code structure, not whether a
  database accepts the SQL.
- **Mermaid is validated by parsing, not by pixel rendering.** Syntax is verified against
  Mermaid 11 in a headless DOM; actual layout needs a browser. Very large diagrams may
  still be unwieldy to read.
- **Reflection needs the code importable.** Classes in modules that fail to import are
  absent from the graph; the shortfall is reported under `unimportable` rather than
  hidden, but it must be read.
- **A full run is slow on a network or mounted filesystem** — roughly 3-4 minutes on
  `/mnt/i`, of which only about 30 seconds is CPU. The cost is importing on the order
  of a thousand modules, so it tracks filesystem latency rather than graph size. Cache
  with `--save-graph` if you need to iterate.
