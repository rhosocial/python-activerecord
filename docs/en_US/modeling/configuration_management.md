# Configuration Management

Hard-coding database credentials and paths in source code makes it impossible to safely
deploy the same codebase to development, testing, and production environments.  This
guide applies [12-Factor App](https://12factor.net/config) principles to
`rhosocial-activerecord` configuration.

> 💡 **AI Prompt:** "How do I use a different database in development vs. production
> without changing my model code?"

---

## 1. The Three-Environment Pattern

| Environment | Typical backend | Purpose |
| --- | --- | --- |
| `development` | SQLite (local file) | Fast iteration, no external services |
| `test` | SQLite (`:memory:`) | Isolated, auto-reset per test run |
| `production` | MySQL / PostgreSQL | Real data, connection pool |

---

## 2. Reading Configuration from Environment Variables

Never store credentials in source code.  Read them from environment variables at
application startup:

```python
# config.py
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
APP_ENV      = os.environ.get("APP_ENV", "development")
```

### Using python-dotenv (recommended for local development)

```bash
# .env  (never commit to version control)
APP_ENV=development
DATABASE_URL=sqlite:///dev.db
```

```python
from dotenv import load_dotenv
load_dotenv()  # loads .env before reading os.environ
```

### Using pydantic-settings (recommended for larger projects)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "development"
    db_path: str = "dev.db"
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "myapp"
    db_user: str = "app"
    db_password: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 3. Environment-Specific Configuration Factory

Centralise all backend construction in one factory function:

```python
# config/database.py
import os
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

def make_backend():
    env = os.environ.get("APP_ENV", "development")

    if env == "test":
        # In-memory: fully isolated, reset between test sessions
        config = SQLiteConnectionConfig(database=":memory:")
        return SQLiteBackend(config)

    if env == "development":
        config = SQLiteConnectionConfig(database="dev.db")
        return SQLiteBackend(config)

    if env == "production":
        # Switch to MySQL/PostgreSQL backend in production
        from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, MySQLConnectionConfig
        config = MySQLConnectionConfig(
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT", 3306)),
            database=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            pool_size=int(os.environ.get("DB_POOL_SIZE", 5)),
        )
        return MySQLBackend(config)

    raise ValueError(f"Unknown APP_ENV: {env!r}")
```

---

## 4. Centralised Startup Configuration

Call `configure()` once in a single entry point so no model is ever missed:

```python
# app.py
from config.database import make_backend
from myapp.models import User, Order, Product

def configure_models():
    """Configure all models.  Call once at application startup."""
    backend = make_backend()
    for cls in [User, Order, Product]:
        cls.configure(backend=backend)

configure_models()
```

> ✅ A single list of model classes makes it easy to audit which models are registered
> and catch omissions during code review.

---

## 5. Test Environment Isolation

In tests, configure an in-memory SQLite backend per test session (or per test for
maximum isolation):

```python
# tests/conftest.py
import pytest
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from myapp.models import User, Order

@pytest.fixture(scope="session", autouse=True)
def configure_test_db():
    """Single in-memory DB shared across all tests in the session."""
    config = SQLiteConnectionConfig(database=":memory:")
    backend = SQLiteBackend(config)
    User.configure(backend=backend)
    Order.configure(backend=backend)
    # Create schema
    User.create_table()
    Order.create_table()
    yield
    # Teardown: nothing to do for :memory: -- it disappears with the process

@pytest.fixture(autouse=True)
def clean_tables():
    """Truncate tables between tests for isolation."""
    yield
    User.query().delete()
    Order.query().delete()
```

For complete isolation between tests, use a per-test `:memory:` database:

```python
@pytest.fixture
def fresh_db():
    """A brand-new in-memory DB for each test -- maximum isolation."""
    config = SQLiteConnectionConfig(database=":memory:")
    backend = SQLiteBackend(config)
    User.configure(backend=backend)
    User.create_table()
    yield backend
    # No explicit cleanup needed; :memory: is discarded after the test
```

---

## 6. Configuration Management Checklist

- [ ] No credentials or database paths hard-coded in source files
- [ ] `.env` file excluded from version control (`.gitignore`)
- [ ] `APP_ENV` variable controls which backend is created
- [ ] All `configure()` calls in a single startup function
- [ ] Tests use `:memory:` SQLite and reset state between runs
- [ ] Production secrets managed via environment variables or a secrets manager

---

## Runnable Example

See [`docs/examples/chapter_03_modeling/configuration_management.py`](../../../examples/chapter_03_modeling/configuration_management.py)
for a self-contained script that demonstrates all five patterns above.

---

## See Also

- [Thread Safety](concurrency.md) — when to call `configure()` in forking and async servers
- [Multiple Independent Connections](best_practices.md#8-multiple-independent-connections) — separate backends for different model classes
