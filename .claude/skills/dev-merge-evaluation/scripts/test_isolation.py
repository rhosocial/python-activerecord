# .claude/skills/dev-merge-evaluation/scripts/test_isolation.py
"""Audit test-isolation declarations against how the suite is actually run.

Why this exists
---------------
A test file can declare that it must not run in parallel and still get no
protection at all, because the marker it used is not the one the runner honours.
That failure mode is invisible in a serial run and only appears intermittently
under CI, so it survives review and then breaks a build on one Python version.

The concrete case this was written for: three files declared
``pytestmark = pytest.mark.serial`` with a comment stating the requirement, while
the suite runs ``pytest -n auto --dist=loadgroup``. ``loadgroup`` schedules by
``xdist_group`` and ignores every other marker, and ``serial`` was not registered
in ``pyproject.toml`` either, so it was an unknown mark that never affected
ordering. The tests passed serially and failed under parallel execution.

What it checks
--------------
1. **Honoured markers.** For each isolation marker found in the test tree, is it
   one the configured distribution mode actually reads? Under ``--dist=loadgroup``
   that is ``xdist_group``; ``load`` / ``loadscope`` / ``loadfile`` / ``loadgroup``
   each read a different set, and ``--dist=each`` reads none of them.
2. **Registered markers.** An unregistered marker is an unknown mark; pytest only
   warns, and a warning nobody reads is not a control.
3. **CI and local parity.** The dist mode and worker count are read from the
   workflow, so a suite that is only ever exercised serially on a developer
   machine is reported as unverified rather than assumed healthy.
4. **Unmarked but risky files.** Files that spawn processes or write to shared
   temporary paths without declaring isolation. This is a heuristic and is
   reported as a review list, never as a verdict.

Usage
-----
    python test_isolation.py [--repo .] [--workflow .github/workflows/test.yml]
                             [--json]

Exit code is 0 when every isolation declaration is honoured, 1 when at least one
is inert, and 2 when the suite runs serially and the check therefore cannot
conclude anything.
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys

SKIP_DIRS = (
    "__pycache__",
    ".git",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    # Virtualenvs and build trees ship their own copies of pytest test suites;
    # walking them buries the real findings under hundreds of third-party files.
    "site-packages",
    "dist",
    "build",
)

# Markers people reach for when they want a test kept away from other tests, and
# the distribution modes that actually read each one. ``--dist=loadgroup``
# schedules by xdist_group and nothing else, which is why a ``serial`` marker is
# inert under it.
ISOLATION_MARKERS = {
    "xdist_group": {"loadgroup", "each"},
    "serial": set(),
    "group": set(),
}

# Markers whose presence changes collection rather than ordering. Listing them
# here keeps them out of the isolation report.
NON_ISOLATION_MARKERS = {
    "skip", "skipif", "xfail", "parametrize", "redis", "slow", "backend",
    "basic", "query", "relation", "field", "validation", "transaction",
    "mixin", "events", "interface", "cte", "benchmark", "asyncio",
}

# Coarse signals that a file depends on process or filesystem state.
RISK_PATTERNS = {
    "spawns processes": re.compile(
        r"\b(?:multiprocessing|subprocess|Process\(|Pool\(|WorkerPool|fork\()"
    ),
    "shared temp paths": re.compile(
        r"\b(?:TEMP_DIR|tempfile\.gettempdir\(\)|/tmp/|NamedTemporaryFile"
        r"|TemporaryDirectory)\b"
    ),
    "wall-clock waits": re.compile(r"\btime\.sleep\("),
    "event loops": re.compile(r"\basyncio\.(?:run|get_event_loop)\("),
}


def run_git(repo, args, check=False):
    proc = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError("git {} failed: {}".format(" ".join(args), proc.stderr.strip()[:160]))
    return proc.stdout


def workflow_pytest_invocations(repo, workflow_rel):
    """Distinct pytest command lines in a workflow, with their runner flags."""
    path = os.path.join(repo, workflow_rel)
    if not os.path.isfile(path):
        return None, []
    text = open(path, encoding="utf-8", errors="replace").read()
    invocations = []
    for match in re.finditer(r"python(?:3(?:\.\d+)?)?\s+-m\s+pytest\s+([^\n|]*)", text):
        args = match.group(1)
        dist = re.search(r"--dist[= ](\w+)", args)
        workers = re.search(r"(?:^|\s)-n\s+(\S+)", args)
        invocations.append(
            {
                "args": " ".join(args.split())[:120],
                "dist": dist.group(1) if dist else None,
                "workers": workers.group(1) if workers else None,
            }
        )
    unique = []
    seen = set()
    for item in invocations:
        key = (item["dist"], item["workers"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return path, unique


def registered_markers(repo):
    """Marker names declared in pyproject.toml, read as text to avoid needing a TOML parser."""
    path = os.path.join(repo, "pyproject.toml")
    if not os.path.isfile(path):
        return set()
    text = open(path, encoding="utf-8", errors="replace").read()
    match = re.search(r"^markers\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if not match:
        return set()
    return set(re.findall(r'"([A-Za-z_][A-Za-z0-9_]*)', match.group(1)))


def collect_module_markers(path):
    """Markers applied at module level, via ``pytestmark`` or a bare ``mark.`` assignment."""
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except (SyntaxError, ValueError):
        return set()
    found = set()

    def attribute_chain(node):
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))

    def visit(value):
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            for element in value.elts:
                visit(element)
            return
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            found.add(("name", value.value))
        elif isinstance(value, ast.Attribute):
            chain = attribute_chain(value)
            if chain.endswith("mark") or ".mark." in chain:
                found.add(("mark", chain.rsplit(".", 1)[-1]))
            if chain.endswith("xdist_group"):
                found.add(("mark", "xdist_group"))
        elif isinstance(value, ast.Call):
            visit(value.func)

    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target.id]
        if "pytestmark" in targets and node.value is not None:
            visit(node.value)
    return found


def risk_signals(path):
    body = open(path, encoding="utf-8", errors="replace").read()
    return sorted(label for label, pattern in RISK_PATTERNS.items() if pattern.search(body))


def test_files(repo, tests_root):
    """Test modules under *tests_root* only.

    Scanning the whole repository pulled in files that merely start with
    ``test_`` but are not part of the suite: documentation examples, and this
    script itself, whose name follows the same convention. The scan is therefore
    bounded, and the root it used is reported so a differently laid out repository
    can be pointed at the right place.
    """
    base = os.path.join(repo, tests_root)
    if not os.path.isdir(base):
        return
    for root, dirs, files in os.walk(base):
        dirs[:] = [
            d
            for d in dirs
            if d not in SKIP_DIRS and not d.startswith(".venv") and d != "venv"
        ]
        for filename in files:
            if not filename.startswith("test_") or not filename.endswith(".py"):
                continue
            yield os.path.join(root, filename)


def analyse(repo, workflow_rel, tests_root):
    workflow_path, invocations = workflow_pytest_invocations(repo, workflow_rel)
    dist_modes = sorted({item["dist"] for item in invocations if item["dist"]})
    serial_only = not invocations or all(item["dist"] is None for item in invocations)
    # marker -> the dist modes that read it, so ask the marker which modes honour it
    honoured = {
        marker
        for marker, modes in ISOLATION_MARKERS.items()
        if modes & set(dist_modes)
    }

    declared = registered_markers(repo)
    report = {
        "repo": repo,
        "workflow": workflow_rel,
        "workflow_found": workflow_path is not None,
        "pytest_invocations": invocations,
        "dist_modes": dist_modes,
        "serial_only": serial_only,
        "honoured_isolation_markers": sorted(honoured),
        "registered_markers_count": len(declared),
        "tests_root": tests_root,
        "files": [],
        "inert_declarations": [],
        "unregistered_markers": [],
        "unmarked_risky": [],
    }

    if not os.path.isdir(os.path.join(repo, tests_root)):
        report["tests_root_missing"] = True
    for path in sorted(test_files(repo, tests_root)):
        rel = os.path.relpath(path, repo)
        markers = collect_module_markers(path)
        names = {name for kind, name in markers}
        # Only the known isolation vocabulary counts as an isolation declaration.
        # pytest.mark.feature, .benchmark_relation and friends are category
        # labels; treating every marker as an isolation claim reported a dozen
        # ordinary files as inert.
        isolation = {
            name
            for kind, name in markers
            if kind == "mark" and name in ISOLATION_MARKERS
        }
        risks = risk_signals(path)
        entry = {
            "file": rel,
            "module_markers": sorted(names),
            "isolation_markers": sorted(isolation),
            "risk_signals": risks,
        }

        for name in sorted(isolation):
            if serial_only:
                entry.setdefault("notes", []).append(
                    "{}: suite runs serially, so no isolation marker has any effect; "
                    "this file's safety is unverified under parallelism".format(name)
                )
            elif name not in honoured:
                report["inert_declarations"].append(
                    {
                        "file": rel,
                        "marker": name,
                        "dist_modes": dist_modes,
                        "reason": "--dist={} schedules by {}, so {} changes nothing".format(
                            "/".join(dist_modes),
                            ", ".join(sorted(honoured)) or "no isolation marker",
                            name,
                        ),
                    }
                )
        for name in sorted(names):
            if name in NON_ISOLATION_MARKERS or name in isolation:
                continue
            if name not in declared and dist_modes:
                report["unregistered_markers"].append({"file": rel, "marker": name})

        if risks and not isolation:
            report["unmarked_risky"].append({"file": rel, "signals": risks})
        if isolation or risks:
            report["files"].append(entry)

    report["unmarked_risky"].sort(key=lambda item: (-len(item["signals"]), item["file"]))
    return report


def render(report):
    lines = []
    add = lines.append
    add("Test isolation audit")
    add("  repo:      {}".format(report["repo"]))
    add("  workflow:  {}".format(
        report["workflow"] if report["workflow_found"] else "(not found)"
    ))
    add("  tests:     {}{}".format(
        report["tests_root"],
        "  (missing)" if report.get("tests_root_missing") else "",
    ))
    add("")

    if not report["workflow_found"]:
        add("  No workflow found, so the runner configuration is unknown and nothing")
        add("  can be concluded. Point --workflow at the workflow that runs the tests.")
        add("")
        return "\n".join(lines)

    if report["serial_only"]:
        add("  The suite runs SERIALLY (no --dist). No isolation marker can take effect,")
        add("  so a file that depends on process or filesystem state is unprotected")
        add("  without any test failing to reveal it. Add a parallel dist mode to CI, or")
        add("  treat the result below as unverified rather than clean.")
        add("")
    else:
        add("  dist mode(s): {}   workers: {}".format(
            ", ".join("--dist=" + d for d in report["dist_modes"]),
            ", ".join(sorted({i["workers"] or "-" for i in report["pytest_invocations"]})),
        ))
        add("  honoured isolation markers: {}".format(
            ", ".join(report["honoured_isolation_markers"]) or "none"
        ))
        add("")

    if report["inert_declarations"]:
        add("  INERT ISOLATION DECLARATIONS ({} file(s))".format(
            len(report["inert_declarations"])
        ))
        add("  These files declare isolation the scheduler never reads. They pass")
        add("  serially and fail intermittently under parallel execution.")
        for item in report["inert_declarations"]:
            add("    {}  [{}]".format(item["file"], item["marker"]))
            add("        {}".format(item["reason"]))
        add("")

    if report["unregistered_markers"]:
        add("  UNREGISTERED MARKERS ({} occurrence(s))".format(len(report["unregistered_markers"])))
        add("  pytest only warns for these, so a misspelt or dropped registration is")
        add("  silent. Register in pyproject.toml under [tool.pytest.ini_options] markers.")
        for item in report["unregistered_markers"][:15]:
            add("    {}  [{}]".format(item["file"], item["marker"]))
        add("")

    if report["unmarked_risky"]:
        add("  STATE-DEPENDENT FILES WITH NO ISOLATION DECLARATION ({} file(s))".format(
            len(report["unmarked_risky"])
        ))
        add("  Heuristic, and a review list rather than a verdict: these files spawn")
        add("  processes or share temporary paths but declare nothing, so they rely on")
        add("  landing on an idle worker. Confirm each one is safe to interleave.")
        for item in report["unmarked_risky"][:20]:
            add("    {}  [{}]".format(item["file"], ", ".join(item["signals"])))
        if len(report["unmarked_risky"]) > 20:
            add("    ... {} more".format(len(report["unmarked_risky"]) - 20))
        add("")

    if report["files"]:
        add("  Files declaring isolation ({}):".format(
            sum(1 for f in report["files"] if f["isolation_markers"])
        ))
        for entry in report["files"]:
            if not entry["isolation_markers"]:
                continue
            add("    {}  [{}]".format(
                entry["file"], ", ".join(entry["isolation_markers"])
            ))
            for note in entry.get("notes", []):
                add("        {}".format(note))
        add("")

    add("  verdict: {}".format(
        "an isolation declaration is inert" if report["inert_declarations"]
        else "no inert isolation declaration found"
    ))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check that test isolation declarations match the runner configuration."
    )
    parser.add_argument("--repo", default=".", help="path to the repository")
    parser.add_argument(
        "--workflow",
        default=".github/workflows/test.yml",
        help="workflow whose pytest invocation defines the runner configuration",
    )
    parser.add_argument(
        "--tests-root",
        default="tests",
        help="subtree holding the test suite (default: tests)",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = parser.parse_args(argv)

    repo = os.path.abspath(args.repo)
    if not run_git(repo, ["rev-parse", "--git-dir"]).strip():
        print("error: {} is not a git repository".format(repo), file=sys.stderr)
        return 2

    report = analyse(repo, args.workflow, args.tests_root)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render(report))
    if not report["workflow_found"] or report.get("tests_root_missing"):
        return 2
    return 1 if report["inert_declarations"] else 0


if __name__ == "__main__":
    sys.exit(main())
