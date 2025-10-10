# 支持的数据库

rhosocial ActiveRecord提供对多种数据库系统的支持，使您能够使用相同的ActiveRecord API，而不管底层数据库是什么。本节提供了关于每个支持的数据库系统的详细信息，包括配置选项、特定功能和优化技术。

> **🔄 当前状态**：目前，只有SQLite作为内置的默认后端包含在内。其他数据库后端（MySQL、MariaDB、PostgreSQL、Oracle、SQL Server）正在作为单独的代码包开发中，可能会在未来发布。这些后端的文档描述了计划中的功能，是作为即将推出功能的参考。实施状态可能有所不同，且可能更改。

## 目录

- [MySQL](mysql.md) - MySQL数据库的配置和功能（即将推出）
- [MariaDB](mariadb.md) - MariaDB数据库的配置和功能（即将推出）
- [PostgreSQL](postgresql.md) - 使用PostgreSQL数据库（即将推出）
- [Oracle](oracle.md) - Oracle数据库集成（即将推出）
- [SQL Server](sql_server.md) - Microsoft SQL Server支持（即将推出）
- [SQLite](sqlite.md) - 轻量级文件型数据库支持（内置）

## 通用配置

rhosocial ActiveRecord中的所有数据库后端都使用`ConnectionConfig`类进行配置，该类为指定连接参数提供了一致的接口。虽然每个数据库系统都有其自己的特定参数，但基本配置模式保持不变：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

# 配置模型使用特定的数据库后端
MyModel.configure(
    ConnectionConfig(
        host='localhost',
        port=3306,
        database='my_database',
        user='username',
        password='password'
    ),
    MySQLBackend
)
```

## 选择数据库

在为应用程序选择数据库时，请考虑以下因素：

1. **应用程序需求**：不同的数据库在不同类型的工作负载中表现出色
2. **可扩展性需求**：某些数据库更适合水平扩展
3. **功能需求**：特定功能如JSON支持、全文搜索或地理空间功能
4. **运维考虑**：备份、复制和高可用性选项
5. **团队专业知识**：对管理和优化的熟悉程度

## 数据库特定功能

虽然rhosocial ActiveRecord在所有支持的数据库中提供统一的API，但它也允许您在需要时利用数据库特定的功能。每个数据库后端都实现了核心ActiveRecord功能，同时还公开了底层数据库系统的独特功能。

请参阅特定数据库文档，了解有关以下内容的详细信息：

- 连接配置选项
- 支持的数据类型
- 事务隔离级别
- 性能优化技术
- 数据库特定的查询功能

## 多数据库支持

rhosocial ActiveRecord允许您同时使用多个数据库，甚至是不同类型的数据库。这对于需要集成来自各种来源的数据的应用程序，或者对于使用不同数据库用于应用程序不同部分的应用程序特别有用。

有关使用多个数据库的更多信息，请参阅[跨数据库查询](../5.2.cross_database_queries/README.md)部分。