---
name: dev-merge-evaluation
description: Merge-evaluation runbook for feature branches targeting release-cycle branches - purpose achievement, branch health, CI gates, breaking-change inventory, backend adaptation matrix, changelog fragments, and reflection regression; produces a merge / conditional-merge / hold verdict
license: MIT
compatibility: opencode
metadata:
  category: release
  level: advanced
  audience: developers
  order: 8
  prerequisites:
    - dev-release-workflow
---

# Feature Branch Merge Evaluation

Before merging a feature branch into its release-cycle target (`release/vX.Y.*` or `main`),
run a fixed six-category evaluation so every merge decision uses the same criteria and nothing
is forgotten. The classic omissions are the **backend adaptation status** (core protocol changes
break unadapted backends), **changelog fragments**, and **reflection regression** — this runbook
makes them mandatory checkpoints.

## 1. Evaluation Discipline

1. **Trust CI.** CI has already run the full test matrix. Do **not** re-run the full suite
   locally during evaluation; only run targeted spot checks when a specific claim needs
   verification (e.g., one test file for a suspected regression).
2. **Use `rg`, never `grep`** when searching repository content.
3. **Breaking scope first.** Evaluation order: **D (breaking surface + backend adaptation)
   → B (divergence/conflict surface) → A (purpose achievement) → E (changelog) → C/F (spot
   checks)**. The backend-adaptation verdict (D) decides merge vs hold before anything else.
4. **Evidence over impression.** Every claim must cite a command, commit hash, or file path.
5. **Enumerate before diving.** List the branch's unique commits and classify them
   (feat/refactor/fix/test/docs/ci/chore) before reading details; identify scope creep early.
6. **Evaluation precedes the PR.** The evaluation runs **before** the PR is opened. At this
   point `changelog.d/` contains only fragments from **previously merged** feature/fix branches
   (they persist until the towncrier build) — a fragment describing the **current** branch's
   changes must not exist yet (its PR is not open). Do not require fragments for the current
   branch during evaluation, and do not open the PR before the evaluation passes. After the
   verdict, the sequence is: open PR → write fragments named by the **actual PR number** (per
   the fragment plan from E1) → push → merge.

## 2. Six-Category Checklist

### A. Purpose Achievement

| Item | How to check |
|---|---|
| A1. Core goal landed | Locate the implementation commit/code for the branch's stated purpose (the plan document under `.claude/plan/**` referenced by the branch) |
| A2. Side refactors closed loop | For each related plan document, confirm its phases/checklists are marked done and the corresponding commits exist |
| A3. Unplanned carry-ins | `git log --oneline <feature> --not <target>` — classify every commit; commits mapping to no plan document are scope creep and need justification |

### B. Branch Health

| Item | How to check |
|---|---|
| B1. Divergence from target | `git rev-list --left-right --count <target>...<feature>`; `git log --oneline <target> --not <feature>` to see what the branch lacks. If the target moved ahead, assess the rebase/merge conflict surface (`git diff <target>...<feature>` on colliding files). **The target must fall behind the feature — a two-way divergence is a blocker to reconcile first** |
| B2. Clean worktree | `git status --short` must be empty; verify recent edits are committed, not lost |
| B3. Commit convention | Spot check conventional commits; all breaking commits carry `!` and a `BREAKING CHANGE` footer |
| B4. Fork source & merge path | Determine the branch the feature was forked from: a candidate branch whose **tip equals `git merge-base <candidate> <feature>`** is a fork-source match; disambiguate multiple matches by ancestry (the fork source is the one the others descend from). Merge path by fork source: **forked from a `release/vX.Y.*` branch → PR into that release branch (fragments per the E1 plan)**; **forked from `main` → direct merge, no PR, no fragments**. **Unreleased repos** (never published, no release branch — e.g. a backend still on dev-only main): work directly on `main`, forks are unnecessary; if a fork already exists (e.g. forked from another feature branch — a process violation), resolve it by direct fast-forward merge into `main`, no PR, no fragments, then delete the fork branches |

### C. Test & Quality Gates (CI-owned)

| Item | How to check |
|---|---|
| C1. CI green | Branch CI status in GitHub Actions — all jobs pass, including the full Python version matrix and free-threaded builds |
| C2. Coverage | `test-with-coverage` job: ≥90% for modified files (per branch protection rules) |
| C3. Lint & types | `ruff check src/` and `mypy src/` clean (spot check locally only if CI does not run them) |

### D. Breaking Changes & Compatibility (decisive)

| Item | How to check |
|---|---|
| D1. Explicit breaking commits | `git log --oneline <feature> --not <target> \| rg "!"` |
| D2. Actual breaking surface | Scan for removed/renamed public classes, methods, module paths, enum value renames, constructor parameter removals — **unmarked-but-breaking commits are the common failure**; do not rely on the `!` marker alone |
| D3. Migration path | Each breaking item needs a documented migration (docstring/plan/changelog); check for `DeprecationWarning` transition where promised |
| D4. Backend adaptation matrix | For each backend repo, verify it works against the new core: `rg "<renamed-or-removed-symbol>" python-activerecord-<backend>/src/` — any hit means that backend is **not adapted**. Cover all 10 backends + devtools + testsuite |
| D5. Testsuite adaptation | `rg "<renamed-symbol>" python-activerecord-testsuite/src/` |

> **D4 is the merge gate.** Core protocol changes (`format_*` signatures, expression class
> model, removed symbols) break unadapted backend repositories at import time. If the strategy
> is "core first, backends follow", the verdict can be conditional-merge **only** if the release
> sequencing accounts for unadapted backends; otherwise hold until adapted.

### E. Release Artifacts & Docs

| Item | How to check |
|---|---|
| E1. Changelog fragment plan | Evaluation runs **before** the PR exists. Expected state: `changelog.d/` holds fragments from **previously merged** features/fixes (normal — they persist until the towncrier build); a fragment describing the **current** branch's changes must **NOT** exist (its PR is not open yet — finding one means it was written pre-PR under the old convention: flag as legacy/process bug; verify by matching fragment numbers against merged PRs via `gh pr list --state merged` or the `(#NNN)` in merge commits). Produce the **fragment to-do list** for the post-evaluation step: for each user-visible change (especially breaking/changed/fixed), record which fragment must be written after the PR is opened (`changelog.d/<PR-N>.<type>.md`) |
| E2. Plan document status | Referenced `.claude/plan/**` docs updated from "待确认" / "方案" to implemented state |
| E3. Docs sync | Spot check en_US XML docs for renamed APIs |

### F. Reflection Regression

| Item | How to check |
|---|---|
| F1. Expression survey | Re-run `python-activerecord/.claude/plan/2026-09-14/expression_survey.py`; compare against `expression_data.json`: new expressions appear in the D2-reachable set (their `format_method` is implemented by at least one dialect), removed ones are gone from protocols and mixins |

## 3. Breaking-Change Inventory Method

For each breaking item, record:

1. **What** changed (class/method/module/enum/parameter)
2. **Marker**: explicitly `!`-marked, or unmarked-but-breaking (flag this — it is a process bug)
3. **Migration path**: where consumers go instead
4. **Deprecation transition**: `DeprecationWarning` present or deliberately skipped
5. **Backend impact**: which of the 10 backends touch the changed surface, and their adaptation status

Practical scans for the inventory:

```bash
# Explicit breaking commits
git log --oneline <feature> --not <target> | rg "!"

# Removal of a public symbol across the whole ecosystem
rg "<symbol>" python-activerecord*/src/ python-activerecord-*/src/

# Import sites of a removed class anywhere
rg "from.*import.*<symbol>" --type py python-activerecord*/ python-activerecord-*/
```

## 4. Verdict Rules

| Verdict | Conditions |
|---|---|
| **merge** | CI green + coverage pass + purpose achieved + every breaking item inventoried with migration + fragment to-do list produced (E1) + all backends/testsuite adapted |
| **conditional merge** | Purpose achieved, CI green, breaking surface fully inventoried, but only non-blocking gaps remain (plan-status updates, minor doc sync, legacy pre-PR fragments). Conditions listed explicitly with owners; merge sequencing must account for any unadapted backend |
| **hold** | Any of: backends not adapted to core protocol changes without a release-sequencing plan; breaking changes without inventory or migration path; purpose not achieved; CI red; unresolved divergence from target |

When in doubt between conditional-merge and hold, **hold** — a merge that lands unadapted
backends into a release line costs more than a delayed merge.

## 5. Output Template

```markdown
# Merge Evaluation: <feature> → <target>

## 结论: merge / conditional merge / hold

## A. 目的达成度
| 项 | 结论 | 依据 (commit / file) |

## B. 分支健康度
| 项 | 结论 | 依据 |

## C. 测试与质量门禁（CI）
| 项 | 结论 | 依据 |

## D. 破坏面清单
| 变更 | 类型 | 标记 | 迁移路径 | 后端适配 |
|---|---|---|---|---|
| ... | removed/renamed/param | ! / unmarked | ... | adapted / NOT adapted |

## E. 发布物（评测在 PR 之前：changelog.d/ 此时应只含已合入分支的历史片段，无当前分支片段）
| 项 | 结论 | 依据 |

## 片段计划（PR 打开后执行）
| 待写片段 | 类型 | 对应变更 |
|---|---|---|
| changelog.d/<PR-N>.breaking.md | breaking | ... |

## F. 反射回归
| 项 | 结论 | 依据 |

## 条件 / 阻塞项
- [ ] <condition> — owner

## 依据汇总
<commands and commit hashes>
```

## 6. Post-Evaluation Sequence & Relation to `dev-release-workflow`

**After the verdict**, in order:

1. Open the PR on GitHub (feature branch → release branch) — the PR number is now assigned.
2. Write the changelog fragments per the E1 fragment plan, named by the **actual PR number**
   (`changelog.d/<PR-N>.{added|changed|fixed|...}.md`), commit and push.
3. Confirm CI (including the Changelog Fragment Check) is green on the PR.
4. Perform the merge per `dev-release-workflow`.

This skill decides **whether** the merge should happen; the merge operation itself
(squash vs rebase, linear history, CI re-check on the target branch, branch deletion,
changelog fragment lifecycle) follows `dev-release-workflow`.
