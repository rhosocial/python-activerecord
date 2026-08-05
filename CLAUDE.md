# rhosocial-activerecord — Developer Instructions

## What this project is

A standalone, Pythonic ActiveRecord implementation built from scratch with **only Pydantic as a
dependency** — no SQLAlchemy/Django ORM. All database interaction goes through a clean backend
abstraction layer. Source lives in `src/rhosocial/activerecord/`.

- **Python**: 3.8+ (`requires-python >=3.8`), free-threaded 3.13t/3.14t supported
- **Version**: defined only in `pyproject.toml` `[project] version` (no `__init__.py`, PEP 420
  namespace package)
- **Related repos**: `python-activerecord-mysql`, `-postgres`, `-mariadb`, `-oracle`,
  `-sqlserver` (backends), `python-activerecord-testsuite` (shared test contracts)

## Iron rules (do not skip)

1. **Run tests with `PYTHONPATH=src`** (tests are not on the module path). Never run tests in
   parallel.
2. **No line exceeds 120 chars**; ruff config in `pyproject.toml` (`[tool.ruff.lint]`, ignore=B024).
3. **Expressions never concatenate SQL** — always delegate to `self.dialect.format_*()`.
4. **Sync/async must be functionally equivalent** — same features, same method names.
5. **Commits follow Conventional Commits** with a scope (see Rules Index → dev-release-workflow);
   version lives in `pyproject.toml` only.
6. **Show full, unfiltered pytest output** — no grep/head/tail on test results.

## Repository map

```
src/rhosocial/activerecord/
├── model.py            # ActiveRecord, AsyncActiveRecord, model mixins
├── field.py            # Field, FieldProxy
├── query/              # ActiveQuery and query mixins (Aggregate/Base/Join/Relational/Range)
├── backend/            # backend abstraction: base, dialect, type_adapter, expression/, impl/
│   └── impl/           # sqlite, dummy, ... (mysql/postgres live in separate packages)
├── interface/          # IActiveRecord, backend interfaces/protocols
└── ...
tests/rhosocial/activerecord_test/   # feature/, realworld/, benchmark/
```

## Rules Index

Load the document or skill matching the task. Resident `.claude/*.md` files are the standing
policy; skills are loaded on demand when a matching task starts.

### Resident policy (`.claude/*.md`)

| File | When to use |
|------|-------------|
| [code_style.md](.claude/code_style.md) | Code style, naming, typing, docs, security (incl. RawSQLPredicate rules) |
| [architecture.md](.claude/architecture.md) | System architecture, design patterns, module organization |
| [version_control.md](.claude/version_control.md) | Versioning policy, branching strategy, commit/changelog standards (policy only — runbooks in skill) |
| [testing.md](.claude/testing.md) | How to set up and run the test suite (PYTHONPATH, dependencies, commands) |
| [backend_development.md](.claude/backend_development.md) | Entry point for backend work (detail lives in skills) |
| [experimental.md](.claude/experimental.md) | Future/experimental feature policy (not active during 1.0 pre-release) |
| [feature_points.md](.claude/feature_points.md) | Authoritative commit-message scope list |
| [field-proxy-comprehensive-guide.md](.claude/field-proxy-comprehensive-guide.md) | Field/FieldProxy deep dive |
| [add_new_testcase.md](.claude/add_new_testcase.md) | How to add a new test case |

### Developer skills (`.claude/skills/dev-*`)

| Skill | When to load |
|-------|--------------|
| `dev-release-workflow` | Branching, dev→alpha→beta→rc→final, release to main, hotfix, backport, towncrier, CI runbooks |
| `dev-testing-contributor` | Writing/modifying tests, provider pattern, protocol feature detection, testsuite architecture |
| `dev-backend-development` | Implementing a new database backend (StorageBackend, adapters, transactions, errors) |
| `dev-expression-dialect` | Expression-Dialect separation, SQL generation rules, adding dialect protocols |
| `dev-protocol-design` | Designing Protocols, runtime_checkable, feature detection |
| `dev-sync-async-parity` | Keeping sync/async APIs equivalent, parity testing |

### User skills (`.claude/skills/user-*`)

`user-getting-started`, `user-modeling-guide`, `user-activerecord-pattern`,
`user-query-advanced`, `user-relationships`, `user-enterprise-features`,
`user-performance-tuning`, `user-testing-guide`, `user-troubleshooting` — for application
developers using the library.

## Test Execution

When executing tests, ALWAYS show the complete unfiltered output. Do NOT:
- Use `grep` or any other filtering to hide parts of the output
- Use `tail`/`head` to truncate output
- Pipe test output through any command that may suppress failure/error lines
- Assume any stage or portion of the output is unimportant

The full pytest output (including the summary line with pass/fail/skip counts) MUST be visible.
Exception: if the output is so large it exceeds tool limits, use the dedicated output capture
mechanism instead of manual truncation.