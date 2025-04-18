# 后端配置

本节涵盖了rhosocial ActiveRecord支持的不同数据库后端的配置和使用。了解后端配置对于优化应用程序的数据库交互至关重要。

## 目录

- [支持的数据库](5.1.supported_databases/README.md) - 关于每个支持的数据库系统的详细信息
  - [MySQL](5.1.supported_databases/mysql.md)
  - [MariaDB](5.1.supported_databases/mariadb.md)
  - [PostgreSQL](5.1.supported_databases/postgresql.md)
  - [Oracle](5.1.supported_databases/oracle.md)
  - [SQL Server](5.1.supported_databases/sql_server.md)
  - [SQLite](5.1.supported_databases/sqlite.md)

- [跨数据库查询](5.2.cross_database_queries/README.md)
  - [跨数据库连接配置](5.2.cross_database_queries/connection_configuration.md)
  - [异构数据源集成](5.2.cross_database_queries/heterogeneous_data_source_integration.md)
  - [数据同步策略](5.2.cross_database_queries/data_synchronization_strategies.md)
  - [跨数据库事务处理](5.2.cross_database_queries/cross_database_transaction_handling.md)

- [数据库特定差异](5.3.database_specific_differences/README.md)
  - 数据类型映射
  - SQL方言差异
  - 性能考虑因素

- [自定义后端](5.4.custom_backends/README.md)
  - 实现自定义数据库后端
  - 扩展现有后端

## 介绍

rhosocial ActiveRecord设计为通过统一接口与多个数据库系统协同工作。这种架构允许您编写与数据库无关的代码，同时在需要时仍然可以利用每个数据库系统的特定功能。

后端配置决定了rhosocial ActiveRecord如何连接到您的数据库、管理连接、处理事务以及将ActiveRecord操作转换为数据库特定的SQL语句。

## 关键概念

### 连接配置

连接配置通过`ConnectionConfig`类管理，该类提供了一种一致的方式来指定连接参数，而不管数据库后端是什么。常见参数包括：

- 数据库名称、主机、端口
- 认证凭据
- 连接池设置
- 超时配置
- SSL/TLS选项

### 后端选择

您可以在配置模型时选择适合您的数据库系统的后端：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import ConnectionConfig
from rhosocial.activerecord.backend.impl.mysql import MySQLBackend

class User(ActiveRecord):
    pass

# 配置模型使用MySQL后端
User.configure(
    ConnectionConfig(database='my_database', user='username', password='password'),
    MySQLBackend
)
```

### 连接池

rhosocial ActiveRecord中的大多数数据库后端都支持连接池，这有助于高效管理数据库连接。连接池通过重用池中的现有连接来减少建立新连接的开销。

### 事务

rhosocial ActiveRecord在所有支持的数据库中提供一致的事务API，同时尊重每个数据库系统的特定事务能力和隔离级别。

请参阅本节中的特定数据库文档，了解有关每个数据库后端的配置选项、支持的功能和优化技术的详细信息。