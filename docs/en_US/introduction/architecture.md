# Architecture

The library is built on a layered architecture to ensure maintainability, testability, and flexibility.

## Component Relationships

The architecture is divided into three main parts: the Core Foundation, the Synchronous Implementation, and the Asynchronous Implementation.

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
        +save() int
        +delete() int
        +refresh() None
        +transaction() ContextManager
    }
    IActiveRecord <|-- BaseActiveRecord

    %% Mixins
    class QueryMixin {
        +query() IActiveQuery
    }
    class RelationManagementMixin {
        +register_relation(name, relation)
        +get_relation(name)
        +clear_relation_cache(name)
    }

    %% User-Facing Class
    class ActiveRecord {
        <<Concrete>>
        +create(**kwargs) IActiveRecord$
    }

    BaseActiveRecord <|-- ActiveRecord
    QueryMixin --|> ActiveRecord
    RelationManagementMixin --|> ActiveRecord
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
        +save() int async
        +delete() int async
        +refresh() None async
        +transaction() AsyncContextManager
    }
    IAsyncActiveRecord <|-- AsyncBaseActiveRecord

    %% Mixins
    class AsyncQueryMixin {
        +query() IAsyncActiveQuery
    }
    class RelationManagementMixin {
        +register_relation(name, relation)
        +get_relation(name)
        +clear_relation_cache(name)
    }

    %% User-Facing Class
    class AsyncActiveRecord {
        <<Concrete>>
        +create(**kwargs) IAsyncActiveRecord$ async
    }

    AsyncBaseActiveRecord <|-- AsyncActiveRecord
    AsyncQueryMixin --|> AsyncActiveRecord
    RelationManagementMixin --|> AsyncActiveRecord
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
    App->>Query: .all()
    Query->>Expr: Build Query Expression
    Expr->>Dialect: Compile to SQL
    Dialect-->>Backend: Raw SQL + Params
    Backend->>DB: Execute SQL
    DB-->>Backend: Result Rows
    Backend-->>Query: Raw Data
    Query->>Model: Instantiate Objects (Pydantic Validation)
    Model-->>App: List[User]
```
