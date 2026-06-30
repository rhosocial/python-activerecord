# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_migrations/run_chain.py
"""
Multi-step migration chain example — two migrations with dependency.

This script demonstrates:
  1. Running v001_create_users (creates ``users`` table)
  2. Running v002_create_posts (creates ``posts`` table, depends on v001)
  3. Dependency validation (v002 fails if v001 is not applied)
  4. Rolling back in reverse order
  5. Tracking applied migrations in JSON record store

Usage:
    python -m rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations.run_chain
"""

from pathlib import Path
import tempfile

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.migration import (
    MigrationRunner,
    MigrationDirection,
    JSONFileMigrationRecordStore,
    MigrationDependencyError,
    MigrationNotAppliedError,
)

BASE = "rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations.migrations"


def table_exists(cursor, name: str) -> bool:
    cursor.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    )
    return cursor.fetchone()[0] == 1


def main():
    print("=" * 60)
    print("Named Migration Demo — Dependency Chain")
    print("=" * 60)

    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    cursor = backend.connection.cursor()

    store_path = Path(tempfile.gettempdir()) / "mig_chain_demo.json"
    if store_path.exists():
        store_path.unlink()
    store = JSONFileMigrationRecordStore(store_path)
    print(f"\n[1] Record store: {store_path}")

    r1 = MigrationRunner(f"{BASE}.V001CreateUsers")
    r2 = MigrationRunner(f"{BASE}.V002CreatePosts")

    # --- Try v002 before v001 (should fail) -----------------------------------
    print("\n[2] Attempt v002 before v001 (should fail) …")
    try:
        r2.run(backend, MigrationDirection.UP, record_store=store)
        print("    ✗ ERROR: should have raised!")
    except MigrationDependencyError as e:
        print(f"    ✓ {e}")

    # --- Apply v001 -----------------------------------------------------------
    print("\n[3] Applying v001_create_users …")
    r1.run(backend, MigrationDirection.UP, record_store=store)
    assert table_exists(cursor, "users")
    print("    ✓ Table 'users' created.")

    # --- Apply v002 -----------------------------------------------------------
    print("\n[4] Applying v002_create_posts …")
    r2.run(backend, MigrationDirection.UP, record_store=store)
    assert table_exists(cursor, "posts")
    print("    ✓ Table 'posts' created (dependency check passed).")

    # --- Show applied ---------------------------------------------------------
    print(f"\n[5] Applied migrations:")
    for rec in store.get_applied():
        print(f"    - {rec.version}")

    # --- Rollback v002 first --------------------------------------------------
    print("\n[6] Rolling back v002_create_posts …")
    r2.run(backend, MigrationDirection.DOWN, record_store=store)
    assert not table_exists(cursor, "posts")
    assert table_exists(cursor, "users")
    print("    ✓ Table 'posts' dropped; 'users' still exists.")

    # --- Rollback v001 --------------------------------------------------------
    print("\n[7] Rolling back v001_create_users …")
    r1.run(backend, MigrationDirection.DOWN, record_store=store)
    assert not table_exists(cursor, "users")
    print("    ✓ Table 'users' dropped.")

    # --- Verify nothing applied -----------------------------------------------
    assert len(store.get_applied()) == 0
    print("\n[8] All migrations rolled back (0 applied).")

    # --- Attempt DOWN on unapplied --------------------------------------------
    print("\n[9] DOWN on unapplied migration (should fail) …")
    try:
        r1.run(backend, MigrationDirection.DOWN, record_store=store)
        print("    ✗ ERROR: should have raised!")
    except MigrationNotAppliedError as e:
        print(f"    ✓ {e}")

    backend.disconnect()
    if store_path.exists():
        store_path.unlink()
    print("\n=== Chain migration demo completed ===")


if __name__ == "__main__":
    main()
