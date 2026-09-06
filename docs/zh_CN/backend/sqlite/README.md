# SQLite 后端文档

> **AI 学习助手**：本文档中的关键概念已用 AI 提示 标记。当您遇到不理解的概念时，可以直接向 AI 助手提问。
>
> **示例**："SQLite 后端如何处理事务？"

## 目录

1. **[简介](introduction/README.md)**
    *   **[SQLite 后端概述](introduction/README.md)**：架构、同步/异步对等性及快速示例
    *   **[支持的版本](introduction/README.md#version-requirements)**：SQLite 版本矩阵

2. **[安装与配置](installation_and_configuration/README.md)**
    *   **[安装](installation_and_configuration/README.md#installation)**：pip 安装及异步驱动配置
    *   **[连接配置](installation_and_configuration/README.md#connection-configuration)**：数据库路径、内存数据库及选项

3. **[SQLite 特有功能](backend_specific_features/README.md)**
    *   **[Pragma 系统](pragma.md)**：SQLite PRAGMA 配置与查询
    *   **[扩展框架](extension.md)**：扩展检测与管理
    *   **[全文搜索 (FTS5)](fts5.md)**：FTS5 全文搜索功能
    *   **[版本功能支持](backend_specific_features/README.md#version-feature-support-matrix)**：按版本划分的功能可用性
    *   **[已知限制](backend_specific_features/README.md#known-limitations)**：SQLite 特定约束

4. **[DDL 操作](ddl/README.md)**
    *   **[DDL 概述](ddl/README.md)**：Schema 管理及 SQLite DDL 限制

5. **[事务支持](transaction_support/README.md)**
    *   **[事务概述](transaction_support/README.md)**：事务管理器 API
    *   **[Savepoints](transaction_support/README.md#savepoints)**：嵌套事务
    *   **[隔离级别](transaction_support/README.md#isolation-level)**：SQLite 隔离语义

6. **[类型适配器](type_adapters/README.md)**
    *   **[类型映射](type_adapters/README.md#type-mapping)**：SQLite 到 Python 的类型转换
    *   **[特殊类型](type_adapters/README.md#special-types)**：datetime、UUID、Decimal、JSON 支持

7. **[测试](testing/README.md)**
    *   **[测试原则](testing/README.md)**：同步/异步对等性、表达式测试、testsuite 使用

8. **[故障排除](troubleshooting/README.md)**
    *   **[常见问题](troubleshooting/README.md)**：数据库锁定、WAL 模式及其他 SQLite 陷阱

9. **[应用场景](scenarios/README.md)**
    *   **[并发特性](scenarios/README.md)**：文件锁定、网络存储及部署模式

10. **[自定义](customization/README.md)**
    *   **[自定义表达式](customization/README.md#custom-expressions)**：SQLite 特定 SQL 语法
    *   **[自定义类型](customization/README.md#custom-data-types)**：扩展类型系统
    *   **[自定义适配器](customization/README.md#custom-type-adapters)**：注册类型转换器

11. **[命令行界面](cli/README.md)**
    *   **[CLI 概述](cli/README.md)**：查询、检查和管理 SQLite 数据库

## 附加资源

- **[自定义 SQLite 构建](custom-sqlite-build.md)**：构建带有扩展的自定义 SQLite
- **[核心库文档](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US)**：完整的 ActiveRecord 框架文档

> **核心库文档**：有关完整的 ActiveRecord 框架文档（建模、查询、关系、性能、工作池），请参阅 [rhosocial-activerecord 文档](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US)。

💡 *AI 提示*："SQLite 后端与 MySQL 或 PostgreSQL 后端有什么区别？"
