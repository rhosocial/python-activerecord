# src/rhosocial/activerecord/backend/impl/sqlite/examples/cli/named_connection_demo.py
"""
Named Connection CLI demo script.

Demonstrates how to invoke named connections (Named Connection) via SQLite CLI.

Usage:
    cd src/rhosocial/activerecord/backend/impl/sqlite/examples
    python3 cli/named_connection_demo.py

Or use CLI directly:
    python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
        --show rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db
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
This section demonstrates typical Named Connection CLI usage.

### 1. List all named connections in a module

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
    --list rhosocial.activerecord.backend.impl.sqlite.examples.named_connections
```

### 2. View single connection configuration details

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
    --show rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db
```

### 3. Dry-run: resolve connection configuration

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
    --describe rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db
```

### 4. Resolve connection with parameters

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
    --describe rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.file.file_db \
    --param delete_on_close=False
```

### 5. Use named connection in query

```bash
python -m rhosocial.activerecord.backend.impl.sqlite query \
    --named-connection rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db \
    "SELECT 1 as test"
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
    print("Named Connection CLI Demo")
    print("=" * 60)

    # 1. List all named connections in a module
    print("\n【1】List all named connections in module")
    run_cli_command(
        [
            "named-connection",
            "--list",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_connections",
        ]
    )

    # 2. View single connection configuration details
    print("\n【2】View single connection configuration details")
    run_cli_command(
        [
            "named-connection",
            "--show",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db",
        ]
    )

    # 3. Dry-run: resolve connection configuration
    print("\n【3】Dry-run: resolve connection configuration")
    run_cli_command(
        [
            "named-connection",
            "--describe",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db",
        ]
    )

    # 4. Resolve connection with parameters
    print("\n【4】Resolve connection with parameters")
    run_cli_command(
        [
            "named-connection",
            "--describe",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.file.file_db",
            "--param",
            "delete_on_close=False",
        ]
    )

    # 5. Use named connection in query
    print("\n【5】Use named connection in query")
    run_cli_command(
        [
            "query",
            "--named-connection",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db",
            "SELECT 1 as test",
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
