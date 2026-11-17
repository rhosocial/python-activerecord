#!/usr/bin/env python3
"""Probe the SQLite engine that the current Python process actually loaded.

Cross-platform (Windows / Linux / macOS), stdlib only. Use it before trusting a
test run against a self-compiled SQLite: it prints the engine version, checks
the compile options that a full-featured build should carry, and exercises the
virtual tables and functions reachable through Python's sqlite3 module.

    python3 scripts/verify_sqlite_features.py

The exit status is 0 only when every wanted compile option is present and every
reachable probe succeeds. Some virtual tables (dbpage, stmtvtab, bytecode) are
compiled in but gated behind sqlite3_db_config() in the C API, which Python's
sqlite3 does not expose; they are reported as notes, not failures.
"""
import os
import sys

# On Windows the private directory must be on sys.path *before* sqlite3 is
# imported; PYTHONPATH alone is not enough. Do it here so this probe can be run
# directly with the same SQLITE_SWAP_DIR used by run_with_sqlite_swap.py.
if sys.platform == "win32" and os.environ.get("SQLITE_SWAP_DIR"):
    sys.path.insert(0, os.environ["SQLITE_SWAP_DIR"])

import sqlite3

WANTED_OPTIONS = (
    "ENABLE_FTS3",
    "ENABLE_FTS4",
    "ENABLE_FTS5",
    "ENABLE_RTREE",
    "ENABLE_GEOPOLY",
    "ENABLE_DBSTAT_VTAB",
    "ENABLE_DBPAGE_VTAB",
    "ENABLE_STMTVTAB",
    "ENABLE_BYTECODE_VTAB",
    "ENABLE_MATH_FUNCTIONS",
    "ENABLE_PERCENTILE",
    "ENABLE_COLUMN_METADATA",
    "ENABLE_UPDATE_DELETE_LIMIT",
    "ENABLE_LOAD_EXTENSION",
    "ENABLE_NORMALIZE",
    "ENABLE_PREUPDATE_HOOK",
    "ENABLE_SESSION",
    "ENABLE_EXPLAIN_COMMENTS",
    "ENABLE_STMT_SCANSTATUS",
)

VTABLE_PROBES = {
    "fts5": "create virtual table temp.p_fts5 using fts5(a)",
    "rtree": "create virtual table temp.p_rtree using rtree(id,x0,x1)",
    "geopoly": "create virtual table temp.p_geo using geopoly(a)",
    "dbstat": "create virtual table temp.p_dbstat using dbstat",
}

FUNCTION_PROBES = {
    "math sin": "select sin(1)",
    "json_extract": "select json_extract('{\"a\":1}','$.a')",
    "geopoly_area": "select geopoly_area('[[0,0],[1,0],[0.5,1],[0,0]]')",
}

DB_CONFIG_ONLY = ("dbpage", "stmtvtab", "bytecode")


def main() -> int:
    conn = sqlite3.connect(":memory:")
    options = {row[0] for row in conn.execute("pragma compile_options")}

    print("python:       ", sys.version.split()[0])
    print("module:       ", sqlite3.__file__ if hasattr(sqlite3, "__file__") else "-")
    print("engine:       ", sqlite3.sqlite_version)
    print("engine (SQL): ", conn.execute("select sqlite_version()").fetchone()[0])

    missing = [name for name in WANTED_OPTIONS if name not in options]
    print("\ncompile options: %d wanted, %d missing" % (len(WANTED_OPTIONS), len(missing)))
    for name in missing:
        print("  MISSING", name)

    print("\nreachable virtual tables:")
    failed = 0
    for name, sql in VTABLE_PROBES.items():
        try:
            conn.execute(sql)
            print("  OK     ", name)
        except Exception as exc:
            failed += 1
            print("  FAIL   ", name, type(exc).__name__, exc)

    print("\nfunctions:")
    for name, sql in FUNCTION_PROBES.items():
        try:
            value = conn.execute(sql).fetchone()[0]
            print("  OK     ", name, "->", value)
        except Exception as exc:
            failed += 1
            print("  FAIL   ", name, type(exc).__name__, exc)

    print("\nnote: %s are compile-enabled but need sqlite3_db_config() in C," % ", ".join(DB_CONFIG_ONLY))
    print("      which Python's sqlite3 does not expose; not probed here.")

    ok = not missing and not failed
    print("\nRESULT:", "PASS" if ok else "INCOMPLETE")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
