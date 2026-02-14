# rhosocial-activerecord Documentation

> 🤖 **AI Learning Assistant**: Throughout this documentation, you'll find AI Prompt markers (💡) next to complex concepts. Feel free to ask your AI assistant to explain anything you don't understand.
>
> **Example:** "What is Expression-Dialect separation and why is it important?"
>
> 📖 **For detailed usage:** See [AI-Assisted Development Guide](introduction/ai_assistance.md)

## Table of Contents

1.  **[Introduction](introduction/README.md)**
    *   **[AI-Assisted Development](introduction/ai_assistance.md)**: Built-in AI configurations and how to use code agents to accelerate your workflow.
    *   **[Glossary](introduction/glossary.md)**: Key terms and concepts explained from scratch.
    *   **[Coming from Other Frameworks](introduction/coming_from_frameworks.md)**: If you know Django, SQLAlchemy, Rails, or others.
    *   **[Philosophy](introduction/philosophy.md)**: The "Gradual ORM" approach — balancing strict Type Safety (OLTP) with Raw Performance (OLAP).
    *   **[Key Features](introduction/key_features.md)**:
        *   Pydantic V2 Integration
        *   Composable Mixins (UUID, Timestamp, Optimistic Locking)
        *   **[Sync-Async Parity](introduction/key_features.md#sync-async-parity)**: Equivalent functionality across synchronous and asynchronous implementations 💡 *AI Prompt: "Why does this project enforce identical method names for sync and async APIs?"*
        *   Zero-IO Testing Strategy
    *   **[Technical Decision Guide](introduction/comparison.md)**: Which ORM to choose? Scenario-based comparison with SQLAlchemy, Django, SQLModel, and others.
    *   **[Architecture](introduction/architecture.md)**: Understanding the layered design (Interface -> Active Record -> Dialect -> Expression -> Backend). 💡 *AI Prompt: "Explain the layered architecture and why Expression-Dialect separation matters."*

2.  **[Getting Started](getting_started/README.md)**
    *   **[Installation](getting_started/installation.md)**: Requirements (Python 3.8+, Pydantic V2) and pip installation.
    *   **[Configuration](getting_started/configuration.md)**: Setting up SQLite and managing shared backend connections.
    *   **[Quick Start](getting_started/quick_start.md)**: A complete "Hello World" example defining User/Post models and performing CRUD.
    *   **[First CRUD App](getting_started/first_crud.md)**: Build a complete Todo application from scratch, learning Create, Read, Update, Delete operations step by step.
    *   **[Troubleshooting](getting_started/troubleshooting.md)**: Running into issues? Common errors and their solutions (No backend configured, FieldProxy missing, PYTHONPATH issues, etc.).

3.  **[Modeling Data](modeling/README.md)**
    *   **[Fields & Proxies](modeling/fields.md)**: Field definition, `FieldProxy`, and mapping legacy columns. 💡 *AI Prompt: "What is FieldProxy and how does it enable type-safe query building?"*
    *   **[Mixins](modeling/mixins.md)**: Reusable logic with built-in (`UUID`, `Timestamp`) and custom Mixins.
    *   **[Validation & Hooks](modeling/validation.md)**: Pydantic validation and lifecycle hooks.
    *   **[Custom Types](modeling/custom_types.md)**: Handling complex data types like JSON and arrays.

4.  **[Relationships](relationships/README.md)**
    *   **[Definitions](relationships/definitions.md)**: Defining `HasOne`, `BelongsTo`, `HasMany`.
    *   **[Many-to-Many](relationships/many_to_many.md)**: Implementing complex N:M relations via Through Models.
    *   **[Loading Strategies](relationships/loading.md)**: Solving N+1 problems with eager loading vs lazy loading.

5.  **[Querying Interface](querying/README.md)**
    *   **[ActiveQuery (Model Query)](querying/active_query.md)**: Filtering, sorting, joins, aggregation, eager loading.
    *   **[CTEQuery (Common Table Expressions)](querying/cte_query.md)**: Recursive and analytical queries.
    *   **[SetOperationQuery (Set Operations)](querying/set_operation_query.md)**: UNION, INTERSECT, EXCEPT.
    *   **[Query Cheatsheet](querying/cheatsheet.md)**: Quick reference for common query patterns.

6.  **[Performance](performance/README.md)**
    *   **[Strict vs Raw Modes](performance/modes.md)**: When to use `.aggregate()` to bypass Pydantic overhead.
    *   **[Concurrency Control](performance/concurrency.md)**: Handling race conditions with Optimistic Locking.
    *   **[Caching](performance/caching.md)**: Understanding internal caching to avoid redundant work.

7.  **[Events](events/README.md)**
    *   **[Lifecycle Events](events/lifecycle.md)**: Hooks for Decoupling business logic (before_save, after_create, etc.).

8.  **[Serialization](serialization/README.md)**
    *   **[JSON Serialization](serialization/json.md)**: Converting models to JSON/Dicts, field filtering.

9.  **[Backend System](backend/README.md)**
    *   **[Expression System](backend/expression/README.md)**: How Python objects are safely transformed into SQL strings. 💡 *AI Prompt: "Explain ToSQLProtocol and how Expression-Dialect separation prevents SQL injection."*
    *   **[Custom Backend](backend/custom_backend.md)**: Implementing a new database driver.

10. **[Testing](testing/README.md)**
    *   **[Strategies](testing/strategies.md)**: Zero-IO Testing vs Integration Testing.
    *   **[Dummy Backend](testing/dummy.md)**: Using the dummy backend for unit tests.

11. **[Scenarios](scenarios/README.md)**
    *   **[FastAPI Integration](scenarios/fastapi.md)**: Async support, dependency injection, and Pydantic model reuse.
    *   **[GraphQL Integration](scenarios/graphql.md)**: Solving N+1 problems with DataLoaders.
