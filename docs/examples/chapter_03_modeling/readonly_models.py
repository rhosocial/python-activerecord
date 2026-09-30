"""
Read-only models and keyless models, demonstrated end to end.

Validates the recommendations from docs/en_US/modeling/readonly_models.md and
keyless_models.md:

  1. The built-in ReadOnlyMixin refuses every framework write path, and does
     so before any SQL is prepared.
  2. Reads are unaffected.
  3. A model can satisfy IReadOnlyBehavior and still be writable -- which is
     why the gate reads the returned value rather than testing the type.
  4. A read-only model can be configured against a separate backend.
  5. __primary_key__ = None declares a keyless relation: queries still work,
     identity-based access raises UnaddressableRecordError.
  6. Keyless-ness and read-only-ness are independent in both directions.
  7. @property fields compute metrics without touching the schema.

All demos use SQLite :memory: backends so the script is self-contained.
"""

from datetime import datetime, timedelta
from typing import ClassVar, Optional

from pydantic import BaseModel

from rhosocial.activerecord.backend.errors import ReadOnlyError, UnaddressableRecordError
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import ReadOnlyMixin
from rhosocial.activerecord.interface import IReadOnlyBehavior
from rhosocial.activerecord.model import ActiveRecord

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

_AUDIT_DDL = """
    CREATE TABLE IF NOT EXISTS audit_log (
        event TEXT NOT NULL,
        level TEXT NOT NULL
    )
"""


def _expect_refusal(label: str, operation, expected) -> None:
    """Run ``operation`` and report whether it raised ``expected``."""
    print(f"\n  {label}")
    try:
        operation()
    except expected as exc:
        print(f"    ✓ {type(exc).__name__}: {exc}")
        return
    raise AssertionError(f"{label} did not raise {expected.__name__}")


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
    """Read-only analytics model -- analytics replica.

    Mixin-first ordering is the documented convention. Note there is no async
    variant of ReadOnlyMixin to choose between: read_only() is a zero-I/O
    classmethod, so the same mixin serves ActiveRecord and AsyncActiveRecord.
    """

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


class ImplementsButWritable(UserFields, ActiveRecord, IReadOnlyBehavior):
    """Satisfies the interface without being read-only.

    The gate reads the value returned by read_only(), never the type, so this
    model writes normally. A type test would have refused it.
    """

    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()


class AuditLog(ActiveRecord):
    """Keyless but writable: an append-only table has no single-row identity."""

    __table_name__ = "audit_log"
    c: ClassVar[FieldProxy] = FieldProxy()
    __primary_key__ = None
    event: str
    level: str


class EventSummary(ReadOnlyMixin, ActiveRecord):
    """Keyless *and* read-only -- the two dimensions compose independently."""

    __table_name__ = "audit_log"
    c: ClassVar[FieldProxy] = FieldProxy()
    __primary_key__ = None
    event: str
    level: str


# ---------------------------------------------------------------------------
# Demo 1: ReadOnlyMixin blocks the framework write paths
# ---------------------------------------------------------------------------


def demonstrate_readonly_protection() -> None:
    print("\n" + "=" * 60)
    print("DEMO 1 — ReadOnlyMixin refuses the framework write paths")
    print("=" * 60)

    UserAnalytics.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
    UserAnalytics.backend().execute(_USERS_DDL, options=_DDL_OPTS)

    print("\n  read_only():", UserAnalytics.read_only())

    _expect_refusal(
        "UserAnalytics(...).save()",
        lambda: UserAnalytics(name="Test", email="t@example.com").save(),
        ReadOnlyError,
    )
    _expect_refusal(
        "UserAnalytics(...).delete()",
        lambda: UserAnalytics(id=1, name="Test", email="t@example.com").delete(),
        ReadOnlyError,
    )
    _expect_refusal(
        "UserAnalytics.bulk_create([...])",
        lambda: UserAnalytics.bulk_create([UserAnalytics(name="X", email="x@example.com")]),
        ReadOnlyError,
    )
    _expect_refusal(
        "UserAnalytics.bulk_update([...], ['name'])",
        lambda: UserAnalytics.bulk_update([UserAnalytics(id=1, name="X", email="x@example.com")], ["name"]),
        ReadOnlyError,
    )
    _expect_refusal(
        "UserAnalytics.bulk_delete([...])",
        lambda: UserAnalytics.bulk_delete([UserAnalytics(id=1, name="X", email="x@example.com")]),
        ReadOnlyError,
    )
    _expect_refusal(
        "UserAnalytics.query().where(...).update_all({...})",
        lambda: UserAnalytics.query().where(UserAnalytics.c.id == 1).update_all({"name": "y"}),
        ReadOnlyError,
    )
    _expect_refusal(
        "UserAnalytics.query().where(...).delete_all()",
        lambda: UserAnalytics.query().where(UserAnalytics.c.id == 1).delete_all(),
        ReadOnlyError,
    )

    print("\n  ✓ Every framework write path is refused.")


# ---------------------------------------------------------------------------
# Demo 2: reads are unaffected, and opt-in means no cost
# ---------------------------------------------------------------------------


def demonstrate_reads_unaffected() -> None:
    print("\n" + "=" * 60)
    print("DEMO 2 — Reads work, and the feature is opt-in")
    print("=" * 60)

    # Seed through direct SQL: the model refuses to write by design.
    UserAnalytics.backend().execute(
        "INSERT INTO users (name, email, created_at, signup_days_ago) VALUES (?, ?, ?, ?)",
        ("Alice", "alice@example.com", datetime.now().isoformat(), 10),
        options=_DML_OPTS,
    )

    print("\n  query().all()      ->", [r.name for r in UserAnalytics.query().all()])
    print("  query().count()    ->", UserAnalytics.query().count())
    print("  where(...).exists()->", UserAnalytics.query().where(UserAnalytics.c.name == "Alice").exists())
    print(
        "  select().aggregate() ->",
        [r["name"] for r in UserAnalytics.query().select(UserAnalytics.c.name).aggregate()],
    )

    assert len(UserAnalytics.query().all()) == 1

    # A model that never mixed in the behaviour does not even answer the question.
    print("\n  User is addressable and writable, untouched:")
    print("    has read_only attr:", hasattr(User, "read_only"))
    User.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
    User.backend().execute(_USERS_DDL, options=_DDL_OPTS)
    record = User(name="Bob", email="bob@example.com")
    record.save()
    print("    User(...).save()  -> id =", record.id)
    assert record.id is not None

    print("\n  ✓ Reads are unaffected and un-opted-in models behave exactly as before.")


# ---------------------------------------------------------------------------
# Demo 3: the gate reads the value, not the type
# ---------------------------------------------------------------------------


def demonstrate_value_not_type() -> None:
    print("\n" + "=" * 60)
    print("DEMO 3 — Satisfying the interface does not make a model read-only")
    print("=" * 60)

    ImplementsButWritable.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
    ImplementsButWritable.backend().execute(_USERS_DDL, options=_DDL_OPTS)

    print("\n  issubclass(..., IReadOnlyBehavior):", issubclass(ImplementsButWritable, IReadOnlyBehavior))
    print("  read_only()                       :", ImplementsButWritable.read_only())

    record = ImplementsButWritable(name="Carol", email="carol@example.com")
    record.save()
    print("  save() succeeded -> id =", record.id)
    assert record.id is not None

    print("\n  ✓ A type test would have refused this model; the value test does not.")


# ---------------------------------------------------------------------------
# Demo 4: read-only model on a separate backend
# ---------------------------------------------------------------------------


def demonstrate_separate_backends() -> None:
    print("\n" + "=" * 60)
    print("DEMO 4 — Writable model (primary) + read-only model (replica)")
    print("=" * 60)

    primary_config = SQLiteConnectionConfig(database=":memory:")
    analytics_config = SQLiteConnectionConfig(database=":memory:")

    User.configure(primary_config, SQLiteBackend)
    UserAnalytics.configure(analytics_config, SQLiteBackend)

    User.backend().execute(_USERS_DDL, options=_DDL_OPTS)
    UserAnalytics.backend().execute(_USERS_DDL, options=_DDL_OPTS)

    User(name="Alice", email="alice@example.com", signup_days_ago=10).save()

    # Simulate replication by inserting the same row into the replica directly.
    UserAnalytics.backend().execute(
        "INSERT INTO users (name, email, created_at, signup_days_ago) VALUES (?, ?, ?, ?)",
        ("Alice", "alice@replica.com", datetime.now().isoformat(), 10),
        options=_DML_OPTS,
    )

    primary_rows = User.query().all()
    replica_rows = UserAnalytics.query().all()

    print(f"\n  Primary DB  (User)         : {[r.name for r in primary_rows]}")
    print(f"  Replica DB  (UserAnalytics): {[r.name for r in replica_rows]}")

    assert User.__backend__ is not UserAnalytics.__backend__
    assert len(primary_rows) == 1 and len(replica_rows) == 1

    print("\n  ✓ Writable and read-only models use fully separate backends.")


# ---------------------------------------------------------------------------
# Demo 5: keyless models
# ---------------------------------------------------------------------------


def demonstrate_keyless() -> None:
    print("\n" + "=" * 60)
    print("DEMO 5 — __primary_key__ = None declares a keyless relation")
    print("=" * 60)

    AuditLog.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
    AuditLog.backend().execute(_AUDIT_DDL, options=_DDL_OPTS)

    print("\n  addressable()          :", AuditLog.addressable())
    print("  primary_key_columns()  :", AuditLog.primary_key_columns())
    print("  primary_key_fields()   :", AuditLog.primary_key_fields())
    print("  is_composite_pk()      :", AuditLog.is_composite_pk())

    # What keeps working: everything that does not need identity.
    AuditLog(event="login", level="info").save()
    AuditLog(event="logout", level="info").save()
    print("\n  after two inserts:")
    print("    query().all()   ->", [r.event for r in AuditLog.query().all()])
    print("    query().count() ->", AuditLog.query().count())
    assert AuditLog.query().count() == 2

    # What stops working: everything that needs identity.
    _expect_refusal("AuditLog.find_one(1)", lambda: AuditLog.find_one(1), UnaddressableRecordError)
    _expect_refusal("AuditLog.find_all([1])", lambda: AuditLog.find_all([1]), UnaddressableRecordError)
    _expect_refusal(
        "AuditLog(...).refresh()", lambda: AuditLog(event="x", level="info").refresh(), UnaddressableRecordError
    )

    # A non-key condition is not a key, so it still works.
    found = AuditLog.find_one(AuditLog.c.event == "login")
    print("\n  find_one(predicate) still works ->", found.event)
    assert found.event == "login"

    # A row read back from the database is recognised as already persisted.
    print("  loaded.is_new_record   ->", found.is_new_record)
    assert found.is_new_record is False

    print("\n  ✓ Queries work; identity-based access raises with a precise message.")


# ---------------------------------------------------------------------------
# Demo 6: the two axes are independent
# ---------------------------------------------------------------------------


def demonstrate_orthogonality() -> None:
    print("\n" + "=" * 60)
    print("DEMO 6 — Keyless and read-only are independent axes")
    print("=" * 60)

    combos = [
        ("AuditLog", AuditLog, False, False),
        ("EventSummary", EventSummary, False, True),
        ("UserAnalytics", UserAnalytics, True, True),
        ("User", User, True, False),
    ]
    print(f"\n  {'Model':<16} {'addressable':>12} {'read_only':>10}")
    print("  " + "-" * 38)
    for name, model, addressable, read_only in combos:
        model_read_only = getattr(model, "read_only", lambda: False)()
        print(f"  {name:<16} {str(model.addressable()):>12} {str(model_read_only):>10}")
        assert model.addressable() is addressable
        assert model_read_only is read_only

    print("\n  ✓ All four combinations are reachable; neither axis implies the other.")


# ---------------------------------------------------------------------------
# Demo 7: derived / computed fields via @property
# ---------------------------------------------------------------------------


def demonstrate_computed_fields() -> None:
    print("\n" + "=" * 60)
    print("DEMO 7 — Derived / computed fields via @property")
    print("=" * 60)

    test_users = [
        ("Brand-New", "new@example.com", 5),
        ("Regular", "regular@example.com", 180),
        ("Veteran", "veteran@example.com", 500),
    ]
    for name, email, days in test_users:
        # Direct SQL, because the model refuses to write by design.
        UserAnalytics.backend().execute(
            "INSERT INTO users (name, email, created_at, signup_days_ago) VALUES (?, ?, ?, ?)",
            (name, email, (datetime.now() - timedelta(days=days)).isoformat(), days),
            options=_DML_OPTS,
        )

    names = {u[0] for u in test_users}
    rows = [r for r in UserAnalytics.query().all() if r.name in names]

    print(f"\n  {'Name':<12} {'signup_days_ago':>16} {'is_new_user':>12} {'tier':>10}")
    print("  " + "-" * 54)
    for row in rows:
        print(
            f"  {row.name:<12} {row.signup_days_ago or 0:>16} "
            f"{str(row.is_new_user):>12} {row.tier:>10}"
        )

    by_name = {r.name: r for r in rows}
    assert by_name["Brand-New"].tier == "new"
    assert by_name["Regular"].tier == "regular"
    assert by_name["Veteran"].tier == "veteran"

    # @property fields are not stored, so Pydantic never tries to persist them.
    assert "is_new_user" not in UserAnalytics.model_fields
    assert "tier" not in UserAnalytics.model_fields

    print("\n  ✓ @property fields compute metrics without touching the database.")


# ---------------------------------------------------------------------------
# Demo 8: shared field Mixin keeps definitions DRY
# ---------------------------------------------------------------------------


def demonstrate_shared_fields() -> None:
    print("\n" + "=" * 60)
    print("DEMO 8 — Shared field Mixin (DRY field definitions)")
    print("=" * 60)

    user_fields = list(User.model_fields.keys())
    analytics_fields = list(UserAnalytics.model_fields.keys())

    print(f"\n  User fields          : {user_fields}")
    print(f"  UserAnalytics fields : {analytics_fields}")

    assert user_fields == analytics_fields

    print("\n  ✓ Stored fields are identical; definitions live in one place (UserFields).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Read-Only and Keyless Models")
    print("=" * 60)

    demonstrate_readonly_protection()
    demonstrate_reads_unaffected()
    demonstrate_value_not_type()
    demonstrate_separate_backends()
    demonstrate_keyless()
    demonstrate_orthogonality()
    demonstrate_computed_fields()
    demonstrate_shared_fields()

    print("\n" + "=" * 60)
    print("EXAMPLE SUMMARY")
    print("=" * 60)
    print("1. The built-in ReadOnlyMixin refuses save(), delete(), the three")
    print("   bulk operations, update_all() and delete_all(), before any SQL is")
    print("   prepared. ReadOnlyError subclasses DatabaseError.")
    print("2. Reads, relations and aggregation are untouched, and a model that")
    print("   never mixed in the behaviour is completely unaffected.")
    print("3. Satisfying IReadOnlyBehavior does not make a model read-only: the")
    print("   gate reads the value returned by read_only(), never the type.")
    print("4. A read-only model can be configured against its own backend.")
    print("5. __primary_key__ = None keeps queries working and raises")
    print("   UnaddressableRecordError only where identity is required.")
    print("6. Keyless-ness and read-only-ness are independent in both directions.")
    print("7. @property fields compute derived metrics without schema changes.")
    print("8. A shared BaseModel mixin keeps field definitions in one place.")
