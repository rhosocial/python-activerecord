# Philosophy

The design of `rhosocial-activerecord` is not just about providing a tool to manipulate databases; it is about establishing a rigorous, efficient, and flexible paradigm for data interaction in modern Python application development.

## Why We Built This

Before diving into the technical details, let's answer the fundamental question: **Why create another ORM when SQLAlchemy and Django already exist?**

### 1. ActiveRecord Pattern Is Intuitive

The ActiveRecord pattern—where a class represents a database table and an instance represents a row—is fundamentally intuitive:

```python
user = User(name="Alice")  # Create an instance (represents a row)
user.save()                # Persist to database
user.name = "Bob"          # Modify attributes
user.save()                # Update in database
```

This maps directly to how developers think about data: "I have a user, I save the user, I modify the user, I save again." The mental model is simple and consistent.

#### Historical Context: From Fowler to Rails to Us

The ActiveRecord pattern was first formally described by **Martin Fowler** in his 2003 book *Patterns of Enterprise Application Architecture*. Fowler's original vision was elegant in its simplicity:

> "An object that wraps a row in a database table or view, encapsulates the database access, and adds domain logic on that data."

**Key characteristics of Fowler's original ActiveRecord:**
- Single class handles both data access and domain logic
- Instance variables map directly to database columns
- Standard CRUD operations (create, read, update, delete) are built-in
- Simple, direct, and easy to understand

**Rails (2004) popularized ActiveRecord** but added its own conventions:
- Convention over configuration (pluralization, foreign key naming)
- Rich callback system (before_save, after_create, etc.)
- Query building through method chaining
- Tight integration with the Rails framework

**Yii2 (2014) brought ActiveRecord to PHP** with similar patterns but added:
- Relational data lazy loading
- Database-agnostic query building
- Validation rules integrated into the model

#### Our Improvements: Modern ActiveRecord for Python

We stand on the shoulders of these giants, but we've made significant improvements for the modern Python ecosystem:

**1. Type Safety Through Pydantic V2**
- Rails uses dynamic typing; we leverage Python's type hints
- FieldProxy provides compile-time safety that Ruby cannot match
- IDE autocompletion and refactoring support out of the box

**2. True Sync-Async Parity**
- Rails added async support late (Rails 7+); we designed for it from day one
- Same API surface for sync and async—no cognitive overhead
- Native async implementation, not greenlet-based wrappers

**3. Framework Independence**
- Rails ActiveRecord is tightly coupled to Rails
- Yii2 ActiveRecord requires Yii2 framework
- **We work everywhere**: Flask, FastAPI, Django, scripts, Jupyter, CLI tools

**4. SQL Transparency**
- Rails' query building can be opaque (magic scopes, complex joins)
- All expressions and queries based on expressions can call `.to_sql()` at any time for debugging
- Expression-Dialect separation makes SQL generation understandable

**5. Expression-Dialect Architecture with Backend Protocol**

Unlike Rails and Yii2, which tightly couple query building to their ORM layers, we implement a **clean separation of concerns**:

- **Expression System**: Defines *what* you want (e.g., `User.c.age > 18`)
- **Dialect**: Handles *how* to generate SQL for different databases
- **Backend Protocol**: Manages database connections and execution

**This architecture enables:**

**a) Cross-Backend Compatibility at the ActiveRecord Level**
```python
# Same model, different backends - just change the configuration
User.configure(sqlite_config, SQLiteBackend)   # SQLite
User.configure(mysql_config, MySQLBackend)     # MySQL  
User.configure(postgres_config, PostgresBackend)  # PostgreSQL
```

**b) Backend Extensibility**
Adding support for a new database (Oracle, SQL Server, etc.) only requires:
1. Implementing a new `Dialect` subclass for SQL generation
2. Implementing a new `Backend` subclass for connection management
3. No changes to ActiveRecord, Query builders, or Expressions

**c) Direct Expression Usage (Bypassing ActiveRecord)**
Advanced users can use Expressions and Backend directly without ActiveRecord:

```python
from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

# Create expression directly
col = Column("users", "age")
expr = col > Literal(18)

# Generate SQL via Dialect
sql, params = expr.to_sql(backend.dialect)
# SQL: "users"."age" > ?
# params: (18,)

# Execute via Backend directly (no ActiveRecord needed)
backend.execute(sql, params)
```

**d) Framework Flexibility - Build Your Own ORM**
The Expression-Dialect-Backend stack is completely independent. You can:
- Use it to build a **Data Mapper** pattern ORM instead of ActiveRecord
- Create a **Repository** pattern with custom query builders
- Implement **CQRS** (Command Query Responsibility Segregation) with different read/write models
- Build **GraphQL resolvers** that translate to optimized SQL expressions

```python
# Example: Building a custom Repository pattern
class UserRepository:
    def __init__(self, backend):
        self.backend = backend
    
    def find_active(self, min_age: int):
        # Use Expression system directly
        expr = (User.c.active == True) & (User.c.age >= min_age)
        sql, params = expr.to_sql(self.backend.dialect)
        return self.backend.execute(sql, params)
```

**Rails and Yii2 don't offer this level of architectural flexibility.** Their query builders are tightly coupled to their ActiveRecord implementations.

> 💡 **AI Prompt:** "Compare the ActiveRecord pattern with Data Mapper pattern. What are the trade-offs in terms of simplicity vs. flexibility?"

**6. AI-Native Design**
- Built-in support for AI code agents (Claude Code, OpenCode, Cursor)
- Skills and commands for automated code generation
- Context files that help AI understand the codebase

### 2. Python Lacks a Mature ActiveRecord Ecosystem

While Python has excellent ORMs, there's a gap in the ecosystem:

*   **SQLAlchemy** follows the Data Mapper pattern with a complex, multi-layered architecture (Core + ORM). It's powerful but has a steep learning curve. It is **not** an ActiveRecord implementation.
*   **Django ORM** is tightly coupled to the Django web framework. You cannot use it in a standalone script, a FastAPI application, or a data processing pipeline without dragging in the entire Django ecosystem.
*   **Peewee** and **Pony ORM** exist but lack comprehensive feature sets, async support, or active maintenance for modern Python versions.

**Python needed a standalone, feature-complete, modern ActiveRecord implementation.**

### 3. Not a Wrapper—A Ground-Up Implementation

Unlike projects that wrap SQLAlchemy, **rhosocial-activerecord is built from scratch** with only Pydantic as a dependency:

```
Your Code → rhosocial-activerecord → Database Driver → Database
     ↑
     └── No SQLAlchemy underneath
     └── No Django dependencies
     └── Just Pydantic for validation
```

This means:
- **Zero hidden complexity** — You control every layer
- **Complete SQL transparency** — Both expressions and queries can call `.to_sql()` to inspect generated SQL
- **Smaller footprint** — Only one external dependency
- **Simpler mental model** — One layer to understand, not three

> 💡 **AI Prompt:** "What are the advantages and disadvantages of building an ORM from scratch versus wrapping an existing one like SQLAlchemy?"

### 4. Framework-Agnostic by Design

We deliberately **avoid coupling to any web framework**:

| | rhosocial-activerecord | Django ORM |
|---|---|---|
| **Dependencies** | Pydantic only | Django framework |
| **Use in Flask** | ✅ Yes | ❌ No (requires Django) |
| **Use in FastAPI** | ✅ Yes | ❌ No (requires Django) |
| **Use in scripts** | ✅ Yes | ❌ No (requires Django) |
| **Use in Jupyter** | ✅ Yes | ⚠️ Difficult (settings required) |

Our goal is to provide a **universal ActiveRecord solution** for all Python applications—web frameworks, CLI tools, data pipelines, Jupyter notebooks, and more.

### 5. A Complete ActiveRecord Ecosystem

We're not just building an ORM; we're building a **complete ActiveRecord ecosystem**:

- ✅ **Query builders** — ActiveQuery, CTEQuery, SetOperationQuery
- ✅ **Relationships** — BelongsTo, HasOne, HasMany with eager loading
- ✅ **Enterprise features** — Optimistic locking, soft delete, timestamps, UUIDs
- ✅ **Async support** — True sync-async parity, not wrappers
- ✅ **Multiple backends** — SQLite (built-in), MySQL, PostgreSQL (planned)
- ✅ **AI-native design** — Built-in support for AI code agents

**Our mission:** Make ActiveRecord the go-to pattern for Python data persistence, accessible to everyone regardless of their framework choices.

---

Our core design philosophy is reflected in the following six main aspects:

## 1. Explicit Control Over Implicit Magic

Our framework emphasizes explicit control over implicit behaviors. All database operations are clearly visible and controllable by the user:
- No automatic flushing or hidden database operations
- No complex object state management with multiple transitions
- No hidden caching mechanisms that users cannot control
- Unlike systems with automatic session management, our approach gives users complete visibility into when database operations occur

## 2. Layered Architecture: Backend and ActiveRecord

Traditional ORMs often tightly couple database connection management with model definitions. We explicitly distinguish between **Backend** and **ActiveRecord** in our design.

*   **Backend**: Responsible for low-level database connections, SQL execution, and dialect handling. It is a completely independent component that does not rely on any model definitions.
*   **ActiveRecord**: It is a "user" of the Backend. ActiveRecord utilizes the capabilities provided by the Backend to perform data persistence and querying.

This separation means that the **Backend can work completely independently**. You can use the Backend directly to execute raw SQL, manage transactions, or build custom data access layers without defining any Models. ActiveRecord is simply a high-level abstraction built upon this solid foundation.

Furthermore, **the Backend itself provides a powerful "Expression-Dialect" system**. This design allows us to easily extend support for mainstream relational databases. Currently, we provide the latest support for **SQLite3**, and plan to or already provide extensions for the following, committed to offering users a consistent development experience across different databases:

*   **MySQL**
*   **PostgreSQL**
*   **Oracle** (Planned)
*   **SQL Server** (Planned)
*   **MariaDB** (Planned)

> **Note**: Different database backends may have varying levels of feature support (e.g., MySQL only supports window functions starting from version 8.0). Please refer to the specific backend's release notes and documentation.

## 3. Sync-Async Parity: Equivalent Functionality Across Paradigms

A fundamental design principle of `rhosocial-activerecord` is **Sync-Async Parity**, meaning that synchronous and asynchronous implementations provide equivalent functionality and consistent APIs.

*   **Method Signature Consistency**: Synchronous methods like `save()`, `delete()`, `all()`, `one()` have direct asynchronous counterparts like `async def save()`, `async def delete()`, `async def all()`, `async def one()`.
*   **Interface Equivalence**: Both `ActiveRecord` and `AsyncActiveRecord` implement equivalent interfaces (`IActiveRecord` and `IAsyncActiveRecord` respectively), ensuring that the same operations are available in both paradigms.
*   **Query Builder Parity**: `ActiveQuery` and `AsyncActiveQuery` provide identical query building capabilities with the same method chains and options, differing only in execution (synchronous vs. asynchronous).
*   **Feature Completeness**: Every feature available in the synchronous version is also available in the asynchronous version, including relationships, validations, events, and complex queries.

This parity allows developers to seamlessly transition between synchronous and asynchronous contexts without learning different APIs or sacrificing functionality.

## 4. Strict Model-Backend Correspondence and Sync/Async Isolation

We adhere to the **"One Model - One Backend - One Table"** design principle:

*   **Strict One-to-One Correspondence**: A model class corresponds to a specific backend instance, which in turn corresponds to a single table (or view) in the database.
*   **Strict Isolation of Sync and Async**:
    *   **Distinct Models**: Synchronous models (inheriting from `ActiveRecord`) and asynchronous models (inheriting from `AsyncActiveRecord`) are treated as completely different model entities.
    *   **No Mixing**: You cannot define a relationship in a synchronous model that points to an asynchronous model, and vice versa. Synchronous `ActiveQuery` and `CTEQuery` can only be used with synchronous models; asynchronous query builders can only be used with asynchronous models. This isolation ensures predictable runtime behavior and avoids the complexity and potential deadlock risks associated with async/await context switching.

## 5. Type Safety and Data Validation

We deeply understand the critical impact of good paradigms on system stability and development efficiency. Therefore, in the design of the data model layer, we made a key decision:

**Let ActiveRecord inherit directly from `pydantic.BaseModel` (Pydantic V2).**

We chose not to implement our own validation system for simple reasons:
*   **Maturity**: Pydantic is the de facto standard for data validation in the Python ecosystem, being extremely mature and powerful.
*   **Cost**: Implementing a validation system from scratch that matches Pydantic's level would be prohibitively expensive and prone to bugs.
*   **Ecosystem**: It allows direct integration with Pydantic's vast ecosystem (e.g., FastAPI integration, IDE intellisense).

Through this inheritance, every ActiveRecord model is essentially a Pydantic model, possessing powerful runtime type checking and data validation capabilities, ensuring the absolute purity of data entering the database.

## 6. Powerful Query System

ActiveRecord is not just about data models; it is paired with a powerful query system, primarily including:

*   **ActiveQuery**: The standard query builder.
*   **CTEQuery**: Common Table Expressions query.
*   **SetOperationQuery**: Set operation query (e.g., Union, Intersect).

**The core mission of ActiveQuery is to instantiate ActiveRecord instances (lists).** When you execute `User.query().where(...)`, it defaults to returning a list of fully validated `User` objects.

At the same time, to meet the needs of performance-sensitive scenarios, `ActiveQuery`, consistent with `CTEQuery` and `SetOperationQuery`, provides **`aggregate()`** functionality. This allows you to skip model instantiation when needed and directly retrieve aggregated data or raw dictionary results, achieving a perfect balance between flexibility and performance.
