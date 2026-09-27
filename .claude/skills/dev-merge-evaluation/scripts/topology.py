# .claude/skills/dev-merge-evaluation/scripts/topology.py
"""Branch topology invariant: ``main`` subset of ``release/<active>`` subset of ``feature``.

Why this exists
---------------
The intended topology is a chain with no divergence at any link:

    main  subset of  release/<active>  subset of  feature/*  |  fix/*

A merge evaluation that inspects only the ``release -> feature`` link misses the
``main -> release`` link entirely, and a repository can sit permanently diverged
without any single review noticing. This tool checks every link and, when a link
is broken, reports *which side* drifted, by how much, and which files are
involved.

The output rule
---------------
Every verdict ships with the evidence that produced it, because a bare verdict is
not auditable and the expensive mistakes in this area all came from trusting one.
Four specific traps are handled explicitly:

1. **Inflated conflict surface.** Diffing two branch *tips* also counts files one
   side reverted after the merge base, pointing at conflicts that do not exist.
   The affected-file set is always computed from the merge base.

2. **Wrong release branch from string ordering.** Sorting ``v1.0.0.dev9`` against
   ``v1.0.0.dev20`` lexicographically picks ``dev9``, which then reports a
   divergence that does not exist. Version components are compared numerically.

3. **Stale local branches.** A local branch left over from before a reset reports
   a divergence that is not on the remote. The remote-tracking ref wins.

4. **Unreleased repositories.** No release branch is not a violation; it is a
   different workflow, reported as such instead of failing.

Usage
-----
    python topology.py --repo <path> --feature <branch> [--main main]
                       [--release release/v1.0.0 | auto] [--fetch] [--json]

Exit code is 0 when the chain holds and 1 when any link diverges, so the tool can
gate a merge evaluation. Exit code 2 means the branch under evaluation does not
exist in this repository, which means "skip this repository", not "failed".
"""

import argparse
import json
import os
import re
import subprocess
import sys

MAX_LISTED_COMMITS = 40
MAX_LISTED_FILES = 30


class GitError(RuntimeError):
    """A git invocation failed in a way that invalidates the report."""


def run_git(repo, args, check=True):
    proc = subprocess.run(
        ["git", "-C", repo] + list(args), capture_output=True, text=True
    )
    if check and proc.returncode != 0:
        raise GitError(
            "git {} failed ({}): {}".format(
                " ".join(args[:4]), proc.returncode, proc.stderr.strip()[:200]
            )
        )
    return proc.stdout


def rev_parse(repo, rev):
    return run_git(repo, ["rev-parse", "--verify", "--quiet", rev + "^{commit}"], check=False).strip() or None


def is_ancestor(repo, ancestor, descendant):
    proc = subprocess.run(
        ["git", "-C", repo, "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def ahead_behind(repo, left, right):
    parts = run_git(repo, ["rev-list", "--left-right", "--count", left + "..." + right]).split()
    if len(parts) != 2:
        raise GitError("unexpected rev-list output: {!r}".format(parts))
    return int(parts[0]), int(parts[1])


def list_commits(repo, spec, limit=MAX_LISTED_COMMITS):
    lines = [
        line
        for line in run_git(repo, ["log", "--oneline", "--no-decorate", spec]).splitlines()
        if line.strip()
    ]
    return lines[:limit], len(lines)


def affected_files(repo, drifted_tip, base_tip, other_tip):
    """Files the drifted side changed since the merge base, and the overlap.

    Computed as ``diff(base..drifted)`` rather than tip-to-tip so reverts are not
    reported as overlap. Returns ``(overlap, drifted, other, note)``; *note*
    explains a failure to compute rather than leaving the caller to interpret a
    crash.
    """
    merge_base = run_git(repo, ["merge-base", base_tip, other_tip], check=False).strip()
    if not merge_base:
        return (
            [],
            [],
            [],
            "no common ancestor between {} and {} (unrelated histories, or stale "
            "refs); overlap cannot be computed".format(base_tip, other_tip),
        )
    drifted = set(run_git(repo, ["diff", "--name-only", merge_base + ".." + drifted_tip]).split())
    other = set(run_git(repo, ["diff", "--name-only", merge_base + ".." + other_tip]).split())
    return sorted(drifted & other), sorted(drifted), sorted(other), ""


def version_key(name):
    """Numeric-aware sort key for release branch names.

    Plain string ordering ranks ``v1.0.0.dev9`` above ``v1.0.0.dev20`` because
    ``'9' > '2'``, which silently audits the wrong release branch.
    """
    parts = re.findall(r"\d+", name)
    return tuple(int(part) for part in parts) if parts else (0,)


def detect_release(repo, pattern):
    """Highest-sorting remote (then local) branch matching *pattern*."""
    for prefix in ("refs/remotes/origin/", "refs/heads/"):
        out = run_git(repo, ["for-each-ref", "--format=%(refname:short)", prefix + pattern])
        candidates = [line.strip() for line in out.splitlines() if line.strip()]
        if candidates:
            return sorted(candidates, key=version_key)[-1]
    return None


def resolve(repo, rev):
    """Resolve a branch name to a ref git can diff, preferring the remote.

    A topology audit must judge what is published. A stale local branch left over
    from before a reset reports a divergence that does not exist remotely.
    ``for-each-ref --format=%(refname:short)`` already yields ``origin/<branch>``
    for remote-tracking refs, so the bare name is tried first to avoid producing
    ``origin/origin/<branch>``.
    """
    for candidate in ("origin/" + rev, rev):
        if rev_parse(repo, candidate):
            return candidate
    return None


def check_link(repo, name, ancestor, descendant, report):
    if not rev_parse(repo, ancestor) or not rev_parse(repo, descendant):
        report["links"].append(
            {
                "link": name,
                "status": "UNRESOLVED",
                "ancestor": ancestor,
                "descendant": descendant,
                "detail": "could not resolve one side to a commit",
            }
        )
        return False

    if is_ancestor(repo, ancestor, descendant):
        ahead, _ = ahead_behind(repo, ancestor, descendant)
        report["links"].append(
            {
                "link": name,
                "status": "OK",
                "ancestor": ancestor,
                "descendant": descendant,
                "commits_ahead": ahead,
                "detail": "{} is contained in {}".format(ancestor, descendant),
            }
        )
        return True

    ancestor_only, descendant_only = ahead_behind(repo, ancestor, descendant)
    drifted_side = "ancestor" if ancestor_only else "descendant"
    drifted_tip = ancestor if ancestor_only else descendant
    overlap, drifted, other, note = affected_files(repo, drifted_tip, ancestor, descendant)
    spec = (
        "{}..{}".format(descendant, ancestor)
        if ancestor_only
        else "{}..{}".format(ancestor, descendant)
    )
    commits, total = list_commits(repo, spec)
    report["links"].append(
        {
            "link": name,
            "status": "DIVERGED",
            "ancestor": ancestor,
            "descendant": descendant,
            "drifted_side": drifted_side,
            "commits_only_on_ancestor": ancestor_only,
            "commits_only_on_descendant": descendant_only,
            "drift_commits": commits,
            "drift_commits_total": total,
            "overlap_files": overlap,
            "drifted_files_count": len(drifted),
            "other_files_count": len(other),
            "note": note,
        }
    )
    return False


def render(report):
    lines = []
    add = lines.append
    add("Branch topology report")
    add("  repo:    {}".format(report["repo"]))
    add("  main:    {}".format(report["main"]))
    add("  release: {}".format(report["release"] or "(none)"))
    add("  feature: {}".format(report["feature"]))
    add("")

    if report["unreleased"]:
        add("UNRELEASED repository: no release branch exists.")
        add("  Not a topology violation. Per skill section B4, work directly on main;")
        add("  if a feature fork already exists, fast-forward it into main and delete")
        add("  the fork. No PR and no changelog fragment are required.")
        add("")

    for link in report["links"]:
        header = "  {}: {} <= {}".format(link["link"], link["ancestor"], link["descendant"])
        if link["status"] == "OK":
            add("{}  OK".format(header))
            add("      {}".format(link["detail"]))
            continue
        if link["status"] == "UNRESOLVED":
            add("{}  UNRESOLVED".format(header))
            add("      {}".format(link["detail"]))
            continue

        add("{}  DIVERGED".format(header))
        ahead = (
            link["commits_only_on_ancestor"]
            if link["drifted_side"] == "ancestor"
            else link["commits_only_on_descendant"]
        )
        add("      drifted side: {} ({} commit(s) not contained in the other)".format(
            link["drifted_side"], ahead
        ))
        add("      commits only on ancestor:  {}".format(link["commits_only_on_ancestor"]))
        add("      commits only on descendant: {}".format(link["commits_only_on_descendant"]))
        shown = link["drift_commits"]
        add("      drifted commits ({} shown of {}):".format(len(shown), link["drift_commits_total"]))
        for commit in shown:
            add("        {}".format(commit))
        if link["drift_commits_total"] > len(shown):
            add("        ... {} more".format(link["drift_commits_total"] - len(shown)))
        note = link.get("note")
        if note:
            add("      note: {}".format(note))
        overlap = link["overlap_files"]
        add("      overlap with the other side: {} file(s)".format(len(overlap)))
        for path in overlap[:MAX_LISTED_FILES]:
            add("        {}".format(path))
        if len(overlap) > MAX_LISTED_FILES:
            add("        ... {} more".format(len(overlap) - MAX_LISTED_FILES))
        if not overlap and not note:
            add("        (disjoint surfaces; the release->main merge will drag the")
            add("         divergence forward, so record the follow-up)")
        add("      file counts since merge base: drifted={} other={}".format(
            link["drifted_files_count"], link["other_files_count"]
        ))
        add("      decision required: sync before merge, defer with a plan, or escalate.")
        add("      A mechanical check cannot choose; see skill section B5.")

    add("")
    add("  verdict: {}".format("chain holds" if report["ok"] else "chain broken"))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check the main -> release -> feature topology chain."
    )
    parser.add_argument("--repo", default=".", help="path to the git repository")
    parser.add_argument("--feature", required=True, help="feature/fix branch under evaluation")
    parser.add_argument("--main", default="main", help="main branch name")
    parser.add_argument(
        "--release",
        default="auto",
        help="release branch name, or 'auto' for the highest-sorting release/*",
    )
    parser.add_argument("--fetch", action="store_true", help="run 'git fetch --prune' first")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    repo = os.path.abspath(args.repo)
    if not run_git(repo, ["rev-parse", "--git-dir"], check=False).strip():
        print("error: {} is not a git repository".format(repo), file=sys.stderr)
        return 2

    if args.fetch:
        run_git(repo, ["fetch", "--prune", "--quiet"], check=False)

    release_ref = detect_release(repo, "release/*") if args.release == "auto" else args.release
    main_ref = resolve(repo, args.main)
    feature_ref = resolve(repo, args.feature)
    release_resolved = resolve(repo, release_ref) if release_ref else None

    if not main_ref:
        print("error: could not resolve main branch {!r}".format(args.main), file=sys.stderr)
        return 2
    if not feature_ref:
        available = run_git(
            repo, ["for-each-ref", "--format=%(refname:short)", "refs/remotes/origin"]
        ).split()
        print(
            "error: could not resolve feature branch {0!r} in {1}\n"
            "  looked for: origin/{0} and {0}\n"
            "  this repository does not participate in the branch under evaluation;\n"
            "  skip it rather than treating it as a topology violation.\n"
            "  available remote branches (first 20): {2}".format(
                args.feature, repo, ", ".join(sorted(available)[:20])
            ),
            file=sys.stderr,
        )
        return 2

    report = {
        "repo": repo,
        "main": main_ref,
        "release": release_resolved,
        "feature": feature_ref,
        "unreleased": release_resolved is None,
        "links": [],
        "ok": True,
    }

    ok = True
    if release_resolved:
        ok &= check_link(repo, "main->release", main_ref, release_resolved, report)
        ok &= check_link(repo, "release->feature", release_resolved, feature_ref, report)
    ok &= check_link(repo, "main->feature", main_ref, feature_ref, report)
    report["ok"] = bool(ok)

    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
