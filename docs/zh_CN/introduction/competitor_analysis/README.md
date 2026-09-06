# 竞争对手分析

本章节提供 rhosocial-activerecord 与主流 Python ORM 框架的详细对比分析，帮助开发者选择适合的工具。

## 文档列表

- [竞争优势总结](./summary.md) — 快速选择指南
- [vs SQLAlchemy](./sqlalchemy.md) — 与 Data Mapper 模式代表对比
- [vs Django ORM](./django_orm.md) — 与框架绑定 ORM 对比
- [vs SQLModel](./sqlmodel.md) — 与 Pydantic+SQLAlchemy 混合方案对比
- [vs Peewee](./peewee.md) — 与轻量级 ActiveRecord 对比
- [vs Tortoise ORM](./tortoise_orm.md) — 与异步优先 ORM 对比

## 快速对比

| 框架 | 设计模式 | 核心特点 | 适用场景 | 最新版本 |
|------|----------|----------|----------|----------|
| **SQLAlchemy** | Data Mapper | 企业级、功能完整、学习曲线陡 | 大型企业应用 | 2.0.x |
| **Django ORM** | ActiveRecord | Django 紧密集成、成熟稳定 | Django 项目 | 6.0 / 5.2 LTS |
| **SQLModel** | 混合 | Pydantic + SQLAlchemy | FastAPI + SQLAlchemy 用户 | 0.0.x |
| **Peewee** | ActiveRecord | 轻量、自包含 | 小型项目 | 4.x |
| **Tortoise ORM** | ActiveRecord | 异步优先、Django 风格 | 纯异步项目 | 1.1.x |
| **rhosocial-activerecord** | ActiveRecord | Pydantic 原生、同步异步对等、多后端 | 现代 Python 项目 | 1.0.0.dev30 |

> 以上版本信息截至 2026 年。各框架持续迭代，请以官方发布为准。

## 核心优势：相对各竞争对手

rhosocial-activerecord 的核心差异化在于：**纯 ActiveRecord 模式（无 Session）+ Pydantic 原生类型安全 + 真正同步/异步对等 + 可独立使用的后端层**。以下是相对每个竞争对手的具体优势。

### 相对 SQLAlchemy

| 维度 | rhosocial-activerecord | SQLAlchemy |
|------|------------------------|------------|
| 心智模型 | 纯 ActiveRecord，无 Session 概念 | Data Mapper，需理解 Session/UoW/Identity Map |
| 操作方式 | `user.save()` 直接落库 | `session.add()` + `session.commit()` |
| 类型系统 | Pydantic 原生，完整类型提示 | 自研类型体系，需额外学习 |
| 异步实现 | 原生异步，API 与同步完全一致 | 2.0 依赖 greenlet 包装 |
| 架构层级 | 单层抽象（代码 → ORM → 驱动） | 三层（ORM API → Core → 驱动） |

**核心优势**：`save()`/`delete()` 直接对应数据库操作、无需管理 Session 生命周期；基于 Pydantic 的类型安全与运行时验证开箱即用；原生同步/异步对等（非 greenlet 包装）；调用栈浅、行为可预测。

### 相对 Django ORM

| 维度 | rhosocial-activerecord | Django ORM |
|------|------------------------|------------|
| 框架独立性 | 任意 Python 项目（FastAPI/Flask/脚本/Jupyter） | 仅限 Django 项目 |
| 异步支持 | 原生异步，API 一致 | 需 async 视图 + `sync_to_async` 转换 |
| 类型安全 | Pydantic 完整类型系统 | 字段类型提示有限（`Any`） |
| 查询灵活度 | FieldProxy 表达式 + CTEQuery/SetOperationQuery | QuerySet + Q 对象，复杂查询受限 |
| 迁移 | 可选，可集成任意工具 | 内置迁移系统（但绑定 Django） |

**核心优势**：完全独立于 Web 框架，可在 FastAPI、Flask、脚本、Jupyter 中直接使用；原生异步不依赖 `sync_to_async`；Pydantic 提供完整 IDE 类型提示；SQL 透明（`.to_sql()` 随时可查）。

### 相对 SQLModel

| 维度 | rhosocial-activerecord | SQLModel |
|------|------------------------|----------|
| 模式纯度 | 纯 ActiveRecord，无 Session | SQLAlchemy + Pydantic 混合，仍需 Session |
| 架构 | 从零构建，单层抽象 | SQLAlchemy 包装层 |
| 同步/异步 | 原生对等，API 一致 | 需区分 Session/AsyncSession |
| 查询 | 链式 + FieldProxy 类型安全 | SQLAlchemy select 风格 |

**核心优势**：同为 Pydantic 生态，但不需要理解 SQLAlchemy 概念与 Session 生命周期；从零构建避免包装层带来的隐藏复杂性；同步/异步 API 完全一致，无需区分 Session/AsyncSession。

### 相对 Peewee

| 维度 | rhosocial-activerecord | Peewee |
|------|------------------------|--------|
| 类型安全 | Pydantic 完整类型提示 + 运行时验证 | 字段类型为 `Any`，无运行时验证 |
| 异步 | 原生对等 | 需 `peewee-async` 等扩展，API 不同 |
| SQL 覆盖 | Expression/Dialect 完整覆盖 | 轻量但 SQL 表达能力有限 |
| 依赖 | 仅 Pydantic | 零依赖（自包含） |

**核心优势**：在保持轻量（仅 Pydantic 一个依赖）的同时提供完整类型安全、运行时验证、原生异步与完整 SQL 覆盖。Peewee 的极简依赖是其优势，但代价是类型安全与 SQL 表达能力的不足。

### 相对 Tortoise ORM

| 维度 | rhosocial-activerecord | Tortoise ORM |
|------|------------------------|--------------|
| 同步/异步 | 两者都是一等公民，API 完全一致 | 异步优先，同步支持有限 |
| 类型安全 | Pydantic 完整类型系统 | 字段类型提示有限 |
| SQL 覆盖 | CTE/窗口函数/集合操作完整支持 | 复杂查询通常需原生 SQL |
| 能力声明 | 后端显式声明支持范围 | 无统一能力声明机制 |

**核心优势**：真正的同步/异步对等（Tortoise 以异步为核心，同步是二等公民）；Pydantic 类型安全；CTE、窗口函数、集合操作开箱即用，无需退回原生 SQL。

### 共同的横切优势

除上述逐项对比外，rhosocial-activerecord 在以下方面对所有竞争对手保持一致优势：

| 优势 | 说明 |
|------|------|
| **纯 ActiveRecord，无 Session** | 心智模型简单，`save()`/`delete()` 直接对应数据库操作 |
| **Pydantic 原生** | 继承 `BaseModel`，完整类型安全、运行时验证、FastAPI 无缝集成 |
| **同步/异步对等** | 同一套 API，方法名完全一致，仅通过 `await` 区分 |
| **SQL 完全透明** | 任何表达式/查询随时 `.to_sql()` 查看生成 SQL |
| **后端独立可用** | 后端层可脱离 ORM 单独使用，支持自定义后端 |
| **能力显式声明** | 后端协议声明 `supports_*` 能力，测试自动跳过不支持特性 |
| **仅一个依赖** | 只有 Pydantic，无 ORM 包装层、无框架耦合 |

> 详细对比请参见各篇 [文档列表](#文档列表) 中的具体分析。

## 后端支持

rhosocial-activerecord 采用核心库 + 独立后端包的架构，目前提供：

| 后端 | 仓库 |
|------|------|
| SQLite | 内置（[python-activerecord](https://github.com/rhosocial/python-activerecord)） |
| MySQL | [python-activerecord-mysql](https://github.com/rhosocial/python-activerecord-mysql) |
| PostgreSQL | [python-activerecord-postgres](https://github.com/rhosocial/python-activerecord-postgres) |
| MariaDB | [python-activerecord-mariadb](https://github.com/rhosocial/python-activerecord-mariadb) |
| Oracle | [python-activerecord-oracle](https://github.com/rhosocial/python-activerecord-oracle) |
| SQL Server | [python-activerecord-sqlserver](https://github.com/rhosocial/python-activerecord-sqlserver) |
| ClickHouse | [python-activerecord-clickhouse](https://github.com/rhosocial/python-activerecord-clickhouse) |
| Snowflake | [python-activerecord-snowflake](https://github.com/rhosocial/python-activerecord-snowflake) |
| BigQuery | [python-activerecord-bigquery](https://github.com/rhosocial/python-activerecord-bigquery) |
| Firebird | [python-activerecord-firebird](https://github.com/rhosocial/python-activerecord-firebird) |

> 各后端的支持程度（功能、版本、Python 版本）以对应后端包文档为准。
