# 架构设计 (Architecture)

本库采用分层架构设计，以确保可维护性、可测试性和灵活性。

## 组件关系图 (Component Relationships)

架构分为三个主要部分：核心基石、同步实现和异步实现。

### 1. 核心基石 (`ActiveRecordBase`)

`ActiveRecordBase` 是所有模型的共同祖先。它连接了 Pydantic 的数据验证能力和 ActiveRecord 模式。

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

### 2. 同步架构 (`ActiveRecord`)

此图展示了同步实现的继承层次结构。它遵循从接口定义到面向用户的具体类的路径。

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

### 3. 异步架构 (`AsyncActiveRecord`)

异步实现镜像了同步结构，但使用了兼容异步的接口和 Mixin。

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

## 查询的生命周期 (The Life of a Query)

```mermaid
sequenceDiagram
    participant App as 用户代码
    participant Model as ActiveRecord 模型
    participant Query as ActiveQuery 查询器
    participant Expr as 表达式引擎
    participant Dialect as SQL 方言层
    participant Backend as 存储后端
    participant DB as 数据库

    App->>Model: User.query().where(...)
    Model->>Query: 创建查询构建器
    App->>Query: .all()
    Query->>Expr: 构建查询表达式
    Expr->>Dialect: 编译为 SQL
    Dialect-->>Backend: 原始 SQL + 参数
    Backend->>DB: 执行 SQL
    DB-->>Backend: 返回结果行
    Backend-->>Query: 原始数据
    Query->>Model: 实例化对象 (Pydantic 验证)
    Model-->>App: List[User]
```
