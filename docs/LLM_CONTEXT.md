# LLM Context: rhosocial-activerecord

> **Purpose**: This document is a structured reference designed to be fed to Large Language Models (LLMs) as context. It provides the essential information an AI assistant needs to understand, use, and contribute to this project. For human-readable documentation, see the [README](../README.md) or the [docs/](en_US/) directory.

## Project Identity

- **Name**: rhosocial-activerecord
- **Type**: Standalone ActiveRecord ORM for Python
- **Core dependency**: Pydantic v2 (no SQLAlchemy, no Django)
- **Python**: 3.8+
- **License**: Apache 2.0
- **Status**: Development stage — APIs may change

## Key Design Principles

1. **Single dependency**: Only Pydantic. No ORM ecosystem underneath.
2. **Expression-Dialect separation**: Query logic (Expression) is decoupled from SQL generation (Dialect).
3. **Transparent SQL**: Every query object implements `.to_sql()` → `(sql_string, params)`.
4. **Sync-Async parity**: Sync and async APIs share the same method names and behavior.
5. **Type-first**: All public APIs use explicit type annotations. No `Any` in public interfaces.

## Module Map

```
rhosocial/activerecord/
├── __init__.py              # Public API: ActiveRecord, AsyncActiveRecord
├── model.py                 # ActiveRecord/AsyncActiveRecord entry point
├── base/
│   ├── base.py              # BaseActiveRecord/AsyncBaseActiveRecord
│   ├── async_base.py        # Async base class
│   ├── field_proxy.py       # FieldProxy — enables User.c.age >= 18 syntax
│   └── query_mixin.py       # QueryMixin — provides .query() method
├── query/
│   ├── active_query.py      # ActiveQuery/AsyncActiveQuery — main query builder
│   ├── cte_query.py         # CTEQuery/AsyncCTEQuery — WITH clauses
│   ├── set_operation.py     # SetOperationQuery/AsyncSetOperationQuery — UNION/INTERSECT/EXCEPT
│   ├── relational.py        # Eager loading via .with_()
│   └── aggregate.py         # Aggregate functions (COUNT, SUM, etc.)
├── relation/
│   ├── descriptors.py       # BelongsTo, HasOne, HasMany + async versions
│   ├── async_descriptors.py # AsyncBelongsTo, AsyncHasOne, AsyncHasMany
│   └── cache.py             # Relation caching
├── field/
│   ├── timestamp.py         # TimestampMixin — created_at/updated_at
│   ├── soft_delete.py       # SoftDeleteMixin — deleted_at
│   ├── version.py           # OptimisticLockMixin — version column
│   ├── uuid.py              # UUIDMixin — UUID primary keys
│   └── integer_pk.py        # IntegerPKMixin
├── backend/
│   ├── base/                # Backend base classes
│   ├── impl/
│   │   └── sqlite/          # SQLiteBackend/AsyncSQLiteBackend
│   ├── expression/          # SQL expression system
│   └── dialect.py           # Base dialect
└── interface/
    └── model.py             # IActiveRecord/IAsyncActiveRecord + ModelEvent
```

## Core Classes and Their Roles

### ActiveRecord (base/active_record.py)
The model base class. Inherits from Pydantic `BaseModel`.
- **Responsibilities**: Define table schema, CRUD operations (`.save()`, `.delete()`, `.find()`), configure backend.
- **Class methods**: `.configure(backend)`, `.query()`, `.find(pk)`, `.find_all()`, `.backend()`.
- **Instance methods**: `.save()`, `.delete()`, `.reload()`, `.to_dict()`.
- **Class variables**: `__table_name__`, `__primary_key__` (default: `"id"`).

### FieldProxy (base/field_proxy.py)
Enables type-safe, IDE-friendly query expressions.
- **Usage**: `User.c.age >= 18` returns a `ComparisonExpression`, not a boolean.
- **Pattern**: Declare as `c: ClassVar[FieldProxy] = FieldProxy()` on the model class.

### Query Types (query/)
Three core query builders with full sync/async parity:

**ActiveQuery/AsyncActiveQuery** (query/active_query.py)
- Model-based queries returned by `Model.query()`
- **Chaining**: `.where()`, `.order_by()`, `.limit()`, `.offset()`, `.join()`, `.with_()` (eager load)
- **Terminal**: `.all()`, `.one()`, `.count()`, `.exists()`, `.to_sql()`
- **Set operations**: `.union()`, `.intersect()`, `.except_()` → returns SetOperationQuery

**CTEQuery/AsyncCTEQuery** (query/cte_query.py)
- Common Table Expressions via `.as_cte()` or standalone
- For recursive queries and complex multi-step operations
- Returns dictionaries, not model instances

**SetOperationQuery/AsyncSetOperationQuery** (query/set_operation.py)
- UNION, INTERSECT, EXCEPT operations
- Created via `.union()`, `.intersect()`, `.except_()` on other queries

### Expression hierarchy (expression/)
All expressions implement `ToSQLProtocol` (i.e., they have `.to_sql(dialect) -> (str, list)`).
- `SQLColumn("users", "age")` — a column reference.
- `SQLLiteral(42)` — a bound parameter.
- `ComparisonExpression(left, op, right)` — e.g., `age >= 18`.
- `LogicalExpression(op, children)` — AND/OR/NOT combinator.
- `AggregateExpression(func, column)` — COUNT, SUM, etc.
- `WindowExpression`, `CTEExpression` — advanced SQL constructs.

### Dialect (dialect/)
Translates expressions into backend-specific SQL strings.
- Each dialect registers how to render each expression type.
- Adding a new backend = implementing a new Dialect subclass.

### Backend (backend/)
Manages the database connection and executes SQL.
- `SyncBackend`: `.execute(sql, params)`, `.transaction()`.
- `AsyncBackend`: `await .execute(sql, params)`, `async with .transaction()`.

### Field Mixins (field/)
Reusable mixins that add automatic fields and logic to models.
- `TimestampMixin` (field/timestamp.py): Adds `created_at`, `updated_at`; auto-set on save.
- `SoftDeleteMixin` (field/soft_delete.py): Adds `deleted_at`; `.delete()` sets timestamp instead of removing row.
- `OptimisticLockMixin` (field/version.py): Adds `version`; raises on concurrent update conflict.
- `UUIDMixin` (field/uuid.py): Generates UUID4 primary keys.
- `IntegerPKMixin` (field/integer_pk.py): Auto-increment integer primary key.

### Events (event/)
Model lifecycle hooks. Register via decorator or method override.
- Events: `before_validate`, `after_validate`, `before_save`, `after_save`, `before_delete`, `after_delete`.

## Common Patterns for Code Generation

### Define a model
```python
from rhosocial.activerecord import ActiveRecord
from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.base import FieldProxy

class User(ActiveRecord):
    __table_name__ = "users"
    name: str = Field(max_length=100)
    email: str
    age: int = 0
    c: ClassVar[FieldProxy] = FieldProxy()
```

### Configure and query
```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

# Configure with connection config
config = SQLiteConnectionConfig(database="app.db")
User.configure(config, SQLiteBackend)

# Type-safe query
users = User.query().where(User.c.age >= 18).order_by(User.c.name).all()

# Inspect SQL
sql, params = User.query().where(User.c.age >= 18).to_sql()
```

### Define relationships
```python
from typing import ClassVar
from rhosocial.activerecord.relation import HasMany, BelongsTo

class Author(ActiveRecord):
    __table_name__ = "authors"
    name: str
    c: ClassVar[FieldProxy] = FieldProxy()
    # Use ClassVar to prevent Pydantic from tracking as model fields
    posts: ClassVar[HasMany["Post"]] = HasMany(foreign_key="author_id")

class Post(ActiveRecord):
    __table_name__ = "posts"
    title: str
    author_id: int
    c: ClassVar[FieldProxy] = FieldProxy()
    author: ClassVar[BelongsTo["Author"]] = BelongsTo(foreign_key="author_id")
```

### Eager loading (avoid N+1)
```python
authors = Author.query().with_("posts").all()
```

### Async usage
```python
# Same API, just await
user = await User.query().where(User.c.email == "alice@example.com").one()
await user.save()
```

### Add field mixins
```python
from rhosocial.activerecord.field import TimestampMixin, SoftDeleteMixin

class Article(ActiveRecord, TimestampMixin, SoftDeleteMixin):
    __table_name__ = "articles"
    title: str
    body: str
    # Automatically has: created_at, updated_at, deleted_at
```

### Use CTEs
```python
cte = User.query().where(User.c.age >= 18).as_cte("adults")
result = cte.query().where(cte.c.name.like("A%")).all()
```

## Rules for Code Contributions

1. Every new public method must have type annotations on all parameters and return type.
2. Every sync method must have an async counterpart with the same name and identical behavior.
3. All query-related classes must implement `ToSQLProtocol`.
4. Tests must cover both sync and async paths.
5. No new runtime dependencies beyond Pydantic.

## File Naming Conventions

- Module files: `snake_case.py`
- Test files: `test_<module_name>.py`, mirroring the source tree under `tests/`
- One class per file for core classes; utility functions may share a file.

## Testing

```bash
# Run all tests
pytest

# Run specific feature tests
pytest tests/test_query/
pytest tests/test_expression/

# Run with coverage
pytest --cov=rhosocial.activerecord
```
