# .claude/skills/dev-merge-evaluation/scripts/port_triage.py
"""Classify commits from one branch by how much work porting them to another needs.

Why this exists
---------------
When work lands on one branch and must reach another, the instinctive measure is
the **conflict-hunk count** from a trial cherry-pick. That number is not a
measure of missing work, and treating it as one produces confidently wrong
estimates. A single divergence produces large hunk counts on both sides for work
that is already present, in a form the target branch evolved past.

The five states this tool separates
-----------------------------------
``CLEAN``
    Applies with no conflict. Port it.

``ALREADY_PRESENT``
    Applies to nothing: the staged diff after the pick is empty. The work is in
    the target. Do not port it, and do not report it as a loss.

``EVOLVED``
    Conflicts, but every symbol the change introduces already exists in the
    target, in a different shape -- usually a signature or convention a later
    refactor replaced. Porting the patch would revert the newer design. Verify
    by symbol, not by text: a target that re-parameterised a call site makes text
    matching report a false absence.

``SUPERSEDED``
    The symbols exist *and* the mechanism the change depends on no longer exists,
    so the added code is unreachable. A serialisation marker for a ``cast_types``
    chain is the canonical case, after casts became ordinary expression nodes:
    the code still names a real symbol, but nothing can produce it.

``NEEDS_REVIEW``
    Symbols are genuinely absent. This is the only state representing real
    outstanding work, and it is a human decision.

The discriminator is the **net staged diff plus a symbol-footprint comparison**,
never the hunk count.

Destructive-operation safety
----------------------------
All state-mutating git commands run against the scratch worktree, never against
the repository's main checkout. This is not theoretical: ``git -C <repo> reset
--hard`` and ``git clean`` act on the checkout that owns the worktree list, so
running them with the repository path silently rewinds the caller's branch and
deletes their untracked files. ``assert_isolated`` refuses to proceed unless the
scratch directory is a real, separate worktree.

Conflicts are never resolved. Deciding which side wins is a design judgement; the
tool only measures the situation and hands the decision over with evidence.

Usage
-----
    python port_triage.py --repo <path> --base <branch> --from <branch> [--range a..b]
                          [--json] [--worktree-dir <path>] [--keep-worktree]

``--base`` receives the work, ``--from`` is where it comes from. With no range,
every commit in ``from`` but not in ``base`` is classified oldest first, which
matters because later commits often depend on earlier ones.
"""

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import warnings

CONFLICT_START = "<<<<<<<"
CONFLICT_MIDDLE = "======="
CONFLICT_END = ">>>>>>>"

SKIP_DIRS = ("__pycache__", ".git", "node_modules", ".mypy_cache", ".pytest_cache")

STATE_ORDER = ["CLEAN", "ALREADY_PRESENT", "EVOLVED", "SUPERSEDED", "NEEDS_REVIEW"]

STATE_MEANING = {
    "CLEAN": "applies with no conflict; port it",
    "ALREADY_PRESENT": (
        "net diff after applying is empty; the work is already in the base "
        "branch. Do not port, do not report as loss"
    ),
    "EVOLVED": (
        "every introduced symbol already exists in the base tree, so the target "
        "evolved past this patch; porting it reverts newer design. Confirm by "
        "symbol, then skip"
    ),
    "SUPERSEDED": (
        "symbols exist but the attributes they depend on are defined nowhere in "
        "the base tree, so the added code is unreachable. Verify, then skip"
    ),
    "NEEDS_REVIEW": "genuine outstanding work; needs a human decision",
}


def run_git(where, args, check=True):
    proc = subprocess.run(
        ["git", "-C", where] + list(args), capture_output=True, text=True
    )
    if check and proc.returncode != 0:
        raise RuntimeError(
            "git {} failed ({}): {}".format(
                " ".join(args[:4]), proc.returncode, proc.stderr.strip()[:200]
            )
        )
    return proc.stdout


def assert_isolated(repo, worktree):
    """Refuse to mutate anything unless *worktree* is a distinct git worktree.

    ``git -C <repo> reset --hard`` / ``git clean`` operate on the checkout that
    owns the worktree list, not on a sibling worktree path. Pointing those at the
    repository rewinds the caller's branch and deletes untracked files, so the
    two paths must provably differ and the scratch path must be registered.
    """
    if os.path.abspath(repo) == os.path.abspath(worktree):
        raise RuntimeError(
            "refusing to run: scratch worktree path equals the repository path"
        )
    listed = run_git(repo, ["worktree", "list", "--porcelain"])
    registered = False
    for line in listed.split("\n"):
        if line.startswith("worktree ") and os.path.abspath(line[9:].strip()) == os.path.abspath(
            worktree
        ):
            registered = True
            break
    if not registered:
        raise RuntimeError(
            "refusing to run: {} is not a registered worktree of {}".format(worktree, repo)
        )


def commit_range(repo, base, source, explicit):
    """Commits to triage, oldest first.

    An explicit ``--range`` may hold ``a..b`` spans as well as bare shas; each
    span is expanded via ``rev-list`` so that passing a range does not silently
    degrade into one unresolvable "commit" that then gets classified as a
    conflict.
    """
    if not explicit:
        out = run_git(repo, ["rev-list", "--reverse", base + ".." + source])
        return [line for line in out.split() if line]

    shas = []
    for item in explicit.split(","):
        item = item.strip()
        if not item:
            continue
        if ".." in item:
            out = run_git(repo, ["rev-list", "--reverse", item])
            shas.extend(line for line in out.split() if line)
        else:
            shas.append(item)
    seen = set()
    ordered = []
    for sha in shas:
        if sha not in seen:
            seen.add(sha)
            ordered.append(sha)
    return ordered


def subject_of(repo, sha):
    return run_git(repo, ["log", "-1", "--format=%s", sha]).strip()


def split_conflicts(text):
    """Split a conflicted file into ``(ours, theirs)`` per hunk.

    Markers are anchored to column zero, which is how git writes them, so a
    marker-looking string inside a code line is not treated as a boundary.
    """
    lines = text.split("\n")
    hunks = []
    index = 0
    total = len(lines)
    while index < total:
        if not lines[index].startswith(CONFLICT_START):
            index += 1
            continue
        index += 1
        ours = []
        while index < total and not lines[index].startswith(CONFLICT_MIDDLE):
            ours.append(lines[index])
            index += 1
        index += 1
        theirs = []
        while index < total and not lines[index].startswith(CONFLICT_END):
            theirs.append(lines[index])
            index += 1
        index += 1
        hunks.append((ours, theirs))
    return hunks


def classify_hunks(text):
    """Count hunks where only one side has content versus both sides."""
    only_one = 0
    both = 0
    for ours, theirs in split_conflicts(text):
        ours_has = any(line.strip() for line in ours)
        theirs_has = any(line.strip() for line in theirs)
        if ours_has and theirs_has:
            both += 1
        else:
            only_one += 1
    return only_one, both


def added_definition_names(repo, sha):
    """Top-level definition names a commit introduces, per file.

    Restricted to ``def`` / ``class`` / non-indented assignment targets, so a
    local variable cannot masquerade as a public symbol.
    """
    names = {}
    current = None
    patterns = (
        re.compile(r"^\s*(?:async\s+)?def\s+(\w+)"),
        re.compile(r"^\s*class\s+(\w+)"),
        re.compile(r"^(\w+)\s*(?::[^=]+)?="),
    )
    for line in run_git(repo, ["show", "--format=", "--unified=0", sha]).split("\n"):
        if line.startswith("+++ b/"):
            current = line[6:].strip()
            names.setdefault(current, set())
            continue
        if current is None or not line.startswith("+") or line.startswith("+++"):
            continue
        body = line[1:]
        for pattern in patterns:
            match = pattern.match(body)
            if match:
                names[current].add(match.group(1))
                break
    return {path: sorted(symbols) for path, symbols in names.items() if symbols}


def collect_tree_symbols(worktree):
    """Every class, function, constant and imported name in the worktree.

    Assignment targets are included, not just ``class`` / ``def`` / imports. The
    comparison in :func:`triage_commit` must be symmetric with
    :func:`added_definition_names`, which extracts module-level assignments by
    regex: if this side skipped constants, every ``SOME_CONSTANT = "..."`` a
    commit introduces would look absent from the target and be misreported as
    outstanding work.
    """
    names = set()
    for root, dirs, files in os.walk(worktree):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in files:
            if not filename.endswith(".py"):
                continue
            path = os.path.join(root, filename)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                try:
                    tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
                except (SyntaxError, ValueError):
                    continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.add(node.name)
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    names.add(node.target.id)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            names.add(target.id)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        names.add(alias.asname or alias.name.split(".")[0])
    return names


def attribute_targets(diff_text):
    """Attribute names read by the added lines of *Python* hunks.

    A supersession signal needs attributes specifically: an attribute that no
    class in the target tree defines or assigns can never hold a value at
    runtime, so code reading it is unreachable.

    Only ``.py`` hunks are scanned. A commit that also adds Markdown or
    configuration files contributes path fragments such as ``.gitattributes`` and
    ``.yaml``, which match the attribute pattern but are not attribute reads, and
    would otherwise mark fully-ported work as superseded.
    """
    found = set()
    in_python = False
    for line in diff_text.split("\n"):
        if line.startswith("+++ b/"):
            in_python = line[6:].strip().endswith(".py")
            continue
        if line.startswith("diff --git"):
            in_python = False
            continue
        if not in_python:
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        for name in re.findall(r"\.(\w+)", line[1:]):
            if len(name) > 3 and not name.startswith("_"):
                found.add(name)
    return found


def tree_defines_attributes(worktree, names):
    """Which of *names* are mentioned anywhere in the worktree as an identifier.

    The bar is deliberately "mentioned at all", not "defined as a class
    attribute". A commit that reads ``expr.cast_types`` is only unreachable when
    nothing in the target tree ever produces that name; an attribute supplied by
    a dataclass field, a ``__getattr__`` or a protocol still counts as existing.
    Requiring a literal ``self.<name>`` or a top-level definition instead would
    flag ordinary reads such as ``constraint.type`` and mislabel fully-ported
    work as superseded.
    """
    present = set()
    wanted = set(names)
    for root, dirs, files in os.walk(worktree):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for filename in files:
            if not filename.endswith(".py"):
                continue
            body = open(
                os.path.join(root, filename), encoding="utf-8", errors="replace"
            ).read()
            for name in wanted - present:
                if re.search(r"\b" + re.escape(name) + r"\b", body):
                    present.add(name)
    return present


def triage_commit(repo, worktree, sha, base_sha, tree_symbols, attribute_cache):
    """Classify one commit. Every mutation targets *worktree*, never *repo*."""
    run_git(worktree, ["cherry-pick", "--abort"], check=False)
    run_git(worktree, ["reset", "--hard", "-q", base_sha])
    run_git(worktree, ["clean", "-qfd"])

    proc = subprocess.run(
        ["git", "-C", worktree, "cherry-pick", "-n", sha],
        capture_output=True,
        text=True,
    )
    definitions = added_definition_names(repo, sha)
    result = {
        "sha": sha,
        "subject": subject_of(repo, sha),
        "state": None,
        "hunks_one_sided": 0,
        "hunks_two_sided": 0,
        "files": [],
        "symbols_introduced": sorted({s for v in definitions.values() for s in v}),
        "missing_symbols": [],
        "unreachable_attributes": [],
    }

    if proc.returncode == 0:
        quiet = subprocess.run(
            ["git", "-C", worktree, "diff", "--cached", "--quiet"], capture_output=True
        )
        result["state"] = "ALREADY_PRESENT" if quiet.returncode == 0 else "CLEAN"
        run_git(worktree, ["cherry-pick", "--abort"], check=False)
        return result

    for path in run_git(worktree, ["diff", "--name-only", "--diff-filter=U"]).split():
        full = os.path.join(worktree, path)
        if not os.path.isfile(full):
            continue
        result["files"].append(path)
        one, two = classify_hunks(open(full, encoding="utf-8", errors="replace").read())
        result["hunks_one_sided"] += one
        result["hunks_two_sided"] += two

    introduced = set(result["symbols_introduced"])
    result["missing_symbols"] = sorted(introduced - tree_symbols)

    # The attribute probe must see the *pristine* base tree. The worktree is
    # still holding the conflicted pick, whose incoming side contains the very
    # attribute being probed, so probing here would find every name and make
    # SUPERSEDED unreachable by construction.
    run_git(worktree, ["cherry-pick", "--abort"], check=False)
    run_git(worktree, ["reset", "--hard", "-q", base_sha])
    run_git(worktree, ["clean", "-qfd"])

    diff_text = run_git(repo, ["show", "--format=", sha], check=False)
    attributes = attribute_targets(diff_text)
    for name in attributes:
        if name not in attribute_cache:
            attribute_cache[name] = bool(tree_defines_attributes(worktree, {name}))
    result["unreachable_attributes"] = sorted(
        name for name in attributes if not attribute_cache[name]
    )

    if result["missing_symbols"]:
        result["state"] = "NEEDS_REVIEW"
    elif result["unreachable_attributes"]:
        result["state"] = "SUPERSEDED"
    else:
        result["state"] = "EVOLVED"

    run_git(worktree, ["cherry-pick", "--abort"], check=False)
    return result


def render(results, args):
    lines = []
    add = lines.append
    add("Port triage report")
    add("  base (receiver): {}".format(args.base))
    add("  from (source):   {}".format(args.source))
    add("")

    buckets = {state: [] for state in STATE_ORDER}
    for item in results:
        buckets.setdefault(item["state"], []).append(item)

    for state in STATE_ORDER:
        items = buckets.get(state) or []
        if not items:
            continue
        add("  {} ({})".format(state, len(items)))
        for item in items:
            add("    {}  {}".format(item["sha"][:8], item["subject"][:62]))
            add("        {}".format(STATE_MEANING[state]))
            if state in ("EVOLVED", "SUPERSEDED", "NEEDS_REVIEW"):
                add(
                    "        hunks: {} one-sided, {} two-sided (not a workload measure)"
                    .format(item["hunks_one_sided"], item["hunks_two_sided"])
                )
            if item["unreachable_attributes"]:
                add("        unreachable attributes:")
                for name in item["unreachable_attributes"][:8]:
                    add("          {}".format(name))
                extra = len(item["unreachable_attributes"]) - 8
                if extra > 0:
                    add("          ... {} more".format(extra))
            if item["missing_symbols"]:
                add("        symbols absent from the base tree:")
                for name in item["missing_symbols"][:10]:
                    add("          {}".format(name))
                extra = len(item["missing_symbols"]) - 10
                if extra > 0:
                    add("          ... {} more".format(extra))
            if item["files"] and state == "NEEDS_REVIEW":
                for path in item["files"][:6]:
                    add("        conflicts in: {}".format(path))
        add("")

    counts = {state: len(buckets.get(state) or []) for state in STATE_ORDER}
    total_hunks = sum(
        item["hunks_one_sided"] + item["hunks_two_sided"] for item in results
    )
    add(
        "  summary: "
        + (", ".join("{}={}".format(s, counts[s]) for s in STATE_ORDER if counts[s]) or "none")
    )
    add("  raw two-sided hunk total: {} (compare against NEEDS_REVIEW)".format(
        sum(item["hunks_two_sided"] for item in results)
    ))
    add("  commits classified: {} of {}".format(len(results), len(results)))
    add("")
    add("  Only NEEDS_REVIEW is real outstanding work. The gap between the raw hunk")
    add("  total and NEEDS_REVIEW is work that was never missing.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Classify commits by the work needed to port them to a base branch."
    )
    parser.add_argument("--repo", default=".", help="path to the git repository")
    parser.add_argument("--base", required=True, help="branch that receives the work")
    parser.add_argument(
        "--from", dest="source", required=True, help="branch the work comes from"
    )
    parser.add_argument(
        "--range", dest="explicit", default="", help="commit list or a..b spans to override the range"
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    parser.add_argument(
        "--worktree-dir", default="", help="where to create the scratch worktree (default: a temp dir)"
    )
    parser.add_argument(
        "--keep-worktree", action="store_true", help="do not delete the scratch worktree on exit"
    )
    args = parser.parse_args(argv)

    repo = os.path.abspath(args.repo)
    base_sha = run_git(
        repo, ["rev-parse", "--verify", args.base + "^{commit}"], check=False
    ).strip()
    if not base_sha:
        print("error: cannot resolve base branch {!r}".format(args.base), file=sys.stderr)
        return 2

    try:
        commits = commit_range(repo, args.base, args.source, args.explicit)
    except RuntimeError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2
    if not commits:
        print("no commits to triage in {}..{}".format(args.base, args.source))
        return 0

    holder = args.worktree_dir or tempfile.mkdtemp(prefix="port-triage-")
    os.makedirs(holder, exist_ok=True)
    worktree = os.path.join(holder, "wt")
    created_holder = not args.worktree_dir

    results = []
    try:
        run_git(repo, ["worktree", "add", "--detach", "-q", worktree, base_sha])
        assert_isolated(repo, worktree)
        tree_symbols = collect_tree_symbols(worktree)
        attribute_cache = {}
        for sha in commits:
            results.append(triage_commit(repo, worktree, sha, base_sha, tree_symbols, attribute_cache))
    except RuntimeError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 2
    finally:
        run_git(worktree, ["cherry-pick", "--abort"], check=False)
        run_git(repo, ["worktree", "remove", "--force", worktree], check=False)
        run_git(repo, ["worktree", "prune"], check=False)
        if created_holder and not args.keep_worktree and os.path.isdir(holder):
            shutil.rmtree(holder, ignore_errors=True)

    if args.json:
        print(json.dumps(results, indent=2, sort_keys=True))
    else:
        print(render(results, args))
    return 0


if __name__ == "__main__":
    sys.exit(main())
