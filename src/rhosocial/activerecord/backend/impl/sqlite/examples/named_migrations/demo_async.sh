#!/usr/bin/env bash
# ===========================================================================
# demo_async.sh — async migration execution (--async)
#
# Scenarios:
#   - apply UP with --async
#   - dry-run with --async (preview SQL)
#   - rollback DOWN with --async
#
# Requires: aiosqlite
#
# Usage:
#   cd python-activerecord
#   DEMO_VENV_PYTHON=.venv3.14-ubuntu26.04/bin/python \
#     PYTHONPATH=src \
#     bash src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/demo_async.sh
# ===========================================================================
set -euo pipefail

if [ -d "./src" ]; then
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
fi

MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations"
FQN="${MODULE}.migrations.V001CreateUsers"
DB="./demo_async.db"
STORE="./demo_async_mig.json"
VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
PYTHON="$VENV_PYTHON -m rhosocial.activerecord.backend.impl.sqlite"

rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm"
echo "=== Async Migration Execution (--async) ==="
echo

# Check async dependencies
echo "Checking..."
$VENV_PYTHON --version 2>&1 || true
echo

# ── 1. async dry-run ───────────────────────────────────────────────────────
echo
echo "[1] Async dry-run (should show generated SQL, no changes):"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction up --dry-run --async
echo
echo "    Verify: users table should NOT exist:"
$PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'" -o table
echo

# ── 2. async apply UP ──────────────────────────────────────────────────────
echo "[2] Async apply UP:"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction up --async --record-store "$STORE"
echo
echo "    Verify: users table should exist:"
$PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'" -o table
echo

# ── 3. async apply DOWN ────────────────────────────────────────────────────
echo "[3] Async rollback DOWN:"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction down --async --record-store "$STORE"
echo
echo "    Verify: users table should be gone:"
$PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'" -o table

rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm"
echo "=== Async Migration Demo Complete ==="