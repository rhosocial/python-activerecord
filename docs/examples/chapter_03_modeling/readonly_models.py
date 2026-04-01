"""
Example script demonstrating read-only analytics model patterns.

This script validates the recommendations from
docs/en_US/modeling/readonly_models.md:
  1. ReadOnlyMixin overrides save(), delete(), and bulk_create() so that
     accidental write attempts raise TypeError immediately.
  2. A read-only model can be configured against a separate backend
     (e.g. an analytics replica).
  3. Combining ReadOnlyMixin with a shared field Mixin keeps field definitions
     DRY while maintaining write safety.
  4. @property fields express computed metrics without touching the database.

All demos use SQLite :memory: backends so the script is fully self-contained.
"""

from datetime import datetime, timedelta
from typing import ClassVar, Optional

from pydantic import BaseModel

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_DDL_OPTS = ExecutionOptions(stmt_type=StatementType.DDL)
_DML_OPTS = ExecutionOptions(stmt_type=StatementType.INSERT)

_USERS_DDL = """
    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT    NOT NULL,
        email           TEXT    NOT NULL UNIQUE,
        created_at      TEXT,
        signup_days_ago INTEGER
    )
"""


# ---------------------------------------------------------------------------
# ReadOnlyMixin (as described in the article)
# ---------------------------------------------------------------------------

class ReadOnlyMixin:
    """Mix into any ActiveRecord subclass to make it read-only."""

    __readonly__: bool = True

    def save(self, *args, **kwargs):
        raise TypeError(
            f"{type(self).__name__} is a read-only model and cannot be saved. "
            "Use the corresponding writable model class instead."
        )

    def delete(self, *args, **kwargs):
        raise TypeError(
            f"{type(self).__name__} is a read-only model and cannot be deleted."
        )

    @classmethod
    def bulk_create(cls, *args, **kwargs):
        raise TypeError(f"{cls.__name__} is a read-only model.")


# ---------------------------------------------------------------------------
# Shared field Mixin (DRY field definitions)
# ---------------------------------------------------------------------------

class UserFields(BaseModel):
    """Shared field definitions for writable and read-only user models."""
    id: Optional[int] = None
    name: str
    email: str
    created_at: Optional[str] = None
    signup_days_ago: Optional[int] = None


# ---------------------------------------------------------------------------
# Model classes
# ---------------------------------------------------------------------------

class User(UserFields, ActiveRecord):
    """Writable business model -- primary database."""
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()


class UserAnalytics(ReadOnlyMixin, UserFields, ActiveRecord):
    """Read-only analytics model -- analytics replica."""
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()

    @property
    def is_new_user(self) -> bool:
        """True if the user signed up within the last 30 days."""
        return (self.signup_days_ago or 0) <= 30

    @property
    def tier(self) -> str:
        """Classify users by signup age."""
        days = self.signup_days_ago or 0
        if days <= 30:
            return "new"
        if days <= 365:
            return "regular"
        return "veteran"


# ---------------------------------------------------------------------------
# Demo 1: ReadOnlyMixin blocks all write operations
# ---------------------------------------------------------------------------

def demonstrate_readonly_protection() -> None:
    """save(), delete(), and bulk_create() all raise TypeError immediately.

    No database call is made; the error is caught in Python before any
    network or disk I/O occurs.
    """

    print("\n" + "=" * 60)
    print("DEMO 1 — ReadOnlyMixin blocks write operations")
    print("=" * 60)

    analytics_config = SQLiteConnectionConfig(database=":memory:")
    UserAnalytics.configure(analytics_config, SQLiteBackend)
    UserAnalytics.backend().execute(_USERS_DDL, options=_DDL_OPTS)

    # --- Test save() ---
    instance = UserAnalytics(name="Test", email="test@example.com")
    print("\nAttempting UserAnalytics(...).save() ...")
    try:
        instance.save()
        print("  ✗ No error raised -- unexpected!")
    except TypeError as exc:
        print(f"  ✓ TypeError raised: {exc}")

    # --- Test delete() ---
    print("\nAttempting UserAnalytics(...).delete() ...")
    try:
        instance.delete()
        print("  ✗ No error raised -- unexpected!")
    except TypeError as exc:
        print(f"  ✓ TypeError raised: {exc}")

    # --- Test bulk_create() ---
    print("\nAttempting UserAnalytics.bulk_create([...]) ...")
    try:
        UserAnalytics.bulk_create([{"name": "X", "email": "x@example.com"}])
        print("  ✗ No error raised -- unexpected!")
    except TypeError as exc:
        print(f"  ✓ TypeError raised: {exc}")

    print("\n✓ All write operations are blocked by ReadOnlyMixin.")


# ---------------------------------------------------------------------------
# Demo 2: read-only model + writable model on separate backends
# ---------------------------------------------------------------------------

def demonstrate_separate_backends() -> None:
    """User writes to the primary DB; UserAnalytics reads from a replica.

    In production these would be separate database servers.  Here we use
    two independent :memory: backends to simulate the same topology.
    """

    print("\n" + "=" * 60)
    print("DEMO 2 — Writable model (primary) + read-only model (replica)")
    print("=" * 60)

    primary_config   = SQLiteConnectionConfig(database=":memory:")
    analytics_config = SQLiteConnectionConfig(database=":memory:")

    User.configure(primary_config, SQLiteBackend)
    UserAnalytics.configure(analytics_config, SQLiteBackend)

    User.backend().execute(_USERS_DDL, options=_DDL_OPTS)
    UserAnalytics.backend().execute(_USERS_DDL, options=_DDL_OPTS)

    # Write via the writable model
    User(
        name="Alice",
        email="alice@example.com",
        created_at=datetime.now().isoformat(),
        signup_days_ago=10
    ).save()

    # Simulate replication by inserting the same row directly into the replica
    UserAnalytics.backend().execute(
        "INSERT INTO users (name, email, created_at, signup_days_ago) "
        "VALUES (?, ?, ?, ?)",
        ("Alice", "alice@replica.com",
         datetime.now().isoformat(), 10),
        options=_DML_OPTS,
    )

    primary_rows  = User.query().all()
    replica_rows  = UserAnalytics.query().all()

    print(f"\nPrimary DB  (User)         : {[r.name for r in primary_rows]}")
    print(f"Replica DB  (UserAnalytics): {[r.name for r in replica_rows]}")

    assert User.__backend__ is not UserAnalytics.__backend__, \
        "Writable and read-only models must have separate backends"
    assert len(primary_rows)  == 1
    assert len(replica_rows) == 1

    print("\n✓ Writable and read-only models use fully separate backends.")


# ---------------------------------------------------------------------------
# Demo 3: derived / computed fields via @property
# ---------------------------------------------------------------------------

def demonstrate_computed_fields() -> None:
    """@property fields compute metrics in Python without any schema change."""

    print("\n" + "=" * 60)
    print("DEMO 3 — Derived / computed fields via @property")
    print("=" * 60)

    # Re-use the analytics backend from Demo 2
    # Insert test records with different signup ages
    test_users = [
        ("Brand-New",  "new@example.com",      5),
        ("Regular",    "regular@example.com", 180),
        ("Veteran",    "veteran@example.com",  500),
    ]
    for name, email, days in test_users:
        # Use direct SQL to avoid ReadOnlyMixin blocking save()
        UserAnalytics.backend().execute(
            "INSERT INTO users (name, email, created_at, signup_days_ago) "
            "VALUES (?, ?, ?, ?)",
            (name, email, (datetime.now() - timedelta(days=days)).isoformat(), days),
            options=_DML_OPTS,
        )

    # Fetch and inspect computed properties
    all_rows = UserAnalytics.query().all()
    # Filter only the users we just inserted
    rows = [r for r in all_rows if r.name in {u[0] for u in test_users}]

    print(f"\n{'Name':<15} {'signup_days_ago':>16} {'is_new_user':>12} {'tier':>10}")
    print("-" * 60)
    for row in rows:
        print(f"{row.name:<15} {row.signup_days_ago or 0:>16} "
              f"{str(row.is_new_user):>12} {row.tier:>10}")

    by_name = {r.name: r for r in rows}
    assert by_name["Brand-New"].is_new_user is True
    assert by_name["Brand-New"].tier == "new"
    assert by_name["Regular"].is_new_user is False
    assert by_name["Regular"].tier == "regular"
    assert by_name["Veteran"].is_new_user is False
    assert by_name["Veteran"].tier == "veteran"

    print("\n✓ @property fields compute metrics without touching the database.")


# ---------------------------------------------------------------------------
# Demo 4: shared field Mixin keeps definitions DRY
# ---------------------------------------------------------------------------

def demonstrate_shared_fields() -> None:
    """Both User and UserAnalytics have the same fields from UserFields."""

    print("\n" + "=" * 60)
    print("DEMO 4 — Shared field Mixin (DRY field definitions)")
    print("=" * 60)

    user_fields     = list(User.model_fields.keys())
    analytics_fields = list(UserAnalytics.model_fields.keys())

    print(f"\nUser fields          : {user_fields}")
    print(f"UserAnalytics fields : {analytics_fields}")

    assert user_fields == analytics_fields, \
        "Both models must expose the same set of stored fields"

    # @property fields are NOT in model_fields (they are not stored)
    assert "is_new_user" not in UserAnalytics.model_fields
    assert "tier"        not in UserAnalytics.model_fields
    assert hasattr(UserAnalytics, "is_new_user")
    assert hasattr(UserAnalytics, "tier")

    print("\n✓ Stored fields are identical; @property fields are not in model_fields.")
    print("  Field definitions are maintained in one place (UserFields).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Read-Only Analytics Models — Safety and DRY Field Patterns")
    print("=" * 60)

    demonstrate_readonly_protection()
    demonstrate_separate_backends()
    demonstrate_computed_fields()
    demonstrate_shared_fields()

    print("\n" + "=" * 60)
    print("EXAMPLE SUMMARY")
    print("=" * 60)
    print("This example demonstrates:")
    print("1. ReadOnlyMixin makes save(), delete(), and bulk_create() raise")
    print("   TypeError immediately -- no database call is made.")
    print("2. A read-only model and its writable counterpart can be configured")
    print("   against separate backends (primary vs. replica/analytics).")
    print("3. @property fields compute derived metrics in Python without schema")
    print("   changes.  They are absent from model_fields, so Pydantic never")
    print("   tries to persist them.")
    print("4. A shared BaseModel Mixin keeps field definitions in one place;")
    print("   both models stay in sync automatically when fields are updated.")
