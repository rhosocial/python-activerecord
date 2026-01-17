# Architecture

The library is built on a layered architecture to ensure maintainability, testability, and flexibility.

## Component Relationships

The architecture is divided into three main parts: the Core Foundation, the Synchronous Implementation, and the Asynchronous Implementation.

> **About SQLite Async Backend**: Please note that the SQLite asynchronous backend implementation included in this library is primarily for testing purposes (verifying the validity of the async abstraction and its equivalence with the synchronous implementation) and is not recommended for use as a high-performance asynchronous solution in production environments. For production asynchronous needs, please use dedicated backend packages such as `rhosocial-activerecord-mysql` or `rhosocial-activerecord-postgres`.

### 1. Core Foundation (`ActiveRecordBase`)

The `ActiveRecordBase` serves as the common ancestor for all models. It bridges the gap between Pydantic's data validation and the ActiveRecord pattern.

```mermaid
classDiagram
    %% External Dependencies
    class PydanticBaseModel {
        <<external>>
    }

    %% Core Abstraction Layer
    class ActiveRecordBase {
        <<abstract>>
        +__table_name__: str
        +__primary_key__: str
        +__backend__: StorageBackend
        +__connection_config__: ConnectionConfig
        +_dirty_fields: Set[str]
        +is_dirty() bool
        +dirty_fields() Dict
        +reset_tracking() None
    }

    PydanticBaseModel <|-- ActiveRecordBase
```

### 2. Synchronous Architecture (`ActiveRecord`)

This diagram shows the inheritance hierarchy for the synchronous implementation. It follows a path from the interface definition down to the user-facing concrete class.

```mermaid
classDiagram
    %% Base Reference
    class ActiveRecordBase {
        <<abstract>>
    }

    %% Interface Layer
    class IActiveRecord {
        <<interface>>
        +save() int
        +delete() int
        +refresh() None
        +find_one(condition) IActiveRecord$
        +find_one_or_fail(condition) IActiveRecord$
        +find_all(condition) List~IActiveRecord~$
    }
    ActiveRecordBase <|-- IActiveRecord

    %% Base Implementation Layer
    class BaseActiveRecord {
        <<abstract>>
        +configure(config, backend_class)$
        +backend() StorageBackend$
        +save() int
        +delete() int
        +refresh() None
        +transaction() ContextManager
    }
    IActiveRecord <|-- BaseActiveRecord
    BaseActiveRecord ..> StorageBackend : uses

    %% Mixins
    class QueryMixin {
        +query() IActiveQuery
    }
    class RelationManagementMixin {
        +register_relation(name, relation)
        +get_relation(name)
        +clear_relation_cache(name)
    }
    class ColumnNameMixin {
        +get_field_to_column_map() Dict
        +get_column_to_field_map() Dict
        +validate_column_names() None
    }
    class FieldAdapterMixin {
        #_get_adapter_for_field(field_name)
    }
    class MetaclassMixin {
        <<Metaclass Provider>>
    }

    %% User-Facing Class
    class ActiveRecord {
        <<Concrete>>
    }

    BaseActiveRecord <|-- ActiveRecord
    QueryMixin --|> ActiveRecord
    RelationManagementMixin --|> ActiveRecord
    ColumnNameMixin --|> ActiveRecord
    FieldAdapterMixin --|> ActiveRecord
    MetaclassMixin --|> ActiveRecord

    %% User Defined Model
    class UserDefinedModel {
        <<User Implementation>>
        +field1: type
        +field2: type
    }
    ActiveRecord <|-- UserDefinedModel

    %% Backend Dependency
    class StorageBackend {
        <<abstract>>
        +connect()
        +disconnect()
        +transaction()
    }
```

### 3. Asynchronous Architecture (`AsyncActiveRecord`)

The asynchronous implementation mirrors the synchronous structure but uses async-compatible interfaces and mixins.

```mermaid
classDiagram
    %% Base Reference
    class ActiveRecordBase {
        <<abstract>>
    }

    %% Interface Layer
    class IAsyncActiveRecord {
        <<interface>>
        +save() int async
        +delete() int async
        +refresh() None async
        +find_one(condition) IAsyncActiveRecord$ async
        +find_one_or_fail(condition) IAsyncActiveRecord$ async
        +find_all(condition) List~IAsyncActiveRecord~$ async
    }
    ActiveRecordBase <|-- IAsyncActiveRecord

    %% Base Implementation Layer
    class AsyncBaseActiveRecord {
        <<abstract>>
        +configure(config, backend_class)$
        +backend() AsyncStorageBackend$
        +save() int async
        +delete() int async
        +refresh() None async
        +transaction() AsyncContextManager
    }
    IAsyncActiveRecord <|-- AsyncBaseActiveRecord
    AsyncBaseActiveRecord ..> AsyncStorageBackend : uses

    %% Mixins
    class AsyncQueryMixin {
        +query() IAsyncActiveQuery
    }
    class RelationManagementMixin {
        +register_relation(name, relation)
        +get_relation(name)
        +clear_relation_cache(name)
    }
    class ColumnNameMixin {
        +get_field_to_column_map() Dict
        +get_column_to_field_map() Dict
        +validate_column_names() None
    }
    class FieldAdapterMixin {
        #_get_adapter_for_field(field_name)
    }
    class MetaclassMixin {
        <<Metaclass Provider>>
    }

    %% User-Facing Class
    class AsyncActiveRecord {
        <<Concrete>>
    }

    AsyncBaseActiveRecord <|-- AsyncActiveRecord
    AsyncQueryMixin --|> AsyncActiveRecord
    RelationManagementMixin --|> AsyncActiveRecord
    ColumnNameMixin --|> AsyncActiveRecord
    FieldAdapterMixin --|> AsyncActiveRecord
    MetaclassMixin --|> AsyncActiveRecord

    %% User Defined Model
    class UserDefinedModel {
        <<User Implementation>>
        +field1: type
        +field2: type
    }
    AsyncActiveRecord <|-- UserDefinedModel

    %% Backend Dependency
    class AsyncStorageBackend {
        <<abstract>>
        +connect() async
        +disconnect() async
        +transaction() async
    }
```

### 4. Query Architecture

The query system uses a composition pattern, reusing functionality through Mixins, and supports both synchronous and asynchronous operations. Notably, `IActiveQuery` and `IAsyncActiveQuery` provide the `aggregate()` method, which allows retrieving raw execution results (list of dictionaries) from the database when it is not suitable or desired to map to `ActiveRecord` instances.

#### Synchronous Query

```mermaid
classDiagram
    %% Interfaces
    class IQuery {
        <<interface>>
        +to_sql() Tuple
        +backend() StorageBackend
    }
    class IActiveQuery {
        <<interface>>
        +model_class: Type
        +all() List~IActiveRecord~
        +one() Optional~IActiveRecord~
        +aggregate() List~Dict~
    }
    class ICTEQuery {
        <<interface>>
        +with_cte(name, query)
        +recursive(enabled)
        +aggregate() List~Dict~
    }
    class ISetOperationQuery {
        <<interface>>
        +union(other)
        +intersect(other)
        +except_(other)
    }

    IActiveQuery --|> IQuery
    ICTEQuery --|> IQuery
    ISetOperationQuery --|> IQuery

    %% Mixins
    class BaseQueryMixin {
        +where(condition)
        +select(columns)
        +order_by(clauses)
        +limit(count)
        +offset(count)
        +group_by(columns)
        +having(condition)
    }
    class JoinQueryMixin {
        +join(target, on)
        +left_join(target, on)
    }
    class AggregateQueryMixin {
        +count()
        +sum(column)
        +avg(column)
        +min(column)
        +max(column)
        +aggregate() List~Dict~
    class RelationalQueryMixin {
        +preload(relation)
        +eager_load(relation)
    }
    class RangeQueryMixin {
        +chunk(size)
        +batch(size)
    }

    %% Implementations
    class ActiveQuery {
        +union(other)
        +intersect(other)
        +except_(other)
    }
    class CTEQuery
    class SetOperationQuery

    ActiveQuery ..|> IActiveQuery
    ActiveQuery --|> BaseQueryMixin
    ActiveQuery --|> JoinQueryMixin
    ActiveQuery --|> AggregateQueryMixin
    ActiveQuery --|> RelationalQueryMixin
    ActiveQuery --|> RangeQueryMixin

    CTEQuery ..|> ICTEQuery
    CTEQuery ..|> ISetOperationQuery
    CTEQuery --|> BaseQueryMixin
    CTEQuery --|> JoinQueryMixin
    CTEQuery --|> AggregateQueryMixin
    CTEQuery --|> RangeQueryMixin

    SetOperationQuery ..|> ISetOperationQuery
```

#### Asynchronous Query

```mermaid
classDiagram
    %% Interfaces
    class IQuery {
        <<interface>>
        +to_sql() Tuple
        +backend() StorageBackend
    }
    class IAsyncActiveQuery {
        <<interface>>
        +model_class: Type
        +all() List~IActiveRecord~ async
        +one() Optional~IActiveRecord~ async
        +aggregate() List~Dict~ async
    }
    class IAsyncCTEQuery {
        <<interface>>
        +with_cte(name, query)
        +recursive(enabled)
        +aggregate() List~Dict~ async
    }
    class ISetOperationQuery {
        <<interface>>
        +union(other)
        +intersect(other)
        +except_(other)
    }

    IAsyncActiveQuery --|> IQuery
    IAsyncCTEQuery --|> IQuery
    ISetOperationQuery --|> IQuery

    %% Mixins
    class BaseQueryMixin {
        +where(condition)
        +select(columns)
        +order_by(clauses)
        +limit(count)
        +offset(count)
        +group_by(columns)
        +having(condition)
    }
    class JoinQueryMixin {
        +join(target, on)
        +left_join(target, on)
    }
    class AsyncAggregateQueryMixin {
        +count() async
        +sum(column) async
        +avg(column) async
        +min(column) async
        +max(column) async
        +aggregate() List~Dict~ async
    }
    class RelationalQueryMixin {
        +preload(relation)
        +eager_load(relation)
    }
    class RangeQueryMixin {
        +chunk(size)
        +batch(size)
    }

    %% Implementations
    class AsyncActiveQuery {
        +union(other)
        +intersect(other)
        +except_(other)
    }
    class AsyncCTEQuery
    class SetOperationQuery

    AsyncActiveQuery ..|> IAsyncActiveQuery
    AsyncActiveQuery --|> BaseQueryMixin
    AsyncActiveQuery --|> JoinQueryMixin
    AsyncActiveQuery --|> AsyncAggregateQueryMixin
    AsyncActiveQuery --|> RelationalQueryMixin
    AsyncActiveQuery --|> RangeQueryMixin

    AsyncCTEQuery ..|> IAsyncCTEQuery
    AsyncCTEQuery ..|> ISetOperationQuery
    AsyncCTEQuery --|> BaseQueryMixin
    AsyncCTEQuery --|> JoinQueryMixin
    AsyncCTEQuery --|> AsyncAggregateQueryMixin
    AsyncCTEQuery --|> RangeQueryMixin

    SetOperationQuery ..|> ISetOperationQuery
```

## The Life of a Query

```mermaid
sequenceDiagram
    participant App as User Code
    participant Model as ActiveRecord Model
    participant Query as ActiveQuery
    participant Expr as Expression Engine
    participant Dialect as SQL Dialect
    participant Backend as Storage Backend
    participant DB as Database

    App->>Model: User.query().where(...)
    Model->>Query: Create Query Builder
    
    alt Call .all() / .one()
        App->>Query: .all()
        Query->>Expr: Collect Query Conditions
        Expr->>Dialect: Construct SQL
        Dialect-->>Expr: SQL & Params
        Expr->>Backend: Execute SQL
        Backend-->>Expr: Result Rows
        Expr->>Query: Result Rows
        Query-->>Model: Result Rows
        Model-->>App: List[User]
    else Call .aggregate()
        App->>Query: .aggregate()
        Query->>Expr: Collect Query Conditions
        Expr->>Dialect: Construct SQL
        Dialect-->>Expr: SQL & Params
        Expr->>Backend: Execute SQL
        Backend-->>Expr: Result Rows
        Expr->>Query: Result Rows
        Query-->>App: List[Dict]
    end
```

### Detailed Flow

1.  **Initiation**
    The user calls `User.query()`. The model instantiates an `ActiveQuery` builder and injects the current model's context. At this point, the query builder knows which model and corresponding database table it serves.

2.  **Condition Collection**
    The user chains methods like `.where()`, `.select()`, etc. This stage primarily involves collecting various conditions and parameters required for the query. Notably, SQL construction can occur at any time, not just at the final moment.

3.  **SQL Construction**
    When the user calls `.all()`, `.one()`, or `.aggregate()`, or needs to inspect the generated SQL, the query builder passes the collected conditions to the `Dialect` layer. The Dialect is responsible for translating abstract conditions into specific database SQL syntax (e.g., handling pagination syntax differences or parameter placeholder styles across different databases).

4.  **Execution**
    The constructed SQL and parameters are passed to the `StorageBackend`. The backend is responsible for retrieving a connection from the pool, executing the query, and handling the underlying database cursor. For asynchronous operations, `await` is used here to wait for the database response non-blockingly.

5.  **Mapping (ORM Mapping)**
    The database returns raw row data (usually tuples or dictionaries).
    *   **If `.all()` or `.one()` is called**: `ActiveRecord` receives this data and uses Pydantic's parsing capabilities to convert it into strongly-typed model instances. This step involves not just data population but also type conversion and validation, ensuring that the objects returned to the user are safe and reliable.
    *   **If `.aggregate()` is called**: The mapping step is skipped, and the raw list of dictionaries (`List[Dict]`) is returned directly. This is useful for aggregation queries or scenarios where model overhead is unnecessary.
