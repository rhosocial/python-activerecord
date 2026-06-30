#!/usr/bin/env bash
# ===========================================================================
# demo_chain.sh — dependency chain migration
#
# Scenarios:
#   - multiple migrations with dependencies executed in order
#   - dependency not satisfied — rejected
#   - rollback in reverse order
#
# Usage:
#   cd python-activerecord
#   DEMO_VENV_PYTHON=.venv3.14-ubuntu26.04/bin/python \
#     PYTHONPATH=src \
#     bash src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/demo_chain.sh
# ===========================================================================
set -euo pipefail

if [ -d "./src" ]; then
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
fi

MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations"
V001="${MODULE}.migrations.V001CreateUsers"
V002="${MODULE}.migrations.V002CreatePosts"
DB="./demo_chain.db"
STORE="./demo_chain_mig.json"
VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
PYTHON="$VENV_PYTHON -m rhosocial.activerecord.backend.impl.sqlite"

rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm"
echo "=== Dependency Chain Migration ==="
echo

# ── 1. list migrations with dependency column ────────────────────────────────
echo "[1] List all migrations (dependencies column):"
$PYTHON named-migration "${MODULE}.migrations" --list -o table
echo

# ── 2. inspect V002 dependencies ─────────────────────────────────────────────
echo "[2] V002CreatePosts dependencies (should declare v001_create_users):"
$PYTHON named-migration "$V002" --describe
echo

# ── 3. try V002 before V001 (should fail) ────────────────────────────────────
echo "[3] Run V002 before V001 (should fail):"
$PYTHON named-migration "$V002" --db-file "$DB" --direction up --record-store "$STORE" 2>&1 || true
echo

# ── 4. apply V001 ────────────────────────────────────────────────────────────
echo "[4] Apply V001 (create users table):"
$PYTHON named-migration "$V001" --db-file "$DB" --direction up --record-store "$STORE"
echo "    V001 applied successfully"
echo

# ── 5. apply V002 ────────────────────────────────────────────────────────────
echo "[5] Apply V002 (create posts table):"
$PYTHON named-migration "$V002" --db-file "$DB" --direction up --record-store "$STORE"
echo "    V002 applied successfully (dependency check passed)"
echo

# ── 6. verify both tables exist ──────────────────────────────────────────────
echo "[6] Verify both tables exist:"
$PYTHON query --db-file "$DB" \
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name" -o table
echo

# ── 7. rollback V002 (downstream first) ──────────────────────────────────────
echo "[7] Rollback V002 (downstream first):"
$PYTHON named-migration "$V002" --db-file "$DB" --direction down --record-store "$STORE"
echo "    V002 rolled back successfully"
echo

# ── 8. rollback V001 ─────────────────────────────────────────────────────────
echo "[8] Rollback V001:"
$PYTHON named-migration "$V001" --db-file "$DB" --direction down --record-store "$STORE"
echo "    V001 rolled back successfully"
echo

# ── 9. verify both tables are gone ───────────────────────────────────────────
echo "[9] Verify all tables dropped:"
COUNT=$($PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table'" -o json 2>/dev/null \
    | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['count'])")
echo "    Remaining tables: $COUNT (should be 0)"
echo

# ── 10. final record_store state ─────────────────────────────────────────────
echo "[10] Record store final state (all rolled back):"
cat "$STORE"
echo

rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm"
echo "=== Dependency Chain Migration Complete ==="