#!/usr/bin/env bash
# ===========================================================================
# demo_all.sh — batch migration (--all)
#
# Scenarios:
#   - --all runs all pending migrations in dependency order
#   - --all --dry-run preview without changes
#   - --all --direction down rolls back everything
#
# Usage:
#   cd python-activerecord
#   DEMO_VENV_PYTHON=.venv3.14-ubuntu26.04/bin/python \
#     PYTHONPATH=src \
#     bash src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/demo_all.sh
# ===========================================================================
set -euo pipefail

if [ -d "./src" ]; then
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
fi

MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations"
DB="./demo_all.db"
STORE="./demo_all_mig.json"
VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
PYTHON="$VENV_PYTHON -m rhosocial.activerecord.backend.impl.sqlite"

rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm"
echo "=== Batch Migration (--all) ==="
echo

# ── 1. --all without --record-store (should error) ──────────────────────────
echo "[1] --all without --record-store (should error):"
$PYTHON named-migration "${MODULE}.migrations" --all --db-file "$DB" 2>&1 || true
echo

# ── 2. --all --dry-run (preview all pending, shows SQL) ─────────────────────
echo "[2] --all --dry-run preview all pending migrations:"
$PYTHON named-migration "${MODULE}.migrations" --all --db-file "$DB" --dry-run --record-store "$STORE"
echo
echo "    Verify: no tables were created"
$PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table'" -o table
echo

# ── 3. --all apply all pending UP ───────────────────────────────────────────
echo "[3] --all apply all pending migrations:"
$PYTHON named-migration "${MODULE}.migrations" --all --db-file "$DB" --record-store "$STORE"
echo
echo "    Verify: users and posts tables both exist"
$PYTHON query --db-file "$DB" \
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name" -o table
echo

# ── 4. record_store contents ─────────────────────────────────────────────────
echo "[4] Record store contents (two UP records):"
cat "$STORE"
echo

# ── 5. re-run --all (duplicate protection) ───────────────────────────────────
echo "[5] Re-run --all (all applied, should error):"
$PYTHON named-migration "${MODULE}.migrations" --all --db-file "$DB" --record-store "$STORE" 2>&1 || true
echo

# ── 6. --all --single-transaction ────────────────────────────────────────────
echo "[6] --all --single-transaction (apply in a single DB transaction):"
$PYTHON named-migration "${MODULE}.migrations" --all --db-file "$DB" \
    --direction down --record-store "$STORE" --single-transaction
echo
echo "    Verify: all tables dropped in one transaction"
$PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table'" -o table
echo

# ── 7. re-apply UP in single transaction ─────────────────────────────────────
echo "[7] --all --single-transaction (re-apply UP):"
$PYTHON named-migration "${MODULE}.migrations" --all --db-file "$DB" \
    --direction up --record-store "$STORE" --single-transaction
echo

# ── 8. --all --direction down rollback everything ───────────────────────────
echo "[8] --all --direction down rollback everything:"
$PYTHON named-migration "${MODULE}.migrations" --all --db-file "$DB" \
    --direction down --record-store "$STORE"
echo
echo "    Verify: all tables dropped"
$PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table'" -o table
echo

# ── 9. final record_store state ─────────────────────────────────────────────
echo "[9] Record store final state:"
cat "$STORE"
echo

rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm"
echo "=== Batch Migration (--all) Complete ==="