# Glossary

This glossary explains key terms and concepts used throughout the documentation.

## Core Concepts

### Active Record Pattern
A design pattern where a database table or view is wrapped into a class. Thus, an object instance is tied to a single row in the table. After creation of an object, a new row is added to the table upon save. Any object loaded gets its information from the database; when an object is updated, the corresponding row in the table is also updated.

**In rhosocial-activerecord:** Your model classes (like `User`, `Post`) inherit from `ActiveRecord` and automatically map to database tables.

> 💡 **AI Prompt:** "Explain the Active Record pattern and compare it with Repository pattern and Data Mapper pattern."

### Pydantic
A Python library for data validation using Python type hints. It ensures that data conforms to specified types and constraints at runtime.

**Key features:**
- Type-safe data validation
- JSON serialization/deserialization
- Automatic error messages
- IDE support through type hints

**Version requirements for this project:**
- Python 3.8/3.9: `pydantic>=2.10.6`
- Python 3.10+: `pydantic>=2.12`
- Supports Python 3.13/3.14 free-threaded builds

> 💡 **AI Prompt:** "What is Pydantic and how does it differ from traditional Python dataclasses or marshmallow?"

### ORM (Object-Relational Mapping)
A technique that lets you query and manipulate data from a database using an object-oriented paradigm instead of SQL.

**Why use an ORM?**
- Write database-agnostic code
- Work with objects instead of SQL strings
- Automatic data validation and type safety
- Easier to maintain and test

> 💡 **AI Prompt:** "What are the pros and cons of using an ORM versus writing raw SQL?"

## Architecture Terms

### Expression-Dialect Separation
Our core architectural principle where **what you want** (Expression) is separated from **how to generate SQL for it** (Dialect).

**Benefits:**
- Same Python code works with different databases
- SQL generation is transparent and testable
- Easy to add new database backends

> 💡 **AI Prompt:** "Explain Expression-Dialect separation and why it's better than string concatenation for SQL generation."

### FieldProxy
A type-safe way to reference model fields in queries. Instead of using string names (prone to typos), you use `User.c.username` which provides IDE autocomplete and type checking.

**Example:**
```python
# ❌ String-based (error-prone)
User.query().where("username == 'alice'")

# ✅ FieldProxy (type-safe)
User.query().where(User.c.username == "alice")
```

> 💡 **AI Prompt:** "How does FieldProxy enable type-safe query building in Python?"

### ToSQLProtocol
A protocol (interface) that all expression classes implement. It requires a `.to_sql()` method that returns the SQL string and parameters.

**Purpose:**
- Every query can show its generated SQL before execution
- Enables testing without database connections
- Makes SQL generation transparent

> 💡 **AI Prompt:** "What is a Protocol in Python and how does ToSQLProtocol enable transparent SQL generation?"

## Design Principles

### Sync-Async Parity
Our design principle that synchronous and asynchronous APIs should have:
- **Identical method names** (no `_async` suffixes)
- **Same functionality** (just add `await` for async)
- **Same code patterns**

**Why?** Makes it easy to convert sync code to async without learning new APIs.

> 💡 **AI Prompt:** "Why does this project enforce identical method names for sync and async APIs? What are the benefits?"

### Gradual ORM
Our philosophy that you should be able to use the ORM at different levels of abstraction:
- **High-level:** Full ActiveRecord objects with validation
- **Mid-level:** Query building with type safety
- **Low-level:** Raw SQL when needed for performance

You choose the level that fits your use case.

> 💡 **AI Prompt:** "What is a 'Gradual ORM' and how does it differ from traditional ORMs that force you into their patterns?"

## Database Terms

### Mixin
A class that provides methods and fields to other classes through inheritance. In our project, Mixins add common functionality like timestamps, UUIDs, or soft deletes.

**Example:**
```python
class Post(TimestampMixin, UUIDMixin, ActiveRecord):
    # Automatically gets created_at, updated_at, and UUID id
    title: str
```

> 💡 **AI Prompt:** "What is the Mixin pattern in Python and how does it enable code reuse?"

### Backend
The database-specific implementation that handles:
- Database connections
- SQL execution
- Transaction management
- Type adaptation

**Available backends:**
- SQLite (built-in)
- MySQL (separate package)
- PostgreSQL (separate package)

> 💡 **AI Prompt:** "What is the role of the Backend in this architecture and how does it enable database independence?"

### Dialect
A component that knows how to generate database-specific SQL syntax. Different databases have different:
- Parameter placeholder styles (`?` vs `$1` vs `:name`)
- Function names and syntax
- Pagination methods (LIMIT vs ROW_NUMBER)

> 💡 **AI Prompt:** "How does the Dialect component enable the same Python code to work with different databases?"

## Common Abbreviations

- **AR**: Active Record
- **ORM**: Object-Relational Mapping
- **API**: Application Programming Interface
- **SQL**: Structured Query Language
- **DB**: Database
- **CTE**: Common Table Expression (WITH clause)
- **CRUD**: Create, Read, Update, Delete
- **PK**: Primary Key
- **FK**: Foreign Key

## See Also

- [Coming from Other Frameworks](coming_from_frameworks.md) - If you're familiar with Django, SQLAlchemy, or Rails
- [AI-Assisted Development](ai_assistance.md) - How to use AI to explain these concepts
- [Architecture](architecture.md) - Deep dive into the system design
