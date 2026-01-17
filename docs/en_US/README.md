# rhosocial-activerecord Documentation

## Table of Contents

1.  **[Introduction](introduction/README.md)**
    *   **[Philosophy](introduction/philosophy.md)**: The "Gradual ORM" approach — balancing strict Type Safety (OLTP) with Raw Performance (OLAP).
    *   **[Key Features](introduction/key_features.md)**:
        *   Pydantic V2 Integration
        *   Composable Mixins (UUID, Timestamp, Optimistic Locking)
        *   Zero-IO Testing Strategy
    *   **[Comparison](introduction/comparison.md)**: Detailed analysis vs SQLModel, SQLAlchemy, Peewee, and Django ORM.
    *   **[Architecture](introduction/architecture.md)**: Understanding the layered design (Interface -> Active Record -> Dialect -> Expression -> Backend).

2.  **[Getting Started](getting_started/README.md)**
    *   **[Installation](getting_started/installation.md)**: Requirements (Python 3.8+, Pydantic V2) and pip installation.
    *   **[Configuration](getting_started/configuration.md)**: Setting up SQLite and managing shared backend connections.
    *   **[Quick Start](getting_started/quick_start.md)**: A complete "Hello World" example defining User/Post models and performing CRUD.

3.  **Modeling Data (The Safe Layer)**
    *   **The `ActiveRecord` Base Class**: The foundation of your domain models.
    *   **Field Definition**: Using Pydantic types for robust schema validation.
    *   **Mixins & Composition**:
        *   `UUIDMixin`: Handling UUID Primary Keys automatically.
        *   `TimestampMixin`: Managing `created_at` and `updated_at`.
        *   `OptimisticLockMixin`: Implementing concurrency control with versioning.
    *   **Validation Lifecycle**: Hooks for `before_save`, `after_save`, etc.
    *   **Advanced Field Configuration**:
        *   **Custom Column Names**: Mapping fields to legacy DB columns via `Annotated[T, UseColumn("col_name")]`.
        *   **Custom Adapters**: defining custom serialization logic via `Annotated[T, UseAdapter(AdapterClass)]`.
        *   **Field Proxy**: Using `ClassVar[FieldProxy]` (e.g., `User.c.name`) for type-safe query construction and aliasing.
    *   **Customizing Metadata**: Table names, indexes, and constraints.

4.  **Relationships & Associations**
    *   **Type-Safe Descriptors**: How `RelationDescriptor` ensures code intelligence.
    *   **Relationship Types**:
        *   `HasOne` / `BelongsTo` (1:1)
        *   `HasMany` (1:N)
        *   Many-to-Many (N:M) via Through Models
    *   **Loading Strategies**:
        *   Eager Loading with `with_()` (Solving N+1 problems).
        *   Lazy Loading (On-demand access).

5.  **Querying Interface**
    *   **ActiveQuery Architecture**: Understanding the Mixin-based design (`ActiveQuery` = `Base` + `Aggregate` + `Join` + ...).
    *   **Core Filtering (`BaseQueryMixin`)**:
        *   `select()`: Choosing specific columns.
        *   `where()`: Applying conditions.
        *   `distinct()`: Deduplicating results.
    *   **Aggregations (`AggregateQueryMixin`)**:
        *   Standard functions: `count()`, `sum()`, `avg()`, `min()`, `max()`.
        *   `aggregate()`: Running arbitrary aggregation expressions.
    *   **Joins (`JoinQueryMixin`)**:
        *   `join()`: Inner joins.
        *   `left_join()`, `cross_join()`: Other join types.
    *   **Ordering & Ranges (`RangeQueryMixin`)**:
        *   `order_by()`: Sorting results.
        *   `limit()`, `offset()`: Slicing result sets.
    *   **Relationships (`RelationalQueryMixin`)**:
        *   `with_()`: Eager loading related records.
    *   **Set Operations (`SetOperationQuery`)**:
        *   `union()`, `intersect()`, `except_()`: Combining query results.
    *   **Common Table Expressions (`CTEQuery`)**:
        *   `with_cte()`: Defining and using CTEs for complex queries.

6.  **Performance & Optimization (The Raw Layer)**
    *   **The "Gradual" Strategy**: When to switch modes.
    *   **Strict Mode**: Full Pydantic validation for high-integrity operations (User input, complex business logic).
    *   **Raw / Aggregate Mode**: Using `.aggregate()` to bypass Pydantic overhead for massive read operations (ETL, Reporting).
    *   **Caching**: Understanding the Column-to-Field Map cache.
    *   **Batch Operations**: Bulk Create and Update strategies.

7.  **The Backend Expression System**
    *   **The `ToSQL` Protocol**: How Python objects transform into SQL strings safely.
    *   **Expression Components**: Columns, Literals, Functions, Windows.
    *   **Dialect System**: How different databases (SQLite, Dummy) are supported.
    *   **Advanced SQL Construction**: Building CTEs (Common Table Expressions) and Recursive queries.
    *   **Implementing Custom Backends**:
        *   **Architecture**: Inheriting from `StorageBackend` and its Mixins (`ConnectionMixin`, `ExecutionMixin`, etc.).
        *   **Dialect Definition**: Subclassing `SQLDialectBase` for database-specific SQL generation.
        *   **Type Adapters**: Mapping Python types to database types.
        *   **Reference Implementation**: Using the `sqlite` backend as a template.

8.  **Testing & Reliability**
    *   **Zero-IO Testing**: The `DummyBackend` advantage.
    *   **Unit Testing Models**: Verifying logic without a database.
    *   **Integration Testing**: Using SQLite for full round-trip verification.
    *   **Test Patterns**: Best practices for maintainable test suites.

9.  **Integration & Real-World Scenarios**
    *   **FastAPI Integration**:
        *   **Pydantic Models as Schemas**: Using ActiveRecord models directly as `response_model` and request bodies.
        *   **Async Route Handlers**: Leveraging `await` for non-blocking database I/O.
        *   **Dependency Injection**: Managing sessions and transactions per request.
    *   **GraphQL Integration (Strawberry/Ariadne)**:
        *   **Resolvers**: Mapping GraphQL fields to `ActiveQuery` methods.
        *   **DataLoader Pattern**: Solving the N+1 problem using `in_` queries and batch loading.
    *   **Data Processing & ETL**:
        *   **Raw Mode**: Using `.aggregate()` for high-performance data export/transformation.
        *   **Bulk Operations**: Efficiently importing large datasets.
    *   **Serverless / FaaS**:
        *   **Cold Start Optimization**: Benefits of the lightweight backend initialization.

10. **Migration & Deployment**
    *   **Schema Management**: Syncing models with database tables.
    *   **Migration Strategies**: Handling schema evolution.
    *   **Production Readiness**: Configuration for high-load environments.

11. **API Reference**
    *   Complete API documentation for all classes and methods.

12. **Contributing**
    *   Setting up the development environment.
    *   Running the test suite.
    *   Writing documentation.
