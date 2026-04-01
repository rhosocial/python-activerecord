# 模型定义 (Modeling Data)

模型是 `rhosocial-activerecord` 的核心。它们不仅定义了数据的结构，还封装了业务逻辑、验证规则和查询能力。

本章将详细介绍如何定义强大的数据模型。

## 核心概念

1. **基于 Pydantic**: 模型本质上是 Pydantic 的 `BaseModel`，这意味着你拥有强大的数据验证和序列化能力。
2. **Active Record 模式**: 每个模型类对应数据库中的一张表，模型实例对应表中的一行记录。
3. **类型安全**: 通过 `FieldProxy`，我们实现了 Python 侧的类型安全查询，避免了硬编码字符串。

## 章节内容

- **[字段定义 (Fields & Proxies)](fields.md)**
  - 如何定义模型字段
  - 使用 `FieldProxy` 进行类型安全查询
  - 映射遗留数据库列 (`UseColumn`)
- **[Mixin 与复用 (Mixins)](mixins.md)**
  - 使用内置 Mixin (`UUIDMixin`, `TimestampMixin`)
  - 创建自定义 Mixin 复用逻辑
- **[验证与钩子 (Validation & Hooks)](validation.md)**
  - Pydantic 验证器
  - 生命周期钩子 (`before_save`, `after_create` 等)
- **[模型最佳实践](best_practices.md)**
  - 命名规范
  - 字段设计原则
  - 大型项目模型组织
  - 版本控制与数据库迁移
  - 性能优化：索引添加时机
  - 多个独立连接（子类继承 vs. 共享字段 Mixin）
- **[线程安全](concurrency.md)**
  - 在 Web 服务器中何时及如何调用 `configure()`
  - SQLite 单连接限制与多 Worker 配置
  - MySQL / PostgreSQL 连接池大小调优
- **[环境隔离配置](configuration_management.md)**
  - 按环境切换配置（dev / test / prod）
  - 从环境变量读取凭据
  - 使用内存 SQLite 实现测试隔离
- **[只读分析模型](readonly_models.md)**
  - 为分析场景 / 只读副本定义只读模型类
  - 与共享字段 Mixin 模式结合使用
  - 使用 `@property` 定义派生 / 计算字段
- **[大批量数据处理](batch_processing.md)**
  - 分块读取避免 OOM
  - 批量写入与避免 N+1 写入陷阱
  - 大批量任务的事务策略

## 示例代码

本章的完整示例代码可以在以下位置找到：
[docs/examples/chapter_03_modeling/basic_models.py](../../../examples/chapter_03_modeling/basic_models.py)
