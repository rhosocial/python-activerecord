# src/rhosocial/activerecord/backend/impl/sqlite/examples/cli/named_query_demo.py
"""
Named Query CLI demo script.

Demonstrates how to invoke named queries (Named Query) via SQLite CLI.

Usage:
    cd src/rhosocial/activerecord/backend/impl/sqlite/examples
    PYTHONPATH=../../../../..:. python3 cli/named_query_demo.py

Or use CLI directly:
    python -m rhosocial.activerecord.backend.impl.sqlite named-query \
        rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.get_order \
        --db-file :memory: \
        --param order_id=1
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================
import subprocess
import sys
from pathlib import Path

# Setup: ensure examples modules can be discovered
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
examples_dir = project_root / "src" / "rhosocial" / "activerecord" / "backend" / "impl" / "sqlite" / "examples"
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(examples_dir))

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================
"""
This section demonstrates typical Named Query CLI usage.

### 1. List all named queries in a module

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries \
    --list
```

### 2. View single query signature and parameters

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.get_order \
    --describe
```

### 3. Dry-run: render SQL without executing

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.get_order \
    --db-file :memory: \
    --dry-run \
    --param order_id=1
```

### 4. Execute a named query

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.get_order \
    --db-file :memory: \
    --param order_id=1
```

### 5. Execute EXPLAIN plan

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-query \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.get_order \
    --db-file :memory: \
    --explain \
    --param order_id=1
```
"""


def run_cli_command(args):
    """Execute CLI command and print output."""
    cmd = [sys.executable, "-m", "rhosocial.activerecord.backend.impl.sqlite"] + args
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    return result.returncode


def main():
    print("Named Query CLI Demo")
    print("=" * 60)

    # 1. List all named queries in a module
    print("\n【1】List all named queries in module")
    run_cli_command([
        "named-query",
        "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries",
        "--list",
    ])

    # 2. View single query signature
    print("\n【2】View single query signature and parameters")
    run_cli_command([
        "named-query",
        "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.get_order",
        "--describe",
    ])

    # 3. Dry-run: render SQL only
    print("\n【3】Dry-run: render SQL, don't execute")
    run_cli_command([
        "named-query",
        "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.get_order",
        "--db-file", ":memory:",
        "--dry-run",
        "--param", "order_id=1",
    ])

    # 4. Execute named query
    print("\n【4】Execute named query")
    run_cli_command([
        "named-query",
        "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.get_order",
        "--db-file", ":memory:",
        "--param", "order_id=1",
    ])

    # 5. View another query
    print("\n【5】View check_inventory query")
    run_cli_command([
        "named-query",
        "rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries.check_inventory",
        "--describe",
    ])

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
# No cleanup needed - CLI commands are self-contained