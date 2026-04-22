# rhosocial-activerecord 文档

> 🤖 **AI 学习助手**：本文档中关键概念旁标有 💡 AI 提示词标记。遇到不理解的概念时，可以直接向 AI 助手提问。
>
> **示例：** "什么是 Expression-Dialect 分离？为什么这种设计很重要？"
>
> 📖 **详细用法请参考**：[AI 辅助开发指南](introduction/ai_assistance.md)

## 目录 (Table of Contents)

1.  **[简介 (Introduction)](introduction/README.md)**
    *   **[AI 辅助开发](introduction/ai_assistance.md)**: 内置 AI 配置以及如何使用代码智能体加速你的工作流。
    *   **[术语表](introduction/glossary.md)**: 从零开始解释关键术语和概念。
    *   **[来自其他框架](introduction/coming_from_frameworks.md)**: 如果你熟悉 Django、SQLAlchemy、Rails 或其他框架。
    *   **[设计哲学](introduction/philosophy.md)**: "渐进式 ORM" (Gradual ORM) —— 在严格的类型安全 (OLTP) 与原始高性能 (OLAP) 之间寻求平衡。
    * **[核心特性 (Key Features)](introduction/key_features.md)**:
        * Pydantic V2 深度集成
        * 可组合的 Mixins (UUID, Timestamp, 乐观锁)
        * **[同步异步对等 (Sync-Async Parity)](introduction/key_features.md#同步异步对等-sync-async-parity)**: 同步和异步实现间的功能等价性 💡 *AI 提示词："为什么这个项目要求同步和异步 API 使用相同的方法名？这样做有什么好处？"*
        * 零 IO 测试策略 (Zero-IO Testing)
    * **[技术选型指南](introduction/comparison.md)**: 选择哪个 ORM？基于场景对比 SQLAlchemy、Django、SQLModel 等。
    * **[竞品分析 (Competitor Analysis)](introduction/competitor_analysis/README.md)**: 与 Django ORM、SQLAlchemy、SQLModel、Peewee、Tortoise ORM 等主流 ORM 的深度对比。
    * **[架构设计 (Architecture)](introduction/architecture.md)**: 理解分层设计 (Interface -> Active Record -> Dialect -> Expression -> Backend). 💡 *AI 提示词："解释分层架构设计，以及 Expression-Dialect 分离的意义和好处。"*

2.  **[快速入门 (Getting Started)](getting_started/README.md)**
    *   **[安装指南 (Installation)](getting_started/installation.md)**: 环境要求 (Python 3.8+, Pydantic V2) 及 pip 安装。
    *   **[数据库配置 (Configuration)](getting_started/configuration.md)**: 设置 SQLite 后端及管理共享连接。
    *   **[快速开始 (Quick Start)](getting_started/quick_start.md)**: 一个完整的 "Hello World" 示例，定义 User/Post 模型并执行 CRUD。
    *   **[第一个 CRUD 应用](getting_started/first_crud.md)**: 从零开始构建完整的 Todo 应用，逐步学习创建、读取、更新、删除操作。
    *   **[常见错误解决](getting_started/troubleshooting.md)**: 遇到问题？常见错误及解决方案（后端未配置、FieldProxy 缺失、PYTHONPATH 问题等）。

3.  **[模型定义 (Modeling Data)](modeling/README.md)**
    *   **[字段定义 (Fields & Proxies)](modeling/fields.md)**: 深入理解 `FieldProxy` 与类型安全，以及如何映射遗留数据库列。 💡 *AI 提示词："什么是 FieldProxy？它是如何实现类型安全的查询构建的？"*
    *   **[Mixin 与复用 (Mixins)](modeling/mixins.md)**: 使用 Mixin 消除重复代码，包括 UUID、时间戳和软删除。
    *   **[验证与生命周期 (Validation & Hooks)](modeling/validation.md)**: 在保存前后自动执行逻辑，确保数据一致性。
    *   **[自定义类型 (Custom Types)](modeling/custom_types.md)**: 处理 JSON、数组等复杂数据类型。
    *   **[模型最佳实践](modeling/best_practices.md)**: 命名规范、字段设计、项目组织、版本控制、索引优化。

4.  **[关联关系 (Relationships)](relationships/README.md)**
    *   **[基础关系 (Definitions)](relationships/definitions.md)**: 定义 `HasOne`, `BelongsTo`, `HasMany`。
    *   **[多对多关系 (Many-to-Many)](relationships/many_to_many.md)**: 通过中间模型实现复杂的 N:N 关系。
    *   **[加载策略 (Loading Strategies)](relationships/loading.md)**: 解决 N+1 问题，掌握预加载与延迟加载。

5.  **[查询接口 (Querying Interface)](querying/README.md)**
    *   **[ActiveQuery (模型查询)](querying/active_query.md)**: 过滤、排序、连接、聚合、关联加载。
    *   **[CTEQuery (公用表表达式)](querying/cte_query.md)**: 递归与分析查询。
    *   **[SetOperationQuery (集合操作)](querying/set_operation_query.md)**: UNION, INTERSECT, EXCEPT。
    *   **[查询速查表](querying/cheatsheet.md)**: 常见查询模式速查。
    *   **[复杂查询实战](querying/recipes.md)**: 常见业务场景的查询解决方案。

6.  **[连接管理 (Connection Management)](connection/README.md)**
    *   **[连接组与连接管理器](connection/connection_management.md)**: 使用 `BackendGroup` 和 `BackendManager` 管理多模型、多数据库连接。
    *   **[连接池 (Connection Pool)](connection/connection_pool.md)**: 高效连接管理与上下文感知访问模式，支持连接复用、生命周期管理和 ActiveRecord 集成。

7.  **[Worker Pool 模块 (Worker Pool)](worker_pool/README.md)**
    *   **[Worker Pool 使用指南](worker_pool/worker_pool.md)**: 独立 Worker 进程池，用于并行任务执行，支持驻留 Worker、崩溃恢复、生命周期钩子和优雅停机。

8.  **[性能与优化 (Performance)](performance/README.md)**
    *   **[运行模式 (Strict vs Raw)](performance/modes.md)**: 何时使用 `.aggregate()` 绕过 Pydantic 开销。
    *   **[并发控制 (Concurrency)](performance/concurrency.md)**: 使用乐观锁处理竞态条件。
    *   **[缓存机制 (Caching)](performance/caching.md)**: 理解内部缓存以避免重复工作。

9.  **[日志系统 (Logging)](logging/README.md)**
    *   **[日志命名空间](logging/namespace.md)**: 层次化日志命名，统一控制与精细调节。
    *   **[数据摘要](logging/data_summarization.md)**: 自动屏蔽敏感字段、截断长字符串。
    *   **[按层级配置](logging/per_logger_config.md)**: 为不同组件设置不同的日志模式。

10. **[事件系统 (Events)](events/README.md)**
    *   **[生命周期事件 (Lifecycle Events)](events/lifecycle.md)**: 业务逻辑解耦 (before_save, after_create 等)。

11. **[序列化 (Serialization)](serialization/README.md)**
    *   **[JSON 序列化 (JSON Serialization)](serialization/json.md)**: 模型转换为 JSON/Dict，字段过滤。

12. **[后端系统 (Backend System)](backend/README.md)**
    *   **[数据库内省 (Introspection)](backend/introspection.md)**: 查询数据库结构元数据。
    *   **[查询解释接口 (Query Explain)](backend/explain.md)**: 执行 EXPLAIN 语句，分析查询计划和索引使用情况。
    *   **[表达式系统 (Expression System)](backend/expression/README.md)**: Python 对象如何安全地转换为 SQL 字符串。 💡 *AI 提示词："解释 ToSQLProtocol 协议，以及 Expression-Dialect 分离如何防止 SQL 注入攻击。"*
    *   **[自定义后端 (Custom Backend)](backend/custom_backend.md)**: 实现一个新的数据库驱动。
    *   **[SQLite 后端](backend/sqlite/README.md)**: SQLite 特定功能和特性。

13. **[测试指南 (Testing)](testing/README.md)**
    *   **[测试策略 (Strategies)](testing/strategies.md)**: 零 IO 测试 vs 集成测试。
    *   **[Dummy Backend](testing/dummy.md)**: 使用内置的 Dummy Backend 进行单元测试。

14. **[场景实战 (Scenarios)](scenarios/README.md)**
    *   **[FastAPI 集成](scenarios/fastapi.md)**: 异步、依赖注入与 Pydantic 模型复用。
    *   **[GraphQL 集成](scenarios/graphql.md)**: 解决 N+1 问题，构建高效 API。
