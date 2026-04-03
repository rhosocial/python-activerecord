"""
Example script demonstrating environment-based configuration management.

This script validates the recommendations from
docs/en_US/modeling/configuration_management.md:
  1. A factory function builds the correct backend based on APP_ENV.
  2. All configure() calls happen in a single startup function.
  3. In-memory SQLite provides fully isolated test environments.
  4. Reconfiguring with a fresh backend resets state between test sessions.

All demos use SQLite (:memory: or temporary on-disk) so the script is fully
self-contained and leaves no permanent files on disk.
"""

import os
import tempfile
from typing import ClassVar, Optional, List, Type

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


# ---------------------------------------------------------------------------
# Configuration factory (mirrors the make_backend() pattern from the article)
# ---------------------------------------------------------------------------

def make_backend(env: Optional[str] = None):
    """Build and return the appropriate backend for the given environment.

    Parameters
    ----------
    env:
        Override the APP_ENV value.  Defaults to os.environ["APP_ENV"]
        or "development" if the variable is not set.
    """
    if env is None:
        env = os.environ.get("APP_ENV", "development")

    if env == "test":
        config = SQLiteConnectionConfig(database=":memory:")
        return SQLiteBackend(config)

    if env == "development":
        # Use a temporary file to avoid writing to the project directory
        tmpdir = tempfile.mkdtemp()
        config = SQLiteConnectionConfig(database=os.path.join(tmpdir, "dev.db"))
        return SQLiteBackend(config)

    # Production would use MySQL/PostgreSQL; we fall back to SQLite here
    # to keep the example self-contained.
    config = SQLiteConnectionConfig(database=":memory:")
    return SQLiteBackend(config)


def configure_models(models: List[Type[ActiveRecord]], env: Optional[str] = None) -> None:
    """Configure all models with the environment-appropriate backend.

    Mirrors the recommended configure_models() pattern from the article.
    """
    if env is None:
        env = os.environ.get("APP_ENV", "development")

    for cls in models:
        # Each class gets its own backend instance built from the same config.
        if env == "test":
            config = SQLiteConnectionConfig(database=":memory:")
            cls.configure(config, SQLiteBackend)
        elif env == "development":
            tmpdir = tempfile.mkdtemp()
            config = SQLiteConnectionConfig(database=os.path.join(tmpdir, "dev.db"))
            cls.configure(config, SQLiteBackend)
        else:
            # production: fallback to :memory: for demo purposes
            config = SQLiteConnectionConfig(database=":memory:")
            cls.configure(config, SQLiteBackend)


# ---------------------------------------------------------------------------
# Demo 1: development environment (file-based SQLite)
# ---------------------------------------------------------------------------

def demonstrate_development_env() -> None:
    """Development environment uses a local SQLite file."""

    print("\n" + "=" * 60)
    print("DEMO 1 — Development environment (file-based SQLite)")
    print("=" * 60)

    configure_models([User, Order], env="development")

    User.backend().execute(_USERS_DDL, options=_DDL_OPTS)
    Order.backend().execute(_ORDERS_DDL, options=_DDL_OPTS)

    User(name="Dev-Alice", email="dev-alice@example.com").save()
    users = User.query().all()
    print(f"\nUsers in dev DB: {[u.name for u in users]}")
    assert any(u.name == "Dev-Alice" for u in users)

    # Confirm both models are configured (each with its own backend instance)
    assert "__backend__" in User.__dict__ and User.__dict__["__backend__"] is not None
    assert "__backend__" in Order.__dict__ and Order.__dict__["__backend__"] is not None
    print("User configured : True")
    print("Order configured: True")
    print("\n✓ Development environment configured correctly.")


# ---------------------------------------------------------------------------
# Demo 2: test environment (:memory: SQLite)
# ---------------------------------------------------------------------------

def demonstrate_test_env() -> None:
    """Test environment uses an in-memory SQLite -- fully isolated."""

    print("\n" + "=" * 60)
    print("DEMO 2 — Test environment (in-memory SQLite)")
    print("=" * 60)

    configure_models([User, Order], env="test")

    User.backend().execute(_USERS_DDL, options=_DDL_OPTS)
    Order.backend().execute(_ORDERS_DDL, options=_DDL_OPTS)

    # The in-memory DB is empty (new backend instance)
    users_before = User.query().all()
    print(f"\nUsers before inserts (fresh :memory: DB): {users_before}")
    assert users_before == [], "In-memory DB should be empty at start"

    User(name="Test-Bob", email="test-bob@example.com").save()
    users_after = User.query().all()
    print(f"Users after insert: {[u.name for u in users_after]}")
    assert len(users_after) == 1
    assert users_after[0].name == "Test-Bob"

    print("\n✓ Test environment is fully isolated from the development DB.")


# ---------------------------------------------------------------------------
# Demo 3: re-configuring with a fresh backend resets state
# ---------------------------------------------------------------------------

def demonstrate_fresh_backend_isolation() -> None:
    """Reconfiguring with a new :memory: backend simulates per-test isolation.

    In a pytest fixture this pattern provides a blank-slate DB for every test.
    """

    print("\n" + "=" * 60)
    print("DEMO 3 — Fresh backend per test session (pytest-style isolation)")
    print("=" * 60)

    def setup_session() -> None:
        """Simulate fixture setup: fresh in-memory DB."""
        configure_models([User, Order], env="test")
        User.backend().execute(_USERS_DDL, options=_DDL_OPTS)
        Order.backend().execute(_ORDERS_DDL, options=_DDL_OPTS)

    # --- Simulated test A ---
    setup_session()
    User(name="Session-A-User", email="a@example.com").save()
    users_a = User.query().all()
    print(f"\n[Session A] Users: {[u.name for u in users_a]}")
    assert [u.name for u in users_a] == ["Session-A-User"]

    # --- Simulated test B (new session = new backend = empty DB) ---
    setup_session()
    users_b_before = User.query().all()
    print(f"[Session B] Users before insert (should be empty): {users_b_before}")
    assert users_b_before == [], "New session should start with empty DB"

    User(name="Session-B-User", email="b@example.com").save()
    users_b_after = User.query().all()
    print(f"[Session B] Users after insert: {[u.name for u in users_b_after]}")
    assert [u.name for u in users_b_after] == ["Session-B-User"]

    print("\n✓ Each test session receives a fresh, isolated in-memory database.")


# ---------------------------------------------------------------------------
# Demo 4: environment variable drives configuration
# ---------------------------------------------------------------------------

def demonstrate_env_variable_switching() -> None:
    """APP_ENV controls which backend is selected."""

    print("\n" + "=" * 60)
    print("DEMO 4 — APP_ENV controls backend selection")
    print("=" * 60)

    for env_value in ("test", "development", "production"):
        backend = make_backend(env=env_value)
        backend_type = type(backend).__name__
        if hasattr(backend, '_config'):
            db_path = getattr(backend._config, 'database', 'unknown')
        else:
            db_path = 'unknown'
        print(f"  APP_ENV={env_value!r:<15} -> backend: {backend_type}, "
              f"database: {db_path!r}")

    print("\n✓ Factory function selects the correct backend for each environment.")


# ---------------------------------------------------------------------------
# Demo 5: all models in one place
# ---------------------------------------------------------------------------

def demonstrate_centralized_configure() -> None:
    """configure_models() configures every model in a single call.

    This prevents individual models from being accidentally omitted.
    """

    print("\n" + "=" * 60)
    print("DEMO 5 — Centralised configure_models() call")
    print("=" * 60)

    ALL_MODELS = [User, Order]
    configure_models(ALL_MODELS, env="test")

    for cls in ALL_MODELS:
        has_backend = "__backend__" in cls.__dict__ and cls.__dict__["__backend__"] is not None
        print(f"  {cls.__name__:<10} configured: {has_backend}")
        assert has_backend, f"{cls.__name__} must be configured"

    print("\n✓ All models configured via a single centralised call.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Configuration Management — Environment-Based Setup Patterns")
    print("=" * 60)

    demonstrate_development_env()
    demonstrate_test_env()
    demonstrate_fresh_backend_isolation()
    demonstrate_env_variable_switching()
    demonstrate_centralized_configure()

    print("\n" + "=" * 60)
    print("EXAMPLE SUMMARY")
    print("=" * 60)
    print("This example demonstrates:")
    print("1. make_backend(env) builds the correct backend for each environment.")
    print("   - test        -> :memory: SQLite (fully isolated)")
    print("   - development -> local file SQLite (fast iteration)")
    print("   - production  -> would use MySQL/PostgreSQL in real code")
    print("2. configure_models() configures all models in one place, preventing")
    print("   models from being accidentally omitted.")
    print("3. A fresh :memory: backend per test session resets state completely,")
    print("   mirroring the pytest fixture pattern described in the article.")
    print("4. APP_ENV drives the backend selection; no source code changes are")
    print("   needed when switching environments.")
