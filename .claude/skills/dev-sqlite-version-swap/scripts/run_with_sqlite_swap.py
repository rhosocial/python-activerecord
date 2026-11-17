#!/usr/bin/env python3
"""Run pytest with a private SQLite DLL/DLLs directory winning the search order.

On Windows, PYTHONPATH is searched *after* the interpreter's DLLs directory, so
setting PYTHONPATH alone will not swap the engine. This launcher puts the
private directory at sys.path[0] before pytest (or anything else) imports
sqlite3, so the copied _sqlite3.pyd loads the custom sqlite3.dll next to it.

    set SQLITE_SWAP_DIR=<prefix>\bin
    python run_with_sqlite_swap.py tests/... -q

On Linux/macOS the normal mechanism is LD_LIBRARY_PATH / DYLD_LIBRARY_PATH;
this launcher is harmless there and can be used if you prefer one command.
"""
import os
import sys

private_dir = os.environ.get("SQLITE_SWAP_DIR")
if not private_dir or not os.path.isdir(private_dir):
    raise SystemExit("set SQLITE_SWAP_DIR to the directory containing sqlite3.dll / _sqlite3.pyd")

sys.path.insert(0, private_dir)

# Import sqlite3 early so a failure reports the swap, not a test error.
import sqlite3

print("sqlite swap:", private_dir, "->", sqlite3.sqlite_version, file=sys.stderr)

import pytest

raise SystemExit(pytest.main(sys.argv[1:]))
