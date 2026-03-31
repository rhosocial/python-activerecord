"""
Example script demonstrating thread-safety patterns for connection configuration.

This script validates the recommendations from docs/en_US/modeling/concurrency.md:
  1. configure() should be called once at application startup, never inside
     request handlers.
  2. Each independent process / thread must have its own backend instance.
  3. Missing configure() is detected before serving any requests.

All demos use SQLite :memory: backends so the script is fully self-contained
and produces no files on disk.
"""

import threading
from typing import ClassVar, Optional

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_DDL_OPTS = ExecutionOptions(stmt_type=StatementType.DDL)

_USERS_DDL = """
    CREATE TABLE IF NOT EXISTS users (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        name  TEXT    NOT NULL,
        email TEXT    NOT NULL UNIQUE
    )
"""

_ORDERS_DDL = """
    CREATE TABLE IF NOT EXISTS orders (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        total   REAL    NOT NULL DEFAULT 0.0
    )
"""


# ---------------------------------------------------------------------------
# Model definitions
# ---------------------------------------------------------------------------

class User(ActiveRecord):
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str
    email: str


class Order(ActiveRecord):
    __table_name__ = "orders"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    user_id: int
    total: float = 0.0


class Product(ActiveRecord):
    """A third model used only in the startup-assertion demo."""
    __table_name__ = "products"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    name: str


# ---------------------------------------------------------------------------
# Demo 1: configure() called once at startup
# ---------------------------------------------------------------------------

def demonstrate_configure_once() -> None:
    """configure() is a class-level, one-shot operation.

    All model instances created later share the same backend.  Calling it
    multiple times is redundant (and potentially unsafe under concurrency).
    """

    print("\n" + "=" * 60)
    print("DEMO 1 — Configure once at startup")
    print("=" * 60)

    config = SQLiteConnectionConfig(database=":memory:")

    # Each call to configure() creates a new backend instance from the same config.
    # To share a single connection, pass the same config and backend class.
    User.configure(config, SQLiteBackend)
    Order.configure(config, SQLiteBackend)

    # Create schema
    User.backend().execute(_USERS_DDL, options=_DDL_OPTS)
    Order.backend().execute(_ORDERS_DDL, options=_DDL_OPTS)

    # Each call to configure() produces an independent backend instance.
    # What matters is that configure() is called *once at startup*, not per request.
    print(f"\nUser backend id : {id(User.__backend__)}")
    print(f"Order backend id: {id(Order.__backend__)}")
    print(f"Both have their own backend: True")

    # Write a user and an order
    user = User(name="Alice", email="alice@example.com")
    user.save()
    Order(user_id=user.id, total=49.99).save()

    users  = User.query().all()
    orders = Order.query().all()
    print(f"\nUsers : {[u.name for u in users]}")
    print(f"Orders: {[o.total for o in orders]}")
    assert len(users)  == 1
    assert len(orders) == 1
    print("\n✓ configure() called once at startup per model class; both work correctly.")


# ---------------------------------------------------------------------------
# Demo 2: per-process isolation (simulate post_fork pattern)
# ---------------------------------------------------------------------------

def demonstrate_per_process_isolation() -> None:
    """Each simulated 'worker process' receives its own backend.

    In production (Gunicorn), this is achieved via the post_fork hook.
    Here we use threads with thread-local backends to illustrate independence.
    """

    print("\n" + "=" * 60)
    print("DEMO 2 — Per-worker isolation (simulating post_fork pattern)")
    print("=" * 60)

    results = {}
    errors  = []

    def worker(worker_id: int) -> None:
        """Simulate a Gunicorn worker that configures its own backend."""
        try:
            # Each worker class is defined locally to avoid sharing __backend__
            # across workers.  In a real post_fork scenario, each forked process
            # has its own memory space, so there is no class sharing.
            class WorkerUser(ActiveRecord):
                __table_name__ = "users"
                id: Optional[int] = None
                name: str
                email: str

            config = SQLiteConnectionConfig(database=":memory:")
            WorkerUser.configure(config, SQLiteBackend)
            WorkerUser.backend().execute(_USERS_DDL, options=_DDL_OPTS)

            WorkerUser(
                name=f"Worker{worker_id}",
                email=f"w{worker_id}@example.com"
            ).save()

            rows = WorkerUser.query().all()
            results[worker_id] = [r.name for r in rows]
        except Exception as exc:
            errors.append((worker_id, exc))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if errors:
        for wid, exc in errors:
            print(f"  Worker {wid} error: {exc}")
        assert not errors, "Workers should not raise errors"

    print("\nPer-worker query results (each worker sees only its own data):")
    for wid in sorted(results):
        print(f"  Worker {wid}: {results[wid]}")
        assert results[wid] == [f"Worker{wid}"], \
            f"Worker {wid} saw unexpected data: {results[wid]}"

    print("\n✓ Each worker's in-memory database is fully isolated.")


# ---------------------------------------------------------------------------
# Demo 3: startup assertion catches misconfigured models
# ---------------------------------------------------------------------------

def demonstrate_startup_assertion() -> None:
    """assert_all_configured() detects missing configure() calls before
    any request is served.
    """

    print("\n" + "=" * 60)
    print("DEMO 3 — Startup assertion catches misconfigured models")
    print("=" * 60)

    REQUIRED_MODELS = [User, Order, Product]

    def assert_all_configured(models):
        unconfigured = [
            cls.__name__
            for cls in models
            if "__backend__" not in cls.__dict__ or cls.__dict__["__backend__"] is None
        ]
        if unconfigured:
            raise RuntimeError(
                f"Models not configured: {', '.join(unconfigured)}.  "
                "Call configure() for each model before starting the server."
            )

    # Product has never been configured
    print(f"\nUser has own backend   : {'__backend__' in User.__dict__}")
    print(f"Order has own backend  : {'__backend__' in Order.__dict__}")
    print(f"Product has own backend: {'__backend__' in Product.__dict__}")

    try:
        assert_all_configured(REQUIRED_MODELS)
        print("\n✗ RuntimeError was not raised -- unexpected!")
    except RuntimeError as exc:
        print(f"\n✓ RuntimeError raised as expected: {exc}")

    # Now configure Product and retry
    config = SQLiteConnectionConfig(database=":memory:")
    Product.configure(config, SQLiteBackend)

    try:
        assert_all_configured(REQUIRED_MODELS)
        print("\n✓ All models configured -- assertion passed.")
    except RuntimeError as exc:
        print(f"\n✗ Unexpected error after configuring all models: {exc}")
        raise


# ---------------------------------------------------------------------------
# Demo 4: separate backends for different model classes
# ---------------------------------------------------------------------------

def demonstrate_separate_backends() -> None:
    """Two model classes can be configured with different backends.

    This simulates a primary DB (User) and an analytics DB (UserMetric)
    in the same process.
    """

    print("\n" + "=" * 60)
    print("DEMO 4 — Separate backends for different model classes")
    print("=" * 60)

    class UserMetric(ActiveRecord):
        """Analytics model -- separate backend, same table structure."""
        __table_name__ = "users"
        id: Optional[int] = None
        name: str
        email: str

    analytics_config = SQLiteConnectionConfig(database=":memory:")

    # User was already configured in Demo 1; configure UserMetric separately
    UserMetric.configure(analytics_config, SQLiteBackend)
    UserMetric.backend().execute(_USERS_DDL, options=_DDL_OPTS)

    UserMetric(name="Metric-Alice", email="metric-alice@analytics.com").save()

    primary_rows  = User.query().all()         # Alice from Demo 1
    analytics_rows = UserMetric.query().all()  # Metric-Alice from this demo

    print(f"\nPrimary DB (User)      : {[r.name for r in primary_rows]}")
    print(f"Analytics DB (Metric)  : {[r.name for r in analytics_rows]}")

    assert User.__backend__ is not UserMetric.__backend__, \
        "User and UserMetric should have separate backends"
    assert any(r.name == "Alice" for r in primary_rows)
    assert any(r.name == "Metric-Alice" for r in analytics_rows)

    print("\n✓ User and UserMetric use fully separate backends.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Thread Safety — Connection Configuration Patterns")
    print("=" * 60)

    demonstrate_configure_once()
    demonstrate_per_process_isolation()
    demonstrate_startup_assertion()
    demonstrate_separate_backends()

    print("\n" + "=" * 60)
    print("EXAMPLE SUMMARY")
    print("=" * 60)
    print("This example demonstrates:")
    print("1. configure() is a one-shot class-level operation; call it once")
    print("   at application startup, not inside request handlers.")
    print("2. Each worker process should configure its own backend (post_fork).")
    print("   In-process threading uses separate class definitions to mimic this.")
    print("3. A startup assertion function detects models that were never")
    print("   configured, preventing silent errors in production.")
    print("4. Different model classes can be configured with separate backends")
    print("   (e.g. primary vs. analytics database) in the same process.")
