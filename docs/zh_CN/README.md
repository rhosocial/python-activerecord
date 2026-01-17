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

3.  **模型定义 (Modeling Data - The Safe Layer)**
    *   **`ActiveRecord` 基类**: 领域模型的基石。
    *   **字段定义**: 使用 Pydantic 类型进行健壮的 Schema 验证。
    *   **Mixin 与组合**:
        *   `UUIDMixin`: 自动处理 UUID 主键。
        *   `TimestampMixin`: 自动管理 `created_at` 和 `updated_at`。
        *   `OptimisticLockMixin`: 基于版本号的并发控制实现。
    *   **验证生命周期**: `before_save`, `after_save` 等钩子函数。
    *   **高级字段配置**:
        *   **自定义列名**: 通过 `Annotated[T, UseColumn("col_name")]` 映射遗留数据库列。
        *   **自定义适配器**: 通过 `Annotated[T, UseAdapter(AdapterClass)]` 定义自定义序列化逻辑。
        *   **字段代理 (Field Proxy)**: 使用 `ClassVar[FieldProxy]` (如 `User.c.name`) 进行类型安全的查询构建与别名支持。
    *   **元数据定制**: 表名、索引与约束配置。

4.  **关联关系 (Relationships & Associations)**
    *   **类型安全的描述符**: `RelationDescriptor` 如何提供智能代码提示。
    *   **关系类型**:
        *   `HasOne` / `BelongsTo` (一对一)
        *   `HasMany` (一对多)
        *   多对多 (Many-to-Many) —— 通过中间模型
    *   **加载策略**:
        *   预加载 (Eager Loading): 使用 `with_()` 解决 N+1 问题。
        *   延迟加载 (Lazy Loading): 按需访问。

5.  **查询接口 (Querying Interface)**
    *   **ActiveQuery 架构**: 理解基于 Mixin 的设计 (`ActiveQuery` = `Base` + `Aggregate` + `Join` + ...)。
    *   **核心过滤 (`BaseQueryMixin`)**:
        *   `select()`: 选择特定列。
        *   `where()`: 应用查询条件。
        *   `distinct()`: 结果去重。
    *   **聚合 (`AggregateQueryMixin`)**:
        *   标准函数: `count()`, `sum()`, `avg()`, `min()`, `max()`。
        *   `aggregate()`: 执行任意聚合表达式。
    *   **连接 (`JoinQueryMixin`)**:
        *   `join()`: 内连接。
        *   `left_join()`, `cross_join()`: 其他连接类型。
    *   **排序与范围 (`RangeQueryMixin`)**:
        *   `order_by()`: 结果排序。
        *   `limit()`, `offset()`: 结果切片与分页。
    *   **关联加载 (`RelationalQueryMixin`)**:
        *   `with_()`: 预加载 (Eager loading) 关联记录。
    *   **集合操作 (`SetOperationQuery`)**:
        *   `union()`, `intersect()`, `except_()`: 组合查询结果。
    *   **公用表表达式 (`CTEQuery`)**:
        *   `with_cte()`: 定义和使用 CTE 以处理复杂查询。

6.  **性能与优化 (Performance & Optimization - The Raw Layer)**
    *   **"渐进式" 策略**: 何时切换模式。
    *   **严格模式 (Strict Mode)**: 为高完整性操作 (用户输入、复杂业务逻辑) 提供完整的 Pydantic 验证。
    *   **原始/聚合模式 (Raw / Aggregate Mode)**: 使用 `.aggregate()` 绕过 Pydantic 开销，用于海量读取 (ETL, 报表)。
    *   **缓存机制**: 理解列名-字段映射 (Column-to-Field Map) 缓存。
    *   **批量操作**: 批量创建 (Bulk Create) 与 更新策略。

7.  **后端表达式系统 (The Backend Expression System)**
    *   **`ToSQL` 协议**: Python 对象如何安全地转换为 SQL 字符串。
    *   **表达式组件**: 列 (Columns)、字面量 (Literals)、函数 (Functions)、窗口 (Windows)。
    *   **方言系统**: 如何支持不同的数据库 (SQLite, Dummy)。
    *   **高级 SQL 构建**: 编程式构建 CTE (公用表表达式) 和递归查询。
    *   **实现自定义后端 (Implementing Custom Backends)**:
        *   **架构设计**: 继承 `StorageBackend` 及其 Mixin 组件 (`ConnectionMixin`, `ExecutionMixin` 等)。
        *   **方言定义**: 继承 `SQLDialectBase` 实现数据库特定的 SQL 生成逻辑。
        *   **类型适配**: 将 Python 类型映射到数据库类型。
        *   **参考实现**: 使用 `sqlite` 后端作为标准模板。

8.  **测试与可靠性 (Testing & Reliability)**
    *   **零 IO 测试 (Zero-IO Testing)**: `DummyBackend` 的独特优势。
    *   **单元测试模型**: 在不连接数据库的情况下验证业务逻辑。
    *   **集成测试**: 使用 SQLite 进行完整的往返验证。
    *   **测试模式**: 可维护测试套件的最佳实践。

9.  **集成与场景案例 (Integration & Real-World Scenarios)**
    *   **FastAPI 集成**:
        *   **Pydantic 模型即 Schema**: 直接将 ActiveRecord 模型用作 `response_model` 和请求体。
        *   **异步路由处理**: 利用 `await` 实现非阻塞数据库 I/O。
        *   **依赖注入**: 每个请求的会话与事务管理。
    *   **GraphQL 集成 (Strawberry/Ariadne)**:
        *   **解析器 (Resolvers)**: 将 GraphQL 字段映射到 `ActiveQuery` 方法。
        *   **DataLoader 模式**: 使用 `in_` 查询和批量加载解决 N+1 问题。
    *   **数据处理与 ETL**:
        *   **原始模式 (Raw Mode)**: 使用 `.aggregate()` 进行高性能数据导出/转换。
        *   **批量操作**: 高效导入海量数据。
    *   **Serverless / FaaS**:
        *   **冷启动优化**: 轻量级后端初始化带来的优势。

10. **迁移与部署 (Migration & Deployment)**
    *   **Schema 管理**: 同步模型与数据库表结构。
    *   **迁移策略**: 处理 Schema 演进。
    *   **生产就绪**: 高负载环境下的配置建议。

11. **API 参考 (API Reference)**
    *   所有类和方法的详细 API 文档。

12. **贡献指南 (Contributing)**
    *   搭建开发环境。
    *   运行测试套件。
    *   编写文档。
