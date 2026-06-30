# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/run_basic.py
"""
Basic migration example — single migration UP then DOWN.

This script demonstrates:
  1. Creating a SQLite in-memory backend
  2. Running a single ``NamedMigration`` UP (creates ``users`` table)
  3. Verifying the table was created
  4. Running the same migration DOWN (drops ``users`` table)
  5. Showing JSON record store persistence
  6. Dry-run mode (no actual changes)
  7. Duplicate execution protection

Usage:
    python -m rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations.run_basic
    # or directly:
    python src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/run_basic.py
"""

from pathlib import Path
import tempfile

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.migration import (
    MigrationRunner,
    MigrationDirection,
    JSONFileMigrationRecordStore,
    MigrationAlreadyAppliedError,
)


def main():
    print("=" * 60)
    print("Named Migration Demo — Basic")
    print("=" * 60)

    # --- Backend --------------------------------------------------------------
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    cursor = backend.connection.cursor()
    print("\n[1] SQLite in-memory backend created.")

    # --- Record store ---------------------------------------------------------
    store_path = Path(tempfile.gettempdir()) / "mig_basic_demo.json"
    if store_path.exists():
        store_path.unlink()
    store = JSONFileMigrationRecordStore(store_path)
    print(f"[2] Record store: {store_path}")

    # --- Dry-run --------------------------------------------------------------
    fqn = (
        "rhosocial.activerecord.backend.impl.sqlite.examples"
        ".named_migrations.migrations.V001CreateUsers"
    )
    runner = MigrationRunner(fqn)

    print("\n[3] Dry-run (UP) — no actual changes …")
    result = runner.run(backend, MigrationDirection.UP, dry_run=True)
    print(f"    Result: version={result.version}, success={result.success}")
    cursor.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
    )
    assert cursor.fetchone()[0] == 0
    print("    ✓ Table 'users' does NOT exist (dry-run respected).")

    # --- Apply UP -------------------------------------------------------------
    print("\n[4] Applying v001_create_users (UP) …")
    result = runner.run(backend, MigrationDirection.UP, record_store=store)
    print(f"    Result: version={result.version}, success={result.success}")
    cursor.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
    )
    assert cursor.fetchone()[0] == 1
    print("    ✓ Table 'users' created.")

    # --- Duplicate protection -------------------------------------------------
    print("\n[5] Duplicate UP (should be rejected) …")
    try:
        runner.run(backend, MigrationDirection.UP, record_store=store)
        print("    ✗ ERROR: should have raised!")
    except MigrationAlreadyAppliedError as e:
        print(f"    ✓ {e}")

    # --- Apply DOWN -----------------------------------------------------------
    print("\n[6] Rolling back v001_create_users (DOWN) …")
    result = runner.run(backend, MigrationDirection.DOWN, record_store=store)
    print(f"    Result: version={result.version}, success={result.success}")
    cursor.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='users'"
    )
    assert cursor.fetchone()[0] == 0
    print("    ✓ Table 'users' dropped.")

    # --- Final state ----------------------------------------------------------
    applied = store.get_applied()
    print(f"\n[7] Applied migrations: {len(applied)} (should be 0)")

    # --- Cleanup --------------------------------------------------------------
    backend.disconnect()
    if store_path.exists():
        store_path.unlink()
    print("\n=== Basic migration demo completed ===")


if __name__ == "__main__":
    main()
