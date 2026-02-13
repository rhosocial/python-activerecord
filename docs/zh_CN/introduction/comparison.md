# 技术选型指南

选择 ORM 是一个影响项目可维护性、性能和团队生产力的重要架构决策。本指南帮助你了解什么时候应该选择 `rhosocial-activerecord`——以及什么时候你可能需要考虑其他方案。

## 概览

| 方面 | rhosocial-activerecord | 最适合 |
| :--- | :--- | :--- |
| **模式** | Active Record | 快速开发、直观的数据建模 |
| **验证** | Pydantic V2（原生）| 类型安全应用、FastAPI 集成 |
| **架构** | 独立 | 与框架无关的项目、微服务 |
| **测试** | 零 IO 测试 | 快速测试套件、CI/CD 流水线 |
| **性能** | 可调（严格 ↔ 原始）| 混合工作负载（OLTP + 报表）|
| **学习曲线** | 低 | ORM 新手团队 |

## 什么时候选择 rhosocial-activerecord

### ✅ 你想要 ActiveRecord 模式，但不想被框架锁定

**场景：** 你喜欢 ActiveRecord 模式（类 = 表，实例 = 行），但 Django ORM 强迫你使用 Django，而 Rails 是 Ruby。

**为什么选我们：** 我们提供了一个**独立的、现代的 ActiveRecord 实现**，可以在以下环境中工作：
- FastAPI 应用
- Flask 微服务
- 独立脚本和 CLI 工具
- Jupyter 笔记本
- 数据处理管道
- 任何 Python 环境

> 💡 **AI 提示词：** "解释在微服务架构中 ActiveRecord 和 Data Mapper 模式的取舍。"

### ✅ 你需要类型安全，但不想有额外开销

**场景：** 你想要编译时类型检查和 IDE 自动补全，但不想复杂配置。

**我们的方案：**
- 原生 Pydantic V2 集成（不是可选插件）
- `FieldProxy` 系统：`User.c.age` 提供 IDE 自动补全和类型检查
- 没有会静默失败的基于字符串的查询

**对比：**
- Django ORM：动态类型，IDE 支持有限
- SQLAlchemy：可以配置类型但需要额外工作
- **我们：默认类型安全，零配置**

### ✅ 你想在没有数据库的情况下测试

**场景：** 你的 CI/CD 流水线很慢，因为测试需要 Docker、数据库设置和种子数据。

**我们的解决方案：** 原生**零 IO 测试**
```python
# 在不接触数据库的情况下测试 SQL 生成
sql, params = User.query().where(User.c.age > 18).to_sql()
assert "age > ?" in sql
assert params == (18,)
```

没有 Docker。没有数据库。测试在毫秒级运行。

> 💡 **AI 提示词：** "比较零 IO 测试与传统数据库依赖测试。各有什么取舍？"

### ✅ 你有混合的性能需求

**场景：** 你的应用既有严格的验证需求（用户注册），又有高性能报表需求（百万行聚合）。

**我们的解决方案：** **渐进式 ORM** 方法
```python
# 严格模式：完整验证、生命周期钩子
user = User(email="alice@example.com")
user.save()  # 验证、钩子等等

# 原始模式：为性能跳过开销
results = User.query().where(User.c.active == True).aggregate()
# 返回字典，跳过模型实例化
```

同一个 ORM，不同的性能配置文件。

### ✅ 你想要 AI 辅助开发

**场景：** 你想利用 AI 代码智能体（Claude Code、GitHub Copilot、Cursor）来加速开发。

**为什么选我们：** 内置 AI 支持
- 为 AI 智能体自动发现的配置
- 用于代码生成的技能和命令
- 类型安全的 API 更容易被 AI 理解和生成

## 什么时候考虑其他方案

### 🤔 如果以下情况，考虑 SQLAlchemy...

**你需要极致的灵活性**
- 复杂的多表继承层次结构
- 与数据库无关的 DDL 操作
- 每个查询都自定义 SQL 编译

**为什么：** SQLAlchemy 的 Data Mapper 模式为复杂领域模型提供了更多灵活性。

> 💡 **AI 提示词：** "什么时候应该选择 SQLAlchemy 的 Data Mapper 而不是 ActiveRecord？"

### 🤔 如果以下情况，考虑 Django ORM...

**你已经在构建 Django 应用程序**
- 使用 Django admin、表单和模板
- 需要 Django 的迁移系统
- 团队已经熟悉 Django

**为什么：** Django ORM 与 Django 生态系统无缝集成。在 Django 中使用独立 ORM 会增加复杂性而没有收益。

> ⚠️ **例外：** 如果你在 admin 中使用 Django 但在 API 中使用 FastAPI，考虑在 FastAPI 服务中使用 rhosocial-activerecord，在 admin 中使用 Django ORM。

### 🤔 如果以下情况，考虑 SQLModel...

**你特别想要 SQLAlchemy + Pydantic 集成**
- 需要 SQLAlchemy 的生态系统（alembic 等）
- 想要与 SQLAlchemy 一起工作的 Pydantic 模型
- 对 SQLAlchemy 的学习曲线感到舒适

**取舍：** SQLModel 同时继承 Pydantic 和 SQLAlchemy，这可能导致元类冲突。它也没有解决 SQLAlchemy 的会话复杂性。

### 🤔 如果以下情况，考虑 Prisma Client Python...

**你想要 schema-first 方法**
- 喜欢在 DSL 中定义 schema
- 需要从 schema 生成代码
- 想要从 schema 生成的类型安全查询

**取舍：** 需要构建步骤，动态查询不够灵活。

## 决策矩阵

| 你的情况 | 推荐 |
| :--- | :--- |
| FastAPI + Pydantic + 类型安全 | **✅ rhosocial-activerecord** |
| Flask 微服务 | **✅ rhosocial-activerecord** |
| 独立脚本/CLI 工具 | **✅ rhosocial-activerecord** |
| Django 单体应用 | 🤔 Django ORM（原生） |
| 复杂领域模型，重度继承 | 🤔 SQLAlchemy |
| 需要 SQLAlchemy 生态系统 | 🤔 SQLAlchemy 或 SQLModel |
| Schema-first，代码生成 | 🤔 Prisma |
| 首次学习 Python ORM | **✅ rhosocial-activerecord**（学习曲线最低） |

## 迁移场景

### 从 Django ORM 迁移到 rhosocial-activerecord

**最适合：**
- 将 Django 应用提取到微服务
- 在 Django admin 旁构建 FastAPI API
- 从单体迁移到服务

**挑战：**
- 失去 Django 的迁移系统（使用 Alembic 或原始 SQL）
- 替换 Django admin（构建自己的或使用替代方案）

**参见：** [来自 Django](coming_from_frameworks.md)

### 从 SQLAlchemy 迁移到 rhosocial-activerecord

**最适合：**
- 简化复杂的 SQLAlchemy 设置
- 想要更少的 CRUD 操作样板代码
- 迁移到异步而无需 SQLAlchemy 的异步复杂性

**挑战：**
- 失去 SQLAlchemy 的极致灵活性
- 使用 Expression 系统重写复杂查询

**参见：** [来自 SQLAlchemy](coming_from_frameworks.md)

### 从 Rails ActiveRecord 迁移

**最适合：**
- Ruby 团队迁移到 Python
- 想要 Ruby 无法提供的类型安全
- 保持熟悉的 ActiveRecord 模式

**挑战：**
- 不同的约定（snake_case vs camelCase）
- Python 生态系统差异

**参见：** [来自 Rails](coming_from_frameworks.md)

## 下一步

### 如果你决定使用 rhosocial-activerecord：

1. **[快速入门](../getting_started/README.md)** — 安装和第一个模型
2. **[来自其他框架](coming_from_frameworks.md)** — 映射你现有的知识
3. **[核心特性](key_features.md)** — 功能导览

### 如果你还在评估：

- **用两者原型：** 用 rhosocial-activerecord 和你当前的 ORM 构建一个小功能
- **检查生态系统：** 确保需要的扩展存在
- **团队认同：** 让你的团队查看这个对比

> 💡 **AI 提示词：** "我正在 [描述你的项目] 中选择 rhosocial-activerecord、SQLAlchemy 和 Django ORM。我应该考虑哪些因素？"

## 另请参阅

- [来自其他框架](coming_from_frameworks.md) — 详细的迁移指南
- [设计哲学](philosophy.md) — 设计原则和架构决策
- [架构设计](architecture.md) — 技术深入
