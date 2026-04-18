# 目录

* [rhosocial-activerecord 文档](README.md)

## 简介

* [概述](introduction/README.md)
* [AI 辅助开发](introduction/ai_assistance.md)
* [术语表](introduction/glossary.md)
* [来自其他框架](introduction/coming_from_frameworks.md)
* [设计哲学](introduction/philosophy.md)
* [核心特性](introduction/key_features.md)
* [技术选型指南](introduction/comparison.md)
* [架构设计](introduction/architecture.md)

### 竞品分析

* [概述](introduction/competitor_analysis/README.md)
* [Django ORM](introduction/competitor_analysis/django_orm.md)
* [SQLAlchemy](introduction/competitor_analysis/sqlalchemy.md)
* [SQLModel](introduction/competitor_analysis/sqlmodel.md)
* [Peewee](introduction/competitor_analysis/peewee.md)
* [Tortoise ORM](introduction/competitor_analysis/tortoise_orm.md)
* [总结](introduction/competitor_analysis/summary.md)

## 快速入门

* [概述](getting_started/README.md)
* [安装指南](getting_started/installation.md)
* [数据库配置](getting_started/configuration.md)
* [快速开始](getting_started/quick_start.md)
* [第一个 CRUD 应用](getting_started/first_crud.md)
* [常见错误解决](getting_started/troubleshooting.md)

## 模型定义

* [概述](modeling/README.md)
* [字段定义](modeling/fields.md)
* [Mixin 与复用](modeling/mixins.md)
* [验证与生命周期](modeling/validation.md)
* [自定义类型](modeling/custom_types.md)
* [模型最佳实践](modeling/best_practices.md)
* [只读模型](modeling/readonly_models.md)
* [批量处理](modeling/batch_processing.md)
* [并发](modeling/concurrency.md)
* [配置管理](modeling/configuration_management.md)
* [DDL](modeling/ddl.md)
* [DDL 视图](modeling/ddl_views.md)

## 关联关系

* [概述](relationships/README.md)
* [基础关系](relationships/definitions.md)
* [多对多关系](relationships/many_to_many.md)
* [加载策略](relationships/loading.md)

## 查询接口

* [概述](querying/README.md)
* [ActiveQuery](querying/active_query.md)
* [CTEQuery](querying/cte_query.md)
* [SetOperationQuery](querying/set_operation_query.md)
* [查询速查表](querying/cheatsheet.md)
* [复杂查询实战](querying/recipes.md)

## 连接管理

* [概述](connection/README.md)
* [连接组与连接管理器](connection/connection_management.md)
* [连接池](connection/connection_pool.md)

## Worker Pool 模块

* [概述](worker_pool/README.md)
* [Worker Pool 使用指南](worker_pool/worker_pool.md)
* [任务指南](worker_pool/task_guide.md)
* [生命周期钩子](worker_pool/lifecycle_hooks.md)
* [管理与统计](worker_pool/management_statistics.md)
* [API 参考](worker_pool/api_reference.md)
* [最佳实践](worker_pool/best_practices.md)

## 性能与优化

* [概述](performance/README.md)
* [运行模式](performance/modes.md)
* [并发控制](performance/concurrency.md)
* [缓存机制](performance/caching.md)
* [批量操作](performance/batch_operations.md)

## 日志系统

* [概述](logging/README.md)
* [日志命名空间](logging/namespace.md)
* [数据摘要](logging/data_summarization.md)
* [按层级配置](logging/per_logger_config.md)

## 事件系统

* [概述](events/README.md)
* [生命周期事件](events/lifecycle.md)

## 序列化

* [概述](serialization/README.md)
* [JSON 序列化](serialization/json.md)

## 后端系统

* [概述](backend/README.md)
* [数据库内省](backend/introspection.md)
* [查询解释接口](backend/explain.md)
* [自定义后端](backend/custom_backend.md)
* [命名查询](backend/named_queries.md)

### 表达式系统

* [概述](backend/expression/README.md)
* [核心](backend/expression/core.md)
* [子句](backend/expression/clauses.md)
* [谓词](backend/expression/predicates.md)
* [函数](backend/expression/functions.md)
* [语句](backend/expression/statements.md)
* [高级用法](backend/expression/advanced.md)
* [限制](backend/expression/limitations.md)

### SQLite 后端

* [概述](backend/sqlite/README.md)
* [Pragma](backend/sqlite/pragma.md)
* [FTS5](backend/sqlite/fts5.md)
* [扩展](backend/sqlite/extension.md)

## 测试指南

* [概述](testing/README.md)
* [测试策略](testing/strategies.md)
* [Dummy Backend](testing/dummy.md)
* [测试夹具](testing/fixtures.md)

## 场景实战

* [概述](scenarios/README.md)
* [FastAPI 集成](scenarios/fastapi.md)
* [GraphQL 集成](scenarios/graphql.md)
