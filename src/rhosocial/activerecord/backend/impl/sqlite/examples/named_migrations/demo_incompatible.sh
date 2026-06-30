#!/usr/bin/env bash
# ===========================================================================
# demo_incompatible.sh — dialect incompatibility detected via dry-run
#
# Scenarios:
#   - dry-run a migration that uses an expression SQLite does not support
#     (partitioned table) → expects MigrationDialectError
#   - show that compatible migrations still work normally
#
# Usage:
#   cd python-activerecord
#   DEMO_VENV_PYTHON=.venv3.14-ubuntu26.04/bin/python \
#     PYTHONPATH=src \
#     bash src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/demo_incompatible.sh
# ===========================================================================
set -euo pipefail

if [ -d "./src" ]; then
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
fi

MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations"
FQN="${MODULE}.migrations.V001CreateUsers"
DB="./demo_incompatible.db"
STORE="./demo_incompatible_mig.json"
VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
PYTHON="$VENV_PYTHON -m rhosocial.activerecord.backend.impl.sqlite"

rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm"
echo "=== Dialect Incompatibility Detection ==="
echo

# ── 1. compatible migration — should work ──────────────────────────────────
echo "[1] Compatible migration dry-run (should succeed):"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction up --dry-run
echo

# ── 2. incompatible expression via inline test ─────────────────────────────
echo "[2] Test incompatible expression (table with PARTITION BY):"
echo "    (This demonstrates how dry-run catches unsupported features.)"
echo
cat << 'PYEOF' > /tmp/demo_incompatible_expr.py
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.migration import (
    MigrationRunner, MigrationDirection, MigrationDialectError,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression, ColumnDefinition, ColumnConstraint, ColumnConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_partition import (
    PartitionClause, PartitionStrategy,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.types import SQLiteIntegerType
from rhosocial.activerecord.backend.expression.core import Column as ColExpr

dialect = SQLiteBackend(database=":memory:").dialect
col_def = ColumnDefinition("id", SQLiteIntegerType(),
    constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)])
col_expr = ColExpr(dialect, "id")
expr = CreateTableExpression(
    dialect, table="partitioned",
    columns=[col_def],
    partition=PartitionClause(dialect, method=PartitionStrategy.RANGE, keys=[col_expr]),
)
try:
    sql, params = expr.to_sql()
    print("SQL:", sql)
except Exception as e:
    print(type(e).__name__ + ":", e)
PYEOF
$VENV_PYTHON /tmp/demo_incompatible_expr.py
echo

# ── 3. compatible — normal apply works ─────────────────────────────────────
echo "[3] Compatible migration apply UP (succeeds):"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction up --record-store "$STORE"
echo
echo "    Verify: users table exists:"
$PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'" -o table
echo

# ── cleanup ─────────────────────────────────────────────────────────────────
rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm" /tmp/demo_incompatible_expr.py
echo "=== Dialect Incompatibility Demo Complete ==="