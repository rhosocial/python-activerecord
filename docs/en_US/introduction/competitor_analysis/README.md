# Competitor Analysis

This section provides detailed comparisons between rhosocial-activerecord and mainstream Python ORM frameworks to help developers choose the right tool.

## Documents

- [Competitive Advantages Summary](./summary.md) — Quick selection guide
- [vs SQLAlchemy](./sqlalchemy.md) — Comparison with the Data Mapper pattern representative
- [vs Django ORM](./django_orm.md) — Comparison with framework-bound ORM
- [vs SQLModel](./sqlmodel.md) — Comparison with Pydantic+SQLAlchemy hybrid solution
- [vs Peewee](./peewee.md) — Comparison with lightweight ActiveRecord
- [vs Tortoise ORM](./tortoise_orm.md) — Comparison with async-first ORM
- [vs Prisma Client Python](./prisma.md) — Comparison with schema-first ORM

## Quick Comparison

| Framework | Design Pattern | Key Features | Use Cases | Latest Version |
|-----------|---------------|--------------|-----------|----------------|
| **SQLAlchemy** | Data Mapper | Enterprise-grade, feature-complete, steep learning curve | Large enterprise applications | 2.0.x |
| **Django ORM** | ActiveRecord | Tightly integrated with Django, mature and stable | Django projects | 6.0 / 5.2 LTS |
| **SQLModel** | Hybrid | Pydantic + SQLAlchemy | FastAPI + SQLAlchemy users | 0.0.x |
| **Peewee** | ActiveRecord | Lightweight, self-contained | Small projects | 4.x |
| **Tortoise ORM** | ActiveRecord | Async-first, Django-style | Pure async projects | 1.1.x |
| **Prisma Client Python** | Schema-first | Type-safe client generated from schema DDL | Schema-driven projects | — |
| **rhosocial-activerecord** | ActiveRecord | Native Pydantic, sync-async parity, multi-backend | Modern Python projects | 1.0.0.dev30 |

> Version information is as of 2026. All frameworks evolve continuously; refer to official releases.

## Core Advantages vs Each Competitor

rhosocial-activerecord differentiates itself on: **pure ActiveRecord (no Session) + native Pydantic type safety + true sync/async parity + a backend layer usable on its own**. Below are the concrete advantages relative to each competitor.

### vs SQLAlchemy

| Dimension | rhosocial-activerecord | SQLAlchemy |
|-----------|------------------------|------------|
| Mental model | Pure ActiveRecord, no Session | Data Mapper; requires Session/UoW/Identity Map |
| Operations | `user.save()` writes directly | `session.add()` + `session.commit()` |
| Type system | Native Pydantic, full type hints | Proprietary type system to learn |
| Async | Native; identical API to sync | 2.0 relies on greenlet wrappers |
| Architecture layers | Single abstraction (code → ORM → driver) | Three layers (ORM API → Core → driver) |

**Core advantage**: `save()`/`delete()` map directly to DB operations with no Session lifecycle to manage; Pydantic-based type safety and runtime validation out of the box; native sync/async parity (not greenlet); shallow call stack, predictable behavior.

### vs Django ORM

| Dimension | rhosocial-activerecord | Django ORM |
|-----------|------------------------|------------|
| Framework independence | Any Python project (FastAPI/Flask/scripts/Jupyter) | Django projects only |
| Async | Native, consistent API | Requires async views + `sync_to_async` |
| Type safety | Full Pydantic type system | Limited field typing (`Any`) |
| Query flexibility | FieldProxy expressions + CTEQuery/SetOperationQuery | QuerySet + Q objects, limited for complex queries |
| Migrations | Optional, integrate any tool | Built-in (but Django-bound) |

**Core advantage**: completely independent of any web framework — usable in FastAPI, Flask, scripts, and Jupyter; native async without `sync_to_async`; full IDE type hints from Pydantic; SQL transparency (`.to_sql()` anytime).

### vs SQLModel

| Dimension | rhosocial-activerecord | SQLModel |
|-----------|------------------------|----------|
| Pattern purity | Pure ActiveRecord, no Session | SQLAlchemy + Pydantic hybrid; Session still required |
| Architecture | Built from scratch, single abstraction | SQLAlchemy wrapper layer |
| Sync/async | Native parity, consistent API | Must distinguish Session/AsyncSession |
| Querying | Chained + type-safe FieldProxy | SQLAlchemy select style |

**Core advantage**: same Pydantic ecosystem, but no need to understand SQLAlchemy concepts or Session lifecycle; built from scratch avoids wrapper-layer hidden complexity; sync/async API fully consistent with no Session/AsyncSession split.

### vs Peewee

| Dimension | rhosocial-activerecord | Peewee |
|-----------|------------------------|--------|
| Type safety | Full Pydantic type hints + runtime validation | Field types are `Any`; no runtime validation |
| Async | Native parity | Needs `peewee-async` etc.; different API |
| SQL coverage | Expression/Dialect full coverage | Lightweight but limited SQL capability |
| Dependencies | Only Pydantic | Zero (self-contained) |

**Core advantage**: stays lightweight (a single Pydantic dependency) while providing full type safety, runtime validation, native async, and complete SQL coverage. Peewee's minimal dependencies are its strength, but at the cost of type safety and SQL expressiveness.

### vs Tortoise ORM

| Dimension | rhosocial-activerecord | Tortoise ORM |
|-----------|------------------------|--------------|
| Sync/async | Both first-class, fully consistent API | Async-first; sync is limited |
| Type safety | Full Pydantic type system | Limited field typing |
| SQL coverage | CTE/window functions/set ops fully supported | Complex queries usually fall back to raw SQL |
| Capability declaration | Backends explicitly declare `supports_*` | No unified capability mechanism |

**Core advantage**: true sync/async parity (Tortoise is async-first, sync is second-class); Pydantic type safety; CTE, window functions, and set operations out of the box without falling back to raw SQL.

### Common Cross-Cutting Advantages

Beyond the per-competitor points, rhosocial-activerecord keeps a consistent edge over all competitors on:

| Advantage | Description |
|-----------|-------------|
| **Pure ActiveRecord, no Session** | Simple mental model; `save()`/`delete()` map directly to DB operations |
| **Native Pydantic** | Inherits `BaseModel`; full type safety, runtime validation, seamless FastAPI integration |
| **Sync/async parity** | One API; identical method names, distinguished only by `await` |
| **Full SQL transparency** | Any expression/query can call `.to_sql()` to inspect generated SQL |
| **Backend usable on its own** | Backend layer can run without the ORM; custom backends supported |
| **Explicit capability declaration** | Backend protocols declare `supports_*`; tests skip unsupported features automatically |
| **Single dependency** | Only Pydantic; no ORM wrapper layer, no framework coupling |

> See each dedicated article in the [Documents](#documents) list for the full analysis.

## Backend Support

rhosocial-activerecord uses a core-library + separate-backend-package architecture. The following backends are available:

| Backend | Repository |
|---------|------------|
| SQLite | Built-in ([python-activerecord](https://github.com/rhosocial/python-activerecord)) |
| MySQL | [python-activerecord-mysql](https://github.com/rhosocial/python-activerecord-mysql) |
| PostgreSQL | [python-activerecord-postgres](https://github.com/rhosocial/python-activerecord-postgres) |
| MariaDB | [python-activerecord-mariadb](https://github.com/rhosocial/python-activerecord-mariadb) |
| Oracle | [python-activerecord-oracle](https://github.com/rhosocial/python-activerecord-oracle) |
| SQL Server | [python-activerecord-sqlserver](https://github.com/rhosocial/python-activerecord-sqlserver) |
| ClickHouse | [python-activerecord-clickhouse](https://github.com/rhosocial/python-activerecord-clickhouse) |
| Snowflake | [python-activerecord-snowflake](https://github.com/rhosocial/python-activerecord-snowflake) |
| BigQuery | [python-activerecord-bigquery](https://github.com/rhosocial/python-activerecord-bigquery) |
| Firebird | [python-activerecord-firebird](https://github.com/rhosocial/python-activerecord-firebird) |

> The level of support (features, versions, Python versions) for each backend depends on its own documentation.
