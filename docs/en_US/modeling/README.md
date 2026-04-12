# Chapter 3: Modeling Data

Models are the core of `rhosocial-activerecord`. They not only define the data structure but also encapsulate business logic, validation rules, and query capabilities.

This chapter details how to define powerful data models.

## Core Concepts

1. **Powered by Pydantic**: Models are essentially Pydantic `BaseModel`s, giving you robust data validation and serialization capabilities.
2. **Active Record Pattern**: Each model class corresponds to a database table, and each instance corresponds to a row.
3. **Type Safety**: With `FieldProxy`, we achieve type-safe querying in Python, avoiding hardcoded strings.

## Chapter Contents

- **[Fields & Proxies](fields.md)**
  - How to define model fields
  - Using `FieldProxy` for type-safe queries
  - Mapping legacy database columns (`UseColumn`)
- **[DDL Statements](ddl.md)**
  - Type-safe CREATE TABLE, DROP TABLE, ALTER TABLE
  - Index creation and management
  - Foreign key relationships
- **[DDL Views](ddl_views.md)**
  - CREATE VIEW, DROP VIEW
  - View with column aliases and OR REPLACE
  - Introspection for views
- **[Mixins](mixins.md)**
  - Using built-in Mixins (`UUIDMixin`, `TimestampMixin`)
  - Creating custom Mixins for reusable logic
- **[Validation & Hooks](validation.md)**
  - Pydantic validators
  - Lifecycle hooks (`before_save`, `after_create`, etc.)
- **[Best Practices](best_practices.md)**
  - Naming conventions
  - Field design principles
  - Organizing models in large projects
  - Version control and migrations
  - Performance optimization: when to add indexes
  - Multiple independent connections (subclass inheritance vs. shared field mixin)
- **[Thread Safety](concurrency.md)**
  - When and how to call `configure()` in web servers
  - SQLite single-connection constraints and multi-worker setup
  - Connection pool sizing for MySQL / PostgreSQL
- **[Configuration Management](configuration_management.md)**
  - Environment-based configuration (dev / test / prod)
  - Reading credentials from environment variables
  - Test isolation with in-memory SQLite
- **[Read-Only Analytics Models](readonly_models.md)**
  - Defining read-only model classes for analytics / read replicas
  - Combining with the shared field mixin pattern
  - Derived / computed fields with `@property`
- **[Batch Data Processing](batch_processing.md)**
  - Chunked reading to avoid OOM
  - Bulk inserts and avoiding the N+1 write trap
  - Transaction strategy for large batch jobs

## Example Code

Full example code for this chapter can be found at:
[docs/examples/chapter_03_modeling/basic_models.py](../../../examples/chapter_03_modeling/basic_models.py)

Additional DDL examples:
- [docs/examples/chapter_03_modeling/ddl_basic.py](../../../examples/chapter_03_modeling/ddl_basic.py) — Basic DDL operations
- [docs/examples/chapter_03_modeling/ddl_relationships.py](../../../examples/chapter_03_modeling/ddl_relationships.py) — Tables with foreign keys
- [docs/examples/chapter_03_modeling/ddl_indexes.py](../../../examples/chapter_03_modeling/ddl_indexes.py) — Index management
- [docs/examples/chapter_03_modeling/ddl_views.py](../../../examples/chapter_03_modeling/ddl_views.py) — View creation and management
