# src/rhosocial/activerecord/backend/impl/sqlite/examples/cli/named_query_demo.py
"""
Named Query CLI demo script.

Demonstrates how to invoke named queries (Named Query) via SQLite CLI.

Usage:
    cd src/rhosocial/activerecord/backend/impl/sqlite/examples
    python3 cli/named_query_demo.py

Or use CLI directly:
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions.get_order \
        --db-file :memory: \
        --param order_id=1
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import subprocess
import sys
from pathlib import Path

# Setup: ensure the package is importable from source (if not installed)
project_root = Path(__file__).resolve().parents[8]
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
"""
This section demonstrates typical Named Query CLI usage.

### 1. List all named queries in a module

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions \
    --list
```

### 2. View single query signature and parameters

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions.get_order \
    --describe
```

### 3. Dry-run: render SQL without executing

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions.get_order \
    --db-file :memory: \
    --dry-run \
    --param order_id=1
```

### 4. Execute a named query

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions.get_order \
    --db-file :memory: \
    --param order_id=1
```

### 5. Execute EXPLAIN plan

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions.get_order \
    --db-file :memory: \
    --explain \
    --param order_id=1
```
"""


def run_cli_command(args):
    """Execute CLI command and print output.

    The subprocess runs with cwd=project_root so the examples directory
    (which contains a 'types' module) is not on the child's sys.path and
    cannot shadow the Python standard library 'types' module.
    """
    cmd = [sys.executable, "-m", "rhosocial.activerecord.backend.impl.sqlite"] + args
    print(f"\n{'=' * 60}")
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    return result.returncode


def main():
    print("Named Query CLI Demo")
    print("=" * 60)

    # 1. List all named queries in a module
    print("\n【1】List all named queries in module")
    run_cli_command(
        [
            "named-expression",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions",
            "--list",
        ]
    )

    # 2. View single query signature
    print("\n【2】View single query signature and parameters")
    run_cli_command(
        [
            "named-expression",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions.get_order",
            "--describe",
        ]
    )

    # 3. Dry-run: render SQL only
    print("\n【3】Dry-run: render SQL, don't execute")
    run_cli_command(
        [
            "named-expression",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions.get_order",
            "--db-file",
            ":memory:",
            "--dry-run",
            "--param",
            "order_id=1",
        ]
    )

    # 4. Execute named query
    # The named expression only builds SQL; the tables must exist in the
    # target database. Pre-populate a temp file db via the query subcommand.
    print("\n【4】Execute named query")
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tf:
        demo_db = tf.name
    os.unlink(demo_db)
    run_cli_command(
        [
            "query",
            "--db-file",
            demo_db,
            "--executescript",
            "CREATE TABLE orders (id INTEGER PRIMARY KEY, status TEXT, user_id INTEGER);"
            "INSERT INTO orders (id, status, user_id) VALUES (1, 'pending', 100);"
            "CREATE TABLE inventory (id INTEGER PRIMARY KEY, order_id INTEGER, available INTEGER);"
            "INSERT INTO inventory (id, order_id, available) VALUES (1, 1, 10);",
        ]
    )
    run_cli_command(
        [
            "named-expression",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions.get_order",
            "--db-file",
            demo_db,
            "--param",
            "order_id=1",
        ]
    )
    os.unlink(demo_db)

    # 5. View another query
    print("\n【5】View check_inventory query")
    run_cli_command(
        [
            "named-expression",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions.check_inventory",
            "--describe",
        ]
    )

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
# No cleanup needed - CLI commands are self-contained
