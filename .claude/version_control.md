# Version Control Principles for rhosocial-activerecord

> **Scope**: This file holds the **policy** (the hard rules). Step-by-step **runbooks**
> (release workflow, dev→alpha→beta→rc→final, hotfix, backport, CI troubleshooting) live in the
> **`dev-release-workflow`** skill — load it when performing an actual release/patch/branch
> operation. See the rules index (`AGENTS.md` → "Rules Index") for the full navigation map.

## 1. Version Management

### Package Ecosystem

Three package kinds with distinct versioning:

| Package | Version | Notes |
|---------|---------|-------|
| `rhosocial-activerecord` (core) | independent semver | only Pydantic dependency |
| `rhosocial-activerecord-testsuite` | tracks core | core + pytest deps |
| `rhosocial-activerecord-{backend}` | MAJOR synced with core; MINOR/PATCH independent | core + native driver |

### Python Version Support

- **requires-python**: `>=3.8` (`[project]` in `pyproject.toml`).
- **Supported (1.0.x)**: 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14 (+ 3.15 in CI/classifiers).
- **Free-threaded builds**: 3.13t, 3.14t.
- **Pydantic**: `==2.10.6` for Python 3.8 (last 3.8-compatible line); `>=2.12.0` for 3.9+.
- `1.1.x` will likely drop 3.8/3.9 (min Python 3.10+); announced ≥6 months before.

Use `requirements-3.8.txt` for Python 3.8 environments.

### Semantic Versioning (PEP 440, strict)

Format: `[EPOCH!]RELEASE[-PRE][.postPOST][.devDEV][+LOCAL]`

- **MAJOR**: breaking public API; removal of deprecated features; Pydantic major bump;
  minimum-Python bump. (a `!` epoch may also reset numbering)
- **MINOR**: backward-compatible new features; MUST NOT break compat or bump min Python.
- **PATCH**: backward-compatible fixes/security/perf/docs only; MUST NOT add features.

Pre-release cycle per new `X.Y.0`: `dev → alpha → beta → rc → final`. Phases:
`X.Y.0.devN`, `X.Y.0aN`, `X.Y.0bN`, `X.Y.0rcN`, then `X.Y.0`.
- Skip intermediate releases if no bugs in a 1-week window; fast-track allowed (≥1 week between
  phase transitions, except critical security).

**Where the version lives**: The package is a PEP 420 namespace package with **no `__init__.py`
and no `__version__`**. The canonical version is `[project] version` in `pyproject.toml`
(currently `1.0.0.dev29`). Version bumps edit `pyproject.toml` only.

## 2. Branching Strategy

- **`main`**: always release-ready. Protected; squash-merge features, rebase hotfixes; linear history.
- **`release/vX.Y.Z[.devN|aN|bN|rcN]`**: per-version staging; created from `main`; the version's
  full lifecycle happens here; reused across dev→final.
- **Development** from a release branch: `feature/{ticket}-{desc}`, `bugfix/{desc}`, `fix/...`,
  `docs/{desc}`, `test/{desc}`.
- **`hotfix/{ticket}-{desc}`**: critical fixes from `main`/tag; merge back to `main` and active
  `release/*`.
- **`maint/*`**: LTS maintenance branches.

### Protection & CI gates (all protected branches)

- **Linear history everywhere** — no merge commits on `main`/`release`/`maint`; rebase/squash.
- Required checks must pass: `test-with-coverage`, `test-other-versions`, `test-free-threaded`.
- Branch must be up-to-date before merge; review required (≥1 approval).
- Maintainers may bypass on release branches only for version bumps / changelog / docs-only.
- Enable CI on push & PR for `main`, `release/v**`, `maint/**`.

Runbooks for creating branches, phase transitions, merging to main, and hotfix fast-tracking are
in the `dev-release-workflow` skill.

## 3. Commit Message Standards

Follow **Conventional Commits**: `<type>[optional scope]: <description>`.

### Types

`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`, `revert`
(`security:`, `feat!:` are also valid with `!` for breaking changes).

### Scopes

See `.claude/feature_points.md` for the full, authoritative scope list. Highlights:
- **Core**: `query` (and `query-aggregate|cte|simple`), `backend` (`backend-cli|adapters`),
  `field`, `relation`, `event`, `mixin`.
- **Backend packages**: `<backend_name>` (e.g. `mysql`, `postgres`, `sqlite`),
  `<backend_name>-cli|adapters`, `dialect`, `driver`.
- **Testsuite**: `feature` (`feature-basic|events|mixins|query|relation|backend|examples|interface`),
  `realworld`, `benchmark`, `provider`.
- Multiple scopes comma-separated (`feat(query,backend): ...`); subdivide with hyphens.

### Description / body

- Imperative mood, lowercase, no trailing period, <72 chars.
- Body explains "why" not "what"; bullet points; blank line after subject.
- Footer: `Fixes/Closes/Resolves <issue>`; `BREAKING CHANGE:`; `Co-authored-by:`.

### Messages with special characters

For messages containing `` ` `` `$` `"` `\` `|` `>` etc., write to `.claude/tmp/` and use
`git commit -F <file>` to avoid shell-escaping errors. Delete the temp file after use.

### Language

English by default. Non-English messages MUST include an English translation + reason in the body.

### Commit hygiene

- Squash related commits; one logical change per commit; no `.claude/tmp/` files or secrets in
  the message; write `wip:` for in-progress pushes.

## 4. Changelog (Towncrier)

- **Fragment dir**: `changelog.d/` (`<issue>.added.md/.fixed.md/.security.md`, etc.).
- Build with `towncrier build --version X.Y.Z --yes` before merging to `main`.
- `CHANGELOG.md` is generated from fragments; fragment files are removed after build.
- **Exemptions** from fragment requirement: changes only to `tests/`, `docs/`, `.github/`;
  PR title `[trivial]`; `no-changelog-needed` label.
- Abandoned features must delete their fragment before release.

## 5. Release / Post-Release Policy (overview)

- Before merging to `main`: build changelog, bump version in `pyproject.toml`, tag `vX.Y.Z`,
  publish to PyPI. CI must be green on `main` before tagging.
- **Backport policy**: see the `dev-release-workflow` skill (hotfix/backport runbooks); patch
  releases never introduce new features.
- Version increment rules, post-release defect handling, multi-version compat, and coverage
  gates are documented in the `dev-release-workflow` skill and this file's earlier full appendix
  is preserved in `devtools` history.

## Rules Index reminder

This is the policy core. For **how-to run** any of the above (exact git/CI commands), load the
`dev-release-workflow` skill. See `AGENTS.md` → "Rules Index" for the complete navigation.