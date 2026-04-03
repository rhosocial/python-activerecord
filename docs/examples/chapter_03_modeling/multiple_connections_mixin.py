"""
Example script demonstrating multiple independent connections using the Mixin pattern.

This example shows two Mixin writing styles (plain Python class vs BaseModel subclass),
and compares the Mixin pattern's isolation behavior against the subclass inheritance trap.

Scenario:
  - User       -> primary database (business logic)
  - UserMetric -> secondary database (analytics / read replica)
  - Shared fields (id, name, email) are extracted into a reusable Mixin.
  - The two model classes have no parent-child relationship with each other.
"""

from typing import Optional, ClassVar
from pydantic import BaseModel

# Import the ActiveRecord framework
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.errors import DatabaseError


# ---------------------------------------------------------------------------
# Shared DDL
# ---------------------------------------------------------------------------

_USERS_DDL = """
    CREATE TABLE IF NOT EXISTS users (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        name  TEXT    NOT NULL,
        email TEXT    NOT NULL UNIQUE
    )
"""

_DDL_OPTS = ExecutionOptions(stmt_type=StatementType.DDL)


# ---------------------------------------------------------------------------
# Mixin style A: plain Python class (no explicit base)
# ---------------------------------------------------------------------------
# Pydantic v2 resolves field annotations through the full MRO, so fields
# declared in a plain Python class mixin are recognized without inheriting
# BaseModel explicitly.

class UserFieldsMixinA:
    """Shared user fields -- plain Python class style."""
    id: Optional[int] = None
    name: str
    email: str


class UserWithMixinA(UserFieldsMixinA, ActiveRecord):
    """Business-side model using the plain Python mixin."""
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()


class UserMetricWithMixinA(UserFieldsMixinA, ActiveRecord):
    """Analytics-side model using the plain Python mixin."""
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()


# ---------------------------------------------------------------------------
# Mixin style B: Mixin inherits BaseModel explicitly
# ---------------------------------------------------------------------------
# This style makes the shared fields more discoverable in IDEs and type
# checkers, and is consistent with Pydantic's documented approach.

class UserFieldsMixinB(BaseModel):
    """Shared user fields -- BaseModel subclass style."""
    id: Optional[int] = None
    name: str
    email: str


class UserWithMixinB(UserFieldsMixinB, ActiveRecord):
    """Business-side model using the BaseModel mixin."""
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()


class UserMetricWithMixinB(UserFieldsMixinB, ActiveRecord):
    """Analytics-side model using the BaseModel mixin."""
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()


# ---------------------------------------------------------------------------
# Demo 1: plain Python class mixin -- independent connections
# ---------------------------------------------------------------------------

def demonstrate_plain_mixin() -> None:
    """User and UserMetric share fields via a plain Python mixin class.

    Each model is configured independently with its own connection.
    """

    print("\n" + "=" * 60)
    print("DEMO 1 — Plain Python class mixin (no BaseModel)")
    print("=" * 60)

    # 1. Configure each class with its own connection
    UserWithMixinA.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
    UserMetricWithMixinA.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

    # 2. Create schemas via their respective backends
    UserWithMixinA.backend().execute(_USERS_DDL, options=_DDL_OPTS)
    UserMetricWithMixinA.backend().execute(_USERS_DDL, options=_DDL_OPTS)

    # 3. Verify independence
    same = UserWithMixinA.__backend__ is UserMetricWithMixinA.__backend__
    print(f"\nUserWithMixinA backend id      : {id(UserWithMixinA.__backend__)}")
    print(f"UserMetricWithMixinA backend id: {id(UserMetricWithMixinA.__backend__)}")
    print(f"Are they the same?             : {same}")
    assert not same

    # 4. Write and read
    UserWithMixinA(name="Alice", email="alice@primary.com").save()
    UserMetricWithMixinA(name="Bob", email="bob@analytics.com").save()

    primary_rows   = UserWithMixinA.query().all()
    analytics_rows = UserMetricWithMixinA.query().all()
    print(f"\nPrimary DB   (UserWithMixinA)      : {[r.name for r in primary_rows]}")
    print(f"Analytics DB (UserMetricWithMixinA): {[r.name for r in analytics_rows]}")

    assert [r.name for r in primary_rows]   == ["Alice"]
    assert [r.name for r in analytics_rows] == ["Bob"]
    print("\n✓ Plain Python class mixin: connections are fully independent.")


# ---------------------------------------------------------------------------
# Demo 2: BaseModel subclass mixin -- independent connections
# ---------------------------------------------------------------------------

def demonstrate_basemodel_mixin() -> None:
    """User and UserMetric share fields via a BaseModel-derived mixin.

    Functionally identical to Demo 1; this style may be preferred for
    stronger IDE/type-checker support.
    """

    print("\n" + "=" * 60)
    print("DEMO 2 — BaseModel subclass mixin")
    print("=" * 60)

    # 1. Configure each class with its own connection
    UserWithMixinB.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
    UserMetricWithMixinB.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

    # 2. Create schemas
    UserWithMixinB.backend().execute(_USERS_DDL, options=_DDL_OPTS)
    UserMetricWithMixinB.backend().execute(_USERS_DDL, options=_DDL_OPTS)

    # 3. Verify independence
    same = UserWithMixinB.__backend__ is UserMetricWithMixinB.__backend__
    print(f"\nUserWithMixinB backend id      : {id(UserWithMixinB.__backend__)}")
    print(f"UserMetricWithMixinB backend id: {id(UserMetricWithMixinB.__backend__)}")
    print(f"Are they the same?             : {same}")
    assert not same

    # 4. Write and read
    UserWithMixinB(name="Carol", email="carol@primary.com").save()
    UserMetricWithMixinB(name="Dave", email="dave@analytics.com").save()

    primary_rows   = UserWithMixinB.query().all()
    analytics_rows = UserMetricWithMixinB.query().all()
    print(f"\nPrimary DB   (UserWithMixinB)      : {[r.name for r in primary_rows]}")
    print(f"Analytics DB (UserMetricWithMixinB): {[r.name for r in analytics_rows]}")

    assert [r.name for r in primary_rows]   == ["Carol"]
    assert [r.name for r in analytics_rows] == ["Dave"]
    print("\n✓ BaseModel subclass mixin: connections are fully independent.")


# ---------------------------------------------------------------------------
# Demo 3: the key advantage -- missing configure() is never silent
# ---------------------------------------------------------------------------

def demonstrate_no_silent_trap() -> None:
    """With the Mixin pattern, forgetting configure() raises an explicit error.

    Unlike the subclass inheritance pattern, there is no MRO fallback to a
    parent's backend.  The error is immediate and unambiguous.
    """

    print("\n" + "=" * 60)
    print("DEMO 3 — Missing configure() raises an explicit error")
    print("=" * 60)

    class UserMixin:
        id: Optional[int] = None
        name: str
        email: str

    class UserX(UserMixin, ActiveRecord):
        __table_name__ = "users"
        c: ClassVar[FieldProxy] = FieldProxy()

    class UserMetricX(UserMixin, ActiveRecord):
        __table_name__ = "users"
        c: ClassVar[FieldProxy] = FieldProxy()

    # Configure only UserX, intentionally skip UserMetricX
    UserX.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

    print(f"\nUserX has its own backend     : {'__backend__' in UserX.__dict__}")
    print(f"UserMetricX has its own backend: {'__backend__' in UserMetricX.__dict__}")
    print(f"UserMetricX.__backend__        : {UserMetricX.__backend__}")

    # Attempting to use UserMetricX raises DatabaseError immediately
    try:
        UserMetricX.query().all()
        print("\n✗ No error raised -- unexpected!")
    except DatabaseError as e:
        print(f"\n✓ DatabaseError raised for UserMetricX: {e}")
        print("  The missing configure() is caught explicitly -- no silent data mix-up.")


# ---------------------------------------------------------------------------
# Demo 4: shared fields are defined once -- DRY check
# ---------------------------------------------------------------------------

def demonstrate_field_reuse() -> None:
    """Verify that both Mixin styles expose the same field set on both models."""

    print("\n" + "=" * 60)
    print("DEMO 4 — Fields defined once, reused by both models (DRY)")
    print("=" * 60)

    for cls in (UserWithMixinA, UserMetricWithMixinA, UserWithMixinB, UserMetricWithMixinB):
        fields = list(cls.model_fields.keys())
        print(f"  {cls.__name__:<30} fields: {fields}")

    print("\n✓ All four models expose the same field set from a single Mixin definition.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Multiple Independent Connections — Mixin Pattern")
    print("=" * 60)

    # Run both Mixin style probes first (before configure() is called),
    # so Demo 3 can show the un-configured state cleanly.
    demonstrate_field_reuse()
    demonstrate_plain_mixin()
    demonstrate_basemodel_mixin()
    demonstrate_no_silent_trap()

    print("\n" + "=" * 60)
    print("EXAMPLE SUMMARY")
    print("=" * 60)
    print("This example demonstrates:")
    print("1. Plain Python class as a field mixin: works with Pydantic v2,")
    print("   fields are resolved through MRO without inheriting BaseModel")
    print("2. BaseModel subclass as a field mixin: explicit Pydantic inheritance,")
    print("   same result, stronger IDE / type-checker support")
    print("3. The key safety advantage: forgetting configure() raises an explicit")
    print("   DatabaseError immediately -- there is no silent MRO fallback")
    print("4. DRY principle: shared fields defined once in the Mixin, reused by")
    print("   any number of independent model classes")
    print("\nBoth Mixin styles produce identical runtime behavior.")
    print("Choose based on your team's preference for explicitness.")
