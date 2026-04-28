# src/rhosocial/activerecord/backend/impl/sqlite/examples/cli/named_procedure_demo.py
"""
Named Procedure CLI demo script.

Demonstrates how to invoke named procedures (Named Procedure) via SQLite CLI.

Usage:
    cd src/rhosocial/activerecord/backend/impl/sqlite/examples
    PYTHONPATH=../../../../..:. python3 cli/named_procedure_demo.py

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

# Setup: ensure examples modules can be discovered
project_root = Path(__file__).parent.parent.parent.parent.parent.parent
examples_dir = project_root / "src" / "rhosocial" / "activerecord" / "backend" / "impl" / "sqlite" / "examples"
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(examples_dir))

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
    print("Named Procedure CLI Demo")
    print("=" * 60)

    # 1. List all named procedures in a module
    print("\n【1】List all named procedures in module")
    run_cli_command([
        "named-procedure",
        "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures",
        "--list",
    ])

    # 2. View single procedure signature
    print("\n【2】View single procedure signature and parameters")
    run_cli_command([
        "named-procedure",
        "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure",
        "--describe",
    ])

    # 3. Dry-run
    print("\n【3】Dry-run: render each step's SQL, don't execute")
    run_cli_command([
        "named-procedure",
        "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure",
        "--db-file", ":memory:",
        "--dry-run",
        "--param", "order_id=1",
        "--param", "user_id=100",
        "--param", "amount=99.99",
    ])

    # 4. Execute named procedure (AUTO)
    print("\n【4】Execute named procedure (AUTO transaction mode)")
    run_cli_command([
        "named-procedure",
        "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure",
        "--db-file", ":memory:",
        "--param", "order_id=1",
        "--param", "user_id=100",
        "--param", "amount=99.99",
        "--transaction", "auto",
    ])

    # 5. Execute named procedure (STEP)
    print("\n【5】Execute named procedure (STEP transaction mode)")
    run_cli_command([
        "named-procedure",
        "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow.OrderProcessingProcedure",
        "--db-file", ":memory:",
        "--param", "order_id=1",
        "--param", "user_id=100",
        "--param", "amount=99.99",
        "--transaction", "step",
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