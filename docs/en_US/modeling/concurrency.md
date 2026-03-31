# Thread Safety and Concurrent Configuration

In multi-threaded environments -- web servers, background workers, async frameworks --
incorrect connection management is one of the most common sources of subtle data
corruption and hard-to-reproduce bugs.  This guide covers what you need to know to
configure models safely.

> 💡 **AI Prompt:** "My Flask/FastAPI app behaves strangely under load -- queries seem
> to return wrong results or fail intermittently.  Could this be a connection issue?"

---

## 1. Configure Once at Application Startup

`configure()` is a **class-level** operation.  It assigns a backend instance that is
shared by every instance of that model class.  Call it exactly once, before any request
or worker thread starts.

```python
# ✅ Correct: configure at application startup
# app.py / main.py
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from myapp.models import User, Order, Product

def create_app():
    config = SQLiteConnectionConfig(database="app.db")
    User.configure(config, SQLiteBackend)
    Order.configure(config, SQLiteBackend)   # shared backend -- same connection pool
    # ... other setup ...
    return app
```

```python
# ❌ Wrong: configure inside a request handler
@app.get("/users")
def list_users():
    User.configure(config, SQLiteBackend)   # called on every request!
    return User.query().all()
```

**Why it matters**: calling `configure()` inside a request handler replaces the shared
backend on every request.  Under concurrent load, one request may overwrite another's
backend mid-query, causing data to be read from or written to the wrong database.

---

## 2. SQLite and Thread Safety

SQLite's default connection mode (`check_same_thread=True`) allows only one thread to
use a connection.  The built-in `SQLiteBackend` handles this, but there are important
constraints to keep in mind.

### Single-threaded servers (development)

A single in-process `SQLiteBackend` is safe for single-threaded servers such as Flask's
built-in dev server:

```python
# Single-threaded development server -- one connection, one thread
config = SQLiteConnectionConfig(database="dev.db")
User.configure(config, SQLiteBackend)
```

### Multi-threaded servers (production)

For multi-threaded WSGI servers (Gunicorn with sync workers, uWSGI), each thread must
have its own connection.  The simplest approach is to configure per-process in a
post-fork hook:

```python
# gunicorn.conf.py
def post_fork(server, worker):
    """Called in each worker process after forking."""
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
    from myapp.models import Base  # your base model or all model classes

    config = SQLiteConnectionConfig(database="app.db")
    Base.configure(config, SQLiteBackend)
```

> ⚠️ **Do NOT configure before forking**: if you call `configure()` in the master
> process and then fork, all workers share the same connection object.  This is
> unsafe and will cause `check_same_thread` errors or silent data corruption.

### Async servers (ASGI)

For ASGI servers (Uvicorn, Hypercorn) running coroutines, the event loop runs in a
single thread, so a single backend is generally safe:

```python
# FastAPI startup event
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Configure on startup
    config = SQLiteConnectionConfig(database="app.db")
    User.configure(config, SQLiteBackend)
    yield
    # Cleanup on shutdown (if needed)

app = FastAPI(lifespan=lifespan)
```

---

## 3. MySQL / PostgreSQL Backends

For server-based databases, the backend uses a connection pool.  Key parameters:

```python
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, MySQLConnectionConfig

config = MySQLConnectionConfig(
    host="db.example.com",
    port=3306,
    database="myapp",
    user="app",
    password="...",
    pool_size=5,          # connections per worker process
    pool_timeout=30,      # seconds to wait for a free connection
    pool_recycle=3600,    # recycle connections after 1 hour
)
User.configure(config, MySQLBackend)
```

**Pool sizing rule of thumb**:

```text
pool_size = (CPU cores per worker) × 2  +  1
```

For a 4-core machine running 4 Gunicorn workers, start with `pool_size=9` per worker.
Adjust based on observed wait times.

---

## 4. Detecting Misconfigured Models at Startup

Add an explicit check after all `configure()` calls to catch missing configurations
before any request is served:

```python
REQUIRED_MODELS = [User, Order, Product, UserMetric]

def assert_all_configured():
    unconfigured = [
        cls.__name__
        for cls in REQUIRED_MODELS
        if "__backend__" not in cls.__dict__ or cls.__dict__["__backend__"] is None
    ]
    if unconfigured:
        raise RuntimeError(
            f"Models not configured: {', '.join(unconfigured)}.  "
            "Call configure() for each model before starting the server."
        )

# Call in application factory, before returning the app
assert_all_configured()
```

---

## 5. Thread Safety Checklist

- [ ] `configure()` called once at application startup, not inside request handlers
- [ ] For forking servers (Gunicorn sync workers): configure in `post_fork` hook, not before fork
- [ ] For async servers (Uvicorn): configure in `lifespan` startup event
- [ ] SQLite: one backend per process/thread -- avoid sharing connections across threads
- [ ] MySQL/PostgreSQL: `pool_size` tuned to match worker concurrency
- [ ] Startup assertion verifies all required models are configured

---

## Runnable Example

See [`docs/examples/chapter_03_modeling/concurrency.py`](../../../examples/chapter_03_modeling/concurrency.py)
for a self-contained script that demonstrates all four patterns above.

---

## See Also

- [Multiple Independent Connections](best_practices.md#8-multiple-independent-connections) — patterns for models sharing field definitions but using different databases
- [Configuration Management](configuration_management.md) — environment-based config (dev / test / prod)
- [Concurrency & Optimistic Locking](../performance/concurrency.md) — handling concurrent writes with `OptimisticLockMixin`
