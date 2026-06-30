#!/usr/bin/env bash
# ===========================================================================
# demo_params.sh — parameterized migration (--param)
#
# Scenarios:
#   - describe a parameterized migration
#   - apply with custom --param table_name=my_config
#   - verify the custom-named table was created
#   - rollback with matching --param
#
# Usage:
#   cd python-activerecord
#   DEMO_VENV_PYTHON=.venv3.14-ubuntu26.04/bin/python \
#     PYTHONPATH=src \
#     bash src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/demo_params.sh
# ===========================================================================
set -euo pipefail

if [ -d "./src" ]; then
    export PYTHONPATH="${PYTHONPATH:-}:$(pwd)/src"
fi

MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations"
FQN="${MODULE}.migrations.V003CreateCustomTable"
DB="./demo_params.db"
STORE="./demo_params_mig.json"
VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
PYTHON="$VENV_PYTHON -m rhosocial.activerecord.backend.impl.sqlite"

rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm"
echo "=== Parameterized Migration (--param) ==="
echo

# ── 1. describe the parameterized migration ─────────────────────────────────
echo "[1] Describe V003CreateCustomTable (shows table_name parameter):"
$PYTHON named-migration "$FQN" --describe
echo

# ── 2. dry-run with custom param (preview) ──────────────────────────────────
echo "[2] Dry-run with --param table_name=my_config:"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction up \
    --param table_name=my_config --dry-run
echo

# ── 3. apply UP with custom param ───────────────────────────────────────────
echo "[3] Apply UP with --param table_name=my_config:"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction up \
    --param table_name=my_config --record-store "$STORE"
echo
echo "    Verify: 'my_config' table should exist (not 'custom_table'):"
$PYTHON query --db-file "$DB" \
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name" -o table
echo

# ── 4. apply DOWN with matching param ───────────────────────────────────────
echo "[4] Rollback with --param table_name=my_config:"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction down \
    --param table_name=my_config --record-store "$STORE"
echo
echo "    Verify: no tables should remain:"
$PYTHON query --db-file "$DB" \
    "SELECT count(*) FROM sqlite_master WHERE type='table'" -o table
echo

# ── 5. dry-run without param (use default) ──────────────────────────────────
echo "[5] Dry-run without --param (uses default 'custom_table'):"
$PYTHON named-migration "$FQN" --db-file "$DB" --direction up --dry-run
echo

rm -f "$DB" "$STORE" "$DB-wal" "$DB-shm"
echo "=== Parameterized Migration Demo Complete ==="