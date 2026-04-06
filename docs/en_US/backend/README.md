# 10. Backend System

This is an advanced topic for users who want to understand the internal workings of the ORM or need to support a new database.

## Backend Ecosystem

The design intent of `rhosocial-activerecord` is to support multiple database backends. In addition to the SQLite implementation included in the core library, we also provide or plan to provide the following independent backend packages:

* `rhosocial-activerecord-mysql`
* `rhosocial-activerecord-postgres`
* `rhosocial-activerecord-oracle` (Planned)
* `rhosocial-activerecord-sqlserver` (Planned)
* `rhosocial-activerecord-mariadb` (Planned)

These independent packages can also serve as examples for you to develop custom third-party backends.

## Sync and Async Parity

The SQLite backend included in the core library provides both **synchronous** and **asynchronous** implementations with complete API parity:

- **Sync API**: `SQLiteBackend` — uses the standard `sqlite3` module (built-in)
- **Async API**: `AsyncSQLiteBackend` — requires the `aiosqlite` package

Both implementations share identical method signatures, return types, and behavior, making it easy to switch between sync and async modes when needed.

### Async SQLite Dependencies

The asynchronous SQLite backend requires `aiosqlite` as an additional dependency. Since it's not included in the core dependencies, you need to install it manually:

```bash
pip install aiosqlite
```

Or install the complete package with all optional dependencies:

```bash
pip install rhosocial-activerecord[all]
```

## Contents

* **[Connection Pool](connection_pool.md)**: Efficient connection management with context awareness.
* **[Database Introspection](introspection.md)**: Query database structure metadata.
* **[Query Explain Interface](explain.md)**: Execute EXPLAIN statements and analyse query plans and index usage.
* **[Expression System](expression/README.md)**: How Python objects are transformed into SQL strings.
* **[Custom Backend](custom_backend.md)**: Implementing a new database driver.
* **[SQLite Backend](sqlite/README.md)**: SQLite-specific features and capabilities.
  * **[Pragma System](sqlite/pragma.md)**: SQLite PRAGMA configuration and inspection.
  * **[Extension Framework](sqlite/extension.md)**: Extension detection and management.
  * **[Full-Text Search (FTS5)](sqlite/fts5.md)**: FTS5 full-text search capabilities.

## Example Code

Full example code for this chapter can be found at `docs/examples/chapter_10_backend/`.
