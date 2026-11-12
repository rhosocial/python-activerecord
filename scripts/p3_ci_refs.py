# scripts/p3_ci_refs.py
"""Point every workflow's cross-repo install ref at the declaration-surface branch.

The family is tested by installing the other repositories from a ref: while a
feature spans core, testsuite and the backends, those refs have to name the
matching branch or the run tests a mixture of two revisions.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path("D:/Projects/rhosocial")
BRANCH = "feature/declaration-surface"

REPOS = [
    "python-activerecord",
    "python-activerecord-testsuite",
    "python-activerecord-mysql",
    "python-activerecord-postgres",
    "python-activerecord-mariadb",
    "python-activerecord-sqlserver",
    "python-activerecord-oracle",
    "python-activerecord-firebird",
    "python-activerecord-clickhouse",
    "python-activerecord-bigquery",
    "python-activerecord-snowflake",
]

# Only refs that name one of the family's repositories are rewritten.
PATTERN = re.compile(
    r"(python-activerecord(?:-testsuite)?\.git@)([^\s\"#]+)"
)


def main() -> None:
    for name in REPOS:
        repo = ROOT / name
        workflows = repo / ".github" / "workflows"
        if not workflows.exists():
            print(f"{name}: no workflows")
            continue
        changed = 0
        for path in sorted(workflows.glob("*.yml")):
            raw = path.read_bytes().decode("utf-8")
            text, count = PATTERN.subn(lambda m: m.group(1) + BRANCH, raw)
            if count:
                path.write_bytes(text.encode("utf-8"))
                changed += count
        print(f"{name}: {changed} refs -> {BRANCH}")


if __name__ == "__main__":
    main()
