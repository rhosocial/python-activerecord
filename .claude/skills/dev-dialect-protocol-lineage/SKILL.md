---
name: dev-dialect-protocol-lineage
description: Compute and visualise dialect protocol lineage across the core dialect and every backend - declarations versus implementations, broken promises, protocol overlap, and conformance-test cross-checking
license: MIT
compatibility: opencode
metadata:
  category: architecture
  level: advanced
  audience: developers
  order: 10
  prerequisites:
    - dev-expression-dialect
    - dev-protocol-design
---

# Dialect Protocol Lineage

The expression lineage in `dev-expression-lineage` answers *where did this class come
from*. This skill answers the adjacent question for the dialect protocol system: *does
the dialect actually do what its protocols promise?*

## 1. The three layers

Most protocol mistakes are confusions between layers that look like one thing in source:

| Layer | Lives in | Role |
|---|---|---|
| **Declaration** | `backend/dialect/protocols.py` (core, 50 protocols) and `impl/<name>/protocols.py` (backend) | A `Protocol` *promises* methods. Never executed. |
| **Implementation** | `backend/dialect/mixins/*.py` (40 modules) and `impl/<name>/mixins/*.py` | A mixin *provides* methods. |
| **Composition** | the concrete dialect's base-class list | Flattens layers 1 and 2 into one MRO. |

Composition is what hides the defects. `PostgresDialect` alone lists **253 base classes**,
mixing protocols and mixins in a single `class` statement. Once flattened, a protocol
that is in the MRO but whose methods nothing provides is invisible until something calls
it. That is the defect class this tool exists to find.

## 2. Findings

| Finding | Meaning | Severity |
|---|---|---|
| `declared_but_absent` | A protocol in the MRO declares a method and no class in the MRO has the attribute at all. | **Blocking**, but currently **0** everywhere. |
| `stubbed_methods` | The winning implementation of a declared method is an ``...`` stub. ``hasattr`` is True and ``isinstance(dialect, Proto)`` holds, so conformance tests pass; calling it returns ``None``. | Review. The failure mode conformance testing structurally cannot see. |
| `protocol_overlap` | Two protocols in one MRO declare the same name, so MRO order silently decides the meaning. | Review. The conformance tests assert against this too. |
| `untriaged_capability_bits` | A `supports_*` bit whose winning implementation is a *core* mixin returning a hardcoded `True`, which no backend class overrides. | **Prompt, not a defect.** See the warning below. |
| `redundant_overrides` | A backend class overrides a core mixin method to return what the core already returns. | **Review.** Breaks the reuse rule; see below. |
| `implemented_but_undeclared` | A mixin provides a `format_*` / `supports_*` method no protocol declares. Usually dead code. | Informational. |
| `protocols_without_members` | A protocol declaring nothing, so it documents rather than contracts. | Review. |
| conformance-test coverage | Whether the repository that *defines* the dialect ships protocol conformance tests. | Missing coverage is a finding, not a pass. |

### `redundant_overrides`: the reuse rule made checkable

The layering rule is that a backend reuses a core mixin's implementation wherever the core
behaviour already fits, and overrides only what its database actually does differently.
`redundant_overrides` finds the cases where that is not what happened: the backend class
shadows a core mixin method and returns the same value the core already returns.

Detection walks the MRO. For each backend implementation class, a method is redundant when a
class further along the MRO defines the same name from `backend/dialect/mixins` and the two
bodies return the same thing. MRO order is what identifies the shadowed implementation as the
one that would otherwise have run.

Current state: **280 across 11 dialects**, 206 of them in real backends and 37 on
`DummyDialect`, which is a test fixture and excluded from merge gates. The largest are sqlite
48, clickhouse 44, firebird 39, oracle 39. Typical members are capability bits whose core
default is already `False`, such as `supports_add_column_if_not_exists` shadowing
`DDLColumnMixin`.

Only bodies that are a single `return` of a constant, a name, an attribute or a comparison are
normalised. Anything with real logic returns no signature and is never reported, and a value
computed at runtime differs per dialect by construction. So a backend that deliberately
restates a default to document intent is not visible here — read the section as "provably
identical", not "all overrides".

> An earlier attempt compared `supports_X` against `format_X` and reported capability claims
> with no renderer, which produced 86-237 false positives and was abandoned. Do not reintroduce
> name-based feature pairing.

### Why `untriaged_capability_bits` is deliberately narrow

An earlier version listed every `supports_*` whose body was `return True` and reported
**124-278 entries per dialect**. That is useless: a hardcoded `True` in a core mixin is the
normal generic-default idiom, so the list trained the reader to skip the section.

Restricting it to bits the backend never overrode brings it to **32-45 per dialect**, which
is small enough to review. Even then it is an audit prompt rather than an accusation: a
dialect asserting a capability purely by inheritance is how a probe ends up lying, but the
core default may well be correct for that database.

> An intermediate attempt paired `supports_X` with `format_X` to find "claims support but
> cannot render". That was abandoned: the naming does not line up (`supports_add_constraint`
> pairs with `format_add_constraint_action`), and the resulting 86-237 false positives
> made the check worthless. Do not reintroduce name-based feature pairing.

## 3. Conformance tests are the authority

Each backend ships protocol conformance tests asserting, among other things, forward
coverage (protocol method implemented) and reverse coverage (mixin method declared), plus
protocol non-overlap. **They are the authority on whether a method is actually callable**,
because they run against a live database.

This tool cannot run them. It therefore *locates* them and reports per dialect, deriving
the owning repository from where the dialect module actually lives rather than from its
project label. SQLite is built into the core package, so a label-based lookup would search
for a `python-activerecord-sqlite` repository that does not exist; a lookup that searched
every root would instead hand each backend the core copy of the SQLite test.

`protocol_members` reuses the same extraction the tests use, so the tool and the tests
cannot disagree about what a protocol promises.

`DummyDialect` is a test fixture, not a backend; it is reported but marked and excluded
from the coverage cross-check.

## 4. Usage

```bash
PY=.venv3.14-ubuntu26.04/bin/python
S=.claude/skills/dev-dialect-protocol-lineage/scripts

$PY $S/dialect_protocol_lineage.py --report                      # text audit
$PY $S/dialect_protocol_lineage.py --mermaid --focus postgres     # one dialect
$PY $S/dialect_protocol_lineage.py --mermaid --out /tmp/all.mmd   # all dialects
$PY $S/dialect_protocol_lineage.py --json /tmp/protocols.json    # machine-readable
```

Dialects are discovered from the runtime, not hard-coded: every `impl/<name>` package, and
within its `dialect` module the class ending in `Dialect` with the richest MRO. Run it from
the venv that has all backends installed.

The Mermaid output is a `flowchart LR` with declaration and implementation nodes. Missing
promises are drawn as dashed edges labelled `MISSING` rather than omitted, because an
invisible gap is the entire problem. Verified to parse against Mermaid 11.

## 5. Current state on `feature/activerecord-derived-ddl`

```
declared_but_absent : 0
stubbed_methods     : 0 - 64 per dialect
redundant_overrides : 7 - 48 per dialect (280 total, 37 of them on the dummy fixture)
```

### Correction: an earlier version of this skill was wrong

It reported `declared_but_unimplemented : 11` and described the methods as
"AttributeError waiting to happen". That was false. The methods **do** exist, because a
protocol written as `def supports_validate_constraint(self) -> bool: ...` leaves a real
attribute on the class. The bug was the checker excluding `Protocol` classes when
collecting providers, which made every protocol-carried default look unimplemented.

The corrected finding is more interesting than the original: **stubbed methods are
invisible to conformance testing.** The per-backend tests assert
`isinstance(dialect, protocol)` and compare against `dir(dialect)`, both of which only
check *presence*. A stub passes both and returns `None` at runtime.

Whether a stub is a defect depends on intent, and the codebase is inconsistent:

- **firebird (6)** - four sit on a mixin literally named
  `FirebirdUnsupportedFeaturesMixin`, so stubbing is a deliberate contract there.
- **oracle (0)** - no stubs at all.
- **clickhouse (64)** - the most, concentrated in `ClickHouseAdminCommandMixin`,
  `ClickHouseRoutineMixin`, `ClickHouseVectorMixin`.

The hazard is uniform even where the intent is benign: a caller gets `None` rather than
`UnsupportedFeatureError`, so a forgotten ``supports_*`` guard turns into a silent
``None`` in the middle of SQL rendering instead of a clear error.

## 6. Using it as a gate

`declared_but_unimplemented` is the blocking signal. `protocol_overlap`,
`untriaged_capability_bits` and `redundant_overrides` are review items, not gates:
`redundant_overrides` is a code-reuse finding rather than a correctness one, so treat a rise
as a diff to read and a long-standing non-zero count as the baseline. Conformance-test absence
is a gap in verification and should be treated as a hold for a new backend.

`dev-merge-evaluation` lists this as check **F3** and holds the branch on any non-zero
finding.

## 7. Known limits

- **Static reflection only.** It reasons about the MRO, not about execution. A `__getattr__`
  fallback could satisfy a name; none exists today in the dialect hierarchy.
- **`protocol_overlap` is a weak signal.** It is dominated by the benign pattern of a
  backend protocol restating a core protocol's method names (PostgreSQL 254, Snowflake 3).
  That is ordinary inheritance shadowing and is only a problem if a redeclared name
  *changes signature*. Signature divergence on redeclared names is the sharp check and is
  **not implemented**; treat overlap counts as exploration, not as findings.
- **Stub detection inspects source, so it needs the source.** A method defined in C or
  dynamically assigned would read as absent rather than stubbed.
- **Depends on the environment.** A backend that cannot be imported is absent from the
  results; import failures are reported rather than hidden, but must be read.
- **Overlap and undeclared counts are large by nature** (hundreds). They are for
  exploration and regression diffing, not pass/fail.
- **`redundant_overrides` needs the source.** It reads method bodies to compare returns, so a
  method defined in C or attached dynamically is invisible rather than reported clean. The
  comparison is also value-based: two bodies that reach the same result by different routes are
  not detected, and a body with real logic is never reported.
- **Conformance tests are located, never executed.** Only the backend's own CI, against a
  real database, settles callability.
