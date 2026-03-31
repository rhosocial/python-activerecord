"""
Example script demonstrating multiple independent connections using subclass inheritance.

This example shows how to configure a parent class and an empty subclass with separate
database connections, and highlights the silent inheritance trap that developers must be
aware of when using this pattern.

Scenario:
  - User       -> primary database (business logic)
  - UserMetric -> secondary database (analytics / read replica)
  - Both classes map to a `users` table, but in different databases.
"""

import os
from typing import Optional, ClassVar
from pathlib import Path

# Import the ActiveRecord framework
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------

_USERS_DDL = """
    CREATE TABLE IF NOT EXISTS users (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        name  TEXT    NOT NULL,
        email TEXT    NOT NULL UNIQUE
    )
"""


class User(ActiveRecord):
    """Business-side user model connected to the primary database."""

    __table_name__ = "users"

    id: Optional[int] = None
    name: str
    email: str

    c: ClassVar[FieldProxy] = FieldProxy()


class UserMetric(User):
    """Analytics-side model.

    Empty subclass of User -- no new fields or methods.
    Intended to be connected to a separate analytics database.
    """
    pass


# ---------------------------------------------------------------------------
# Demo 1: both classes configured independently -> truly isolated
# ---------------------------------------------------------------------------

def demonstrate_independent_connections() -> None:
    """Both User and UserMetric are configured with separate connections."""

    print("\n" + "=" * 60)
    print("DEMO 1 — Independent connections (both configured)")
    print("=" * 60)

    # 1. Configure User to use the primary database
    config_primary = SQLiteConnectionConfig(database=":memory:")
    User.configure(config_primary, SQLiteBackend)

    # 2. Configure UserMetric to use a different (analytics) database.
    #    configure() writes into UserMetric.__dict__, so User is unaffected.
    config_analytics = SQLiteConnectionConfig(database=":memory:")
    UserMetric.configure(config_analytics, SQLiteBackend)

    # 3. Create schemas via each class's own backend
    opts = ExecutionOptions(stmt_type=StatementType.DDL)
    User.backend().execute(_USERS_DDL, options=opts)
    UserMetric.backend().execute(_USERS_DDL, options=opts)

    # 4. Verify they hold different backend instances
    same = User.__backend__ is UserMetric.__backend__
    print(f"\nUser backend id      : {id(User.__backend__)}")
    print(f"UserMetric backend id: {id(UserMetric.__backend__)}")
    print(f"Are they the same?   : {same}")
    assert not same, "Backends should be independent after separate configure() calls"

    # 5. Write data through each model independently
    User(name="Alice", email="alice@primary.com").save()
    UserMetric(name="Bob", email="bob@analytics.com").save()

    # 6. Read back -- each model only sees its own database
    user_rows   = User.query().all()
    metric_rows = UserMetric.query().all()

    print(f"\nPrimary DB   (User)      : {[r.name for r in user_rows]}")
    print(f"Analytics DB (UserMetric): {[r.name for r in metric_rows]}")

    assert [r.name for r in user_rows]   == ["Alice"]
    assert [r.name for r in metric_rows] == ["Bob"]
    print("\n✓ The two databases are completely isolated.")


# ---------------------------------------------------------------------------
# Demo 2: only User configured -> UserMetric silently inherits User's backend
# ---------------------------------------------------------------------------

def demonstrate_silent_inheritance_trap() -> None:
    """Only the parent is configured; the subclass is used without configure().

    This is the 'silent trap': UserMetric.__backend__ resolves to User.__backend__
    via Python MRO, so both classes share the same connection -- with no error raised.
    """

    print("\n" + "=" * 60)
    print("DEMO 2 — The silent inheritance trap")
    print("=" * 60)

    # Define a fresh subclass so it has no __backend__ entry of its own
    class FreshUserMetric(User):
        pass

    # Configure only the parent
    config = SQLiteConnectionConfig(database=":memory:")
    User.configure(config, SQLiteBackend)
    User.backend().execute(_USERS_DDL, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # FreshUserMetric never called configure() -- check what it resolves to
    same = User.__backend__ is FreshUserMetric.__backend__
    print(f"\nUser backend id                : {id(User.__backend__)}")
    print(f"FreshUserMetric backend id     : {id(FreshUserMetric.__backend__)}")
    print(f"Are they the same?             : {same}")
    assert same, "Without configure(), the subclass should fall back to the parent backend"
    print(
        "\n⚠  FreshUserMetric never called configure(), yet it shares User's backend.\n"
        "   Both classes will read/write to the SAME database -- silently."
    )

    # Both models write to the same DB
    User(name="Alice", email="alice@shared.com").save()
    FreshUserMetric(name="Bob", email="bob@shared.com").save()

    user_rows   = User.query().all()
    metric_rows = FreshUserMetric.query().all()

    print(f"\nUser.query().all()           : {[r.name for r in user_rows]}")
    print(f"FreshUserMetric.query().all(): {[r.name for r in metric_rows]}")

    assert len(user_rows) == 2 and len(metric_rows) == 2
    print("\n⚠  Both queries return ALL rows -- they share the same database!")


# ---------------------------------------------------------------------------
# Demo 3: guard pattern to detect missing configure() at startup
# ---------------------------------------------------------------------------

def demonstrate_guard_pattern() -> None:
    """Show how a simple startup check catches the missing configure() early."""

    print("\n" + "=" * 60)
    print("DEMO 3 — Guard pattern to detect missing configure()")
    print("=" * 60)

    class GuardedUserMetric(User):
        """Subclass that requires its own independent backend."""
        pass

    def assert_independently_configured(cls) -> None:
        """Raise RuntimeError if cls shares its backend with a parent class."""
        own_backend = cls.__dict__.get("__backend__")
        if own_backend is None:
            raise RuntimeError(
                f"{cls.__name__} has no independent backend configured. "
                f"Call {cls.__name__}.configure() before use."
            )

    # Configure only the parent
    config = SQLiteConnectionConfig(database=":memory:")
    User.configure(config, SQLiteBackend)

    try:
        assert_independently_configured(GuardedUserMetric)
        print("\n✗ Guard did not fire -- something is wrong.")
    except RuntimeError as e:
        print(f"\n✓ Guard caught the problem at startup: {e}")

    print("\n  Tip: add this check to your application startup or __init_subclass__.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Multiple Independent Connections — Subclass Inheritance Pattern")
    print("=" * 60)

    demonstrate_independent_connections()
    demonstrate_silent_inheritance_trap()
    demonstrate_guard_pattern()

    print("\n" + "=" * 60)
    print("EXAMPLE SUMMARY")
    print("=" * 60)
    print("This example demonstrates:")
    print("1. How to give a subclass its own independent connection via configure()")
    print("2. The silent inheritance trap: a subclass that never calls configure()")
    print("   will silently fall back to the parent's backend via Python MRO --")
    print("   with no error, no warning, and no visible sign of the problem")
    print("3. A simple guard pattern that detects missing configure() at startup")
    print("\nKey takeaway:")
    print("  When using the inheritance pattern, EVERY class in the hierarchy")
    print("  that needs its own connection MUST call configure() explicitly.")
