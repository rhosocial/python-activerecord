# src/rhosocial/activerecord/backend/impl/sqlite/examples/cli/named_connection_demo.py
"""
Named Connection CLI demo script.

Demonstrates how to invoke named connections (Named Connection) via SQLite CLI.

Usage:
    cd src/rhosocial/activerecord/backend/impl/sqlite/examples
    PYTHONPATH=../../../../..:. python3 cli/named_connection_demo.py

Or use CLI directly:
    python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
        --named-connection rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory \
        --show
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
This section demonstrates typical Named Connection CLI usage.

### 1. List all named connections in a module

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
    --named-connection rhosocial.activerecord.backend.impl.sqlite.examples.named_connections \
    --list
```

### 2. View single connection configuration details

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
    --named-connection rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db \
    --show
```

### 3. Dry-run: resolve connection configuration

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
    --named-connection rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db \
    --describe
```

### 4. Resolve connection with parameters

```bash
python -m rhosocial.activerecord.backend.impl.sqlite named-connection \
    --named-connection rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.file.file_db \
    --describe \
    --conn-param database=custom.db
```

### 5. Use named connection in query

```bash
python -m rhosocial.activerecord.backend.impl.sqlite query \
    --named-connection rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db \
    "SELECT 1 as test"
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
    print("Named Connection CLI Demo")
    print("=" * 60)

    # 1. List all named connections in a module
    print("\n【1】List all named connections in module")
    run_cli_command([
        "named-connection",
        "--named-connection", "rhosocial.activerecord.backend.impl.sqlite.examples.named_connections",
        "--list",
    ])

    # 2. View single connection configuration details
    print("\n【2】View single connection configuration details")
    run_cli_command([
        "named-connection",
        "--named-connection", "rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db",
        "--show",
    ])

    # 3. Dry-run: resolve connection configuration
    print("\n【3】Dry-run: resolve connection configuration")
    run_cli_command([
        "named-connection",
        "--named-connection", "rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db",
        "--describe",
    ])

    # 4. Resolve connection with parameters
    print("\n【4】Resolve connection with parameters")
    run_cli_command([
        "named-connection",
        "--named-connection", "rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.file.file_db",
        "--describe",
        "--conn-param", "database=custom.db",
    ])

    # 5. Use named connection in query
    print("\n【5】Use named connection in query")
    run_cli_command([
        "query",
        "--named-connection", "rhosocial.activerecord.backend.impl.sqlite.examples.named_connections.memory.memory_db",
        "SELECT 1 as test",
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