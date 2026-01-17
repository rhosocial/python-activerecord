# rhosocial-activerecord 文档

## 目录 (Table of Contents)

1.  **[简介 (Introduction)](introduction/README.md)**
    *   **[设计哲学 (Philosophy)](introduction/philosophy.md)**: "渐进式 ORM" (Gradual ORM) —— 在严格的类型安全 (OLTP) 与原始高性能 (OLAP) 之间寻求平衡。
    *   **[核心特性 (Key Features)](introduction/key_features.md)**:
        *   Pydantic V2 深度集成
        *   可组合的 Mixins (UUID, Timestamp, 乐观锁)
        *   零 IO 测试策略 (Zero-IO Testing)
    *   **[对比分析 (Comparison)](introduction/comparison.md)**: 与 SQLModel, SQLAlchemy, Peewee, Django ORM 的详细对比。
    *   **[架构设计 (Architecture)](introduction/architecture.md)**: 理解分层设计 (Interface -> Active Record -> Dialect -> Expression -> Backend).

2.  **[快速入门 (Getting Started)](getting_started/README.md)**
    *   **[安装指南 (Installation)](getting_started/installation.md)**: 环境要求 (Python 3.8+, Pydantic V2) 及 pip 安装。
    *   **[数据库配置 (Configuration)](getting_started/configuration.md)**: 设置 SQLite 后端及管理共享连接。
    *   **[快速开始 (Quick Start)](getting_started/quick_start.md)**: 一个完整的 "Hello World" 示例，定义 User/Post 模型并执行 CRUD。

3.  **[模型定义 (Modeling Data)](modeling/README.md)**
    *   **[字段定义 (Fields & Proxies)](modeling/fields.md)**: 深入理解 `FieldProxy` 与类型安全，以及如何映射遗留数据库列。
    *   **[Mixin 与复用 (Mixins)](modeling/mixins.md)**: 使用 Mixin 消除重复代码，包括 UUID、时间戳和软删除。
    *   **[验证与生命周期 (Validation & Hooks)](modeling/validation.md)**: 在保存前后自动执行逻辑，确保数据一致性。
    *   **[自定义类型 (Custom Types)](modeling/custom_types.md)**: 处理 JSON、数组等复杂数据类型。

4.  **[关联关系 (Relationships)](relationships/README.md)**
    *   **[基础关系 (Definitions)](relationships/definitions.md)**: 定义 `HasOne`, `BelongsTo`, `HasMany`。
    *   **[多对多关系 (Many-to-Many)](relationships/many_to_many.md)**: 通过中间模型实现复杂的 N:N 关系。
    *   **[加载策略 (Loading Strategies)](relationships/loading.md)**: 解决 N+1 问题，掌握预加载与延迟加载。

5.  **[查询接口 (Querying Interface)](querying/README.md)**
    *   **[ActiveQuery (模型查询)](querying/active_query.md)**: 过滤、排序、连接、聚合、关联加载。
    *   **[CTEQuery (公用表表达式)](querying/cte_query.md)**: 递归与分析查询。
    *   **[SetOperationQuery (集合操作)](querying/set_operation_query.md)**: UNION, INTERSECT, EXCEPT。

6.  **[性能与优化 (Performance)](performance/README.md)**
    *   **[运行模式 (Strict vs Raw)](performance/modes.md)**: 何时使用 `.aggregate()` 绕过 Pydantic 开销。
    *   **[并发控制 (Concurrency)](performance/concurrency.md)**: 使用乐观锁处理竞态条件。
    *   **[缓存机制 (Caching)](performance/caching.md)**: 理解内部缓存以避免重复工作。

7.  **[事件系统 (Events)](events/README.md)**
    *   **[生命周期事件 (Lifecycle Events)](events/lifecycle.md)**: 业务逻辑解耦 (before_save, after_create 等)。

8.  **[序列化 (Serialization)](serialization/README.md)**
    *   **[JSON 序列化 (JSON Serialization)](serialization/json.md)**: 模型转换为 JSON/Dict，字段过滤。

9.  **[后端系统 (Backend System)](backend/README.md)**
    *   **[表达式系统 (Expression System)](backend/expression.md)**: Python 对象如何安全地转换为 SQL 字符串。
    *   **[自定义后端 (Custom Backend)](backend/custom_backend.md)**: 实现一个新的数据库驱动。

10. **[测试指南 (Testing)](testing/README.md)**
    *   **[测试策略 (Strategies)](testing/strategies.md)**: 零 IO 测试 vs 集成测试。
    *   **[Dummy Backend](testing/dummy.md)**: 使用内置的 Dummy Backend 进行单元测试。

11. **[场景实战 (Scenarios)](scenarios/README.md)**
    *   **[FastAPI 集成](scenarios/fastapi.md)**: 异步、依赖注入与 Pydantic 模型复用。
    *   **[GraphQL 集成](scenarios/graphql.md)**: 解决 N+1 问题，构建高效 API。
