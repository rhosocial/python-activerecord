# Feature Comparison

| Feature | rhosocial ActiveRecord | SQLAlchemy | Django ORM | Peewee |
|---------|-------------------|------------|------------|--------|
| **Database Support** | SQLite, MySQL, PostgreSQL, MariaDB, Oracle, SQL Server | Extensive support for almost all SQL databases | SQLite, MySQL, PostgreSQL, Oracle | SQLite, MySQL, PostgreSQL |
| **Schema Definition** | Pydantic models with type validation | Declarative classes or explicit table definitions | Django model classes | Model classes with field definitions |
| **Migrations** | Basic support | Via Alembic (separate package) | Built-in with Django | Via playhouse extension |
| **Relationships** | Has-one, has-many, belongs-to with eager loading | Extensive relationship options with lazy/eager loading | ForeignKey, ManyToMany, OneToOne | ForeignKeyField, ManyToManyField |
| **Query Construction** | Fluent chainable API | Powerful expression language | QuerySet API | Model-based query methods |
| **Transactions** | ACID with isolation levels | ACID with isolation levels | Basic transaction support | Context manager-based transactions |
| **Type Validation** | Strong with Pydantic | Type hints for static analysis | Basic type checking | Basic field validation |
| **Async Support** | Native dual API (sync+async) | Yes (SQLAlchemy 1.4+) with different patterns | Limited (Django 3.1+) | Via peewee-async extension |
| **JSON Operations** | Native support | Comprehensive support | Basic support | Limited support |
| **Raw SQL Support** | Yes, with parameter safety | Yes, with parameter safety | Yes, with parameter safety | Yes, with raw() method |
| **Connection Pooling** | Yes | Yes | Yes | Limited |
| **Event System** | Comprehensive model lifecycle hooks | Extensive event listeners | Signal system | Basic hooks |
| **Pydantic Integration** | Native | Via extensions | Via third-party packages | Not supported natively |
| **SSL Connection Support** | Comprehensive, with certificate validation | Comprehensive, with full SSL option control | Basic support | Basic support |
| **Debugging Capabilities** | Extensive (SQL logging, parameter inspection, query timing) | Extensive (multiple logging levels, statistics) | Basic with third-party extensions | Limited |

## Aggregation Feature Comparison

| Aggregation Feature | rhosocial ActiveRecord | SQLAlchemy | Django ORM | Peewee |
|--------------------|-------------------|------------|------------|--------|
| **Scalar Queries** | Comprehensive support | Comprehensive support | Good support | Good support |
| **Aggregate Functions** | Full support (COUNT, SUM, AVG, etc. with DISTINCT) | Full support | Good support | Basic support |
| **Arithmetic Expressions** | Comprehensive support | Comprehensive support | Basic support | Limited support |
| **Window Functions** | Full support with complex frame specs | Full support | Limited support | Basic support |
| **CASE-WHEN Expressions** | Comprehensive support | Comprehensive support | Basic support | Limited support |
| **COALESCE/NULLIF Expressions** | Full support | Full support | Basic support | Basic support |
| **Subquery Expressions** | Comprehensive support | Comprehensive support | Limited support | Basic support |
| **JSON Expressions** | Cross-database abstraction | Database-specific implementation | Limited support | Minimal support |
| **Grouping Set Expressions** | Full support for CUBE, ROLLUP, GROUPING SETS | Full support | Limited support | No support |
| **CTE Queries** | Comprehensive support | Comprehensive support | Limited support | Limited support |
| **Advanced Aggregation** | Intuitive API | Powerful but complex API | Basic API | Limited API |

## Debugging Capabilities Comparison

| Debugging Feature | rhosocial ActiveRecord | SQLAlchemy | Django ORM | Peewee |
|-------------------|-------------------|------------|------------|--------|
| **SQL Statement Logging** | Built-in with format options | Comprehensive with multiple log levels | Via Django debug toolbar | Basic |
| **Parameter Binding Inspection** | Full parameter inspection | Comprehensive inspection | Limited | Basic |
| **Query Timing** | Built-in per-query timing | Via event system | Via Django debug toolbar | Manual implementation |
| **Query Profiling** | Built-in profiling tools | Via event listeners | Via third-party tools | Limited |
| **Explain Plan Access** | Built-in method | Via execution options | Via third-party tools | Basic method |
| **Connection Tracing** | Built-in connection tracking | Via event system | Limited | Not available |
| **Query Count Tracking** | Built-in statistics | Via event system | Via Django debug toolbar | Not available |
| **Memory Usage Analysis** | Basic tools | Limited | Via third-party tools | Not available |
| **SQL Formatting/Highlighting** | Yes | Yes | Via Django debug toolbar | No |