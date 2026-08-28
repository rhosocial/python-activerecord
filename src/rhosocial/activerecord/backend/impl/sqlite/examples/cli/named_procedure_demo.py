# src/rhosocial/activerecord/backend/impl/sqlite/examples/cli/named_procedure_demo.py
"""
Named Procedure CLI demo script.

Demonstrates how to invoke named procedures (Named Procedure) via SQLite CLI.

Usage:
    cd src/rhosocial/activerecord/backend/impl/sqlite/examples
    python3 cli/named_procedure_demo.py

Or use CLI directly:
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
        rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure \
        --db-file :memory: \
        --param order_id=1 \
        --param user_id=100 \
        --param amount=99.99
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
This section demonstrates typical Named Procedure CLI usage.

### 1. List all named procedures in a module

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures \
    --list
```

### 2. View single procedure signature and parameters

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure \
    --describe
```

### 3. Dry-run: render each step's SQL without executing

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure \
    --db-file :memory: \
    --dry-run \
    --param order_id=1 \
    --param user_id=100 \
    --param amount=99.99
```

### 4. Execute named procedure (AUTO transaction mode)

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure \
    --db-file :memory: \
    --param order_id=1 \
    --param user_id=100 \
    --param amount=99.99 \
    --transaction auto
```

### 5. Execute named procedure (STEP transaction mode)

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
    rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure \
    --db-file :memory: \
    --param order_id=1 \
    --param user_id=100 \
    --param amount=99.99 \
    --transaction step
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


def create_demo_db() -> str:
    """Create a temp SQLite db pre-populated with the workflow tables.

    The named procedure references tables created by the
    order_expressions example module. Those tables only exist in the
    module's own in-memory backend at import time, so this helper builds
    them in a file db the procedure CLI can actually connect to.

    Returns:
        Path to the temp database file.
    """
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tf:
        demo_db = tf.name
    os.unlink(demo_db)

    setup_sql = (
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, status TEXT, user_id INTEGER);"
        "INSERT INTO orders (id, status, user_id) VALUES (1, 'pending', 100);"
        "CREATE TABLE inventory (id INTEGER PRIMARY KEY, order_id INTEGER, available INTEGER);"
        "INSERT INTO inventory (id, order_id, available) VALUES (1, 1, 10);"
        "CREATE TABLE notifications (id INTEGER PRIMARY KEY, user_id INTEGER, type TEXT);"
        "CREATE TABLE payments (id INTEGER PRIMARY KEY, order_id INTEGER, status TEXT, transaction_id TEXT);"
        "CREATE TABLE order_records (id INTEGER PRIMARY KEY, order_id INTEGER, created_at TEXT);"
    )
    run_cli_command(
        [
            "query",
            "--db-file",
            demo_db,
            "--executescript",
            setup_sql,
        ]
    )
    return demo_db


def main():
    print("Named Procedure CLI Demo")
    print("=" * 60)

    # 1. List all named procedures in a module
    print("\n【1】List all named procedures in module")
    run_cli_command(
        [
            "named-procedure",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures",
            "--list",
        ]
    )

    # 2. View single procedure signature
    print("\n【2】View single procedure signature and parameters")
    run_cli_command(
        [
            "named-procedure",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure",
            "--describe",
        ]
    )

    # 3. Dry-run
    print("\n【3】Dry-run: render each step's SQL, don't execute")
    run_cli_command(
        [
            "named-procedure",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure",
            "--db-file",
            ":memory:",
            "--dry-run",
            "--param",
            "order_id=1",
            "--param",
            "user_id=100",
            "--param",
            "amount=99.99",
        ]
    )

    # 4. Execute named procedure (AUTO)
    print("\n【4】Execute named procedure (AUTO transaction mode)")
    demo_db = create_demo_db()
    run_cli_command(
        [
            "named-procedure",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure",
            "--db-file",
            demo_db,
            "--param",
            "order_id=1",
            "--param",
            "user_id=100",
            "--param",
            "amount=99.99",
            "--transaction",
            "auto",
        ]
    )

    # 5. Execute named procedure (STEP)
    print("\n【5】Execute named procedure (STEP transaction mode)")
    run_cli_command(
        [
            "named-procedure",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure",
            "--db-file",
            demo_db,
            "--param",
            "order_id=1",
            "--param",
            "user_id=100",
            "--param",
            "amount=99.99",
            "--transaction",
            "step",
        ]
    )
    import os

    os.unlink(demo_db)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
# No cleanup needed - CLI commands are self-contained
