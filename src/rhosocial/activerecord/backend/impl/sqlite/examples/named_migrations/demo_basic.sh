#!/usr/bin/env bash
# ===========================================================================
# demo_basic.sh — single migration basic operations
#
# Scenarios:
#   - apply / rollback a single migration
#   - dry-run preview
#   - duplicate execution protection
#
# Usage:
#   cd python-activerecord
#   DEMO_VENV_PYTHON=.venv3.14-ubuntu26.04/bin/python \
#     PYTHONPATH=src \
#     bash src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/demo_basic.sh
# ===========================================================================
set -euo pipefail

if [ -d "./src" ]; then
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
fi

MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations"
FQN="${MODULE}.migrations.V001CreateUsers"
DB="./demo_basic.db"
STORE="./demo_basic_mig.json"
VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
PYTHON="$VENV_PYTHON -m rhosocial.activerecord.backend.impl.sqlite"

# ── cleanup from previous runs ───────────────────────────────────────────────
rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm"
echo "=== Single Migration Basic Operations ==="
echo

# ── 1. list all migrations in the module ─────────────────────────────────────
echo "[1] List all migrations in the module:"
$PYTHON named-migration "${MODULE}.migrations" --list -o table
echo

# ── 2. describe a migration ─────────────────────────────────────────────────
echo "[2] Describe V001CreateUsers (--describe):"
$PYTHON named-migration "$FQN" --describe
echo

# ── 3. dry-run (preview SQL, no actual changes) ──────────────────────────────
echo "[3] Dry-run preview (should show generated SQL):"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction up --dry-run
echo
echo "    Verify: users table should NOT exist"
$PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'" -o table
echo

# ── 4. apply UP ──────────────────────────────────────────────────────────────
echo "[4] Apply UP (create users table):"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction up --record-store "$STORE"
echo
echo "    Verify: users table should exist"
$PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'" -o table
echo

# ── 5. inspect record_store ──────────────────────────────────────────────────
echo "[5] Record store contents:"
cat "$STORE"
echo

# ── 6. duplicate UP (should be rejected) ─────────────────────────────────────
echo
echo "[6] Duplicate UP (should be rejected):"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction up --record-store "$STORE" 2>&1 || true
echo

# ── 7. rollback ──────────────────────────────────────────────────────────────
echo "[7] Apply DOWN (drop users table):"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction down --record-store "$STORE"
echo
echo "    Verify: users table should be gone"
$PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'" -o table
echo

# ── 8. final record_store state ──────────────────────────────────────────────
echo "[8] Record store after rollback:"
cat "$STORE"
echo

# ── cleanup ──────────────────────────────────────────────────────────────────
rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm"
echo "=== Single Migration Basic Operations Complete ==="